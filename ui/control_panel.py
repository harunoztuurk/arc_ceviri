import sys
import os
import logging
import webbrowser
from PyQt6.QtWidgets import (

    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QLineEdit, QFormLayout, QFrame, QComboBox, QTabWidget,
    QSlider, QSpinBox, QMessageBox, QRadioButton, QButtonGroup, QCheckBox
)
from PyQt6.QtGui import QFont, QIcon, QColor, QCursor
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize

from config import Config
from capture.engine import ScreenCaptureEngine
from ocr.reader import OCRReader
from translator.llm_client import LLMTranslator
from learning.flashcards import FlashcardManager
from ui.overlay import TranslationOverlayWindow
from ui.region_selector import RegionSelectorWidget
from pipeline.async_worker import AsyncPipelineController
from settings_manager import SettingsManager
from hotkey_manager import GlobalHotkeyManager

from PyQt6.QtSvgWidgets import QSvgWidget
from ui.splash import get_logo_path

logger = logging.getLogger(__name__)

class QuizDialog(QDialog):
    """
    Kaydedilen kelimelerden rastgele alıştırma ve quiz yapma penceresi.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎯 Kelime Alıştırma & Quiz Modu")
        self.resize(480, 360)
        self.flashcard_mgr = FlashcardManager()
        self.cards = self.flashcard_mgr.get_cards()
        self.current_card = None
        
        logo_path = get_logo_path()
        if logo_path and os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))
            
        self._setup_ui()
        self.next_question()

    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog { background-color: #0F172A; color: #F8FAFC; }
            QLabel { color: #F8FAFC; }
            QPushButton {
                background-color: #1E293B; color: #38BDF8;
                border: 1px solid #38BDF8; border-radius: 8px;
                padding: 10px; font-weight: bold; font-size: 13px;
            }
            QPushButton:hover { background-color: #0284C7; color: white; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        self.title_label = QLabel("🎯 Kelime Bilgi Yarışması", self)
        self.title_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("color: #38BDF8;")
        layout.addWidget(self.title_label)

        self.score_label = QLabel("Doğru: 0 | Yanlış: 0", self)
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.score_label.setFont(QFont("Segoe UI", 10))
        self.score_label.setStyleSheet("color: #94A3B8;")
        layout.addWidget(self.score_label)

        layout.addSpacing(10)

        self.word_label = QLabel("Kelime Hazırlanıyor...", self)
        self.word_label.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self.word_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.word_label.setStyleSheet("color: #38BDF8; background: #1E293B; padding: 15px; border-radius: 10px;")
        layout.addWidget(self.word_label)

        layout.addSpacing(15)

        # 4 Şıklı Seçenek Butonları
        self.option_btns = []
        for i in range(4):
            btn = QPushButton(f"Seçenek {i+1}", self)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, b=btn: self.check_answer(b))
            layout.addWidget(btn)
            self.option_btns.append(btn)

        self.correct_count = 0
        self.wrong_count = 0

    def next_question(self):
        if not self.cards:
            self.word_label.setText("Sözlükte kelime bulunamadı.")
            for btn in self.option_btns:
                btn.setEnabled(False)
            return

        import random
        self.current_card = random.choice(self.cards)
        self.word_label.setText(self.current_card["english"])

        # Seçenekleri oluştur
        wrong_cards = [c for c in self.cards if c["id"] != self.current_card["id"]]
        random.shuffle(wrong_cards)
        
        options = [self.current_card["turkish"]]
        for c in wrong_cards[:3]:
            options.append(c["turkish"])
            
        while len(options) < 4:
            options.append(f"Çeviri-{len(options)+1}")

        random.shuffle(options)

        for i, btn in enumerate(self.option_btns):
            btn.setText(options[i])
            btn.setEnabled(True)
            btn.setStyleSheet("")  # Reset style

    def check_answer(self, btn: QPushButton):
        if not self.current_card:
            return

        user_ans = btn.text()
        correct_ans = self.current_card["turkish"]

        if user_ans == correct_ans:
            self.correct_count += 1
            btn.setStyleSheet("background-color: #166534; color: white; border: 1px solid #22C55E;")
        else:
            self.wrong_count += 1
            btn.setStyleSheet("background-color: #991B1B; color: white; border: 1px solid #EF4444;")

        self.score_label.setText(f"Doğru: {self.correct_count} | Yanlış: {self.wrong_count}")

        for b in self.option_btns:
            b.setEnabled(False)

        QTimer.singleShot(1200, self.next_question)


class ControlPanelWindow(QMainWindow):
    """
    Ana arc Masaüstü Kontrol Paneli ve Arayüzü.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("arc - Gerçek Zamanlı Ekran Çevirmeni")
        self.resize(920, 640)
        
        logo_path = get_logo_path()
        if logo_path and os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))
        
        self.settings_mgr = SettingsManager()
        self.pipeline = None
        self.overlay = None
        self.is_translating = False
        self.region_selector = None
        self.temp_capture_engine = ScreenCaptureEngine()
        self.temp_ocr_reader = OCRReader()
        self.temp_llm_translator = LLMTranslator()
        self.flashcard_mgr = FlashcardManager()

        self.hotkey_mgr = GlobalHotkeyManager(self)
        self.hotkey_mgr.toggle_requested.connect(self.toggle_translator)
        self.hotkey_mgr.macro_translate_requested.connect(self.on_mouse_macro_translate)

        self._setup_ui()
        self._apply_stylesheet()
        self._load_monitors()

    def _setup_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Üst Başlık Bölümü
        header_layout = QHBoxLayout()
        
        # SVG Logo container badge
        logo_path = get_logo_path()
        if logo_path and os.path.exists(logo_path):
            logo_frame = QFrame(self)
            logo_frame.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1E293B, stop:1 #0F172A);
                    border: 2px solid #38BDF8;
                    border-radius: 12px;
                }
            """)
            logo_layout = QVBoxLayout(logo_frame)
            logo_layout.setContentsMargins(4, 4, 4, 4)
            logo_widget = QSvgWidget(logo_path, logo_frame)
            logo_widget.setFixedSize(44, 44)
            logo_layout.addWidget(logo_widget)
            header_layout.addWidget(logo_frame)
        
        title_label = QLabel("arc", self)
        title_label.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #38BDF8;")
        
        subtitle_label = QLabel("Gerçek Zamanlı Ekran Çevirmeni & Oyun Dil Asistanı", self)
        subtitle_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        subtitle_label.setStyleSheet("color: #E2E8F0; margin-left: 10px;")

        self.status_badge = QLabel("● Çeviri Durduruldu", self)
        self.status_badge.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.status_badge.setStyleSheet("color: #EF4444; background: #331C1C; padding: 6px 14px; border-radius: 12px;")

        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        header_layout.addStretch()
        header_layout.addWidget(self.status_badge)
        main_layout.addLayout(header_layout)

        # Sekme (Tab) Arayüzü
        self.tabs = QTabWidget(self)
        
        # 1. SEKME: CANLI ÇEVİRİ
        self.tab_live = QWidget()
        self._setup_live_tab(self.tab_live)
        self.tabs.addTab(self.tab_live, "📺 Canlı Çeviri")

        # 2. SEKME: GÖRÜNÜM & AYARLAR
        self.tab_settings = QWidget()
        self._setup_settings_tab(self.tab_settings)
        self.tabs.addTab(self.tab_settings, "⚙️ Görünüm & Ayarlar")

        # 3. SEKME: OYUN TERİM SÖZLÜĞÜ
        self.tab_glossary = QWidget()
        self._setup_glossary_tab(self.tab_glossary)
        self.tabs.addTab(self.tab_glossary, "📖 Oyun Terim Sözlüğü")

        # 4. SEKME: KELİME KARTLARI & QUIZ
        self.tab_cards = QWidget()
        self._setup_cards_tab(self.tab_cards)
        self.tabs.addTab(self.tab_cards, "📗 Kelime Defteri & Quiz")

        main_layout.addWidget(self.tabs)

        # Bottom Info Bar
        footer_layout = QHBoxLayout()
        app_info_label = QLabel("v2.5 | ⚡ Ultra Düşük Gecikme (100ms) | GPU & CPU Hızlandırma", self)
        app_info_label.setFont(QFont("Segoe UI", 9))
        app_info_label.setStyleSheet("color: #94A3B8;")
        footer_layout.addWidget(app_info_label)
        footer_layout.addStretch()

        macro_btn = QPushButton("🔤 Fare Altında Çeviri Yap (Alt+T)", self)
        macro_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        macro_btn.clicked.connect(self.on_mouse_macro_translate)
        footer_layout.addWidget(macro_btn)

        main_layout.addLayout(footer_layout)

    def _setup_live_tab(self, parent: QWidget):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # Monitör Seçim Satırı
        mon_layout = QHBoxLayout()
        mon_label = QLabel("💻 İzlenecek Ekran (Monitör):", parent)
        mon_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        mon_label.setStyleSheet("color: #F8FAFC;")
        
        self.monitor_combo = QComboBox(parent)
        self.monitor_combo.setFixedHeight(38)
        self.monitor_combo.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.monitor_combo.currentIndexChanged.connect(self._on_monitor_changed)

        mon_layout.addWidget(mon_label)
        mon_layout.addWidget(self.monitor_combo, stretch=1)
        layout.addLayout(mon_layout)

        # Kontrol Butonları Satırı
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.start_btn = QPushButton("▶ Çeviriyi Başlat (Ctrl+Shift+S)", parent)
        self.start_btn.setFixedHeight(45)
        self.start_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.clicked.connect(self.toggle_translator)

        self.region_btn = QPushButton("🎯 Ekran Bölgesi Seç (Alt+R)", parent)
        self.region_btn.setFixedHeight(45)
        self.region_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.region_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.region_btn.clicked.connect(self.open_region_selector)

        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.region_btn)
        layout.addLayout(btn_layout)

        # Canlı Çeviri Akış Kutusu
        log_group = QFrame(parent)
        log_group_layout = QVBoxLayout(log_group)
        log_group_layout.setContentsMargins(10, 10, 10, 10)

        log_title = QLabel("Canlı Çevrilen Kelimeler & Altyazı Akışı", log_group)
        log_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        log_title.setStyleSheet("color: #38BDF8;")
        log_group_layout.addWidget(log_title)

        self.log_text = QTextEdit(log_group)
        self.log_text.setReadOnly(True)
        log_group_layout.addWidget(self.log_text)

        layout.addWidget(log_group)

    def _setup_settings_tab(self, parent: QWidget):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        form_layout = QFormLayout()
        form_layout.setSpacing(15)

        # Font Ailesi
        self.font_family_combo = QComboBox(parent)
        self.font_family_combo.addItems(["Segoe UI", "Arial", "Consolas", "Roboto", "Montserrat", "Trebuchet MS"])
        self.font_family_combo.setCurrentText(self.settings_mgr.get("font_family", "Segoe UI"))
        self.font_family_combo.currentTextChanged.connect(lambda v: self.settings_mgr.set("font_family", v))
        
        lbl_font = QLabel("🔤 Altyazı Font Ailesi:", parent)
        lbl_font.setStyleSheet("color: #F8FAFC; font-weight: bold;")
        form_layout.addRow(lbl_font, self.font_family_combo)

        # Font Boyutu
        self.font_spin = QSpinBox(parent)
        self.font_spin.setRange(10, 32)
        self.font_spin.setValue(self.settings_mgr.get("font_size", 16))
        self.font_spin.valueChanged.connect(lambda v: self.settings_mgr.set("font_size", v))
        
        lbl_size = QLabel("🔤 Altyazı Yazı Boyutu (pt):", parent)
        lbl_size.setStyleSheet("color: #F8FAFC; font-weight: bold;")
        form_layout.addRow(lbl_size, self.font_spin)

        # Oto gizlenme süresi
        self.hide_spin = QSpinBox(parent)
        self.hide_spin.setRange(2, 20)
        self.hide_spin.setValue(int(self.settings_mgr.get("auto_hide_seconds", 6)))
        self.hide_spin.valueChanged.connect(lambda v: self.settings_mgr.set("auto_hide_seconds", float(v)))
        
        lbl_hide = QLabel("⏱️ Oto Gizlenme Süresi (Saniye):", parent)
        lbl_hide.setStyleSheet("color: #F8FAFC; font-weight: bold;")
        form_layout.addRow(lbl_hide, self.hide_spin)

        # Kart Renk / Tema Seçenekleri
        self.theme_combo = QComboBox(parent)
        self.theme_combo.addItems(["Koyu Mavi & Sarı Metin (Varsayılan)", "Derin Siyah Transparan", "Neon Cyan Accent"])
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        
        lbl_theme = QLabel("🎨 Altyazı Kart Teması:", parent)
        lbl_theme.setStyleSheet("color: #F8FAFC; font-weight: bold;")
        form_layout.addRow(lbl_theme, self.theme_combo)

        # Altyazı Konum Modu
        self.pos_mode_combo = QComboBox(parent)
        self.pos_mode_combo.addItem("📺 Ekranın En Alt Ortasında (Film Altyazısı Modu)", "bottom_center")
        self.pos_mode_combo.addItem("🎯 Kelimenin Tam Üstünde/Altında (Orijinal Konum)", "relative")
        
        curr_mode = self.settings_mgr.get("subtitle_position_mode", "bottom_center")
        if curr_mode == "relative":
            self.pos_mode_combo.setCurrentIndex(1)
        else:
            self.pos_mode_combo.setCurrentIndex(0)
            
        self.pos_mode_combo.currentIndexChanged.connect(
            lambda: self.settings_mgr.set("subtitle_position_mode", self.pos_mode_combo.currentData())
        )
        
        lbl_pos = QLabel("📌 Altyazı Ekran Konumu:", parent)
        lbl_pos.setStyleSheet("color: #F8FAFC; font-weight: bold;")
        form_layout.addRow(lbl_pos, self.pos_mode_combo)

        # Target Language
        self.lang_combo = QComboBox(parent)
        self.lang_combo.addItems(["Türkçe (TR)", "İngilizce (EN)", "Almanca (DE)", "Fransızca (FR)"])
        
        lbl_lang = QLabel("🌐 Hedef Çeviri Dili:", parent)
        lbl_lang.setStyleSheet("color: #F8FAFC; font-weight: bold;")
        form_layout.addRow(lbl_lang, self.lang_combo)

        # Metin Değişmedikçe Çeviriyi Sabit Tut (CheckBox)
        self.keep_static_chk = QCheckBox("Metin Değişmedikçe Çeviriyi Ekranda Sabit Tut (Oyun/Metin Durduğunda Gizleme)", parent)
        self.keep_static_chk.setChecked(bool(self.settings_mgr.get("keep_static_subtitles", True)))
        self.keep_static_chk.setStyleSheet("color: #38BDF8; font-weight: bold; font-size: 13px;")
        self.keep_static_chk.stateChanged.connect(
            lambda state: self.settings_mgr.set("keep_static_subtitles", state == 2)
        )
        form_layout.addRow("📌 Metin Sabitleme:", self.keep_static_chk)

        # Çift Yapay Zeka (Dual-LLM & Meta NLLB-200) CheckBox
        self.dual_llm_chk = QCheckBox("Çift Yapay Zeka Pası (Meta NLLB-200 ile Devrik Cümleleri Düzelt)", parent)
        self.dual_llm_chk.setChecked(bool(self.settings_mgr.get("enable_dual_llm", True)))
        self.dual_llm_chk.setStyleSheet("color: #38BDF8; font-weight: bold; font-size: 13px;")
        self.dual_llm_chk.stateChanged.connect(
            lambda state: self.settings_mgr.set("enable_dual_llm", state == 2)
        )
        form_layout.addRow("🤖 Çift LLM Editör:", self.dual_llm_chk)

        layout.addLayout(form_layout)

        save_btn = QPushButton("💾 Ayarları Kaydet ve Uygula", parent)
        save_btn.setFixedHeight(40)
        save_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self.save_and_apply_settings)
        layout.addWidget(save_btn)

    def _setup_glossary_tab(self, parent: QWidget):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        add_layout = QHBoxLayout()
        self.term_in = QLineEdit(parent)
        self.term_in.setPlaceholderText("İngilizce Terim (Örn: HP, Vault)...")
        self.trans_in = QLineEdit(parent)
        self.trans_in.setPlaceholderText("Türkçe Karşılığı (Örn: Can Puanı)...")
        
        add_btn = QPushButton("➕ Terim Ekle", parent)
        add_btn.clicked.connect(self.add_glossary_term)

        add_layout.addWidget(self.term_in)
        add_layout.addWidget(self.trans_in)
        add_layout.addWidget(add_btn)
        layout.addLayout(add_layout)

        self.glossary_table = QTableWidget(parent)
        self.glossary_table.setColumnCount(2)
        self.glossary_table.setHorizontalHeaderLabels(["Oyun Terimi (İngilizce)", "Özel Çevirisi (Türkçe)"])
        self.glossary_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.glossary_table)

        del_btn = QPushButton("🗑️ Seçili Terimi Sil", parent)
        del_btn.clicked.connect(self.delete_glossary_term)
        layout.addWidget(del_btn)

        self.load_glossary_table()

    def _setup_cards_tab(self, parent: QWidget):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        action_bar = QHBoxLayout()
        quiz_btn = QPushButton("🎯 Quiz & Alıştırma Yap", parent)
        quiz_btn.setFixedHeight(38)
        quiz_btn.clicked.connect(self.open_quiz_dialog)

        tts_btn = QPushButton("🔊 Seçileni Dinle (TTS)", parent)
        tts_btn.setFixedHeight(38)
        tts_btn.clicked.connect(self.play_selected_tts)

        export_anki = QPushButton("📑 Anki (.CSV) Aktar", parent)
        export_anki.setFixedHeight(38)
        export_anki.clicked.connect(self.export_anki)

        action_bar.addWidget(quiz_btn)
        action_bar.addWidget(tts_btn)
        action_bar.addWidget(export_anki)
        layout.addLayout(action_bar)

        self.cards_table = QTableWidget(parent)
        self.cards_table.setColumnCount(3)
        self.cards_table.setHorizontalHeaderLabels(["İngilizce Metin", "Türkçe Çevirisi", "Kayıt Tarihi"])
        self.cards_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.cards_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.cards_table)

        self.load_cards_table()

    def _apply_stylesheet(self):
        self.setStyleSheet("""
            QMainWindow, QTabWidget::pane { 
                background-color: #0B1120; 
            }
            QLabel {
                color: #F1F5F9;
                font-size: 13px;
            }
            QTabBar::tab {
                background-color: #1E293B; 
                color: #CBD5E1;
                padding: 10px 20px; 
                font-weight: bold; 
                font-size: 13px;
                border-top-left-radius: 8px; 
                border-top-right-radius: 8px;
                border: 1px solid #334155;
                margin-right: 4px;
            }
            QTabBar::tab:hover {
                background-color: #334155;
                color: #FFFFFF;
            }
            QTabBar::tab:selected { 
                background-color: #0284C7; 
                color: #FFFFFF; 
                border: 1px solid #38BDF8;
            }
            QFrame { 
                background-color: #1E293B; 
                border: 1.5px solid #334155; 
                border-radius: 10px; 
            }
            QPushButton {
                background-color: #0284C7; 
                color: #FFFFFF; 
                border-radius: 8px;
                padding: 9px 18px; 
                font-weight: bold; 
                font-size: 13px;
                border: none;
            }
            QPushButton:hover { 
                background-color: #0369A1; 
                color: #FFFFFF;
            }
            QComboBox, QSpinBox, QLineEdit {
                background-color: #1E293B; 
                color: #F8FAFC; 
                border: 1.5px solid #0EA5E9;
                border-radius: 8px; 
                padding: 8px 12px;
                font-size: 13px;
                font-weight: bold;
            }
            QComboBox:hover, QSpinBox:hover, QLineEdit:hover {
                border-color: #38BDF8;
            }
            QComboBox QAbstractItemView {
                background-color: #0F172A;
                color: #F8FAFC;
                selection-background-color: #0284C7;
                selection-color: #FFFFFF;
                border: 1.5px solid #38BDF8;
                border-radius: 8px;
                padding: 6px;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                min-height: 32px;
                color: #F8FAFC;
                padding-left: 10px;
                font-weight: bold;
                font-size: 13px;
            }
            QComboBox QAbstractItemView::item:hover, QComboBox QAbstractItemView::item:selected {
                background-color: #0284C7;
                color: #FFFFFF;
            }
            QTextEdit {
                background-color: #0B132B; 
                color: #38BDF8; 
                border: 1.5px solid #334155; 
                border-radius: 8px;
                font-family: Consolas, 'Segoe UI', monospace;
                font-size: 13px;
                font-weight: 600;
                padding: 8px;
            }
            QTableWidget {
                background-color: #0F172A; 
                color: #F8FAFC; 
                border: 1.5px solid #334155; 
                border-radius: 8px;
                gridline-color: #334155;
            }
            QTableWidget::item {
                color: #F8FAFC;
                padding: 6px;
                font-size: 13px;
            }
            QTableWidget::item:selected {
                background-color: #0284C7;
                color: #FFFFFF;
            }
            QHeaderView::section { 
                background-color: #1E293B; 
                color: #38BDF8; 
                font-weight: bold; 
                font-size: 13px;
                padding: 8px; 
                border: 1px solid #334155;
            }
        """)

    def _load_monitors(self):
        monitors = self.temp_capture_engine.get_available_monitors()
        self.monitor_combo.clear()
        for mon in monitors:
            self.monitor_combo.addItem(mon["label"], mon["index"])
            
        if len(monitors) > 1:
            self.monitor_combo.setCurrentIndex(1)
            self.append_log(f"💻 Sistemde {len(monitors)-1} adet monitör tespit edildi.")
        else:
            self.append_log("💻 Ana Monitör algılandı.")

    def _on_monitor_changed(self, index: int):
        monitor_idx = self.monitor_combo.currentData()
        if monitor_idx is not None:
            if self.pipeline:
                self.pipeline.capture_engine.set_monitor_index(monitor_idx)
            if self.overlay:
                self.overlay.set_target_monitor_index(monitor_idx)
            self.append_log(f"💻 İzleme Hedefi Değiştirildi: {self.monitor_combo.currentText()}")

    def _on_theme_changed(self, index: int):
        if index == 0:
            self.settings_mgr.set("card_bg_color", "rgba(15, 23, 42, 0.90)")
            self.settings_mgr.set("border_color", "#38BDF8")
        elif index == 1:
            self.settings_mgr.set("card_bg_color", "rgba(0, 0, 0, 0.95)")
            self.settings_mgr.set("border_color", "#475569")
        elif index == 2:
            self.settings_mgr.set("card_bg_color", "rgba(6, 182, 212, 0.20)")
            self.settings_mgr.set("border_color", "#06B6D4")

    def save_and_apply_settings(self):
        if self.overlay:
            self.overlay.apply_settings()
        QMessageBox.information(self, "Başarılı", "Görünüm ve altyazı ayarları kaydedildi ve uygulandı!")

    def toggle_translator(self):
        if self.is_translating:
            # Pause translation without closing windows or killing threads
            self.is_translating = False
            if self.pipeline:
                self.pipeline.pause_pipeline()
            if self.overlay:
                self.overlay.clear_translations()
                self.overlay.hide()

            self.start_btn.setText("▶ Çeviriyi Başlat (Ctrl+Shift+S)")
            self.start_btn.setStyleSheet("background-color: #0284C7;")
            self.status_badge.setText("● Çeviri Durduruldu")
            self.status_badge.setStyleSheet("color: #EF4444; background: #331C1C; padding: 6px 14px; border-radius: 12px;")
            self.append_log(">>> arc Çevirici Durduruldu.")
        else:
            # Start / Resume translation
            self.is_translating = True
            selected_mon = self.monitor_combo.currentData() or 1

            if self.overlay is None:
                self.overlay = TranslationOverlayWindow(target_monitor_index=selected_mon)
            else:
                self.overlay.set_target_monitor_index(selected_mon)

            self.overlay.show()

            if self.pipeline is None:
                self.pipeline = AsyncPipelineController()
                self.pipeline.translations_updated.connect(self._on_translations_received)

            if selected_mon is not None:
                self.pipeline.capture_engine.set_monitor_index(selected_mon)
            if Config.CAPTURE_REGION:
                self.pipeline.capture_engine.region = Config.CAPTURE_REGION

            self.pipeline.resume_pipeline()

            self.start_btn.setText("⏸ Çeviriyi Durdur (Ctrl+Shift+S)")
            self.start_btn.setStyleSheet("background-color: #DC2626;")
            self.status_badge.setText("● Canlı İzleme Aktif")
            self.status_badge.setStyleSheet("color: #22C55E; background: #1C3322; padding: 6px 14px; border-radius: 12px;")
            self.append_log(">>> arc Ekran Çevirisi Başlatıldı.")

    def open_region_selector(self):
        selected_mon = self.monitor_combo.currentData()
        mon_idx = (selected_mon - 1) if (selected_mon is not None and selected_mon > 0) else None
        
        self.region_selector = RegionSelectorWidget(monitor_index=mon_idx)
        self.region_selector.region_selected.connect(self._on_region_selected)
        self.region_selector.show()

    def _on_region_selected(self, region: dict):
        Config.CAPTURE_REGION = region
        if self.pipeline:
            self.pipeline.capture_engine.region = region
        self.append_log(f"🎯 İzleme Bölgesi Güncellendi: {region['width']}x{region['height']} (Sol:{region['left']}, Üst:{region['top']})")

    def _on_translations_received(self, results: list):
        if self.overlay:
            self.overlay.update_translations(results)

        for item in results:
            orig = item.get("orig", "")
            trans = item.get("trans", "")
            if orig and trans:
                self.append_log(
                    f"\n{'─'*42}\n"
                    f"🔤  {orig}\n"
                    f"🇹🇷  {trans}\n"
                    f"{'─'*42}"
                )
                self.flashcard_mgr.add_card(english=orig, turkish=trans, context="Ekran Çevirisi")
                self.load_cards_table()

    def load_glossary_table(self):
        glossary = self.settings_mgr.get_glossary()
        self.glossary_table.setRowCount(len(glossary))
        for row, (k, v) in enumerate(glossary.items()):
            self.glossary_table.setItem(row, 0, QTableWidgetItem(k))
            self.glossary_table.setItem(row, 1, QTableWidgetItem(v))

    def add_glossary_term(self):
        term = self.term_in.text().strip()
        trans = self.trans_in.text().strip()
        if term and trans:
            self.settings_mgr.add_glossary_term(term, trans)
            self.term_in.clear()
            self.trans_in.clear()
            self.load_glossary_table()

    def delete_glossary_term(self):
        row = self.glossary_table.currentRow()
        if row >= 0:
            term = self.glossary_table.item(row, 0).text()
            self.settings_mgr.remove_glossary_term(term)
            self.load_glossary_table()

    def load_cards_table(self):
        cards = self.flashcard_mgr.get_all_cards()
        self.cards_table.setRowCount(len(cards))
        for row, card in enumerate(cards):
            self.cards_table.setItem(row, 0, QTableWidgetItem(card["english"]))
            self.cards_table.setItem(row, 1, QTableWidgetItem(card["turkish"]))
            self.cards_table.setItem(row, 2, QTableWidgetItem(str(card.get("created_at", ""))))

    def open_quiz_dialog(self):
        dialog = QuizDialog(self)
        dialog.exec()

    def on_mouse_macro_translate(self):
        """
        Triggered globally when Alt+T is pressed.
        Captures screen area around mouse cursor (or screen center if locked in game),
        runs OCR, translates the word/sentence under the virtual cursor,
        and renders a virtual mouse pointer & floating translation tooltip.
        """
        try:
            selected_mon = self.monitor_combo.currentData() or 1
            if self.overlay is None:
                self.overlay = TranslationOverlayWindow(target_monitor_index=selected_mon)
            else:
                self.overlay.set_target_monitor_index(selected_mon)

            target_geo = self.overlay.get_target_screen_geometry()
            pos = QCursor.pos()
            mx, my = pos.x(), pos.y()

            # If cursor is locked, hidden, or out of bounds in 3D game, default to center of active monitor
            if mx < target_geo.x() or mx > target_geo.x() + target_geo.width() or \
               my < target_geo.y() or my > target_geo.y() + target_geo.height() or \
               (mx == 0 and my == 0):
                mx = target_geo.x() + target_geo.width() // 2
                my = target_geo.y() + target_geo.height() // 2

            box_w, box_h = 480, 220
            left = max(target_geo.x(), mx - box_w // 2)
            top = max(target_geo.y(), my - box_h // 2)

            bbox = (left, top, left + box_w, top + box_h)
            from PIL import ImageGrab
            import numpy as np
            import cv2

            pil_img = ImageGrab.grab(bbox=bbox, all_screens=True)
            frame_rgb = np.array(pil_img)
            frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

            raw_blocks = self.temp_ocr_reader.extract_text(frame_bgr)
            if not raw_blocks:
                self.append_log(f"⚠️ Fare/Sanal imleç konumunda ({mx}, {my}) okunabilir metin bulunamadı.")
                return

            cx, cy = box_w // 2, box_h // 2
            best_block = None
            min_dist = float('inf')

            for b in raw_blocks:
                rx, ry, rw, rh = b["rect"]
                bcx = rx + rw / 2
                bcy = ry + rh / 2
                dist = ((bcx - cx)**2 + (bcy - cy)**2)**0.5
                if dist < min_dist:
                    min_dist = dist
                    best_block = b

            if not best_block:
                return

            orig_text = best_block["text"].strip()
            if not orig_text or len(orig_text) < 2:
                return

            trans_text = self.temp_llm_translator.translate(orig_text)

            self.overlay.show_mouse_tooltip(orig_text, trans_text, mx, my)
            self.flashcard_mgr.add_card(english=orig_text, turkish=trans_text, context="Sanal Fare Makro Çeviri")
            self.append_log(f"🎯 Sanal Fare Çeviri (Alt+T): '{orig_text}' ➔ '{trans_text}'")
            self.load_cards_table()
        except Exception as e:
            logger.error(f"Error in on_mouse_macro_translate: {e}")

    def play_selected_tts(self):
        row = self.cards_table.currentRow()
        if row >= 0:
            text = self.cards_table.item(row, 0).text()
            self.flashcard_mgr.speak_text(text)
        else:
            QMessageBox.information(self, "Bilgi", "Lütfen seslendirilecek kelimeyi tablodan seçin.")

    def export_anki(self):
        self.flashcard_mgr.export_to_anki_csv("anki_cards.csv")
        QMessageBox.information(self, "Başarılı", "Kelimeler Anki uyumlu 'anki_cards.csv' dosyası olarak aktarıldı!")

    def append_log(self, text: str):
        self.log_text.append(text)
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def closeEvent(self, event):
        if self.pipeline:
            self.pipeline.stop()
        if self.overlay:
            self.overlay.close()
        self.hotkey_mgr.stop()
        self.temp_capture_engine.close()
        event.accept()

