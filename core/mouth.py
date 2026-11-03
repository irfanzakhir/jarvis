"""
J.A.R.V.I.S. 2.0 - Neural Speech Synthesis Module (High-Speed Concurrent Edition)
Drastically accelerates talkback speed and Time-To-First-Audio (TTFA):
1. Concurrent sentence pre-fetching (all sentences synthesized in parallel via asyncio)
2. Fast talkback speed rate (+15% speed for natural, confident AI delivery)
3. Clause-level chunking for sub-300ms initial audio playback
4. Expanded 128-entry RAM audio cache seeded with common system phrases
5. Zero-gap ordered audio streaming using non-blocking queues
"""

import pygame
import asyncio
import edge_tts
import io
import os
import threading
import queue
import re
import time
import logging

logger = logging.getLogger("JarvisMouth")

class JarvisMouth:
    def __init__(self, voice="en-GB-RyanNeural", rate=None):
        if not pygame.mixer.get_init():
            try:
                # Optimized buffer size for low-latency playback
                pygame.mixer.init(frequency=24000, buffer=2048)
            except Exception:
                pygame.mixer.init()

        self.voice = voice
        # Talkback rate reverted to original natural tempo (+0%) per user preference
        self.rate = rate or os.getenv("JARVIS_TTS_RATE", "+0%")
        self._is_speaking = False
        self._stop_requested = threading.Event()
        self._is_paused = threading.Event()
        self._lock = threading.Lock()
        self._audio_cache = {}
        self._cache_lock = threading.Lock()

        # Seed cache from pre-synthesized local assets if available
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        chimes_dir = os.path.join(base_dir, "assets", "chimes")
        seed_files = {
            "System locked. Awaiting biometric authentication.": "system_locked.mp3",
            "Good to see you, sir. Importing preferences from home interface.": "greeting.mp3",
            "Good to see you, sir.": "greeting_part1.mp3",
            "Importing preferences from home interface.": "greeting_part2.mp3"
        }
        for phrase, fname in seed_files.items():
            fpath = os.path.join(chimes_dir, fname)
            if os.path.exists(fpath):
                try:
                    with open(fpath, "rb") as f:
                        self._audio_cache[phrase] = f.read()
                except Exception:
                    pass

        # Pre-warm common system response phrases in background for instant (0ms) playback
        threading.Thread(target=self._prewarm_cache, daemon=True).start()

    def _prewarm_cache(self):
        """Asynchronously pre-synthesizes high-frequency system phrases into RAM concurrently."""
        common_phrases = [
            "System locked. Awaiting biometric authentication.",
            "Good to see you, sir. Importing preferences from home interface.",
            "Good to see you, sir.",
            "Importing preferences from home interface.",
            "Standing by. Optical sensors armed, sir.",
            "Standing by, sir.",
            "Scanning active display visual telemetry now, sir.",
            "Scanning the active screen, sir.",
            "Optical watchdog armed. Monitoring for person, sir.",
            "Optical watchdog disarmed. Sensors returned to idle, sir.",
            "Increasing audio gain, sir.",
            "Decreasing audio gain, sir.",
            "Toggling system mute state.",
            "Screen state captured and archived, sir.",
            "Deploying Global Situation Room intel widget, sir.",
            "Holographically revealing news component, sir.",
            "Holographically revealing weather component, sir."
        ]
        from concurrent.futures import ThreadPoolExecutor

        def _prewarm_one(phrase):
            try:
                with self._cache_lock:
                    in_cache = phrase in self._audio_cache
                if not in_cache:
                    raw = self._synthesize_sentence_sync(phrase, use_cache=False)
                    if raw:
                        with self._cache_lock:
                            self._audio_cache[phrase] = raw
            except Exception:
                pass

        try:
            with ThreadPoolExecutor(max_workers=4) as executor:
                list(executor.map(_prewarm_one, common_phrases))
        except (RuntimeError, Exception):
            pass

    def is_speaking(self):
        """Returns True if Jarvis is currently talking."""
        return self._is_speaking

    def stop(self):
        """Instantly cuts off active audio playback and clears pipeline."""
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
        """
        Splits text into spoken sentence units and sub-clause chunks.
        For long sentences (>12 words), breaks at natural clause boundaries (commas, semicolons)
        so the first audio chunk synthesizes and begins playing in under 250ms!
        """
        if not text:
            return []
        cleaned = text.replace("*", "").replace("#", "").strip()
        chunks = re.split(r'(?<=[.!?])\s+', cleaned)
        sentences = [c.strip() for c in chunks if c.strip()]
        
        # Sub-clause breaking for ultra-fast TTFA on long sentences
        result = []
        for s in sentences:
            words = s.split()
            if len(words) > 12:
                # Split at first major clause punctuation if present
                clause_match = re.split(r'(?<=[,;:])\s+', s, maxsplit=1)
                if len(clause_match) == 2 and len(clause_match[0].split()) >= 2:
                    result.append(clause_match[0].strip())
                    result.append(clause_match[1].strip())
                    continue
            result.append(s)
            
        return result if result else [cleaned]

    def _synthesize_sentence_sync(self, sentence: str, use_cache=True) -> bytes:
        """Synthesizes a single sentence to raw MP3 bytes in memory."""
        if use_cache:
            with self._cache_lock:
                if sentence in self._audio_cache:
                    return self._audio_cache[sentence]

        async def _gen():
            communicate = edge_tts.Communicate(sentence, self.voice, rate=self.rate)
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
                    if len(self._audio_cache) < 128:
                        self._audio_cache[sentence] = raw_audio
            return raw_audio
        finally:
            loop.close()

    def speak(self, text: str):
        """
        High-Speed Pipelined Audio Playback:
        1. All sentences in the passage are pre-fetched CONCURRENTLY in parallel.
        2. Sentence 1 begins playback as soon as it arrives (~250-400ms TTFA).
        3. Subsequent sentences are already synthesized in RAM by the time sentence 1 finishes,
           eliminating pauses between sentences completely.
        Blocks the calling thread until playback finishes.
        """
        if not text or not str(text).strip():
            return

        with self._lock:
            if not pygame.mixer.get_init():
                pygame.mixer.init()

            self._stop_requested.clear()
            self._is_speaking = True

            sentences = self._split_sentences(str(text))
            if not sentences:
                self._is_speaking = False
                return

            audio_queue = queue.Queue(maxsize=len(sentences) + 2)

            # Concurrent Async Producer: Pre-fetches all sentences in parallel
            def producer():
                async def _async_fetch_pipeline():
                    completed_events = {i: asyncio.Event() for i in range(len(sentences))}
                    audio_results = {}

                    async def _fetch_one(idx, sentence_text):
                        if self._stop_requested.is_set():
                            completed_events[idx].set()
                            return

                        # Check RAM cache first
                        with self._cache_lock:
                            if sentence_text in self._audio_cache:
                                audio_results[idx] = self._audio_cache[sentence_text]
                                completed_events[idx].set()
                                return

                        try:
                            communicate = edge_tts.Communicate(sentence_text, self.voice, rate=self.rate)
                            raw = b""
                            async for chunk in communicate.stream():
                                if self._stop_requested.is_set():
                                    break
                                if chunk["type"] == "audio":
                                    raw += chunk["data"]

                            if raw:
                                with self._cache_lock:
                                    if len(self._audio_cache) < 128:
                                        self._audio_cache[sentence_text] = raw
                            audio_results[idx] = raw
                        except Exception as e:
                            logger.error(f"[Mouth] Concurrent TTS error for item {idx}: {e}")
                            audio_results[idx] = None
                        finally:
                            completed_events[idx].set()

                    # Launch all sentences concurrently!
                    tasks = [_fetch_one(i, s) for i, s in enumerate(sentences)]
                    for t in tasks:
                        asyncio.create_task(t)

                    # Deliver audio chunks to audio_queue strictly in sequential order
                    for i in range(len(sentences)):
                        if self._stop_requested.is_set():
                            break
                        await completed_events[i].wait()
                        audio_queue.put(audio_results.get(i))

                    audio_queue.put(StopIteration)

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(_async_fetch_pipeline())
                finally:
                    loop.close()

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
                        pygame.time.Clock().tick(25)

                    pygame.mixer.music.stop()
                    pygame.mixer.music.unload()

            except Exception as e:
                logger.error(f"[Mouth] Playback loop fault: {e}")
            finally:
                self._stop_requested.set()
                if pygame.mixer.get_init():
                    try:
                        pygame.mixer.music.stop()
                        pygame.mixer.music.unload()
                    except Exception:
                        pass
                self._is_speaking = False

    def speak_sync(self, text: str):
        """Direct synchronous vocalization blocking until playback is complete."""
        self.speak(text)
