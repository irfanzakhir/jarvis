import cv2
import threading
import base64
import time
import os

# Suppress annoying OpenCV C++ backend warnings in the terminal
os.environ["OPENCV_LOG_LEVEL"] = "SILENT"

class JarvisEyes:
    def __init__(self, camera_index=0):
        print("[Eyes] Initializing Optical Array (Dedicated Thread)...")
        
        # Auto-select backend, no forced DSHOW
        self.cap = cv2.VideoCapture(camera_index)
        
        # AUTO-FALLBACK: If port 0 is blocked, try port 1, then port 2
        if not self.cap.isOpened():
            print("[Eyes] Port 0 offline. Hunting for alternative camera ports...")
            for alt_index in [1, 2]:
                self.cap = cv2.VideoCapture(alt_index)
                if self.cap.isOpened():
                    print(f"[Eyes] Successfully locked onto camera at port {alt_index}.")
                    break

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        self.current_frame = None
        self.running = False
        self.lock = threading.Lock()
        
        if self.cap.isOpened():
            self.running = True
            # Start the background Daemon Thread.
            self.thread = threading.Thread(target=self._update_frame, daemon=True)
            self.thread.start()
        else:
            print("[CRITICAL FAULT] Camera hardware offline or inaccessible.")

    def _update_frame(self):
        """Silently runs in the background keeping the frame instantly fresh."""
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                with self.lock:
                    self.current_frame = frame.copy()
            else:
                # Failsafe: Prevent infinite terminal spam if a frame drops
                time.sleep(0.1)

    def capture_snapshot(self, return_base64=True):
        """Instantly grabs the frame from RAM with 0.00ms latency."""
        if not self.running or self.current_frame is None:
            return None, "Camera offline."

        with self.lock:
            frame = self.current_frame.copy()

        if return_base64:
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