import sys
from typing import List, Dict, Any
from PyQt6.QtCore import Qt, QTimer, QRect
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt6.QtGui import QFont, QColor
from config import Config

class TranslationCard(QWidget):
    """
    Sub-widget card rendered as a clean Cinema/Movie Subtitle bar at the bottom center of the monitor.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(18, 10, 18, 10)
        
        self.label = QLabel(self)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.apply_style()
        self.layout.addWidget(self.label)

    def apply_style(self):
        try:
            from settings_manager import SettingsManager
            sm = SettingsManager()
            font_family = sm.get("font_family", Config.OVERLAY_FONT_FAMILY)
            font_size = sm.get("font_size", Config.OVERLAY_FONT_SIZE)
            text_color = sm.get("text_color", Config.OVERLAY_TEXT_COLOR)
            card_bg = sm.get("card_bg_color", Config.OVERLAY_CARD_BG)
            border_color = sm.get("border_color", Config.OVERLAY_BORDER_COLOR)
        except Exception:
            font_family = Config.OVERLAY_FONT_FAMILY
            font_size = Config.OVERLAY_FONT_SIZE
            text_color = Config.OVERLAY_TEXT_COLOR
            card_bg = Config.OVERLAY_CARD_BG
            border_color = Config.OVERLAY_BORDER_COLOR

        # Subtitle font (default 16pt - 18pt bold for clear reading)
        font = QFont(font_family, max(15, font_size), QFont.Weight.Bold)
        self.label.setFont(font)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {card_bg};
                color: {text_color};
                border: 1.5px solid {border_color};
                border-radius: 10px;
            }}
            QLabel {{
                background-color: transparent;
                border: none;
            }}
        """)

    def set_text(self, text: str):
        self.label.setText(text)
        self.adjustSize()

class TranslationOverlayWindow(QWidget):
    """
    Full-screen transparent, click-through overlay window.
    Renders live cinema-style subtitles anchored at bottom center of the target screen.
    """
    def __init__(self, target_monitor_index: int = 1):
        super().__init__()
        self.cards: List[TranslationCard] = []
        self.target_monitor_index = target_monitor_index
        
        # Configure frameless, transparent, click-through overlay
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        # Cover full virtual desktop across all connected monitors so overlay is unbounded
        screens = QApplication.screens()
        combined_geo = QRect()
        for screen in screens:
            combined_geo = combined_geo.united(screen.geometry())
        if not combined_geo.isEmpty():
            self.setGeometry(combined_geo)
        elif screens:
            self.setGeometry(screens[0].geometry())

        # Timer to clear stale translations after timeout
        self.clear_timer = QTimer(self)
        self.clear_timer.setSingleShot(True)
        self.clear_timer.timeout.connect(self.clear_translations)

    def set_target_monitor_index(self, monitor_index: int):
        self.target_monitor_index = monitor_index

    def get_target_screen_geometry(self) -> QRect:
        screens = QApplication.screens()
        # MSS monitor indexes are 1-based (1 = Monitör 1, 2 = Monitör 2)
        idx = max(0, self.target_monitor_index - 1)
        if idx < len(screens):
            return screens[idx].geometry()
        elif screens:
            return screens[0].geometry()
        return self.geometry()

    def apply_settings(self):
        for card in self.cards:
            card.apply_style()

    def update_translations(self, items: List[Dict[str, Any]]):
        """
        Updates displayed subtitle overlay anchored cleanly at the bottom center of the screen.
        """
        if not items:
            return

        self.show()
        self.raise_()

        for card in self.cards:
            card.hide()

        if not self.cards:
            card = TranslationCard(self)
            self.cards.append(card)

        try:
            from settings_manager import SettingsManager
            sm = SettingsManager()
            pos_mode = sm.get("subtitle_position_mode", "bottom_center")
        except Exception:
            pos_mode = "bottom_center"

        target_geo = self.get_target_screen_geometry()

        # Clean and filter subtitle lines (prioritize dialogue sentences, max 3 lines)
        valid_lines = []
        for item in items:
            trans = item.get("trans", "").strip()
            orig = item.get("orig", "").strip()
            # Ignore empty strings or error fallbacks
            if not trans or trans.startswith("[") or len(trans) < 2:
                continue
            # Ignore duplicate lines
            if trans not in valid_lines:
                valid_lines.append(trans)

        if not valid_lines:
            return

        if pos_mode == "bottom_center":
            # Pick top 3 main subtitle lines max to prevent huge text walls
            selected_lines = valid_lines[:3]
            combined_trans = "\n".join(selected_lines)
            
            card = self.cards[0]
            card.apply_style()
            card.set_text(combined_trans)
            
            max_w = int(target_geo.width() * 0.75)
            card_w = min(max_w, max(380, card.sizeHint().width() + 40))
            card.setFixedWidth(card_w)
            card.adjustSize()
            
            card_h = card.height()
            
            # Anchor strictly at bottom center (70px above bottom edge of target monitor)
            pos_x = target_geo.x() + max(0, int((target_geo.width() - card_w) / 2))
            pos_y = target_geo.y() + max(0, int(target_geo.height() - card_h - 70))
            
            card.move(pos_x, pos_y)
            card.show()
        else:
            # Relative positioning mode
            while len(self.cards) < len(valid_lines):
                c = TranslationCard(self)
                self.cards.append(c)

            for idx, trans_text in enumerate(valid_lines[:5]):
                card = self.cards[idx]
                card.apply_style()
                item = items[idx] if idx < len(items) else items[0]
                x, y, w, h = item["rect"]
                
                card.set_text(trans_text)
                card_h = card.sizeHint().height()
                
                pos_y = y + h + 4
                if pos_y + card_h > target_geo.y() + target_geo.height():
                    pos_y = max(target_geo.y(), y - card_h - 4)

                pos_x = max(target_geo.x(), min(x, target_geo.x() + target_geo.width() - card.sizeHint().width()))
                card.move(pos_x, pos_y)
                card.show()

        # Reset clear timer based on settings
        try:
            from settings_manager import SettingsManager
            auto_hide = float(SettingsManager().get("auto_hide_seconds", Config.OVERLAY_AUTO_HIDE_SECONDS))
        except Exception:
            auto_hide = Config.OVERLAY_AUTO_HIDE_SECONDS

        self.clear_timer.start(int(auto_hide * 1000))

    def clear_translations(self):
        for card in self.cards:
            card.hide()
