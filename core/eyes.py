import cv2
import threading
import base64
import time # NEW: Needed for the failsafe delay

class JarvisEyes:
    def __init__(self, camera_index=0):
        print("[Eyes] Initializing Optical Array (Dedicated Thread)...")
        
        # FIX 1: Added cv2.CAP_DSHOW to bypass the buggy MSMF Windows backend
        self.cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        self.current_frame = None
        self.running = False
        self.lock = threading.Lock()
        
        if self.cap.isOpened():
            self.running = True
            # Start the background Daemon Thread. It dies automatically when the app closes.
            self.thread = threading.Thread(target=self._update_frame, daemon=True)
            self.thread.start()
        else:
            print("[CRITICAL FAULT] Camera hardware offline or inaccessible.")

    def _update_frame(self):
        """Silently runs in the background keeping the frame instantly fresh."""
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                # Thread-safe write
                with self.lock:
                    self.current_frame = frame.copy()
            else:
                # FIX 2: If the camera drops a frame, wait 0.1 seconds before trying again 
                # to prevent infinite terminal spamming!
                time.sleep(0.1)

    def capture_snapshot(self, return_base64=True):
        """Instantly grabs the frame from RAM with 0.00ms latency."""
        if not self.running or self.current_frame is None:
            return None, "Camera offline."

        # Thread-safe read
        with self.lock:
            frame = self.current_frame.copy()

        if return_base64:
            # Compress and encode directly in RAM! No physical files written.
            ret, buffer = cv2.imencode('.jpg', frame)
            if ret:
                encoded_string = base64.b64encode(buffer).decode('utf-8')
                return encoded_string, None
            return None, "Memory encoding failed."
            
        return frame, None

    def shutdown(self):
        """Safely releases the hardware thread."""
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=1.0)
        if self.cap.isOpened():
            self.cap.release() 