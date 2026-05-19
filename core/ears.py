import speech_recognition as sr
import time

class JarvisEars:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        
        try:
            self.microphone = sr.Microphone()
            with self.microphone as source:
                print("[Ears] Calibrating for room noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1.5)
                
                # --- OPTIMIZATION 3: DISABLE CONTINUOUS CPU AUDIO POLLING ---
                # We already calibrated above, so we don't need it wasting CPU calculating background noise continuously.
                self.recognizer.dynamic_energy_threshold = False
                # Lock the threshold to whatever it just calculated
                self.recognizer.energy_threshold = self.recognizer.energy_threshold + 50 
                
        except Exception as e:
            print(f"[CRITICAL ERROR] Could not initialize microphone on startup: {e}")
            self.microphone = None

    def listen(self):
        if not self.microphone:
            print("[Ears] Microphone offline. Attempting to reconnect...")
            time.sleep(2)
            self._reboot_mic()
            return None

        try:
            with self.microphone as source:
                print("[Ears] Listening...")
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=15)
                
            print("[Ears] Recognizing...")
            text = self.recognizer.recognize_google(audio)
            return text
            
        except AttributeError:
            print("[WARNING] Audio stream dropped. Rebooting microphone hardware...")
            self._reboot_mic()
            return None
            
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"[Ears] API Request failed: {e}")
            return None
        except Exception as e:
            print(f"[Ears] Unexpected error: {e}")
            return None

    def _reboot_mic(self):
        try:
            self.microphone = sr.Microphone()
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                self.recognizer.dynamic_energy_threshold = False
            time.sleep(1) 
        except Exception as e:
            print(f"[ERROR] Failed to reboot microphone: {e}")
            self.microphone = None