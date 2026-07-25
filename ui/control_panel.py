import sys
import os
import logging
import webbrowser
from PyQt6.QtWidgets import (

    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QLineEdit, QFormLayout, QFrame, QComboBox, QTabWidget,
    QSlider, QSpinBox, QMessageBox, QRadioButton, QButtonGroup
)
from PyQt6.QtGui import QFont, QIcon, QColor
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

logger = logging.getLogger(__name__)

class QuizDialog(QDialog):
    """
    Kaydedilen kelimelerden rastgele alıştırma ve quiz yapma penceresi.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("arc - Kelime Alıştırması & Quiz")
        self.resize(500, 380)
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
        
        self.flashcard_mgr = FlashcardManager()
        self.questions = self.flashcard_mgr.get_quiz_questions(count=5)
        self.current_idx = 0
        self.score = 0
        
        self._setup_ui()

    def _setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        self.title_label = QLabel("🎯 Kelime Alıştırması (Quiz)", self)
        self.title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #38BDF8;")
        self.layout.addWidget(self.title_label)

        if not self.questions:
            no_data = QLabel("⚠️ Quiz yapmak için en az 2 kaydedilmiş kelimeniz olmalıdır.", self)
            no_data.setFont(QFont("Segoe UI", 11))
            self.layout.addWidget(no_data)
            return

        self.score_label = QLabel(f"Soru 1 / {len(self.questions)} | Puan: 0", self)
        self.score_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.score_label.setStyleSheet("color: #94A3B8;")
        self.layout.addWidget(self.score_label)

        self.word_label = QLabel("", self)
        self.word_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.word_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.word_label.setStyleSheet("color: #38BDF8; background: #1E293B; padding: 15px; border-radius: 10px;")
        self.layout.addWidget(self.word_label)

        self.opt_buttons = []
        for i in range(4):
            btn = QPushButton(f"Seçenek {i+1}", self)
            btn.clicked.connect(lambda checked, b=btn: self.check_answer(b))
            self.layout.addWidget(btn)
            self.opt_buttons.append(btn)

        self.load_question()

    def load_question(self):
        if self.current_idx >= len(self.questions):
            QMessageBox.information(self, "Quiz Tamamlandı!", f"Tebrikler! Quiz Bitti.\nToplam Puanınız: {self.score} / {len(self.questions)}")
            self.accept()
            return

        q = self.questions[self.current_idx]
        self.score_label.setText(f"Soru {self.current_idx + 1} / {len(self.questions)} | Puan: {self.score}")
        self.word_label.setText(f"🔤 '{q['english']}' ne demek?")

        for i, opt in enumerate(q["options"]):
            btn = self.opt_buttons[i]
            btn.setText(opt)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #1E293B; color: #F8FAFC;
                    border: 1px solid #334155; border-radius: 8px;
                    padding: 10px; font-weight: bold; font-size: 13px;
                }
                QPushButton:hover { background-color: #0284C7; color: white; }
            """)
            btn.setEnabled(True)

    def check_answer(self, btn: QPushButton):
        q = self.questions[self.current_idx]
        selected_text = btn.text()

        if selected_text == q["correct"]:
            self.score += 1
            btn.setStyleSheet("background-color: #166534; color: white; border: 1px solid #22C55E;")
        else:
            btn.setStyleSheet("background-color: #991B1B; color: white; border: 1px solid #EF4444;")

        for b in self.opt_buttons:
            b.setEnabled(False)

        self.current_idx += 1
        QTimer.singleShot(1000, self.load_question)


