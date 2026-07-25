import sys
import time
import argparse
import cv2
import logging
import warnings

# Suppress PyTorch/EasyOCR UserWarnings globally
warnings.filterwarnings("ignore")
logging.getLogger("easyocr").setLevel(logging.ERROR)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from config import Config
from capture.engine import ScreenCaptureEngine
from ocr.reader import OCRReader
from translator.llm_client import LLMTranslator
from ui.overlay import TranslationOverlayWindow
from pipeline.async_worker import AsyncPipelineController

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("Antigravity")

def run_phase_1(duration_sec: float = 10.0):
    """
    Aşama 1 (Core Loop): Screen capture with mss & OpenCV display at ~5 FPS.
    """
    logger.info("--- Starting Aşama 1: Core Screen Capture Loop ---")
    capture_engine = ScreenCaptureEngine()
    start_time = time.time()
    
    try:
        while time.time() - start_time < duration_sec:
            loop_start = time.time()
            frame = capture_engine.capture_frame()
            changed, pct = capture_engine.has_changed(frame)
            
            status_text = f"FPS: 5 | Frame Diff: {pct:.2f}% | Changed: {changed}"
            cv2.putText(frame, status_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Show OpenCV preview window if display backend is available
            try:
                cv2.imshow("Antigravity - Phase 1 Capture Test (Press 'q' to exit)", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            except cv2.error:
                logger.info(f"Frame #{int((time.time()-start_time)*5)} captured successfully ({pct:.2f}% diff). (Headless preview mode)")

            elapsed = time.time() - loop_start
            sleep_time = max(0.0, (1.0 / Config.CAPTURE_FPS) - elapsed)
            time.sleep(sleep_time)
            
    finally:
        capture_engine.close()
        try:
            cv2.destroyAllWindows()
        except cv2.error:
            pass
        logger.info("--- Aşama 1 completed ---")

def run_phase_2(max_frames: int = 1):
    """
    Aşama 2 (OCR Entegrasyonu): EasyOCR text extraction and bounding box detection.
    """
    logger.info("--- Starting Aşama 2: OCR & Text Extraction ---")
    capture_engine = ScreenCaptureEngine()
    reader = OCRReader()
    
    try:
        processed_frames = 0
        while processed_frames < max_frames:
            frame = capture_engine.capture_frame()
            changed, pct = capture_engine.has_changed(frame)
            
            if changed:
                processed_frames += 1
                logger.info(f"Frame #{processed_frames} capture changed ({pct:.2f}%). Running EasyOCR...")
                raw_blocks = reader.extract_text(frame)
                grouped = reader.group_text_blocks(raw_blocks)
                
                print("\n================ OCR DETECTED TEXT ================")
                if not grouped:
                    print("No text detected in current frame.")
                for item in grouped:
                    x, y, w, h = item["rect"]
                    text = item["text"]
                    conf = item["confidence"]
                    print(f" [POS] (X:{x:4d}, Y:{y:4d}, W:{w:4d}, H:{h:4d}) | Conf: {conf:.2f} | Text: '{text}'")
                print("===================================================\n")
                break
                
            time.sleep(1.0 / Config.CAPTURE_FPS)
    finally:
        capture_engine.close()
        logger.info("--- Aşama 2 completed ---")

def run_phase_3(max_items: int = 3):
    """
    Aşama 3 (AI/Çeviri Entegrasyonu): Sends extracted text to local LLM endpoint (Jan.ai format).
    """
    logger.info("--- Starting Aşama 3: AI Translation Integration ---")
    capture_engine = ScreenCaptureEngine()
    reader = OCRReader()
    translator = LLMTranslator()
    
    try:
        frame = capture_engine.capture_frame()
        logger.info("Capturing frame for OCR & Translation test...")
        raw_blocks = reader.extract_text(frame)
        grouped = reader.group_text_blocks(raw_blocks)
        
        print("\n================ ENGLISH -> TURKISH TRANSLATION ================")
        for item in grouped[:max_items]:
            english_text = item["text"]
            turkish_text = translator.translate(english_text)
            x, y, w, h = item["rect"]
            print(f" [EN] ({x},{y}): {english_text}")
            print(f" [TR]       : {turkish_text}")
            print("-" * 60)
        print("=================================================================\n")
    finally:
        capture_engine.close()
        logger.info("--- Aşama 3 completed ---")

def run_phase_4():
    """
    Aşama 4 (PyQt6 UI): Transparent, frameless, click-through overlay showing translations.
    """
    logger.info("--- Starting Aşama 4: PyQt6 Transparent Overlay UI ---")
    app = QApplication.instance() or QApplication(sys.argv)
    
    overlay = TranslationOverlayWindow()
    overlay.show()
    
    # Mock translation item to demonstrate overlay positioning
    dummy_items = [
        {
            "rect": (200, 150, 300, 40),
            "orig": "Press START to begin your adventure",
            "trans": "Macerana başlamak için BAŞLA düğmesine bas"
        },
        {
            "rect": (200, 350, 400, 40),
            "orig": "Inventory full. Sell items to free up space.",
            "trans": "Envanter dolu. Yer açmak için eşyaları sat."
        }
    ]
    overlay.update_translations(dummy_items)
    
    logger.info("Overlay displayed. Auto-close in 6 seconds...")
    QTimer.singleShot(6000, app.quit)
    app.exec()
    logger.info("--- Aşama 4 completed ---")

def run_phase_5():
    """
    Aşama 5 (Optimizasyon / Tam Uygulama): Multi-threaded asynchronous capture, OCR, and translation pipeline.
    """
    logger.info("--- Starting Aşama 5: Full Asynchronous Antigravity Application ---")
    app = QApplication.instance() or QApplication(sys.argv)
    
    overlay = TranslationOverlayWindow()
    overlay.show()
    
    pipeline = AsyncPipelineController()
    pipeline.translations_updated.connect(overlay.update_translations)
    
    logger.info("Antigravity is running in background! Press Ctrl+C in terminal or close window to exit.")
    try:
        app.exec()
    finally:
        pipeline.stop()
        logger.info("--- Aşama 5 completed ---")

from ui.control_panel import ControlPanelWindow

def run_gui_app():
    """
    Launches full Desktop GUI Dashboard application with Control Panel,
    Region Selector, Flashcards Manager, and Transparent Overlay.
    """
    logger.info("--- Starting Umutrans Desktop Control Panel GUI ---")
    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = ControlPanelWindow()
    window.show()
    sys.exit(app.exec())

def main():
    parser = argparse.ArgumentParser(description="arc - Gerçek Zamanlı Ekran Çevirisi ve Dil Öğrenim Asistanı")
    parser.add_argument("--phase", type=int, choices=[1, 2, 3, 4, 5], default=None,
                        help="Select prototype phase to test (1: Capture, 2: OCR, 3: Translation, 4: Overlay UI, 5: Async CLI)")
    parser.add_argument("--duration", type=float, default=5.0, help="Duration in seconds for test phases")
    
    args = parser.parse_args()
    
    if args.phase is None:
        run_gui_app()
    elif args.phase == 1:
        run_phase_1(duration_sec=args.duration)
    elif args.phase == 2:
        run_phase_2()
    elif args.phase == 3:
        run_phase_3()
    elif args.phase == 4:
        run_phase_4()
    elif args.phase == 5:
        run_phase_5()

if __name__ == "__main__":
    main()
