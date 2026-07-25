import logging
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut


logger = logging.getLogger(__name__)

class GlobalHotkeyManager(QObject):
    """
    Manages global keyboard shortcuts for toggling translation and selecting region.
    Supports pynput background listener for system-wide hotkeys when gaming.
    """
    toggle_requested = pyqtSignal()
    region_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._listener = None
        self._start_pynput_listener()

    def _start_pynput_listener(self):
        try:
            from pynput import keyboard

            def on_press(key):
                pass

            # Define combinations
            COMBINATIONS = [
                {keyboard.Key.ctrl_l, keyboard.Key.shift, keyboard.KeyCode.from_char('s')},
                {keyboard.Key.ctrl_l, keyboard.Key.shift, keyboard.KeyCode.from_char('S')},
                {keyboard.Key.ctrl_r, keyboard.Key.shift, keyboard.KeyCode.from_char('s')},
            ]

            current_keys = set()

            def on_key_press(key):
                current_keys.add(key)
                # Check toggle (Ctrl+Shift+S)
                if (keyboard.Key.ctrl_l in current_keys or keyboard.Key.ctrl_r in current_keys) and \
                   (keyboard.Key.shift in current_keys or keyboard.Key.shift_r in current_keys) and \
                   (keyboard.KeyCode.from_char('s') in current_keys or keyboard.KeyCode.from_char('S') in current_keys):
                    self.toggle_requested.emit()

            def on_key_release(key):
                if key in current_keys:
                    current_keys.remove(key)

            self._listener = keyboard.Listener(on_press=on_key_press, on_release=on_key_release)
            self._listener.daemon = True
            self._listener.start()
            logger.info("pynput Global Hotkey Listener started successfully.")
        except Exception as e:
            logger.info(f"pynput not available or failed: {e}. Falling back to PyQt local shortcuts.")

    def stop(self):
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
