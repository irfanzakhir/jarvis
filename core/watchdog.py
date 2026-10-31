"""
J.A.R.V.I.S. 2.0 - Optical Watchdog Guard
Ultralight motion-triggered cascade detector.
Uses OpenCV HOG People Detector and Haar cascades as primary zero-overhead,
100% offline engines, with optional YOLO fallback for generic COCO objects.
"""

import cv2
import time
import numpy as np
import logging

logger = logging.getLogger(__name__)

class VisionWatchdog:
    def __init__(self, command_queue=None, eyes=None, alert_callback=None):
        self.command_queue = command_queue
        self.eyes = eyes
        self.alert_callback = alert_callback
        self.is_active = False
        self.watch_target = "person"
        
        self.base_gray = None
        self.last_check_time = 0.0
        self.check_interval = 0.30  # ~3.3 FPS inference check rate
        
        # Built-in lightweight OpenCV models (Zero dependencies, offline)
        self._hog = None
        self._face_cascade = None
        
        # Optional YOLO lazy-loader
        self._yolo = None
        self._yolo_attempted = False

    def arm(self, target_object="person"):
        """Arms the optical watchdog."""
        self.watch_target = (target_object or "person").lower().strip()
        self.is_active = True
        self.base_gray = None  # Reset background baseline
        logger.info(f"[WATCHDOG]: Armed. Target locked: '{self.watch_target}'")

    def disarm(self):
        """Disarms the optical watchdog."""
        self.is_active = False
        self.base_gray = None
        logger.info("[WATCHDOG]: Disarmed and offline.")

    # Backwards-compatibility aliases
    def start_watching(self, target_object="person"):
        self.arm(target_object)

    def stop_watching(self):
        self.disarm()

    def _init_opencv_detectors(self):
        if self._hog is None:
            self._hog = cv2.HOGDescriptor()
            self._hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        if self._face_cascade is None:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self._face_cascade = cv2.CascadeClassifier(cascade_path)

    def _detect_in_roi(self, roi):
        """Runs detection on moving region of interest."""
        target = self.watch_target
        is_person_target = target in [
            "person", "human", "someone", "intruder", "people",
            "face", "anybody", "motion", "movement"
        ]
        
        # 1. Primary: OpenCV HOG + Haar cascade for person/face detection
        if is_person_target:
            self._init_opencv_detectors()
            
            # Haar face check
            gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
            faces = self._face_cascade.detectMultiScale(
                gray_roi, scaleFactor=1.15, minNeighbors=3, minSize=(30, 30)
            )
            if len(faces) > 0:
                return True, "face"
                
            # HOG people detector check
            h, w = roi.shape[:2]
            if h >= 96 and w >= 48:
                resized = cv2.resize(roi, (64, 128)) if (h < 128 or w < 64) else roi
                rects, _ = self._hog.detectMultiScale(
                    resized, winStride=(8, 8), padding=(4, 4), scale=1.05
                )
                if len(rects) > 0:
                    return True, "person"
            
            # If target was just generic motion / movement, contour presence is enough
            if target in ["motion", "movement"]:
                return True, "motion"

        # 2. Optional: YOLO for generic COCO objects (e.g. cat, dog, phone, bottle)
        if not self._yolo_attempted:
            self._yolo_attempted = True
            try:
                from ultralytics import YOLO
                self._yolo = YOLO("yolov8n.pt")
                logger.info("[WATCHDOG]: YOLOv8-Nano engine loaded.")
            except Exception:
                self._yolo = None

        if self._yolo is not None:
            results = self._yolo(roi, conf=0.25, verbose=False)
            for r in results:
                for c in r.boxes.cls:
                    detected_name = self._yolo.names[int(c)].lower()
                    if target in detected_name or detected_name in target:
                        return True, detected_name

        return False, None

    def process_frame(self, frame):
        """Processes a single camera frame from VisionMaster multiplexer."""
        if not self.is_active or frame is None:
            return None

        now = time.time()
        if now - self.last_check_time < self.check_interval:
            return None
        self.last_check_time = now

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self.base_gray is None:
            self.base_gray = gray.astype("float")
            return None

        # Compute running background difference
        frame_delta = cv2.absdiff(cv2.convertScaleAbs(self.base_gray), gray)
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)

        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            if cv2.contourArea(contour) > 1000:  # Significant movement threshold
                x, y, w, h = cv2.boundingRect(contour)
                cropped_roi = frame[y:y+h, x:x+w]
                if cropped_roi.size > 0:
                    detected, name = self._detect_in_roi(cropped_roi)
                    if detected:
                        alert_msg = f"watchdog_alert: {self.watch_target}"
                        logger.info(f"[WATCHDOG ALERT]: Detected {name} matching target '{self.watch_target}'!")
                        if self.command_queue:
                            self.command_queue.put(alert_msg)
                        if self.alert_callback:
                            self.alert_callback(self.watch_target)
                        self.disarm()
                        return self.watch_target

        # Update running background model
        cv2.accumulateWeighted(gray, self.base_gray, 0.05)
        return None
