import sys
import os
import cv2
import math
import urllib.request
import time
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

class KineticEngine:
    def __init__(self, smoothing_factor=0.3, pinch_engage_threshold=0.04, pinch_release_threshold=0.055):
        print("[SYSTEM]: Initializing MediaPipe Tasks API (High-Speed Video Architecture)...")

        # =====================================================================
        # BULLETPROOF ASSET RESOLVER: Detects whether we are Frozen or Live
        # =====================================================================
        if hasattr(sys, '_MEIPASS'):
            self.model_path = os.path.join(sys._MEIPASS, "assets", "hand_landmarker.task")
        else:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.model_path = os.path.join(project_root, "assets", "hand_landmarker.task")

        if not os.path.exists(self.model_path):
            print(f"[SYSTEM]: Downloading model to {self.model_path}...")
            url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
            urllib.request.urlretrieve(url, self.model_path)
            print("[SYSTEM]: Download complete.")

        with open(self.model_path, "rb") as f:
            model_bytes = f.read()

        # --- OPTIMIZATION 1: Switch to VIDEO mode for temporal tracking ---
        base_options = python.BaseOptions(model_asset_buffer=model_bytes)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO, 
            num_hands=1, 
            min_hand_detection_confidence=0.5, # Lowered slightly for faster acquisition
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.detector = vision.HandLandmarker.create_from_options(options)

        self.smoothing_factor = smoothing_factor
        self.pinch_engage_threshold = pinch_engage_threshold
        self.pinch_release_threshold = pinch_release_threshold

        self.is_left_pinched = False
        self.is_right_pinched = False
        self.prev_x = None
        self.prev_y = None
        self.last_timestamp = 0

    def process_frame(self, frame):
        original_h, original_w, _ = frame.shape
        
        # --- OPTIMIZATION 2: AI Downscale Pipeline ---
        # We shrink the frame strictly for the neural network to chew on. 
        # This drastically cuts CPU latency while keeping the output accurate.
        ai_frame = cv2.resize(frame, (640, 480))
        rgb_frame = cv2.cvtColor(ai_frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Monotonically increasing timestamp required for VIDEO mode
        timestamp_ms = time.time_ns() // 1_000_000
        if timestamp_ms <= self.last_timestamp:
            timestamp_ms = self.last_timestamp + 1
        self.last_timestamp = timestamp_ms

        # Execute temporal tracking
        detection_result = self.detector.detect_for_video(mp_image, timestamp_ms)

        data = None

        if detection_result.hand_landmarks:
            hand_landmarks = detection_result.hand_landmarks[0]

            # Map the Three Trigger Nodes
            thumb_tip = hand_landmarks[4]
            index_tip = hand_landmarks[8]
            middle_tip = hand_landmarks[12]

            # 1. Cursor Coordinate Calculation (Mapped back to original resolution)
            raw_x = int(index_tip.x * original_w)
            raw_y = int(index_tip.y * original_h)

            if self.prev_x is None or self.prev_y is None:
                smooth_x, smooth_y = raw_x, raw_y
            else:
                smooth_x = int(self.prev_x + self.smoothing_factor * (raw_x - self.prev_x))
                smooth_y = int(self.prev_y + self.smoothing_factor * (raw_y - self.prev_y))

            self.prev_x, self.prev_y = smooth_x, smooth_y

            # 2. Dual-Distance Math (Using normalized coordinates for consistency)
            dist_index = math.hypot(index_tip.x - thumb_tip.x, index_tip.y - thumb_tip.y)
            dist_middle = math.hypot(middle_tip.x - thumb_tip.x, middle_tip.y - thumb_tip.y)

            # 3. Left Click Hysteresis (Index + Thumb)
            if not self.is_left_pinched:
                if dist_index < self.pinch_engage_threshold:
                    self.is_left_pinched = True
            else:
                if dist_index > self.pinch_release_threshold:
                    self.is_left_pinched = False

            # 4. Right Click Hysteresis (Middle + Thumb)
            if not self.is_right_pinched:
                if dist_middle < self.pinch_engage_threshold:
                    self.is_right_pinched = True
            else:
                if dist_middle > self.pinch_release_threshold:
                    self.is_right_pinched = False

            # ==========================================
            # VISUAL DEBUGGING (Drawn on the High-Res Frame)
            # ==========================================
            orb_color = (255, 255, 0)  # Default Cyan
            if self.is_left_pinched:
                orb_color = (0, 0, 255)  # Red for Left Click
            elif self.is_right_pinched:
                orb_color = (0, 255, 0)  # Green for Right Click
            cv2.circle(frame, (smooth_x, smooth_y), 12, orb_color, cv2.FILLED)

            thumb_x, thumb_y = int(thumb_tip.x * original_w), int(thumb_tip.y * original_h)
            middle_x, middle_y = int(middle_tip.x * original_w), int(middle_tip.y * original_h)

            if self.is_left_pinched:
                cv2.line(frame, (smooth_x, smooth_y), (thumb_x, thumb_y), (0, 0, 255), 3)
            if self.is_right_pinched:
                cv2.line(frame, (middle_x, middle_y), (thumb_x, thumb_y), (0, 255, 0), 3)

            # Pack the updated telemetry
            data = {
                "x": smooth_x,
                "y": smooth_y,
                "is_left_pinched": self.is_left_pinched,
                "is_right_pinched": self.is_right_pinched,
                "frame_w": original_w,
                "frame_h": original_h,
            }

        return frame, data