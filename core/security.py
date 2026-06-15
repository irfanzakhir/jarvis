import cv2
import os

class BiometricSecurity:
    def __init__(self):
        print("[Security] Initializing Advanced LBPH Facial Recognition...")
        
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
        # Load the encrypted facial signature we just trained
        model_path = 'assets/jarvis_admin_biometrics.yml'
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.is_armed = False
        
        if not os.path.exists(model_path):
            print("[Security Warning] Biometric file not found. Run enroll_face.py first!")
        else:
            self.recognizer.read(model_path)
            self.is_armed = True
            print("[Security] Admin biometric signature loaded successfully.")

        # Lower is stricter. 60 is usually a very solid match. 
        # If Jarvis doesn't recognize you easily, increase this to 70 or 80.
        self.confidence_threshold = 40 

    def scan_for_presence(self, frame):
        """Authenticates the frame against the Admin's facial geometry."""
        if frame is None or not self.is_armed: 
            return False
        
        try:
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray_frame = cv2.equalizeHist(gray_frame)
            
            faces = self.face_cascade.detectMultiScale(gray_frame, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100))
            
            for (x, y, w, h) in faces:
                # We found a face. Now we crop it and ask the AI "Who is this?"
                face_roi = gray_frame[y:y+h, x:x+w]
                id_, confidence = self.recognizer.predict(face_roi)
                
                # In LBPH, 'confidence' is actually 'distance'. Closer to 0 means a perfect match.
                if confidence <= self.confidence_threshold:
                    print(f"[Security] ADMIN RECOGNIZED. Identity Match Confidence: {round(100 - confidence)}%")
                    return True # Unlocks the system
                else:
                    print(f"[Security] UNKNOWN ENTITY DETECTED. Rejecting unlock. (Deviation: {round(confidence)})")
                    
        except Exception as e:
            print(f"[Security Fault] {e}")
            
        return False # Stays locked if no face, or wrong face is seen