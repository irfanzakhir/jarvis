import cv2
import time
import logging

logger = logging.getLogger(__name__)

class OpticalHardware:
    """Universal Win32 DirectShow Camera Factory. Eliminates MSMF frame locks and normalizes sensor geometry."""
    @staticmethod
    def get_camera(device_index=0, width=1920, height=1080, fps=30):
        logger.info(f"[OPTICAL FACTORY]: Requesting camera index {device_index} via Win32 DirectShow...")
        
        # CAP_DSHOW bypasses Microsoft Media Foundation (MSMF) deadlocks on Windows 11
        cap = cv2.VideoCapture(device_index, cv2.CAP_DSHOW)
        
        if not cap.isOpened():
            logger.warning(f"[OPTICAL FACTORY]: Index {device_index} failed DirectShow. Attempting generic driver fallback...")
            cap = cv2.VideoCapture(device_index)
            
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            cap.set(cv2.CAP_PROP_FPS, fps)
            
            # Warm-up purge: Discard initial uncalibrated sensor frames
            for _ in range(5):
                cap.read()
                time.sleep(0.01)
                
            actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            logger.info(f"[OPTICAL FACTORY]: Hardware locked at {actual_w}x{actual_h} @ {fps}FPS.")
        else:
            logger.critical("[OPTICAL FACTORY]: CRITICAL FAULT - Optical hardware array inaccessible.")
            
        return cap

class JarvisEyes:
    """Handles multimodal visual snapshots and screen telemetry parsing."""
    def __init__(self):
        pass