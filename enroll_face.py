import cv2
import os
import numpy as np

def train_jarvis_biometrics():
    print("=========================================")
    print(" J.A.R.V.I.S. BIOMETRIC ENROLLMENT PROTOCOL")
    print("=========================================")
    print("Initializing optical array...")

    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)
    
    # Initialize the LBPH Recognizer (requires opencv-contrib-python)
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    
    cap = cv2.VideoCapture(0) # Change to 1 or 2 if camera fails
    if not cap.isOpened():
        print("[CRITICAL] Cannot connect to camera.")
        return

    face_samples = []
    ids = []
    user_id = 1 # You are User #1 (The Admin)
    sample_count = 0
    max_samples = 100 # 100 frames is enough for a strong lock

    print("\n[INSTRUCTIONS]: Look directly at the camera.")
    print("Slowly tilt your head up, down, left, and right to map all angles.")
    print("Starting capture in 3 seconds...\n")
    cv2.waitKey(3000)

    while True:
        ret, frame = cap.read()
        if not ret: continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(100, 100))

        for (x, y, w, h) in faces:
            sample_count += 1
            # Crop exactly to your face
            face_img = gray[y:y+h, x:x+w]
            face_samples.append(face_img)
            ids.append(user_id)

            # Draw a box so you can see what Jarvis sees
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 212, 255), 2)
            cv2.putText(frame, f"Mapping... {sample_count}%", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 212, 255), 2)
            
            print(f"Mapping geometry: {sample_count}/{max_samples}")

        cv2.imshow("Jarvis Biometric Scanner", frame)
        cv2.waitKey(50) # 50ms delay between captures

        if sample_count >= max_samples:
            break

    print("\n[SYSTEM]: Capture complete. Training Neural Network... Please wait.")
    cap.release()
    cv2.destroyAllWindows()

    # Train the model and save it to the assets folder
    recognizer.train(face_samples, np.array(ids))
    os.makedirs('assets', exist_ok=True)
    recognizer.write('assets/jarvis_admin_biometrics.yml')
    
    print("[SUCCESS]: Admin facial geometry encrypted and saved to assets/jarvis_admin_biometrics.yml")
    print("You may now close this terminal.")

if __name__ == "__main__":
    train_jarvis_biometrics()