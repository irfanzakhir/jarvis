import speech_recognition as sr
import time
import os
import re
import logging

logger = logging.getLogger("JarvisEars")

class JarvisEars:
    def __init__(self, primary_lang=None, fallback_lang="en-US"):
        self.recognizer = sr.Recognizer()
        self.calibrated = False
        self.primary_lang = primary_lang or os.getenv("SPEECH_LANGUAGE", "en-IN")
        self.fallback_lang = fallback_lang
        
        # Audio tuning for high-accuracy conversational speech recognition:
        # - dynamic_energy_threshold: True allows adapting to changing ambient room noise
        # - pause_threshold: 0.8s prevents cutting off user mid-sentence during thinking pauses
        # - phrase_threshold: 0.3s avoids false triggers on keyboard taps or transient noise
        # - non_speaking_duration: 0.5s preserves trailing word syllables
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.energy_threshold = 350
        self.recognizer.dynamic_energy_adjustment_damping = 0.15
        self.recognizer.dynamic_energy_ratio = 1.5
        self.recognizer.pause_threshold = 0.8
        self.recognizer.phrase_threshold = 0.3
        self.recognizer.non_speaking_duration = 0.5
        
        try:
            self.microphone = sr.Microphone()
        except Exception as e:
            logger.error(f"[Ears] Could not initialize microphone on startup: {e}")
            self.microphone = None

    def _correct_transcript(self, text: str) -> str:
        """
        Applies phonetic normalization and contextual correction to common speech recognition
        misinterpretations of Jarvis wake words, system commands, and regional names.
        """
        if not text:
            return text
        cleaned = text.strip()
        
        rules = [
            # Jarvis name / wake word variants
            (r"\b(service|java|travis|harvest|sharvis|charvis)\b", "jarvis"),
            # Weather intel variants
            (r"\b(whether|leather|weathering)\s+(intel|report|forecast)\b", "weather intel"),
            (r"\b(whether|leather)\b", "weather"),
            # News intel variants
            (r"\b(use|views|new|loose)\s+(intel|report)\b", "news intel"),
            # Map intel variants
            (r"\bmap\s+(into|in\s*tell|in\s*tel)\b", "map intel"),
            # Regional names (Kerala etc.)
            (r"\b(carla|care\s*la|carroll|car roll a)\b", "kerala"),
            # Antigravity variants
            (r"\b(anti\s*gravity|integrate)\b", "antigravity"),
            # Telemetry variants
            (r"\b(tell\s*him\s*a\s*tree|the\s*chemistry)\b", "telemetry"),
            # Uplink variants
            (r"\bup\s*link\b", "uplink"),
        ]
        
        for pattern, repl in rules:
            cleaned = re.sub(pattern, repl, cleaned, flags=re.IGNORECASE)
        return cleaned

    def listen(self):
        """
        Captures speech from the microphone and performs multi-lingual recognition
        with primary/fallback acoustic models and transcript correction.
        """
        if not self.microphone:
            logger.warning("[Ears] Microphone offline. Attempting to reconnect...")
            time.sleep(2)
            self._reboot_mic()
            return None

        try:
            with self.microphone as source:
                if not self.calibrated:
                    try:
                        logger.info("[Ears] Calibrating for room noise (background thread)...")
                        self.recognizer.adjust_for_ambient_noise(source, duration=0.8)
                    except Exception as ce:
                        logger.warning(f"[Ears] Noise calibration notice: {ce}")
                    finally:
                        self.calibrated = True

                logger.debug("[Ears] Listening...")
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=15)
                
            logger.debug("[Ears] Recognizing...")
            raw_text = None
            
            # 1. Try primary acoustic model (en-IN)
            try:
                raw_text = self.recognizer.recognize_google(audio, language=self.primary_lang)
            except sr.UnknownValueError:
                # 2. Fallback to secondary acoustic model (en-US) if primary failed
                if self.fallback_lang and self.fallback_lang != self.primary_lang:
                    try:
                        raw_text = self.recognizer.recognize_google(audio, language=self.fallback_lang)
                    except sr.UnknownValueError:
                        return None
                else:
                    return None

            if raw_text:
                corrected = self._correct_transcript(raw_text)
                logger.info(f"[Ears] Captured: {corrected} (raw: {raw_text})")
                return corrected
            return None
            
        except AttributeError:
            logger.warning("[Ears] Audio stream dropped. Rebooting microphone hardware...")
            self._reboot_mic()
            return None
            
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            logger.warning(f"[Ears] API Request failed: {e}")
            return None
        except Exception as e:
            logger.warning(f"[Ears] Unexpected error: {e}")
            return None

    def _reboot_mic(self):
        try:
            self.microphone = sr.Microphone()
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            self.calibrated = True
            time.sleep(0.5) 
        except Exception as e:
            logger.error(f"[Ears] Failed to reboot microphone: {e}")
            self.microphone = None
