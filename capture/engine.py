import numpy as np
import cv2
import mss
import logging
from typing import Optional, Tuple, Dict
from PIL import ImageGrab
from config import Config

logger = logging.getLogger(__name__)

class ScreenCaptureEngine:
    """
    High-performance low-latency screen capture engine using mss (with PIL.ImageGrab fallback).
    Includes frame difference detection to avoid redundant processing.
    """
    def __init__(self, region: Optional[Dict[str, int]] = None, diff_threshold: float = Config.FRAME_DIFF_THRESHOLD):
        # mss 10+ uses MSS class
        self.sct = mss.MSS()
        self.region = region
        self.selected_monitor_index = 1 if len(self.sct.monitors) > 1 else 0
        self.diff_threshold = diff_threshold
        self.prev_gray_frame: Optional[np.ndarray] = None
        self._use_fallback = False

    def get_available_monitors(self) -> list:
        """
        Returns a list of dicts describing all available connected monitors.
        Format: [{'index': i, 'label': 'Monitör 1 (1920x1080)', 'bounds': {...}}, ...]
        """
        monitors_list = []
        for i, mon in enumerate(self.sct.monitors):
            if i == 0 and len(self.sct.monitors) > 1:
                label = f"Tüm Ekranlar Birleşik ({mon['width']}x{mon['height']})"
            else:
                label = f"Monitör {i} ({mon['width']}x{mon['height']})"
                
            monitors_list.append({
                "index": i,
                "label": label,
                "bounds": {
                    "top": int(mon["top"]),
                    "left": int(mon["left"]),
                    "width": int(mon["width"]),
                    "height": int(mon["height"])
                }
            })
        return monitors_list

    def set_monitor_index(self, index: int):
        """
        Sets active monitor to capture.
        """
        if 0 <= index < len(self.sct.monitors):
            self.selected_monitor_index = index
            self.region = None  # Reset region when monitor changes
            self.prev_gray_frame = None

    def get_monitor_bounds(self) -> Dict[str, int]:
        """
        Returns monitor dimensions dict format: {'top': int, 'left': int, 'width': int, 'height': int}.
        """
        if self.region:
            return self.region
        
        idx = self.selected_monitor_index
        if idx < len(self.sct.monitors):
            mon = self.sct.monitors[idx]
        else:
            mon = self.sct.monitors[0]
            
        return {
            "top": int(mon["top"]),
            "left": int(mon["left"]),
            "width": int(mon["width"]),
            "height": int(mon["height"])
        }

    def capture_frame(self) -> np.ndarray:
        """
        Ultra-fast low-latency DirectX / MSS screen capture (<3ms frame capture).
        """
        target_monitor = self.get_monitor_bounds()
        
        # Primary grab method using MSS (DirectX / MemoryMapped C extension - sub-3ms ultra fast!)
        try:
            sct_img = self.sct.grab(target_monitor)
            frame_bgra = np.array(sct_img)
            frame_bgr = cv2.cvtColor(frame_bgra, cv2.COLOR_BGRA2BGR)
            return frame_bgr
        except Exception:
            # Fallback to PIL.ImageGrab if MSS encounters display handle loss
            try:
                left = target_monitor["left"]
                top = target_monitor["top"]
                width = target_monitor["width"]
                height = target_monitor["height"]
                bbox = (left, top, left + width, top + height)
                pil_img = ImageGrab.grab(bbox=bbox, all_screens=True)
                frame_rgb = np.array(pil_img)
                return cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            except Exception:
                return np.zeros((target_monitor.get("height", 720), target_monitor.get("width", 1280), 3), dtype=np.uint8)

    def has_changed(self, frame: np.ndarray) -> Tuple[bool, float]:
        """
        Fast frame difference detection. Avoids redundant OCR scanning when screen text is static.
        """
        if frame is None or frame.size == 0:
            return False, 0.0

        # Downscale for instant <1ms diff check
        small_gray = cv2.cvtColor(cv2.resize(frame, (320, 180), interpolation=cv2.INTER_NEAREST), cv2.COLOR_BGR2GRAY)
        
        if self.prev_gray_frame is None or self.prev_gray_frame.shape != small_gray.shape:
            self.prev_gray_frame = small_gray
            return True, 100.0

        diff = cv2.absdiff(self.prev_gray_frame, small_gray)
        _, diff_thresh = cv2.threshold(diff, 12, 255, cv2.THRESH_BINARY)
        
        changed_pixels = np.count_nonzero(diff_thresh)
        change_percentage = (changed_pixels / float(small_gray.size)) * 100.0

        has_changed_flag = change_percentage >= 0.05
        if has_changed_flag:
            self.prev_gray_frame = small_gray

        return has_changed_flag, change_percentage

    def close(self):
        """
        Clean up resources.
        """
        try:
            self.sct.close()
        except Exception:
            pass

