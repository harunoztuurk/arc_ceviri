import os

class Config:
    # App Name
    APP_NAME = "arc"

    # Screen Capture settings
    CAPTURE_REGION = None  
    CAPTURE_FPS = 10.0  # Ultra-fast 10 FPS screen capture
    FRAME_DIFF_THRESHOLD = 0.01  # Ultra sensitive to sub-second text changes


    # Multi-monitor settings
    DEFAULT_MONITOR_INDEX = 1  # Primary monitor
    
    # OCR settings
    OCR_LANGUAGES = ['en']
    OCR_GPU = False  # Set True if CUDA PyTorch is available

    # LLM & Translation settings
    LLM_API_URL = os.getenv("LLM_API_URL", "http://localhost:1337/v1/chat/completions")
    LLM_MODEL = os.getenv("LLM_MODEL", "llama-3-8b-instruct")
    LLM_TIMEOUT = 3.0  # seconds
    
    TRANSLATION_SYSTEM_PROMPT = (
        "Sen uzman bir arc oyun ve ekran altyazı çevirmenisin. "
        "Aşağıdaki İngilizce metni doğal, akıcı ve bağlama uygun bir Türkçe ile çevir. "
        "Sadece çevrilmiş Türkçe metni döndür."
    )

    # UI Overlay settings
    OVERLAY_FONT_FAMILY = "Segoe UI"
    OVERLAY_FONT_SIZE = 14
    OVERLAY_TEXT_COLOR = "#FFFFFF"
    OVERLAY_CARD_BG = "rgba(15, 23, 42, 0.90)"  # Sleek dark slate transparent card
    OVERLAY_BORDER_COLOR = "#38BDF8"
    OVERLAY_AUTO_HIDE_SECONDS = 6.0
