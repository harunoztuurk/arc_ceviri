import os
import sys
import logging
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, 
    QApplication, QGraphicsDropShadowEffect, QFrame, QPushButton
)
from PyQt6.QtGui import QFont, QColor, QIcon
from PyQt6.QtSvgWidgets import QSvgWidget

from translator.llm_client import LLMTranslator

logger = logging.getLogger(__name__)

LOGO_FILENAME = "harunozturk (1280 x 700 piksel) (Logo).svg"

def get_logo_path() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    light_path = os.path.join(base_dir, "logo_light.svg")
    if os.path.exists(light_path):
        return light_path
    if os.path.exists("logo_light.svg"):
        return "logo_light.svg"
    orig_path = os.path.join(base_dir, LOGO_FILENAME)
    if os.path.exists(orig_path):
        return orig_path
    if os.path.exists(LOGO_FILENAME):
        return LOGO_FILENAME
    return ""

class ConnectionCheckWorker(QThread):
    result_signal = pyqtSignal(bool, str)

    def run(self):
        try:
            translator = LLMTranslator()
            success, msg = translator.check_connection()
            self.result_signal.emit(success, msg)
        except Exception as e:
            self.result_signal.emit(False, f"Bağlantı Kontrol Hatası: {e}")

class ArcSplashScreen(QWidget):
    """
    Spacious, modern dark glassmorphism Splash Screen.
    Renders large SVG logo, glowing titles, LLM connection check, and interactive error/retry controls.
    """
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SplashScreen
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # Widescreen 16:9 Aspect Ratio (800 x 450)
        self.setFixedSize(800, 450)
        self.center_on_screen()

        # Main Card container (16:9 Cinema Card)
        self.container = QWidget(self)
        self.container.setObjectName("SplashCard")
        self.container.setGeometry(10, 10, 780, 430)
        self.container.setStyleSheet("""
            QWidget#SplashCard {
                background-color: #0F172A;
                border: 2px solid #0EA5E9;
                border-radius: 24px;
            }
        """)

        # Glow Drop Shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(14, 165, 233, 120))
        shadow.setOffset(0, 6)
        self.container.setGraphicsEffect(shadow)

        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(40, 20, 40, 20)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # SVG Logo Container Frame (Square 1:1 ratio matching original SVG 375x375 shape)
        logo_path = get_logo_path()
        if logo_path and os.path.exists(logo_path):
            self.logo_frame = QFrame(self.container)
            self.logo_frame.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1E293B, stop:1 #0F172A);
                    border: 2px solid #38BDF8;
                    border-radius: 24px;
                }
            """)
            frame_layout = QVBoxLayout(self.logo_frame)
            frame_layout.setContentsMargins(10, 10, 10, 10)
            self.logo_widget = QSvgWidget(logo_path, self.logo_frame)
            self.logo_widget.setFixedSize(190, 190)
            frame_layout.addWidget(self.logo_widget, alignment=Qt.AlignmentFlag.AlignCenter)
            self.layout.addWidget(self.logo_frame, alignment=Qt.AlignmentFlag.AlignCenter)
        else:
            self.title_fallback = QLabel("arc", self.container)
            self.title_fallback.setFont(QFont("Segoe UI", 42, QFont.Weight.Bold))
            self.title_fallback.setStyleSheet("color: #38BDF8;")
            self.layout.addWidget(self.title_fallback, alignment=Qt.AlignmentFlag.AlignCenter)

        self.layout.addSpacing(6)

        # App Title & Subtitle
        title_label = QLabel("arc", self.container)
        title_label.setFont(QFont("Segoe UI", 26, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #F8FAFC; letter-spacing: 2px;")
        self.layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        subtitle_label = QLabel("Gerçek Zamanlı Ekran Çevirmeni & Yapay Zeka Asistanı", self.container)
        subtitle_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        subtitle_label.setStyleSheet("color: #38BDF8;")
        self.layout.addWidget(subtitle_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.layout.addSpacing(15)

        # Progress bar
        self.progress_bar = QProgressBar(self.container)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.set_progress_bar_color("#0284C7", "#38BDF8")
        self.layout.addWidget(self.progress_bar)

        # Status Label
        self.status_label = QLabel("Sistem ve OCR Modülleri Yükleniyor...", self.container)
        self.status_label.setFont(QFont("Segoe UI", 10))
        self.status_label.setStyleSheet("color: #94A3B8;")
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Error Container Box (Hidden by default)
        self.error_box = QFrame(self.container)
        self.error_box.setStyleSheet("""
            QFrame {
                background-color: #1E1218;
                border: 1.5px solid #EF4444;
                border-radius: 12px;
                padding: 10px;
            }
        """)
        error_layout = QVBoxLayout(self.error_box)
        error_layout.setContentsMargins(12, 10, 12, 10)

        self.error_msg_label = QLabel("", self.error_box)
        self.error_msg_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.error_msg_label.setStyleSheet("color: #FCA5A5;")
        self.error_msg_label.setWordWrap(True)
        self.error_msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_layout.addWidget(self.error_msg_label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.retry_btn = QPushButton("🔄 Bağlantıyı Tekrar Dene", self.error_box)
        self.retry_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.retry_btn.setStyleSheet("""
            QPushButton {
                background-color: #0284C7; color: white;
                border: none; border-radius: 8px;
                padding: 8px 16px; font-weight: bold; font-size: 11px;
            }
            QPushButton:hover { background-color: #0369A1; }
        """)
        self.retry_btn.clicked.connect(self.retry_connection)
        btn_layout.addWidget(self.retry_btn)

        self.offline_btn = QPushButton("⚠️ Çevrimdışı Modda Devam Et", self.error_box)
        self.offline_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.offline_btn.setStyleSheet("""
            QPushButton {
                background-color: #334155; color: #F8FAFC;
                border: 1px solid #475569; border-radius: 8px;
                padding: 8px 16px; font-weight: bold; font-size: 11px;
            }
            QPushButton:hover { background-color: #475569; }
        """)
        self.offline_btn.clicked.connect(self.proceed_offline)
        btn_layout.addWidget(self.offline_btn)

        error_layout.addLayout(btn_layout)
        self.layout.addWidget(self.error_box)
        self.error_box.hide()

        # State flags
        self.progress = 0
        self.connection_checked = False
        self.checking_in_progress = False

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(25)

    def set_progress_bar_color(self, color1: str, color2: str):
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #1E293B;
                border-radius: 4px;
                border: none;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {color1}, stop:1 {color2});
                border-radius: 4px;
            }}
        """)

    def center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.geometry()
            x = (geo.width() - self.width()) // 2
            y = (geo.height() - self.height()) // 2
            self.move(x, y)

    def update_progress(self):
        if self.progress < 50:
            self.progress += 2
            self.progress_bar.setValue(self.progress)
            if self.progress == 24:
                self.status_label.setText("OCR ve Ekran Yakalama Motoru Hazırlanıyor...")
            elif self.progress == 48 and not self.connection_checked and not self.checking_in_progress:
                self.checking_in_progress = True
                self.status_label.setText("🌐 Yapay Zeka (LLM) Sunucu Bağlantısı Kontrol Ediliyor...")
                self.start_connection_check()
        elif self.connection_checked and self.progress < 100:
            self.progress += 5
            self.progress_bar.setValue(self.progress)
            if self.progress >= 100:
                self.timer.stop()
                QTimer.singleShot(400, self.finish_splash)

    def start_connection_check(self):
        self.worker = ConnectionCheckWorker()
        self.worker.result_signal.connect(self.on_connection_result)
        self.worker.start()

    @pyqtSlot(bool, str)
    def on_connection_result(self, is_connected: bool, message: str):
        self.checking_in_progress = False

        if is_connected:
            self.connection_checked = True
            self.status_label.setText(f"✅ {message}")
            self.status_label.setStyleSheet("color: #22C55E; font-weight: bold;")
            self.set_progress_bar_color("#166534", "#22C55E")
            self.error_box.hide()
            # Resume progress animation to 100%
            self.timer.start(20)
        else:
            # STOP splash progress and STAY on screen!
            self.timer.stop()
            self.set_progress_bar_color("#991B1B", "#EF4444")
            self.status_label.setText("❌ Yapay Zeka / LLM Bağlantı Hatası!")
            self.status_label.setStyleSheet("color: #EF4444; font-weight: bold;")

            self.error_msg_label.setText(
                f"⚠️ {message}\n\n"
                "Lütfen Jan.ai, Ollama veya LM Studio uygulamanızı başlatın ve modelin yüklü olduğundan emin olun."
            )
            self.error_box.show()

    def retry_connection(self):
        self.error_box.hide()
        self.set_progress_bar_color("#0284C7", "#38BDF8")
        self.status_label.setText("🔄 Yapay Zeka Sunucu Bağlantısı Tekrar Deneniyor...")
        self.status_label.setStyleSheet("color: #38BDF8; font-weight: bold;")
        self.checking_in_progress = True
        self.start_connection_check()

    def proceed_offline(self):
        self.error_box.hide()
        self.status_label.setText("⚠️ Çevrimdışı (GTX Fallback) Modunda Başlatılıyor...")
        self.status_label.setStyleSheet("color: #F59E0B; font-weight: bold;")
        self.connection_checked = True
        self.timer.start(15)

    def finish_splash(self):
        self.finished.emit()
        self.close()
