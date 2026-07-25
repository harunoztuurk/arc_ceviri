import sqlite3
import json
import time
from typing import List, Dict, Any

class FlashcardManager:
    """
    SQLite-backed flashcard manager for saved unknown words and contextual sentences.
    Helps users study vocabulary captured during gaming/reading sessions.
    """
    def __init__(self, db_path: str = "flashcards.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS flashcards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    english TEXT NOT NULL,
                    turkish TEXT NOT NULL,
                    context TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def add_card(self, english: str, turkish: str, context: str = "") -> int:
        """
        Adds a new word/sentence pair to flashcards database.
        Aynı İngilizce metin zaten kayıtlıysa tekrar eklenmez (duplicate önleme).
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Duplicate check: aynı İngilizce metin varsa ekleme
            cursor.execute(
                "SELECT id FROM flashcards WHERE english = ? COLLATE NOCASE",
                (english.strip(),)
            )
            existing = cursor.fetchone()
            if existing:
                return existing[0]  # Mevcut kaydın id'sini döndür, tekrar kaydetme
            cursor.execute(
                "INSERT INTO flashcards (english, turkish, context) VALUES (?, ?, ?)",
                (english.strip(), turkish.strip(), context.strip())
            )
            return cursor.lastrowid

    def get_all_cards(self) -> List[Dict[str, Any]]:
        """
        Retrieves all saved flashcards.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM flashcards ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def export_to_json(self, filepath: str = "flashcards_export.json"):
        """
        Exports flashcards to JSON format for study app import.
        """
        cards = self.get_all_cards()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(cards, f, ensure_ascii=False, indent=2)

    def export_to_anki_csv(self, filepath: str = "anki_cards.csv"):
        """
        Exports flashcards to Anki-compatible CSV format (Front/Back/Context).
        """
        import csv
        cards = self.get_all_cards()
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter=";")
            for card in cards:
                writer.writerow([card["english"], card["turkish"], card.get("context", "")])

    def speak_text(self, text: str):
        """
        Pronounces English text using Text-to-Speech engine in background thread.
        """
        import threading
        def _speak():
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.say(text)
                engine.runAndWait()
            except Exception:
                # Online fallback via gTTS/Web sound if pyttsx3 is not available
                try:
                    import urllib.parse
                    import os
                    encoded = urllib.parse.quote(text)
                    url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={encoded}&tl=en&client=tw-ob"
                    import winsound
                    # Play online audio via system
                    import urllib.request
                    temp_audio = os.path.join(os.path.expanduser("~"), "arc_temp_tts.mp3")
                    urllib.request.urlretrieve(url, temp_audio)
                except Exception:
                    pass

        threading.Thread(target=_speak, daemon=True).start()

    def get_quiz_questions(self, count: int = 5) -> List[Dict[str, Any]]:
        """
        Generates multiple-choice quiz questions from saved flashcards.
        """
        import random
        cards = self.get_all_cards()
        if len(cards) < 2:
            return []

        selected = random.sample(cards, min(count, len(cards)))
        all_tr = [c["turkish"] for c in cards]

        questions = []
        for card in selected:
            correct_ans = card["turkish"]
            wrong_choices = [tr for tr in all_tr if tr != correct_ans]
            random.shuffle(wrong_choices)
            options = wrong_choices[:3] + [correct_ans]
            random.shuffle(options)

            questions.append({
                "id": card["id"],
                "english": card["english"],
                "correct": correct_ans,
                "options": options
            })
        return questions

    def delete_card(self, card_id: int):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM flashcards WHERE id = ?", (card_id,))