class ControlPanelWindow(QMainWindow):
    """
    arc Ana Masaüstü Kontrol Paneli (Gelişmiş Sekmeli Arayüz & Çoklu Monitör & Ayarlar).
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("arc")
        self.resize(920, 640)
        
        self.settings_mgr = SettingsManager()
        self.pipeline = None
        self.overlay = None
        self.is_translating = False
        self.region_selector = None
        self.temp_capture_engine = ScreenCaptureEngine()
        self.flashcard_mgr = FlashcardManager()

        self.hotkey_mgr = GlobalHotkeyManager(self)
        self.hotkey_mgr.toggle_requested.connect(self.toggle_translator)

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
        title_label = QLabel("arc", self)
        title_label.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #38BDF8;")
        
        subtitle_label = QLabel("Gerçek Zamanlı Ekran Çevirmeni & Oyun Dil Asistanı", self)
        subtitle_label.setFont(QFont("Segoe UI", 10))
        subtitle_label.setStyleSheet("color: #94A3B8; margin-left: 10px;")

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
        self.tabs.addTab(self.tab_cards, "📚 Kelime Defteri & Quiz")

        main_layout.addWidget(self.tabs)

        # Alt Bilgi Barı ve Sağ Alt Geliştirici & Kick Destek Butonu
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(5, 6, 5, 0)

        app_info_label = QLabel("arc v1.2.0 • Gerçek Zamanlı Ekran Çeviri & Oyun Asistanı", self)
        app_info_label.setFont(QFont("Segoe UI", 9))
        app_info_label.setStyleSheet("color: #64748B;")

        self.kick_btn = QPushButton("💚 Harun Öztürk tarafından geliştirildi — Desteklerinizi bekleriz (kick.com/harunozturk)", self)
        self.kick_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.kick_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #53FC18;
                border: 1.5px solid #22C55E;
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #15803D;
                color: #FFFFFF;
                border-color: #53FC18;
            }
        """)
        self.kick_btn.clicked.connect(lambda: webbrowser.open("https://kick.com/harunozturk"))

        footer_layout.addWidget(app_info_label)
        footer_layout.addStretch()
        footer_layout.addWidget(self.kick_btn)

        main_layout.addLayout(footer_layout)

    def _setup_live_tab(self, parent: QWidget):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        # Monitör Seçimi Barı
        mon_frame = QFrame(parent)
        mon_layout = QHBoxLayout(mon_frame)
        mon_layout.setContentsMargins(10, 8, 10, 8)

        mon_label = QLabel("💻 İzlenecek Ekran (Monitör):", parent)
        mon_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.monitor_combo = QComboBox(parent)
        self.monitor_combo.setFixedHeight(34)
        self.monitor_combo.currentIndexChanged.connect(self._on_monitor_changed)

        mon_layout.addWidget(mon_label)
        mon_layout.addWidget(self.monitor_combo, stretch=1)
        layout.addWidget(mon_frame)

        # Butonlar
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("▶ Çeviriyi Başlat (Ctrl+Shift+S)", parent)
        self.start_btn.setFixedHeight(42)
        self.start_btn.clicked.connect(self.toggle_translator)

        self.select_region_btn = QPushButton("🎯 Ekran Bölgesi Seç (Alt+R)", parent)
        self.select_region_btn.setFixedHeight(42)
        self.select_region_btn.clicked.connect(self.open_region_selector)

        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.select_region_btn)
        layout.addLayout(btn_layout)

        # Log Akış Konsolu
        log_frame = QFrame(parent)
        log_layout = QVBoxLayout(log_frame)
        log_title = QLabel("Canlı Çevrilen Kelimeler & Altyazı Akışı", parent)
        log_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        log_layout.addWidget(log_title)

        self.log_text = QTextEdit(parent)
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        log_layout.addWidget(self.log_text)

        layout.addWidget(log_frame, stretch=1)

    def _setup_settings_tab(self, parent: QWidget):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        # Font boyutu slider
        self.font_spin = QSpinBox(parent)
        self.font_spin.setRange(10, 32)
        self.font_spin.setValue(self.settings_mgr.get("font_size", 14))
        self.font_spin.valueChanged.connect(lambda v: self.settings_mgr.set("font_size", v))
        form_layout.addRow("🔤 Altyazı Yazı Boyutu (pt):", self.font_spin)

        # Oto gizlenme süresi
        self.hide_spin = QSpinBox(parent)
        self.hide_spin.setRange(2, 20)
        self.hide_spin.setValue(int(self.settings_mgr.get("auto_hide_seconds", 6)))
        self.hide_spin.valueChanged.connect(lambda v: self.settings_mgr.set("auto_hide_seconds", float(v)))
        form_layout.addRow("⏱️ Oto Gizlenme Süresi (Saniye):", self.hide_spin)

        # Kart Renk / Tema Seçenekleri
        self.theme_combo = QComboBox(parent)
        self.theme_combo.addItems(["Koyu Mavi & Sarı Metin (Varsayılan)", "Derin Siyah Transparan", "Neon Cyan Accent"])
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        form_layout.addRow("🎨 Altyazı Kart Teması:", self.theme_combo)

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
        form_layout.addRow("📌 Altyazı Ekran Konumu:", self.pos_mode_combo)

        # Target Language
        self.lang_combo = QComboBox(parent)

        self.lang_combo.addItems(["Türkçe (TR)", "İngilizce (EN)", "Almanca (DE)", "Fransızca (FR)"])
        form_layout.addRow("🌐 Hedef Çeviri Dili:", self.lang_combo)

        layout.addLayout(form_layout)

        save_btn = QPushButton("💾 Ayarları Kaydet & Uygula", parent)
        save_btn.setFixedHeight(40)
        save_btn.clicked.connect(self.save_and_apply_settings)
        layout.addWidget(save_btn)
        layout.addStretch()

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
            QMainWindow, QTabWidget::pane { background-color: #0F172A; }
            QTabBar::tab {
                background-color: #1E293B; color: #94A3B8;
                padding: 10px 18px; font-weight: bold; border-top-left-radius: 8px; border-top-right-radius: 8px;
            }
            QTabBar::tab:selected { background-color: #0284C7; color: white; }
            QFrame { background-color: #1E293B; border: 1px solid #334155; border-radius: 8px; }
            QPushButton {
                background-color: #0284C7; color: white; border-radius: 6px;
                padding: 8px 16px; font-weight: bold; border: none;
            }
            QPushButton:hover { background-color: #0369A1; }
            QComboBox, QSpinBox, QLineEdit {
                background-color: #0F172A; color: #38BDF8; border: 1px solid #38BDF8;
                border-radius: 6px; padding: 6px 10px;
            }
            QTextEdit, QTableWidget {
                background-color: #0F172A; color: #38BDF8; border: 1px solid #334155; border-radius: 6px;
            }
            QHeaderView::section { background-color: #334155; color: #38BDF8; font-weight: bold; padding: 6px; }
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

