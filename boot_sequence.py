import sys
import os
import math
import random
import time
import wave
import io
import threading
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QFont, QPolygonF,
    QLinearGradient, QRadialGradient, QPixmap, QFontMetrics
)

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


# ══════════════════════════════════════════════════════════════════════
#  BOOT AUDIO — Procedural Sci-Fi Synthesizer / Audio Loader
# ══════════════════════════════════════════════════════════════════════

class BootAudioSynth:
    """
    Plays boot sound either from an existing audio file or by procedurally
    generating a multi-layered sci-fi boot soundtrack in code.
    """

    def __init__(self, duration: float = 4.2, sample_rate: int = 44100, sound_file: str = None):
        self.duration = duration
        self.sr = sample_rate
        self.sound_file = sound_file
        self.n = int(duration * sample_rate)
        self._playing = False

    @staticmethod
    def _env_linear(t, start, end, t0, t1):
        frac = np.clip((t - t0) / max(t1 - t0, 1e-9), 0.0, 1.0)
        return start + (end - start) * frac

    @staticmethod
    def _env_adsr(t, t0, attack, decay, sustain_level, release, t_end):
        dt = t - t0
        env = np.zeros_like(t, dtype=np.float64)
        mask_a = (dt >= 0) & (dt < attack)
        env[mask_a] = dt[mask_a] / max(attack, 1e-9)
        mask_d = (dt >= attack) & (dt < attack + decay)
        env[mask_d] = 1.0 - (1.0 - sustain_level) * (dt[mask_d] - attack) / max(decay, 1e-9)
        sus_end = t_end - t0 - release
        mask_s = (dt >= attack + decay) & (dt < sus_end)
        env[mask_s] = sustain_level
        mask_r = (dt >= sus_end) & (dt < t_end - t0)
        rel_dt = dt[mask_r] - sus_end
        env[mask_r] = sustain_level * (1.0 - rel_dt / max(release, 1e-9))
        return np.clip(env, 0.0, 1.0)

    def generate(self) -> bytes:
        if not HAS_NUMPY:
            return b""

        t = np.linspace(0, self.duration, self.n, endpoint=False)
        mix = np.zeros(self.n, dtype=np.float64)

        # Layer 1: Sub-bass power hum (40-48 Hz)
        drone_freq = 42.0 + 4.0 * np.sin(2.0 * np.pi * 0.3 * t)
        drone_phase = np.cumsum(drone_freq / self.sr)
        drone = 0.28 * np.sin(2.0 * np.pi * drone_phase)
        drone *= self._env_linear(t, 0, 1, 0, 1.0) * self._env_linear(t, 1, 0, self.duration - 0.8, self.duration)
        mix += drone

        # Layer 2: Power-up sweep (80 -> 720 Hz)
        sweep_mask = t < (self.duration * 0.6)
        sweep_t = t[sweep_mask]
        sweep_frac = sweep_t / max(self.duration * 0.6, 1e-9)
        sweep_freq = 80.0 * (9.0 ** sweep_frac)
        sweep_phase = np.cumsum(sweep_freq / self.sr)
        sweep_sig = 0.14 * np.sin(2.0 * np.pi * sweep_phase) * np.sin(np.pi * sweep_frac)
        mix[sweep_mask] += sweep_sig

        # Layer 3: High tech data beeps
        beep_times = [0.2, 0.5, 0.9, 1.3, 1.8, 2.2, 2.6, 3.1, 3.5]
        for bt in beep_times:
            if bt + 0.04 < self.duration:
                bf = random.choice([1200, 1500, 1800, 2200])
                bd = 0.035
                mask = (t >= bt) & (t < bt + bd)
                if np.any(mask):
                    env = 1.0 - (t[mask] - bt) / bd
                    mix[mask] += 0.18 * env * np.sin(2.0 * np.pi * bf * t[mask])

        # Layer 4: Final confirmation chord and ping
        chord_start = max(0.0, self.duration - 1.2)
        conf_mask = t >= chord_start
        if np.any(conf_mask):
            ct = t[conf_mask]
            c_env = self._env_adsr(ct, chord_start, 0.08, 0.2, 0.5, 0.5, self.duration)
            for f in [220, 277.18, 329.63, 440]:
                mix[conf_mask] += 0.05 * c_env * np.sin(2.0 * np.pi * f * ct)
            pt = ct - chord_start
            ping_env = np.exp(-pt * 8.0)
            mix[conf_mask] += 0.20 * ping_env * np.sin(2.0 * np.pi * 1760 * ct)

        # Master processing
        fade_len = int(0.02 * self.sr)
        mix[:fade_len] *= np.linspace(0, 1, fade_len)
        mix[-fade_len:] *= np.linspace(1, 0, fade_len)
        mix = np.tanh(mix * 1.2)
        peak = np.max(np.abs(mix))
        if peak > 0:
            mix = mix / peak * 0.9

        pcm = (mix * 32767).astype(np.int16)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sr)
            wf.writeframes(pcm.tobytes())
        return buf.getvalue()

    def play(self):
        def _worker():
            try:
                import winsound
                # If an external sound file is provided and exists, play it
                if self.sound_file and os.path.exists(self.sound_file):
                    self._playing = True
                    winsound.PlaySound(self.sound_file, winsound.SND_FILENAME)
                    return

                # Otherwise synthesize procedurally
                wav_data = self.generate()
                if wav_data:
                    self._playing = True
                    winsound.PlaySound(wav_data, winsound.SND_MEMORY)
            except Exception as e:
                print(f"[Audio Error] {e}")
            finally:
                self._playing = False

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    def stop(self):
        try:
            import winsound
            winsound.PlaySound(None, 0)
        except Exception:
            pass
        self._playing = False


