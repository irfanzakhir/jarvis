"""
core/awareness.py - Live Situational Awareness Subsystem for Jarvis 2.0
Inspired by Friday Mark 2's LiveContextState & live awareness loop.

Maintains an always-on, real-time background awareness of:
1. Current date and time (temporal ground truth).
2. Active foreground window title (via Win32 user32.dll ctypes - zero external dependencies).
3. Mobile Phone Uplink connectivity status (FastAPI port 8000).
4. System hardware health (CPU / RAM snapshot).
5. Active background agent or task status.

Injects a unified, lean [SITUATIONAL AWARENESS] string into every LLM call, ensuring
Jarvis always understands the user's real-time desktop context without asking.
"""

import sys
import time
import socket
import psutil
import ctypes
import threading
import logging
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Win32 user32 API bindings for instantaneous foreground window title resolution (<0.05ms)
user32 = ctypes.windll.user32 if sys.platform == "win32" else None


def get_active_window_title() -> str:
    """Retrieves the title of the active foreground window in Windows via ctypes."""
    if not user32:
        return "Unknown (Non-Windows)"
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return "Desktop"
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value.strip()
            return title if title else "Desktop"
        return "Desktop"
    except Exception:
        return "Desktop"


def check_port_open(port: int = 8000, host: str = "127.0.0.1", timeout: float = 0.1) -> bool:
    """Checks if a local service port is actively accepting connections."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False


class LiveContextState:
    """
    Thread-safe container holding the live operating context of Jarvis 2.0.
    Updated asynchronously by AwarenessDaemon every 8 seconds.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.time_str: str = ""
        self.active_window: str = "Desktop"
        self.mobile_uplink_active: bool = False
        self.cpu_percent: float = 0.0
        self.ram_percent: float = 0.0
        self.background_status: str = "IDLE"
        self.last_update_ts: float = 0.0

    def update(
        self,
        *,
        time_str: str,
        active_window: str,
        mobile_uplink_active: bool,
        cpu_percent: float,
        ram_percent: float,
        background_status: str = "IDLE",
    ):
        with self._lock:
            self.time_str = time_str
            self.active_window = active_window
            self.mobile_uplink_active = mobile_uplink_active
            self.cpu_percent = cpu_percent
            self.ram_percent = ram_percent
            self.background_status = background_status
            self.last_update_ts = time.time()

    def set_background_status(self, status: str):
        with self._lock:
            self.background_status = status

    def as_system_block(self) -> str:
        """
        Returns a compact Markdown context block for LLM prompt injection.
        Executes in microsecond RAM speed.
        """
        with self._lock:
            now_str = self.time_str or datetime.now().strftime("%A, %B %d, %Y | %I:%M:%S %p")
            window = self.active_window or "Desktop"
            mobile_str = "ONLINE (Port 8000)" if self.mobile_uplink_active else "OFFLINE"
            cpu = self.cpu_percent
            ram = self.ram_percent
            bg = self.background_status

        return (
            f"[SITUATIONAL AWARENESS & REAL-TIME GROUND TRUTH]:\n"
            f"- Hardware Clock: {now_str}\n"
            f"- Active Window in Focus: \"{window}\"\n"
            f"- Mobile Phone Uplink: {mobile_str}\n"
            f"- Telemetry: CPU {cpu:.0f}%, RAM {ram:.0f}%\n"
            f"- Background Operations: {bg}"
        )


class AwarenessDaemon:
    """
    Lightweight background worker that updates LiveContextState every refresh_interval seconds.
    CPU footprint: <0.02%.
    """

    def __init__(self, state: LiveContextState, refresh_interval: float = 8.0):
        self.state = state
        self.refresh_interval = refresh_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="JarvisAwarenessDaemon", daemon=True)
        self._thread.start()
        print("[Awareness Daemon]: Real-time situational awareness loop active (8s refresh).")

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            try:
                now = datetime.now()
                now_str = now.strftime("%A, %B %d, %Y | %I:%M:%S %p")
                active_win = get_active_window_title()
                mobile_on = check_port_open(8000)
                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory().percent

                self.state.update(
                    time_str=now_str,
                    active_window=active_win,
                    mobile_uplink_active=mobile_on,
                    cpu_percent=cpu,
                    ram_percent=ram,
                )
            except Exception as e:
                logger.debug(f"[Awareness Daemon Loop Error]: {e}")

            time.sleep(self.refresh_interval)
