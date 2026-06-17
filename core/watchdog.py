import cv2
import time
import numpy as np
import threading
import logging
from ultralytics import YOLO

logger = logging.getLogger(__name__)

class VisionWatchdog:
    def __init__(self, command_queue, eyes):
        self.command_queue = command_queue
        self.eyes = eyes 
        self.is_active = False
        self.watch_target = None
        self.yolo_model = None
        self.thread = None

    def start_watching(self, target_object="person"):
        """Activates the background optical guard with light weights."""
        if self.is_active:
            logger.warning("[WATCHDOG]: Watchdog is already active.")
            return
        
        self.watch_target = target_object.lower()
        self.is_active = True
        
        if self.yolo_model is None:
            logger.info("[WATCHDOG]: Reverting to ultra-lightweight YOLOv8-Nano to protect hardware...")
            self.yolo_model = YOLO("yolov8n.pt") # Back to ~6MB ultra-fast weights

        self.thread = threading.Thread(target=self._cascade_vision_loop, daemon=True)
        self.thread.start()
        logger.info(f"[WATCHDOG]: Motion-Cropped Pipeline active. Target: {self.watch_target}")

    def stop_watching(self):
        """Disarms the optical guard and releases hardware."""
        self.is_active = False
        logger.info("[WATCHDOG]: Disarmed and offline.")

    def _cascade_vision_loop(self):
        base_frame, error = self.eyes.capture_snapshot(return_base64=False)
        if base_frame is None:
            logger.error("[WATCHDOG]: Failed to retrieve base frame.")
            self.is_active = False
            return

        base_gray = cv2.cvtColor(base_frame, cv2.COLOR_BGR2GRAY)
        base_gray = cv2.GaussianBlur(base_gray, (21, 21), 0)

        while self.is_active:
            frame, error = self.eyes.capture_snapshot(return_base64=False)
            if frame is None:
                time.sleep(0.5)
                continue

            # LAYER 1: Standard low-power math
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            frame_delta = cv2.absdiff(base_gray, gray)
            thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
            thresh = cv2.dilate(thresh, None, iterations=2)

            # Find the physical boundaries (contours) of the movement
            contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                # If the movement area is big enough to matter (prevents camera static noise)
                if cv2.contourArea(contour) > 800: 
                    # Extract the exact coordinates of the moving object
                    x, y, w, h = cv2.boundingRect(contour)
                    
                    # CROP THE FRAME: Isolate just the moving object!
                    cropped_roi = frame[y:y+h, x:x+w]
                    
                    if cropped_roi.size > 0:
                        logger.info("[WATCHDOG]: Motion detected. Running micro-inference on cropped ROI.")
                        
                        # LAYER 2: Run ultra-lightweight YOLO on ONLY the tiny cropped image
                        results = self.yolo_model(cropped_roi, conf=0.20, verbose=False)
                        detected_objects = []

                        for r in results:
                            for c in r.boxes.cls:
                                detected_objects.append(self.yolo_model.names[int(c)].lower())

                        logger.info(f"[WATCHDOG]: Cropped signatures detected: {detected_objects}")

                        if self.watch_target in detected_objects:
                            alert_msg = f"watchdog_alert: {self.watch_target}"
                            self.command_queue.put(alert_msg)
                            self.stop_watching()
                            return # Exit loop immediately

            base_gray = gray
            time.sleep(0.4) # Slightly increased sleep to completely eliminate CPU stress