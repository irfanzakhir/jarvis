import cv2
import math
import os
import urllib.request
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

class KineticEngine:
    def __init__(self, smoothing_factor=0.2, pinch_engage_threshold=0.04, pinch_release_threshold=0.055):
        print("[SYSTEM]: Initializing MediaPipe Tasks API (Modern Architecture)...")
        
        self.model_path = "hand_landmarker.task"
        if not os.path.exists(self.model_path):
            print(f"[SYSTEM]: Downloading {self.model_path} from Google CDN...")
            url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
            urllib.request.urlretrieve(url, self.model_path)
            print("[SYSTEM]: Download complete.")

        base_options = python.BaseOptions(model_asset_path=self.model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=1, 
            min_hand_detection_confidence=0.7,
            min_hand_presence_confidence=0.7,
            min_tracking_confidence=0.7
        )
        self.detector = vision.HandLandmarker.create_from_options(options)
        
        self.smoothing_factor = smoothing_factor
        
        self.pinch_engage_threshold = pinch_engage_threshold 
        self.pinch_release_threshold = pinch_release_threshold 
        
        # Dual-State Memory
        self.is_left_pinched = False
        self.is_right_pinched = False
        
        self.prev_x = None
        self.prev_y = None

    def process_frame(self, frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        detection_result = self.detector.detect(mp_image)
        
        data = None
        
        if detection_result.hand_landmarks:
            hand_landmarks = detection_result.hand_landmarks[0]
            h, w, _ = frame.shape
            
            # Map the Three Trigger Nodes
            thumb_tip = hand_landmarks[4]
            index_tip = hand_landmarks[8]
            middle_tip = hand_landmarks[12]
            
            # 1. Cursor Coordinate Calculation (Always tracks the Index Finger)
            raw_x = int(index_tip.x * w)
            raw_y = int(index_tip.y * h)
            
            if self.prev_x is None or self.prev_y is None:
                smooth_x, smooth_y = raw_x, raw_y
            else:
                smooth_x = int(self.prev_x + self.smoothing_factor * (raw_x - self.prev_x))
                smooth_y = int(self.prev_y + self.smoothing_factor * (raw_y - self.prev_y))
            
            self.prev_x, self.prev_y = smooth_x, smooth_y
            
            # 2. Dual-Distance Math
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
            # VISUAL DEBUGGING
            # ==========================================
            # Cursor Orb
            orb_color = (255, 255, 0) # Default Cyan
            if self.is_left_pinched: orb_color = (0, 0, 255) # Red for Left Click
            elif self.is_right_pinched: orb_color = (0, 255, 0) # Green for Right Click
            cv2.circle(frame, (smooth_x, smooth_y), 12, orb_color, cv2.FILLED)
            
            # Laser Lines for Tension visualization
            thumb_x, thumb_y = int(thumb_tip.x * w), int(thumb_tip.y * h)
            middle_x, middle_y = int(middle_tip.x * w), int(middle_tip.y * h)
            
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
                "frame_w": w,
                "frame_h": h
            }
            
        return frame, data