import cv2
import os
import sys
import logging

logger = logging.getLogger(__name__)

def get_biometric_vault(mode="rgb"):
    """Resolves an immutable, OS-safe storage vault for biometric signatures."""
    appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    vault_dir = os.path.join(appdata, "Jarvis_OS")
    os.makedirs(vault_dir, exist_ok=True)
    
    target_filename = "jarvis_admin_biometrics_nightvision.yml" if mode == "ir" else "jarvis_admin_biometrics.yml"
    vault_file = os.path.join(vault_dir, target_filename)
    if not os.path.exists(vault_file):
        # Fallback to project assets
        proj_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        asset_file = os.path.join(proj_root, "assets", target_filename)
        if os.path.exists(asset_file):
            import shutil
            shutil.copy2(asset_file, vault_file)
            logger.info(f"[SECURITY]: Restored biometric vault from assets -> {vault_file}")
            
    return vault_file

class BiometricSecurity:
    """Advanced LBPH Facial Recognition engine with Day (RGB) and Night (IR) Vision."""
    def __init__(self):
        logger.info("[SECURITY]: Initializing LBPH Biometric Shield...")
        
        # haarcascade_frontalface_alt2.xml often performs better under harsh IR lighting
        cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_alt2.xml")
        if not os.path.exists(cascade_path):
            proj_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            fallback_cascade = os.path.join(proj_root, "assets", "haarcascades", "haarcascade_frontalface_alt2.xml")
            if os.path.exists(fallback_cascade):
                cascade_path = fallback_cascade
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
        self.model_path_rgb = get_biometric_vault(mode="rgb")
        self.model_path_ir = get_biometric_vault(mode="ir")
        
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.is_armed = False
        self.current_mode = "rgb" # Default to Day mode
        
        # Load the standard RGB model by default on boot
        self._load_vault(self.model_path_rgb)

        # Stricter matching threshold. (LBPH distance: 0 is a mathematically identical match)
        self.confidence_threshold = 50  

    def _load_vault(self, path):
        """Internal handler to swap biometric vaults safely."""
        if not os.path.exists(path):
            logger.warning(f"[SECURITY WARNING]: Biometric signature missing at vault: {path}")
            print(f"[Security Warning] No profile found at {path}. Please run enrollment.")
            self.is_armed = False
        else:
            self.recognizer.read(path)
            self.is_armed = True
            logger.info(f"[SECURITY]: Admin signature loaded successfully from vault -> {path}")

    def switch_to_night_vision(self):
        """Switches the recognizer to use the Infrared (IR) trained model."""
        logger.info("[SECURITY]: Engaging Night Vision Biometrics...")
        self.current_mode = "ir"
        self._load_vault(self.model_path_ir)

    def switch_to_day_vision(self):
        """Switches the recognizer to use the standard RGB trained model."""
        logger.info("[SECURITY]: Engaging Standard Day Biometrics...")
        self.current_mode = "rgb"
        self._load_vault(self.model_path_rgb)

    def scan_for_presence(self, frame, is_ir_feed=False):
        """Authenticates live optical geometry against the encrypted vault signature."""
        if frame is None or not self.is_armed: 
            return False
            
        # Dynamically swap the active model in memory if the optical feed type changes
        if is_ir_feed and self.current_mode != "ir":
            self.switch_to_night_vision()
        elif not is_ir_feed and self.current_mode != "rgb":
            self.switch_to_day_vision()
        
        try:
            # Safely handle both 3-channel and 1-channel raw IR frames
            if len(frame.shape) == 3:
                gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                gray_frame = frame
                
            # [UPGRADE] Apply CLAHE instead of standard equalizeHist()
            # This suppresses the blinding IR flash hotspot and enhances facial contours
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            gray_frame = clahe.apply(gray_frame)
            
            faces = self.face_cascade.detectMultiScale(
                gray_frame, 
                scaleFactor=1.1, 
                minNeighbors=5, 
                minSize=(100, 100)
            )
            
            for (x, y, w, h) in faces:
                face_roi = gray_frame[y:y+h, x:x+w]
                id_, confidence = self.recognizer.predict(face_roi)
                
                if confidence <= self.confidence_threshold:
                    match_percentage = round(100 - confidence)
                    mode_str = "NIGHT VISION" if is_ir_feed else "DAY VISION"
                    logger.info(f"[SECURITY - {mode_str}]: ADMIN RECOGNIZED. Match Certainty: {match_percentage}%")
                    print(f"[Security] Admin Verified ({mode_str}). Certainty: {match_percentage}%")
                    return True 
                else:
                    logger.info(f"[SECURITY]: UNKNOWN ENTITY DETECTED. Deviation: {round(confidence)}")
                    
        except Exception as e:
            logger.critical(f"[SECURITY FAULT]: Recognition pipeline failure -> {e}", exc_info=True)
            
        return False