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
        Supports static text preservation (does not hide subtitle if screen text has not changed).
        """
        try:
            from settings_manager import SettingsManager
            sm = SettingsManager()
            keep_static = sm.get("keep_static_subtitles", True)
            auto_hide = float(sm.get("auto_hide_seconds", Config.OVERLAY_AUTO_HIDE_SECONDS))
        except Exception:
            keep_static = True
            auto_hide = Config.OVERLAY_AUTO_HIDE_SECONDS

        if not items:
            if keep_static and self.cards and any(c.isVisible() for c in self.cards):
                return
            else:
                self.clear_translations()
                return

        # Clean and filter subtitle lines
        valid_lines = []
        for item in items:
            trans = item.get("trans", "").strip()
            orig = item.get("orig", "").strip()
            if not trans or trans.startswith("[") or len(trans) < 2:
                continue
            if trans not in valid_lines:
                valid_lines.append(trans)

        if not valid_lines:
            if keep_static and self.cards and any(c.isVisible() for c in self.cards):
                return
            return

        combined_trans = "\n".join(valid_lines[:3])

        # If text is identical to current subtitle and keep_static is active, do not auto-hide!
        if hasattr(self, "_last_combined_trans") and self._last_combined_trans == combined_trans:
            if keep_static:
                self.clear_timer.stop()
                return

        self._last_combined_trans = combined_trans

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

        if pos_mode == "bottom_center":
            card = self.cards[0]
            card.apply_style()
            card.set_text(combined_trans)
            
            max_w = int(target_geo.width() * 0.75)
            card_w = min(max_w, max(380, card.sizeHint().width() + 40))
            card.setFixedWidth(card_w)
            card.adjustSize()
            
            card_h = card.height()
            
            pos_x = target_geo.x() + max(0, int((target_geo.width() - card_w) / 2))
            pos_y = target_geo.y() + max(0, int(target_geo.height() - card_h - 70))
            
            card.move(pos_x, pos_y)
            card.show()
        else:
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

        if not keep_static:
            self.clear_timer.start(int(auto_hide * 1000))

    def show_mouse_tooltip(self, orig: str, trans: str, pos_x: int, pos_y: int):
        """
        Renders a floating translation tooltip right next to mouse cursor when Macro hotkey (Alt+T) is pressed.
        """
        if not hasattr(self, "mouse_card") or self.mouse_card is None:
            self.mouse_card = TranslationCard(self)
            self.mouse_card.setStyleSheet("""
                QWidget {
                    background-color: rgba(15, 23, 42, 0.98);
                    color: #FDE047;
                    border: 2px solid #0EA5E9;
                    border-radius: 8px;
                }
                QLabel { background-color: transparent; border: none; }
            """)
        
        display_text = f"🔤 {orig}\n🇹🇷 {trans}"
        self.mouse_card.set_text(display_text)
        self.mouse_card.adjustSize()
        
        target_x = pos_x + 20
        target_y = pos_y + 20
        
        target_geo = self.geometry()
        card_w = self.mouse_card.width()
        card_h = self.mouse_card.height()
        
        if target_x + card_w > target_geo.width():
            target_x = max(0, pos_x - card_w - 10)
        if target_y + card_h > target_geo.height():
            target_y = max(0, pos_y - card_h - 10)
            
        self.mouse_card.move(target_x, target_y)
        self.mouse_card.show()
        self.show()
        self.raise_()
        
        QTimer.singleShot(8000, lambda: self.mouse_card.hide() if hasattr(self, "mouse_card") and self.mouse_card else None)

    def clear_translations(self):
        if hasattr(self, "_last_combined_trans"):
            delattr(self, "_last_combined_trans")
        for card in self.cards:
            card.hide()
        if hasattr(self, "mouse_card") and self.mouse_card:
            self.mouse_card.hide()