# ══════════════════════════════════════════════════════════════════════
#  JARVIS BOOT SCREEN
# ══════════════════════════════════════════════════════════════════════

class JarvisBootScreen(QWidget):
    """
    Focused cinematic boot sequence displaying:
      1. Background image (or deep black if none provided)
      2. Top-left live diagnostic script stream
      3. Bottom-center futuristic HUD with loading bar
    """

    def __init__(self, on_complete_callback=None, background_image=None, audio_file=None):
        super().__init__()
        self.on_complete = on_complete_callback

        # Frameless, fullscreen, stays on top
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setStyleSheet("background-color: #000000;")
        self.showFullScreen()

        # ── Color Palette ──────────────────────────────────────────────
        self.cyan_bright = QColor(0, 240, 255)
        self.cyan_glow = QColor(0, 180, 255, 70)
        self.cyan_dim = QColor(0, 130, 180, 150)
        self.white_core = QColor(235, 252, 255)

        # ── Animation State Variables ──────────────────────────────────
        self.elapsed_ms = 0
        self.total_duration_ms = 4200  # 4.2 seconds matching video keyframes
        self.cursor_visible = True
        self.progress_blocks = 0
        self.max_blocks = 24
        self.ring_angle = 0

        # ── Background Image Setup ─────────────────────────────────────
        self.bg_pixmap = None
        self._load_background_image(background_image)

        # ── Top-Left Scrolling Script Pool ─────────────────────────────
        self.script_pool = [
            r"\\NETWARE   196.25.65.9",
            r"\\NETWARE   196.25.65.10",
            r"DIR: F:\BACKUP\GHOST\ (HIDDEN)",
            r"C:\PROJECTS\Jarvis2.0\core\brain.py ... LOADED",
            r"C:\PROJECTS\Jarvis2.0\hud.py ... INITIALIZED",
            r"RUN SYSTEM TOOL --OPTICAL-ARRAY",
            r"ALLOCATING SQLITE BUFFER: jarvis_memory.db",
            r"MOUNTING DIRECTSHOW STREAM [INDEX 0]...",
            r"VERIFYING DWM COMPOSITION PIPELINE...",
            r"LOADING SEMANTIC VECTORS [2048 DIM]...",
            r"SYNCHRONIZING TEMPORAL ANCHOR...",
            r"ESTABLISHING NEURAL AUDIO BRIDGE...",
            r"CHECKSUM: OK",
            r"BYPASSING KERNEL FRAME RESTRICTION...",
            r"ENGAGING COMBAT HUD PROTOCOLS...",
            r"SYSTEM READY."
        ]
        self.active_logs = []

        # Middle-track status text
        self.sub_track_text = r"\\NETWARE   196.25.65.9"

        # ── Timers ─────────────────────────────────────────────────────
        # Master 60 FPS update loop
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_state)
        self.anim_timer.start(16)

        # Blinking cursor timer
        self.cursor_timer = QTimer(self)
        self.cursor_timer.timeout.connect(self.toggle_cursor)
        self.cursor_timer.start(200)

        # Top-left script line injector
        self.log_timer = QTimer(self)
        self.log_timer.timeout.connect(self.inject_script_line)
        self.log_timer.start(170)

        # ── Audio Initialization ───────────────────────────────────────
        sound_to_play = audio_file
        if not sound_to_play:
            # Check for standard jarvis_boot.wav in local or assets path
            default_wav = r"C:\PROJECTS\Jarvis2.0\assets\jarvis_boot.wav"
            if os.path.exists(default_wav):
                sound_to_play = default_wav

        self.audio = BootAudioSynth(
            duration=self.total_duration_ms / 1000.0,
            sound_file=sound_to_play
        )
        self.audio.play()

    def _load_background_image(self, background_image):
        """Loads and configures the optional background image."""
        if background_image:
            if isinstance(background_image, QPixmap):
                self.bg_pixmap = background_image
            elif isinstance(background_image, str) and os.path.exists(background_image):
                self.bg_pixmap = QPixmap(background_image)
            return

        # Check for common background image file names in the script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(script_dir, "background.jpg"),
            os.path.join(script_dir, "background.png"),
            os.path.join(script_dir, "bg.jpg"),
            os.path.join(script_dir, "bg.png"),
        ]
        for path in candidates:
            if os.path.exists(path):
                self.bg_pixmap = QPixmap(path)
                break

    def toggle_cursor(self):
        self.cursor_visible = not self.cursor_visible

    def inject_script_line(self):
        if self.script_pool:
            next_line = self.script_pool.pop(0)
            hex_addr = f"0x{random.randint(0x1000, 0xFFFF):04X}"
            self.active_logs.append(f"[{hex_addr}] {next_line}")
            if len(self.active_logs) > 15:
                self.active_logs.pop(0)

    def update_state(self):
        self.elapsed_ms += 16
        self.ring_angle = (self.ring_angle + 5) % 360

        # Sequence timing matching the 0:00 - 0:04 video keyframes
        if self.elapsed_ms < 1000:
            self.sub_track_text = r"\\NETWARE   196.25.65.9"
        elif self.elapsed_ms < 2000:
            self.sub_track_text = r"DIR: F:\BACKUP\GHOST\ (HIDDEN)   |   RUN SYSTEM TOOL"
        elif self.elapsed_ms < 2700:
            self.sub_track_text = "CHECKSUM: OK"
        else:
            # 2.7s to 4.0s: Rapidly fill the segmented progress bar
            self.sub_track_text = ""
            progress_ratio = (self.elapsed_ms - 2700) / 1100.0
            self.progress_blocks = min(self.max_blocks, int(progress_ratio * self.max_blocks))

        # Smooth cinematic fade-out during the final 300ms
        if self.elapsed_ms >= self.total_duration_ms - 300:
            fade_ratio = max(0.0, min(1.0, (self.total_duration_ms - self.elapsed_ms) / 300.0))
            self.setWindowOpacity(fade_ratio)

        if self.elapsed_ms >= self.total_duration_ms:
            self.anim_timer.stop()
            self.cursor_timer.stop()
            self.log_timer.stop()
            self.audio.stop()
            if self.on_complete:
                self.on_complete()
            self.close()

        self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.audio.stop()
            self.close()

    # ══════════════════════════════════════════════════════════════════
    #  PAINT
    # ══════════════════════════════════════════════════════════════════
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # 1. Background (Image if provided, else solid dark background)
        if self.bg_pixmap and not self.bg_pixmap.isNull():
            scaled = self.bg_pixmap.scaled(
                w, h,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            sx = max(0, (scaled.width() - w) // 2)
            sy = max(0, (scaled.height() - h) // 2)
            painter.drawPixmap(0, 0, scaled, sx, sy, w, h)
            # Subtle dark wash overlay so text and HUD elements pop with high contrast
            painter.fillRect(self.rect(), QColor(0, 0, 0, 85))
        else:
            painter.fillRect(self.rect(), QColor(0, 0, 0))

        # 2. Top-Left Scrolling Diagnostic Scripts
        self.draw_top_left_scripts(painter)

        # 3. Bottom-Center Futuristic HUD + Loading Bar
        self.draw_bottom_center_hud(painter, w, h)

        painter.end()

    # ── Top-Left Scrolling Diagnostic Scripts ─────────────────────────
    def draw_top_left_scripts(self, painter):
        font = QFont("Courier New", 10, QFont.Weight.Bold)
        painter.setFont(font)

        x_offset = 40
        y_offset = 45
        line_height = 20

        # Header
        painter.setPen(QPen(self.white_core))
        painter.drawText(x_offset, y_offset, "J.A.R.V.I.S. BOOTLOADER // KERNEL STREAM")

        painter.setPen(QPen(self.cyan_dim, 1))
        painter.drawLine(x_offset, y_offset + 8, x_offset + 380, y_offset + 8)

        # Draw active scrolling script lines
        y_cursor = y_offset + 30
        for i, line in enumerate(self.active_logs):
            # Newest lines glow brightest white-cyan
            if i == len(self.active_logs) - 1:
                painter.setPen(QPen(self.white_core))
            elif i >= len(self.active_logs) - 3:
                painter.setPen(QPen(self.cyan_bright))
            else:
                alpha = max(60, 240 - (len(self.active_logs) - i) * 12)
                painter.setPen(QPen(QColor(0, 180, 220, alpha)))
            painter.drawText(x_offset, y_cursor, line)
            y_cursor += line_height

        # Blinking cursor on active input line
        if self.cursor_visible and self.active_logs:
            painter.setPen(QPen(self.cyan_bright))
            painter.drawText(x_offset, y_cursor, "█")

    # ── Bottom-Center Futuristic Video HUD + Loading Bar ──────────────
    def draw_bottom_center_hud(self, painter, w, h):
        hud_w = 760
        hud_h = 150
        cx = w / 2
        by = h - 130  # Positioned at bottom center

        left = cx - hud_w / 2
        right = cx + hud_w / 2
        top = by - hud_h / 2

        # --- A. Rotating Mini Tech Core above the HUD bar ---
        painter.save()
        painter.translate(cx, top - 45)
        painter.rotate(self.ring_angle)
        painter.setPen(QPen(self.cyan_bright, 2))
        painter.drawArc(-24, -24, 48, 48, 0 * 16, 100 * 16)
        painter.drawArc(-24, -24, 48, 48, 180 * 16, 100 * 16)
        painter.rotate(-self.ring_angle * 2)
        painter.setPen(QPen(self.cyan_dim, 1, Qt.PenStyle.DashLine))
        painter.drawEllipse(-16, -16, 32, 32)
        painter.restore()

        # --- B. Angled Chamfered Rails ---
        top_rail = QPolygonF([
            QPointF(left, top + 30),
            QPointF(left + 110, top + 30),
            QPointF(left + 135, top + 5),
            QPointF(right - 160, top + 5),
            QPointF(right - 135, top + 30),
            QPointF(right, top + 30)
        ])

        mid_y = top + 58

        bot_rail = QPolygonF([
            QPointF(left, top + 110),
            QPointF(left + 95, top + 110),
            QPointF(left + 120, top + 135),
            QPointF(right - 140, top + 135),
            QPointF(right - 115, top + 110),
            QPointF(right, top + 110)
        ])

        # Draw Outer Glow Pass
        glow_pen = QPen(self.cyan_glow, 6)
        painter.setPen(glow_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolyline(top_rail)
        painter.drawPolyline(bot_rail)
        painter.drawLine(QPointF(left - 40, mid_y), QPointF(right + 40, mid_y))

        # Draw Crisp Inner Core Pass
        core_pen = QPen(self.cyan_bright, 2)
        painter.setPen(core_pen)
        painter.drawPolyline(top_rail)
        painter.drawPolyline(bot_rail)

        # Extra bright center horizontal beam
        painter.setPen(QPen(self.white_core, 2))
        painter.drawLine(QPointF(left - 20, mid_y), QPointF(right + 20, mid_y))

        # --- C. Optical Flares on Intersection ---
        for flare_x in [left + 35, right - 35]:
            flare = QRadialGradient(QPointF(flare_x, mid_y), 45)
            flare.setColorAt(0.0, QColor(255, 255, 255, 230))
            flare.setColorAt(0.3, QColor(0, 240, 255, 140))
            flare.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(flare)
            painter.drawEllipse(QPointF(flare_x, mid_y), 45, 18)

        # --- D. "INITIATING SYSTEM 1...." + Blinking Block Cursor ---
        title_font = QFont("OCR A Extended", 17, QFont.Weight.Bold)
        if not title_font.exactMatch():
            title_font = QFont("Courier New", 18, QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.setPen(QPen(self.white_core))

        title_text = "INITIALIZING...."
        fm = QFontMetrics(title_font)
        tw = fm.horizontalAdvance(title_text)
        text_x = left + 165
        text_y = top + 45
        painter.drawText(int(text_x), int(text_y), title_text)

        # Blinking block cursor right after the text
        cursor_x = text_x + tw + 10
        cursor_y = text_y - 24
        painter.setBrush(QColor(0, 180, 255, 50))
        painter.setPen(QPen(self.cyan_dim, 1))
        painter.drawRect(QRectF(cursor_x, cursor_y, 20, 26))

        if self.cursor_visible:
            painter.setBrush(self.white_core)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(QRectF(cursor_x + 2, cursor_y + 2, 16, 22))

        # --- E. Lower Track: Rapid Status Text OR Segmented Progress Bar ---
        track_x = left + 135
        track_y = mid_y + 14
        track_w = right - left - 275
        track_h = 30

        if self.sub_track_text:
            sub_font = QFont("Courier New", 11, QFont.Weight.Bold)
            painter.setFont(sub_font)
            painter.setPen(QPen(self.cyan_bright))
            painter.drawText(int(track_x), int(track_y + 19), self.sub_track_text)
        else:
            # Segmented glowing loading blocks
            gap = 4
            block_w = (track_w - (gap * (self.max_blocks - 1))) / self.max_blocks

            for i in range(self.max_blocks):
                bx = track_x + i * (block_w + gap)
                rect = QRectF(bx, track_y, block_w, track_h)

                if i < self.progress_blocks:
                    # Active glowing cyan-white block
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(self.cyan_glow)
                    painter.drawRect(rect.adjusted(-2, -2, 2, 2))

                    grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
                    grad.setColorAt(0.0, self.white_core)
                    grad.setColorAt(0.5, self.cyan_bright)
                    grad.setColorAt(1.0, QColor(0, 160, 220))
                    painter.setBrush(grad)
                    painter.drawRect(rect)
                else:
                    # Unlit dim slot
                    painter.setPen(QPen(QColor(0, 90, 120, 90), 1))
                    painter.setBrush(QColor(0, 30, 45, 80))
                    painter.drawRect(rect)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    boot_screen = JarvisBootScreen()
    sys.exit(app.exec())
