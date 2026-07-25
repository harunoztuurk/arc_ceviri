import logging
import time
from typing import List, Dict, Any
from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, QTimer

from capture.engine import ScreenCaptureEngine
from ocr.reader import OCRReader
from translator.llm_client import LLMTranslator
from config import Config

logger = logging.getLogger(__name__)

class OCRWorker(QObject):
    finished = pyqtSignal(list)

    def __init__(self, reader: OCRReader):
        super().__init__()
        self.reader = reader

    @pyqtSlot(object)
    def process_frame(self, frame):
        try:
            if frame is None or frame.size == 0:
                self.finished.emit([])
                return
                
            raw_blocks = self.reader.extract_text(frame)
            grouped_blocks = self.reader.group_text_blocks(raw_blocks)
            self.finished.emit(grouped_blocks)
        except Exception as e:
            logger.error(f"OCRWorker exception: {e}")
            self.finished.emit([])

class TranslationWorker(QObject):
    finished = pyqtSignal(list)

    def __init__(self, translator: LLMTranslator):
        super().__init__()
        self.translator = translator

    @pyqtSlot(list)
    def process_blocks(self, blocks: List[Dict[str, Any]]):
        try:
            results = []
            for block in blocks:
                original_text = block["text"]
                translated_text = self.translator.translate(original_text)
                
                results.append({
                    "rect": block["rect"],
                    "orig": original_text,
                    "trans": translated_text
                })
                
            self.finished.emit(results)
        except Exception as e:
            logger.error(f"TranslationWorker exception: {e}")
            self.finished.emit([])

class AsyncPipelineController(QObject):
    """
    Asynchronous pipeline orchestrating Screen Capture (Main Timer),
    OCR (Worker Thread 1), and Translation API Requests (Worker Thread 2).
    Dispatches tasks via PyQt QueuedConnection signals for true asynchronous performance.
    """
    translations_updated = pyqtSignal(list)
    start_ocr_signal = pyqtSignal(object)
    start_trans_signal = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self._running = True
        self.capture_engine = ScreenCaptureEngine()
        self.ocr_reader = OCRReader()
        self.llm_translator = LLMTranslator()
        from learning.flashcards import FlashcardManager
        self.flashcard_mgr = FlashcardManager()

        # Thread setup for OCR
        self.ocr_thread = QThread()
        self.ocr_worker = OCRWorker(self.ocr_reader)
        self.ocr_worker.moveToThread(self.ocr_thread)
        self.start_ocr_signal.connect(self.ocr_worker.process_frame)
        self.ocr_worker.finished.connect(self._on_ocr_finished)
        self.ocr_thread.start()

        # Thread setup for Translation
        self.trans_thread = QThread()
        self.trans_worker = TranslationWorker(self.llm_translator)
        self.trans_worker.moveToThread(self.trans_thread)
        self.start_trans_signal.connect(self.trans_worker.process_blocks)
        self.trans_worker.finished.connect(self._on_translation_finished)
        self.trans_thread.start()

        self.ocr_busy = False
        self.trans_busy = False
        self.last_ocr_timestamp = 0.0
        self.min_ocr_interval = 0.10  # Instant 0.10s scan interval for real-time responsiveness


        # Capture timer
        self.timer = QTimer()
        self.timer.timeout.connect(self._capture_tick)
        interval_ms = int(1000.0 / Config.CAPTURE_FPS)
        self.timer.start(interval_ms)

    def force_immediate_scan(self):
        """
        Forces an immediate frame capture and OCR scan upon user start.
        """
        if not self._running:
            return
        self.last_ocr_timestamp = 0.0
        self.ocr_busy = False
        self.trans_busy = False
        self._capture_tick()

    def _capture_tick(self):
        if not self._running:
            return

        now = time.time()
        
        # Generous safety reset if worker gets stuck > 10 seconds
        if self.ocr_busy and (now - self.last_ocr_timestamp > 10.0):
            self.ocr_busy = False
            self.trans_busy = False

        if self.ocr_busy:
            return

        if now - self.last_ocr_timestamp < self.min_ocr_interval:
            return

        try:
            frame = self.capture_engine.capture_frame()
            changed, percentage = self.capture_engine.has_changed(frame)

            if changed or self.last_ocr_timestamp == 0.0:
                self.ocr_busy = True
                self.last_ocr_timestamp = now
                self.start_ocr_signal.emit(frame)
        except Exception as e:
            logger.error(f"Error in capture tick: {e}")
            self.ocr_busy = False

    def _on_ocr_finished(self, grouped_blocks: list):
        if not self._running:
            return

        self.ocr_busy = False
        
        if not grouped_blocks:
            # Clear overlay if no text detected
            self.translations_updated.emit([])
            return

        if not self.trans_busy:
            self.trans_busy = True
            self.start_trans_signal.emit(grouped_blocks)

    def _on_translation_finished(self, results: list):
        if not self._running:
            return

        self.trans_busy = False
        
        # Automatically save all detected words & contextual translations to FlashcardManager
        for item in results:
            orig = item.get("orig", "")
            trans = item.get("trans", "")
            if orig and trans and not trans.startswith("["):
                try:
                    self.flashcard_mgr.add_card(english=orig, turkish=trans, context="Ekran Çevirisi")
                except Exception:
                    pass

        self.translations_updated.emit(results)

    def stop(self):
        """
        Stops all pipeline activities instantly and cleanly terminates worker threads.
        """
        self._running = False
        self.timer.stop()
        
        try:
            self.start_ocr_signal.disconnect()
            self.start_trans_signal.disconnect()
            self.ocr_worker.finished.disconnect(self._on_ocr_finished)
            self.trans_worker.finished.disconnect(self._on_translation_finished)
        except Exception:
            pass

        self.ocr_thread.quit()
        self.ocr_thread.wait(500)
        self.trans_thread.quit()
        self.trans_thread.wait(500)
        self.capture_engine.close()
