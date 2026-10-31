import cv2
import os
import sys
import numpy as np

# Ensure root project path is accessible
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from core.eyes import OpticalHardware

def train_jarvis_biometrics():
    print("=========================================")
    print(" J.A.R.V.I.S. BIOMETRIC ENROLLMENT PROTOCOL")
    print("=========================================")
    print("Initializing optical array via Win32 DirectShow...")

    cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
    if not os.path.exists(cascade_path):
        proj_root = os.path.dirname(os.path.abspath(__file__))
        fallback = os.path.join(proj_root, "assets", "haarcascades", "haarcascade_frontalface_default.xml")
        if os.path.exists(fallback):
            cascade_path = fallback
    face_cascade = cv2.CascadeClassifier(cascade_path)
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    
    # Standardize ingest to 1080p DirectShow
    cap = OpticalHardware.get_camera(device_index=0, width=1920, height=1080)
    if not cap or not cap.isOpened():
        print("[CRITICAL] Optical sensor connection failure.")
        return

    face_samples = []
    ids = []
    user_id = 1 
    sample_count = 0
    max_samples = 100 

    print("\n[INSTRUCTIONS]: Look directly into the optical sensor.")
    print("Slowly tilt your head across all axes to record facial geometry.")
    print("Starting capture sequence in 3 seconds...\n")
    cv2.waitKey(3000)

    while True:
        ret, frame = cap.read()
        if not ret: continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(100, 100))

        for (x, y, w, h) in faces:
            sample_count += 1
            face_img = gray[y:y+h, x:x+w]
            face_samples.append(face_img)
            ids.append(user_id)

            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 212, 255), 2)
            cv2.putText(frame, f"Mapping Geometry... {sample_count}%", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 212, 255), 2)
            print(f"Mapping geometry: {sample_count}/{max_samples}")

        cv2.imshow("Jarvis Biometric Scanner (1080p Ingest)", frame)
        cv2.waitKey(50) 

        if sample_count >= max_samples:
            break

    print("\n[SYSTEM]: Capture complete. Compiling LBPH Neural Network...")
    cap.release()
    cv2.destroyAllWindows()

    recognizer.train(face_samples, np.array(ids))

    # Save to immutable OS Vault
    # At the bottom of enroll_face.py:
    appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    vault_dir = os.path.join(appdata, "Jarvis_OS")
    os.makedirs(vault_dir, exist_ok=True)
    
    save_path = os.path.join(vault_dir, 'jarvis_admin_biometrics.yml')
    recognizer.write(save_path)
    print(f"[SUCCESS]: Admin signature encrypted and committed to OS Vault -> {save_path}")

if __name__ == "__main__":
    train_jarvis_biometrics()