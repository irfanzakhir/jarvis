"""
J.A.R.V.I.S. 2.0 - Neural Speech Synthesis Module (Pipelined Streaming Edition)
Inspired by Friday Mark 2's pipelined execution architecture.
Synthesizes and streams speech in sentence-level chunks to drastically reduce
Time-To-First-Audio (TTFA) from ~3.5s down to ~500ms.
"""

import pygame
import asyncio
import edge_tts
import io
import threading
import queue
import re
import time

class JarvisMouth:
    def __init__(self, voice="en-GB-RyanNeural"):
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        self.voice = voice
        self._is_speaking = False
        self._stop_requested = threading.Event()
        self._is_paused = threading.Event()
        self._lock = threading.Lock()
        self._audio_cache = {}
        self._cache_lock = threading.Lock()
        # Pre-warm common system response phrases in background for instant (0ms) playback
        threading.Thread(target=self._prewarm_cache, daemon=True).start()

    def _prewarm_cache(self):
        """Asynchronously pre-synthesizes high-frequency system phrases into RAM concurrently."""
        common_phrases = [
            "System locked. Awaiting biometric authentication.",
            "Good to see you, sir. Importing preferences from home interface.",
            "Standing by. Optical sensors armed, sir.",
            "Standing by, sir.",
            "Scanning active display visual telemetry now, sir.",
            "Scanning the active screen, sir.",
            "Optical watchdog armed. Monitoring for person, sir.",
            "Optical watchdog disarmed. Sensors returned to idle, sir.",
            "Increasing audio gain, sir.",
            "Decreasing audio gain, sir.",
            "Toggling system mute state.",
            "Screen state captured and archived, sir."
        ]
        from concurrent.futures import ThreadPoolExecutor
        def _prewarm_one(phrase):
            try:
                if phrase not in self._audio_cache:
                    raw = self._synthesize_sentence_sync(phrase, use_cache=False)
                    if raw:
                        with self._cache_lock:
                            self._audio_cache[phrase] = raw
            except Exception:
                pass

        with ThreadPoolExecutor(max_workers=4) as executor:
            executor.map(_prewarm_one, common_phrases)

    def is_speaking(self):
        """Returns True if Jarvis is currently talking."""
        return self._is_speaking

    def stop(self):
        """Instantly cuts off the audio playback."""
        self._is_paused.clear()
        self._stop_requested.set()
        self._is_speaking = False
        if pygame.mixer.get_init():
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass

    def pause(self):
        """Pauses the current speech playback."""
        self._is_paused.set()
        if pygame.mixer.get_init():
            try:
                pygame.mixer.music.pause()
            except Exception:
                pass

    def resume(self):
        """Resumes paused speech playback."""
        if self._is_paused.is_set():
            self._is_paused.clear()
            if pygame.mixer.get_init():
                try:
                    pygame.mixer.music.unpause()
                except Exception:
                    pass

    def _split_sentences(self, text: str) -> list:
        """Splits text into spoken sentence units while preserving punctuation."""
        if not text:
            return []
        # Remove markdown stars and hashes
        cleaned = text.replace("*", "").replace("#", "").strip()
        # Split on sentence terminals followed by space or newline
        chunks = re.split(r'(?<=[.!?])\s+', cleaned)
        sentences = [c.strip() for c in chunks if c.strip()]
        return sentences if sentences else [cleaned]

    def _synthesize_sentence_sync(self, sentence: str, use_cache=True) -> bytes:
        """Asynchronously synthesizes a single sentence to raw MP3 bytes in memory."""
        if use_cache:
            with self._cache_lock:
                if sentence in self._audio_cache:
                    return self._audio_cache[sentence]

        async def _gen():
            communicate = edge_tts.Communicate(sentence, self.voice)
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            return audio_data

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            raw_audio = loop.run_until_complete(_gen())
            if use_cache and raw_audio:
                with self._cache_lock:
                    if len(self._audio_cache) < 64:  # Cap at 64 entries (~1MB RAM)
                        self._audio_cache[sentence] = raw_audio
            return raw_audio
        finally:
            loop.close()

    def speak(self, text: str):
        """
        Pipelined sentence playback:
        Synthesizes sentence 1 and begins playback immediately (~400-500ms TTFA),
        while pre-fetching subsequent sentences in a background queue.
        Blocks the calling thread until the entire passage has been spoken.
        """
        if not text or not text.strip():
            return

        with self._lock:
            # Self-healing failsafe for mixer
            if not pygame.mixer.get_init():
                pygame.mixer.init()

            self._stop_requested.clear()
            self._is_speaking = True

            sentences = self._split_sentences(text)
            if not sentences:
                self._is_speaking = False
                return

            # Pipeline queue: holds (sentence_idx, audio_bytes_or_None)
            audio_queue = queue.Queue(maxsize=3)

            # Background pre-fetch producer thread
            def producer():
                for s in sentences:
                    if self._stop_requested.is_set():
                        break
                    try:
                        raw_bytes = self._synthesize_sentence_sync(s)
                        while not self._stop_requested.is_set():
                            try:
                                audio_queue.put(raw_bytes, timeout=0.2)
                                break
                            except queue.Full:
                                continue
                    except Exception as e:
                        print(f"[Mouth] TTS synthesis error: {e}")
                        while not self._stop_requested.is_set():
                            try:
                                audio_queue.put(None, timeout=0.2)
                                break
                            except queue.Full:
                                continue
                while not self._stop_requested.is_set():
                    try:
                        audio_queue.put(StopIteration, timeout=0.2)
                        break
                    except queue.Full:
                        continue

            producer_thread = threading.Thread(target=producer, daemon=True)
            producer_thread.start()

            # Consumer: plays audio chunks sequentially as they arrive
            try:
                while not self._stop_requested.is_set():
                    item = audio_queue.get()
                    if item is StopIteration:
                        break
                    if item is None:
                        continue

                    # Load audio from RAM buffer
                    stream = io.BytesIO(item)
                    pygame.mixer.music.load(stream)
                    pygame.mixer.music.play()

                    # Wait while currently playing sentence finishes or paused
                    while (pygame.mixer.music.get_busy() or self._is_paused.is_set()) and not self._stop_requested.is_set():
                        pygame.time.Clock().tick(20)

                    pygame.mixer.music.stop()
                    pygame.mixer.music.unload()

            except Exception as e:
                print(f"[Mouth] Playback loop fault: {e}")
            finally:
                self._stop_requested.set()
                if pygame.mixer.get_init():
                    try:
                        pygame.mixer.music.stop()
                        pygame.mixer.music.unload()
                    except Exception:
                        pass
                self._is_speaking = False
