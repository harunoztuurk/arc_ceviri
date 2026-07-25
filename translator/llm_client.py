import requests
import json
import logging
from typing import Optional
from config import Config

logger = logging.getLogger(__name__)

class LLMTranslator:
    """
    Client for contextual translation using local LLM APIs (Ollama, Jan.ai, Nvidia NIM, LM Studio).
    Format complies with standard OpenAI v1/chat/completions schema.
    Auto-detects active local ports (11434, 1337, 1234) for seamless local AI performance.
    """
    def __init__(
        self, 
        api_url: str = Config.LLM_API_URL, 
        model: str = Config.LLM_MODEL, 
        timeout: float = 0.4,  # Fast 0.4s timeout for real-time responsiveness
        system_prompt: str = Config.TRANSLATION_SYSTEM_PROMPT
    ):
        self.api_url = api_url
        self.model = model
        self.timeout = timeout
        self.system_prompt = system_prompt
        self.session = requests.Session()
        self._warned_offline = False
        self._cache = {}


        # Auto-detect local AI servers if default endpoint is not responding
        self._auto_detect_local_endpoint()

    def _auto_detect_local_endpoint(self):
        """
        Scans local ports (Ollama 11434, Jan.ai 1337, LM Studio 1234)
        and configures active local AI endpoint.
        """
        candidates = [
            ("http://localhost:11434/v1/chat/completions", "Ollama (Port 11434)", 11434),
            ("http://localhost:1337/v1/chat/completions", "Jan.ai (Port 1337)", 1337),
            ("http://localhost:1234/v1/chat/completions", "LM Studio (Port 1234)", 1234)
        ]
        
        for url, name, port in candidates:
            try:
                res = self.session.get(f"http://localhost:{port}/", timeout=0.2)
                if res.status_code in (200, 404, 405):  # Active local AI server
                    self.api_url = url
                    return
            except Exception:
                continue

    def translate(self, text: str) -> str:
        """
        Translates text from English to Turkish with ultra-low latency (<100ms).
        Applies game glossary term overrides automatically.
        """
        if not text or not text.strip():
            return ""

        clean_key = text.strip().lower()

        # Instant in-memory cache return
        if clean_key in self._cache:
            return self._cache[clean_key]

        # Check glossary exact or word match override
        try:
            from settings_manager import SettingsManager
            glossary = SettingsManager().get_glossary()
            
            # Direct full text match in glossary
            if text.strip() in glossary:
                res = glossary[text.strip()]
                self._cache[clean_key] = res
                return res
        except Exception:
            glossary = {}

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": text.strip()}
            ],
            "temperature": 0.2,
            "max_tokens": 100
        }

        translated = ""
        try:
            response = self.session.post(
                self.api_url, 
                json=payload, 
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            translated_content = data["choices"][0]["message"]["content"].strip()
            if translated_content:
                translated = translated_content
            else:
                translated = self._fallback_translate(text)
        except Exception:
            translated = self._fallback_translate(text)

        # Apply glossary word overrides cleanly without appending extra text
        for term, tr_term in glossary.items():
            import re
            pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
            if pattern.search(text) and tr_term.lower() not in translated.lower():
                translated = pattern.sub(tr_term, translated)

        if translated:
            self._cache[clean_key] = translated

        return translated


    def _fallback_translate(self, text: str) -> str:
        """
        Automatic online translation fallback (via Google Translate GTX endpoint)
        when local LLM endpoint (Jan.ai / Ollama) is not running locally.
        """
        if not text or not text.strip():
            return ""

        try:
            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                "client": "gtx",
                "sl": "en",
                "tl": "tr",
                "dt": "t",
                "q": text.strip()
            }
            res = self.session.get(url, params=params, timeout=3.0)
            if res.status_code == 200:
                data = res.json()
                if data and isinstance(data, list) and len(data) > 0 and data[0]:
                    translated_chunks = [segment[0] for segment in data[0] if segment and segment[0]]
                    online_translation = "".join(translated_chunks).strip()
                    if online_translation:
                        return online_translation
        except Exception as e:
            logger.debug(f"Online translation fallback error: {e}")

        # Ultimate fallback if completely offline
        return f"[Çeviri]: {text}"
