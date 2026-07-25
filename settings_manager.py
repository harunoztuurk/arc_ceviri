import json
import os
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "font_family": "Segoe UI",
    "font_size": 16,
    "text_color": "#FDE047",
    "card_bg_color": "rgba(15, 23, 42, 0.95)",
    "border_color": "#38BDF8",
    "auto_hide_seconds": 6.0,
    "subtitle_position_mode": "bottom_center",
    "keep_static_subtitles": True,
    "ocr_languages": ["en"],

    "target_language": "tr",
    "hotkey_toggle": "Ctrl+Shift+S",
    "hotkey_region": "Alt+R",
    "hotkey_macro": "Alt+T",
    "glossary": {
        "HP": "Can Puanı",
        "MP": "Büyü Puanı",
        "XP": "Deneyim Puanı",
        "Vault": "Mahzen / Kasa",
        "Quest": "Görev"
    }
}

class SettingsManager:
    """
    Manages persistent JSON configuration for arc settings and game glossary.
    """
    def __init__(self, filepath: str = SETTINGS_FILE):
        self.filepath = filepath
        self.settings: Dict[str, Any] = {}
        self.load_settings()

    def load_settings(self) -> Dict[str, Any]:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.settings = {**DEFAULT_SETTINGS, **data}
            except Exception as e:
                logger.error(f"Error loading settings.json: {e}")
                self.settings = DEFAULT_SETTINGS.copy()
        else:
            self.settings = DEFAULT_SETTINGS.copy()
            self.save_settings()
        return self.settings

    def save_settings(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Error saving settings.json: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    def set(self, key: str, value: Any):
        self.settings[key] = value
        self.save_settings()

    def get_glossary(self) -> Dict[str, str]:
        return self.settings.get("glossary", {})

    def add_glossary_term(self, term: str, translation: str):
        if "glossary" not in self.settings:
            self.settings["glossary"] = {}
        self.settings["glossary"][term.strip()] = translation.strip()
        self.save_settings()

    def remove_glossary_term(self, term: str):
        if "glossary" in self.settings and term in self.settings["glossary"]:
            del self.settings["glossary"][term]
            self.save_settings()
