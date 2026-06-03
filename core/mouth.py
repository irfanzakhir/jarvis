import pygame
import asyncio
import edge_tts
import io
import threading

class JarvisMouth:
    def __init__(self):
        # Initialize the audio mixer for playback
        pygame.mixer.init()
        self._is_speaking = False

    def is_speaking(self):
        """Returns True if Jarvis is currently talking."""
        return self._is_speaking

    def stop(self):
        """Instantly cuts off the audio playback."""
        self._is_speaking = False
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()

    def speak(self, text):
        # SELF-HEALING FAILSAFE: Ensure mixer is alive before speaking
        if not pygame.mixer.get_init():
            pygame.mixer.init()
            
        print("[Mouth] Generating high-speed neural audio (In-Memory)...")
        self._is_speaking = True
        
        def tts_task():
            async def generate_audio():
                communicate = edge_tts.Communicate(text, "en-GB-RyanNeural")
                # ... [keep the rest of your tts_task exactly the same]
                audio_data = b""
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_data += chunk["data"]
                return audio_data

            try:
                # 1. Isolate the async loop to this specific thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                audio_bytes = loop.run_until_complete(generate_audio())
                loop.close()
                
                # 2. Convert bytes into a virtual file object in RAM
                audio_stream = io.BytesIO(audio_bytes)
                
                # 3. Load and play directly from RAM
                pygame.mixer.music.load(audio_stream)
                pygame.mixer.music.play()
                
                # 4. Zero-Lag Intercept Loop
                while pygame.mixer.music.get_busy() and self._is_speaking:
                    pygame.time.Clock().tick(10) 
                    
            except Exception as e:
                print(f"[Mouth] Audio playback error: {e}")
                
            finally:
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
                self._is_speaking = False
                
        # Spawn the isolated thread and block until finished so the mic doesn't hear Jarvis
        t = threading.Thread(target=tts_task, daemon=True)
        t.start()
        t.join()