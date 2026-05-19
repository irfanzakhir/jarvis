import pygame
import asyncio
import edge_tts
import io

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
        print("[Mouth] Generating high-speed neural audio (In-Memory)...")
        self._is_speaking = True
        
        async def generate_audio():
            # Generate the voice using Edge-TTS
            communicate = edge_tts.Communicate(text, "en-GB-RyanNeural")
            audio_data = b""
            # Stream the bytes directly into memory instead of saving to a file
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            return audio_data

        try:
            # 1. Generate the raw audio bytes
            audio_bytes = asyncio.run(generate_audio())
            
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