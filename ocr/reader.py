import cv2
import numpy as np
import easyocr
import logging
import warnings
import torch
from typing import List, Dict, Any, Tuple
from config import Config

# Suppress PyTorch and EasyOCR CPU warnings cleanly
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
logging.getLogger("easyocr").setLevel(logging.ERROR)

logger = logging.getLogger(__name__)

# Optimize PyTorch CPU threads for maximum parallel OCR performance
try:
    import os
    torch.set_num_threads(min(4, os.cpu_count() or 4))
except Exception:
    pass

class OCRReader:
    """
    EasyOCR and OpenCV based text extraction engine.
    Optimized with fast multi-threading and downscaling for sub-second real-time performance.
    """
    def __init__(self, languages: List[str] = Config.OCR_LANGUAGES, gpu: bool = Config.OCR_GPU):
        self.languages = languages
        self.gpu = gpu
        self._reader = None

    @property
    def reader(self) -> easyocr.Reader:
        if self._reader is None:
            self._reader = easyocr.Reader(self.languages, gpu=self.gpu)
        return self._reader

    def preprocess_image(self, frame: np.ndarray) -> Tuple[np.ndarray, float, float]:
        """
        Fast contrast normalization with CLAHE for sub-second detection of game & video text.
        """
        h, w = frame.shape[:2]
        max_dim = 1440  # Fast 1440 resolution balance for instant OCR
        
        if max(h, w) > max_dim:
            scale = max_dim / float(max(h, w))
            new_w = max(1, int(w * scale))
            new_h = max(1, int(h * scale))
            resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            scale_x = w / float(new_w)
            scale_y = h / float(new_h)
        else:
            resized = frame
            scale_x = 1.0
            scale_y = 1.0

        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        
        # Fast contrast stretch for character readability
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        norm = clahe.apply(gray)
        return norm, scale_x, scale_y

    def is_app_ui_text(self, text: str) -> bool:
        """
        Filters out self-referential text, system hardware specs, or random single-word UI noise
        to prevent cluttering live subtitle output.
        """
        text_lower = text.lower().strip()
        
        ignored_keywords = [
            "arc", "antigravity", "gerçek zamanlı", "ekran çevir", "çeviriyi başlat",
            "çeviriyi durdur", "ekran bölgesi", "kelime kart", "canlı çeviri",
            "bağlantısız", "lokal llm", "locked desktop", "screen capture",
            "[çeviri]", "[en]:", "[tr]:", "pos:", "conf:", "frame #", "izlenecek ekran",
            "kaydedilen kelime", "dışa aktar", "çeviri akış", "durduruldu", "aktif", "arc",
            "tomahawk", "motaerboard", "motherboard", "intel", "amd", "nvidia", "wifi", "geforce"
        ]
        
        for kw in ignored_keywords:
            if kw in text_lower:
                return True
                
        return False

    def extract_text(self, frame: np.ndarray, min_confidence: float = 0.05) -> List[Dict[str, Any]]:
        """
        Runs EasyOCR on image frame with high speed parameters for sub-second translation.
        """
        if frame is None or frame.size == 0:
            return []

        try:
            preprocessed, scale_x, scale_y = self.preprocess_image(frame)
            # Ultra-fast EasyOCR parameters
            raw_results = self.reader.readtext(
                preprocessed,
                low_text=0.3,         # Detect thin/faint text
                text_threshold=0.4,   # Detect stylized fonts
                link_threshold=0.3,   # Link sentence words
                mag_ratio=1.1,        # Fast 1.1x magnification ratio
                contrast_ths=0.02,
                adjust_contrast=0.8,
                paragraph=False
            )

            structured_results = []
            for bbox, text, conf in raw_results:
                clean_text = text.strip()
                if conf < min_confidence or not clean_text or len(clean_text) < 1:
                    continue

                if self.is_app_ui_text(clean_text):
                    continue

                scaled_bbox = []
                for pt in bbox:
                    scaled_bbox.append([int(pt[0] * scale_x), int(pt[1] * scale_y)])

                pts = np.array(scaled_bbox, dtype=np.int32)
                x, y, w, h = cv2.boundingRect(pts)

                structured_results.append({
                    "text": clean_text,
                    "confidence": float(conf),
                    "bbox": scaled_bbox,
                    "rect": (int(x), int(y), int(w), int(h))
                })

            return structured_results
        except Exception as e:
            logger.error(f"Error during OCR extraction: {e}")
            return []


    def group_text_blocks(self, blocks: List[Dict[str, Any]], vertical_threshold: int = 20) -> List[Dict[str, Any]]:
        """
        Combines fragmented text blocks located on the same line or in close proximity
        into unified sentences with combined bounding boxes.
        """
        if not blocks:
            return []

        # Sort blocks by top Y coordinate, then left X coordinate
        sorted_blocks = sorted(blocks, key=lambda b: (b["rect"][1], b["rect"][0]))
        grouped = []
        
        current_group = [sorted_blocks[0]]

        for block in sorted_blocks[1:]:
            prev_rect = current_group[-1]["rect"]
            curr_rect = block["rect"]

            # Check if block is on roughly the same horizontal line
            same_line = abs(curr_rect[1] - prev_rect[1]) <= vertical_threshold
            horizontal_near = (curr_rect[0] - (prev_rect[0] + prev_rect[2])) <= 120

            if same_line and horizontal_near:
                current_group.append(block)
            else:
                grouped.append(self._merge_group(current_group))
                current_group = [block]

        if current_group:
            grouped.append(self._merge_group(current_group))

        return grouped

    def _merge_group(self, group: List[Dict[str, Any]]) -> Dict[str, Any]:
        combined_text = " ".join(b["text"] for b in group)
        min_x = min(b["rect"][0] for b in group)
        min_y = min(b["rect"][1] for b in group)
        max_x = max(b["rect"][0] + b["rect"][2] for b in group)
        max_y = max(b["rect"][1] + b["rect"][3] for b in group)
        
        avg_conf = sum(b["confidence"] for b in group) / len(group)
        
        return {
            "text": combined_text,
            "confidence": avg_conf,
            "rect": (min_x, min_y, max_x - min_x, max_y - min_y)
        }
