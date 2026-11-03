import os
# Tells Google's C++ logger: "Only print FATAL system crashes, shut up about everything else."
os.environ["GLOG_minloglevel"] = "2"  
os.environ["MP_SILENT_LOGS"] = "1"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--single-process --process-per-site --disable-logging --log-level=3"
os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.webenginecontext=false"
import sys
import runpy

# =====================================================================
# THE FROZEN TRAPDOOR: Intercepts sub-processes called by JARVIS.exe
# =====================================================================
if getattr(sys, 'frozen', False) and len(sys.argv) > 1 and sys.argv[1].endswith(".py"):
    sub_script = sys.argv[1]
    sys.argv = [sub_script] + sys.argv[2:] # Shift arguments down one slot
    runpy.run_path(sub_script, run_name="__main__")
    sys.exit(0)
import subprocess
import re
import time
import logging
import threading
import cv2
import base64
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QThread, pyqtSignal
QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
try:
    import PyQt6.QtWebEngineWidgets
except Exception:
    pass
import queue
from gui.hud import JarvisHUD
from core.brain import JarvisBrain
from core.eyes import JarvisEyes, OpticalHardware
from core.ears import JarvisEars
from core.mouth import JarvisMouth
from core.monitor import SystemMonitor 
from utils.automation import JarvisAutomation
from core.security import BiometricSecurity
from core.event_engine import EventEngine
from core.router import JarvisRouter
try:
    from core.screen_reader import ScreenReader
except Exception:
    ScreenReader = None
from services.intel_hub import IntelHub

# Lazy Global Google Workspace Bridge Proxy
_workspace_instance = None

def get_workspace():
    global _workspace_instance
    if _workspace_instance is None:
        from core.workspace import GoogleWorkspaceBridge
        _workspace_instance = GoogleWorkspaceBridge()
    return _workspace_instance

class _LazyWorkspace:
    def __getattr__(self, name):
        return getattr(get_workspace(), name)

workspace = _LazyWorkspace()

# ==========================================
# 1. SYSTEM LOGGING & CRASH INTERCEPTOR
# ==========================================
logging.basicConfig(
    filename='jarvis_system.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logger.info("=======================================")
logger.info("SYSTEM BOOT SEQUENCE INITIATED.")

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.critical("FATAL SYSTEM CRASH", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception

# ==========================================
# Chromium Hardware Acceleration flags are applied in main() 

# ==========================================
# PHASE 1: THE VISION MULTIPLEXER
# ==========================================
class VisionMultiplexer(QThread):
    auth_signal = pyqtSignal(bool)
    kinetic_signal = pyqtSignal(dict)
    
    def __init__(self, security, command_queue=None):
        super().__init__()
        self.security = security
        self.command_queue = command_queue
        self.running = True
        self.current_mode = "SECURITY" 
        self.watchdog_target = None
        self.latest_frame = None
        
        # --- OPTICAL WATCHDOG PIPELINE ---
        from core.watchdog import VisionWatchdog
        self.watchdog = VisionWatchdog(command_queue=self.command_queue)
        
        # --- KINETIC ENGINE SETUP (LAZY INITIALIZATION) ---
        self.kinetic_engine = None
        
        import ctypes
        self.user32 = ctypes.windll.user32
        self.screen_w = self.user32.GetSystemMetrics(0)
        self.screen_h = self.user32.GetSystemMetrics(1)
        self.was_left_pinched = False
        self.was_right_pinched = False

    def set_vision_mode(self, mode: str, target=None):
        if mode in ["SECURITY", "WATCHDOG", "KINETIC", "IDLE"]:
            if mode == "KINETIC" and self.kinetic_engine is None:
                try:
                    from core.kinetic import KineticEngine
                    self.kinetic_engine = KineticEngine(smoothing_factor=0.25, pinch_engage_threshold=0.04, pinch_release_threshold=0.055)
                except Exception as e:
                    logger.error(f"[VISION MASTER]: Failed to initialize KineticEngine: {e}")
            self.current_mode = mode
            self.watchdog_target = target
            if mode == "WATCHDOG":
                self.watchdog.arm(target or "person")
            elif hasattr(self, 'watchdog') and self.watchdog.is_active:
                self.watchdog.disarm()
            logger.info(f"[VISION MASTER]: Multiplexer shifted to {mode} mode.")

    def stop(self):
        self.running = False
        self.wait()

    def get_base64_snapshot(self):
        if self.latest_frame is not None:
            _, buffer = cv2.imencode('.jpg', self.latest_frame)
            return base64.b64encode(buffer).decode('utf-8')
        return None

    def run(self):
        # Universal Hardware Access Point via DirectShow Factory (1080p Ingest)
        cap = OpticalHardware.get_camera(device_index=0, width=1920, height=1080, fps=30)
        
        if not cap or not cap.isOpened():
            logger.critical("[VISION MASTER]: Optical sensor initialization aborted.")
            self.auth_signal.emit(False)
            return

        while self.running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.03)
                continue
            
            # Store frame for immediate LLM multimodal snapshots
            self.latest_frame = frame

            # ----------------------------------------
            # EXCLUSIVE PIPELINE ROUTING
            # ----------------------------------------
            if self.current_mode == "SECURITY":
                if self.security.scan_for_presence(frame):
                    self.auth_signal.emit(True)
                    self.current_mode = "IDLE" 
                    time.sleep(1) 
                    
            elif self.current_mode == "KINETIC":
                if self.kinetic_engine is None:
                    try:
                        from core.kinetic import KineticEngine
                        self.kinetic_engine = KineticEngine(smoothing_factor=0.25, pinch_engage_threshold=0.04, pinch_release_threshold=0.055)
                    except Exception as e:
                        logger.error(f"[VISION MASTER]: Failed to initialize KineticEngine in run loop: {e}")
                        self.current_mode = "IDLE"
                        continue
                frame, telemetry = self.kinetic_engine.process_frame(frame)
                
                if telemetry:
                    cam_x, cam_y = telemetry["x"], telemetry["y"]
                    cam_w, cam_h = telemetry["frame_w"], telemetry["frame_h"]

                    mirrored_x = cam_w - cam_x
                    screen_x = int((mirrored_x / cam_w) * self.screen_w)
                    screen_y = int((cam_y / cam_h) * self.screen_h)

                    self.user32.SetCursorPos(screen_x, screen_y)

                    import pyautogui
                    pyautogui.FAILSAFE = False 
                    pyautogui.PAUSE = 0
                    
                    is_left_pinched = telemetry["is_left_pinched"]
                    is_right_pinched = telemetry["is_right_pinched"]
                    
                    if is_left_pinched and not self.was_left_pinched:
                        pyautogui.mouseDown(button='left')
                        self.was_left_pinched = True
                    elif not is_left_pinched and self.was_left_pinched:
                        pyautogui.mouseUp(button='left')
                        self.was_left_pinched = False
                        
                    if is_right_pinched and not self.was_right_pinched:
                        pyautogui.click(button='right')
                        self.was_right_pinched = True
                    elif not is_right_pinched and self.was_right_pinched:
                        self.was_right_pinched = False
                
            elif self.current_mode == "WATCHDOG":
                self.watchdog.process_frame(frame)
                
            elif self.current_mode == "IDLE":
                time.sleep(0.03)

        cap.release()

# ==========================================
# 3. JARVIS WORKER ENGINE
# ==========================================
class _MouthProxy:
    """Non-blocking proxy wrapping JarvisMouth to decouple audio vocalization from worker threads."""
    def __init__(self, real_mouth, worker):
        self._real_mouth = real_mouth
        self._worker = worker

    def speak(self, text):
        self._worker.speak_async(text)

    def speak_sync(self, text):
        """Synchronously vocalizes speech directly through the real mouth, blocking until playback finishes."""
        if self._real_mouth and hasattr(self._real_mouth, 'speak'):
            self._real_mouth.speak(text)
        else:
            self._worker.speak_async(text)

    def stop(self):
        self._worker.clear_speech_queue()

    def is_speaking(self):
        if hasattr(self._real_mouth, 'is_speaking'):
            return self._real_mouth.is_speaking()
        return False

    def __getattr__(self, name):
        return getattr(self._real_mouth, name)


class JarvisWorker(QThread):
    status_signal = pyqtSignal(dict)

    def __init__(self, ears, brain, mouth, automation, security, hud=None):
        super().__init__()
        self.ears = ears
        self.brain = brain
        self.mouth = _MouthProxy(mouth, self)
        self.automation = automation
        self.security = security
        self.hud = hud
        self.is_mic_muted = False
        
        self.command_queue = queue.Queue()
        self.system_locked = True 
        self.first_boot = True 
        
        self.vision_master = VisionMultiplexer(security, command_queue=self.command_queue)
        self.vision_master.auth_signal.connect(self.handle_auth)
        self.vision_master.start(QThread.Priority.HighPriority)
        logger.info("Vision Multiplexer initialized.")
        
        # Reuse global Workspace Bridge & initialize EventEngine with Calendar link
        self.workspace = get_workspace()
        self.event_engine = EventEngine(self.command_queue, workspace_bridge=self.workspace)
        self.event_engine.start()

        # Initialize Fast Intent Hot-Path Router and Dual-Layer Screen Reader
        self.router = JarvisRouter()
        if ScreenReader is not None:
            try:
                self.screen_reader = ScreenReader(gemini_client=getattr(self.brain, 'gemini_client', None))
            except Exception as e:
                logger.warning(f"ScreenReader initialization failed: {e}")
                self.screen_reader = None
        else:
            self.screen_reader = None
        IntelHub().bind_core_references(mouth=self.mouth)

        # Decoupled Non-blocking Speech Pipeline
        self.speech_queue = queue.Queue()
        self._speech_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self._speech_thread.start()

    def speak_async(self, text):
        """Asynchronously vocalizes speech without blocking the calling thread."""
        if not text or not str(text).strip():
            return
        self.speech_queue.put(str(text))

    def speak(self, text):
        self.speak_async(text)

    def _speech_worker(self):
        """Background worker thread draining the speech queue sequentially."""
        while True:
            text = self.speech_queue.get()
            if text is None:
                break
            try:
                real_mouth = getattr(self.mouth, '_real_mouth', self.mouth)
                if real_mouth and hasattr(real_mouth, 'speak'):
                    real_mouth.speak(text)
            except Exception as e:
                logger.error(f"Speech playback worker error: {e}", exc_info=True)
            finally:
                self.speech_queue.task_done()

    def clear_speech_queue(self):
        """Discards queued speech items and immediately halts active audio playback."""
        while not self.speech_queue.empty():
            try:
                self.speech_queue.get_nowait()
                self.speech_queue.task_done()
            except (queue.Empty, ValueError):
                break
        real_mouth = getattr(self.mouth, '_real_mouth', self.mouth)
        if real_mouth and hasattr(real_mouth, 'stop'):
            try:
                real_mouth.stop()
            except Exception:
                pass

    def stop(self):
        if hasattr(self, 'vision_master') and self.vision_master:
            self.vision_master.stop()
        if hasattr(self, 'event_engine') and self.event_engine:
            self.event_engine.stop()
        if hasattr(self, 'speech_queue'):
            self.clear_speech_queue()
            self.speech_queue.put(None)

    def handle_auth(self, success):
        if success and self.system_locked:
            self.system_locked = False
            if self.first_boot:
                # 1. Force the UI out of combat mode (Cyan Theme)
                self.status_signal.emit({"log": "[SYSTEM]: DISARMING PROTOCOL OMEGA.", "action": "combat_off"})
                
                # 2. Trigger the staggered cinematic fade-in
                self.status_signal.emit({"log": "[SECURITY]: ADMIN VERIFIED. INITIATING BOOT.", "action": "cinematic_boot"})
                
                self.first_boot = False
            else:
                self.status_signal.emit({"log": "[SECURITY]: BIOMETRIC MATCH. WAKING SYSTEM.", "action": "restore_dashboard"})
                self.speak_async("Welcome back, sir. System restored.")
        elif not success and self.system_locked:
            if self.first_boot:
                logger.warning("[SECURITY]: Optical hardware offline on boot. Auto-unlocking in desktop console mode.")
                self.system_locked = False
                self.first_boot = False
                self.status_signal.emit({"log": "[SECURITY]: OPTICAL SENSOR OFFLINE. DESKTOP CONSOLE UNLOCKED.", "action": "restore_dashboard"})
                self.speak_async("Optical sensor offline. Desktop console unlocked, sir.")
            else:
                self.status_signal.emit({"log": "[SECURITY]: OPTICAL SENSOR OFFLINE. USE HUD INPUT (TYPE 'UNLOCK' TO OVERRIDE)."})

    def intercept_audio(self):
        """Clean Qt Slot triggered by HUD ApplicationShortcuts"""
        self.clear_speech_queue()
        logger.info("User manually interrupted audio playback via UI hotkey.")
        self.status_signal.emit({"log": "[SYSTEM]: VOCAL OUTPUT INTERRUPTED", "action": "standby"})

    def handle_hud_state(self, state):
        if state == "restored":
            self.system_locked = False
            if hasattr(self, 'vision_master') and self.vision_master:
                if self.vision_master.current_mode == "SECURITY":
                    self.vision_master.set_vision_mode("IDLE")

    def receive_text_command(self, text):
        logger.info(f"Manual Override Text Received: {text}")
        clean_cmd = text.strip().lower()
        if hasattr(self, 'mouth') and self.mouth and self.mouth.is_speaking():
            self.clear_speech_queue()
        if self.system_locked:
            unlock_pattern = r"\b(unlock|override|bypass|admin|open|hello|hi|hey|maximize|maximise|restore|wake)\b"
            if re.search(unlock_pattern, clean_cmd):
                logger.info("[SECURITY]: Manual admin override bypass accepted via text input.")
                self.handle_auth(True)
                if clean_cmd in ["unlock", "admin", "bypass", "override"]:
                    return
            else:
                logger.info("[SECURITY]: Manual admin override command accepted via text input.")
                self.handle_auth(True)
        self.command_queue.put(text)

    def audio_listener_loop(self):
        while True:
            if not self.is_mic_muted:
                text = self.ears.listen()
                if text and len(text.strip()) > 3:
                    self.command_queue.put(text)
                time.sleep(0.1)
            else:
                time.sleep(0.5)
            
    def set_mute_state(self, is_muted):
        self.is_mic_muted = is_muted
        state_log = "[SYSTEM]: AUDIO PIPELINE MUTED" if is_muted else "[SYSTEM]: AUDIO PIPELINE ACTIVE"
        self.status_signal.emit({"log": state_log})
        
    def launch_intel_matrix(self, voice_command):
        layer = "CONFLICTS" 
        if "infrastructure" in voice_command or "outage" in voice_command:
            layer = "INFRASTRUCTURE"
        elif "market" in voice_command or "stock" in voice_command:
            layer = "ECONOMIC"
        elif "military" in voice_command or "defense" in voice_command:
            layer = "MILITARY"
        elif "weather" in voice_command or "natural disaster" in voice_command:
            layer = "NATURAL ANOMALIES"
            
        self.automation.dispatch_satellite_app("news", layer)

    def handle_system_alert(self, msg):
        if isinstance(msg, dict):
            if msg.get("type") == "wifi_telemetry":
                self.status_signal.emit({"action": "update_wifi", "data": msg})
            return
        self.status_signal.emit({"log": msg})
        
        if "[WARNING]" in msg:
            threading.Thread(target=self.mouth.speak, args=("Warning. Anomaly detected in system resource telemetry.",), daemon=True).start()
        elif "[CRITICAL]" in msg:
            threading.Thread(target=self.mouth.speak, args=("Critical alert. Secure uplink to the global network has been severed.",), daemon=True).start()

    def run(self):
        self.vision_master.set_vision_mode("SECURITY")
        time.sleep(1)
        self.status_signal.emit({"log": "AWAITING BIOMETRIC AUTHENTICATION...", "action": "combat_on"})
        self.mouth.speak("System locked. Awaiting biometric authentication.")

        while self.system_locked:
            time.sleep(0.1)
        
        # Wait for the cinematic boot screen to finish its 4.2s sequence and transition to cyan Arc Reactor
        if self.hud and hasattr(self.hud, 'boot_screen_finished'):
            self.hud.boot_screen_finished.wait(timeout=5.5)
        else:
            time.sleep(4.2)

        # Ensure event engine is running safely without dropping workspace_bridge
        if not hasattr(self, 'event_engine') or not self.event_engine.is_alive():
            self.event_engine = EventEngine(self.command_queue, workspace_bridge=self.workspace)
            self.event_engine.start()

        # 1. Screen is currently the normal Jarvis Arc Reactor spinning on plain background (all widgets hidden)
        welcome_phrase = "Good to see you, sir. Importing preferences from home interface."
        self.mouth.speak_sync(welcome_phrase)

        # 2. ONLY AFTER vocal greeting finishes: reveal widgets (docks Arc Reactor to side and reveals command, log, telemetry widgets with sci-fi clicks)
        self.status_signal.emit({"log": ">> J.A.R.V.I.S. SYSTEM FULLY OPERATIONAL.", "action": "reveal_home_preferences"})

        # Start background system monitor and audio listener
        self.monitor = SystemMonitor(alert_callback=self.handle_system_alert)
        threading.Thread(target=self.audio_listener_loop, daemon=True).start()
        
        logger.info("UI Cold Start complete. Agentic loop running.")
        
        vision_triggers = ["look", "see", "what is this", "who is", "describe this"]
        
        while True:
            try:
                self.status_signal.emit({"action": "standby"})
                user_input = self.command_queue.get() 
            
                if user_input.startswith("watchdog_alert:"):
                    alert_target = user_input.split(":")[-1].strip()
                    self.status_signal.emit({
                        "log": f"[WARNING]: {alert_target.upper()} DETECTED IN OPTICAL SECTOR.",
                        "action": "watchdog_disarmed"
                    })
                    self.mouth.speak(f"Sir, the optical watchdog has detected the {alert_target}.")
                    continue 
            
                self.status_signal.emit({"action": "wake"})
                self.status_signal.emit({"log": f"[USER]: {user_input}"})
                logger.info(f"Command Injected: {user_input}")
            
                # --- TIER 1: FAST INTENT HOT-PATH ROUTER (<10ms) ---
                fast_decision = self.router.route(user_input)
                if fast_decision.get("intercepted"):
                    logger.info(f"[ROUTER HOT-PATH]: Intercepted in <10ms: {fast_decision}")
                    decision = fast_decision
                    # Preserve dialogue context in Brain conversation history cleanly
                    clean_spoken = fast_decision.get("spoken_response", "")
                    if hasattr(self.brain, "conversation_history"):
                        self.brain.conversation_history.append({"role": "user", "content": user_input})
                        if clean_spoken:
                            self.brain.conversation_history.append({"role": "assistant", "content": clean_spoken})
                elif "watchdog" not in user_input.lower() and any(trigger in user_input.lower() for trigger in vision_triggers):
                    self.status_signal.emit({"log": "[SYSTEM]: OPTICAL ARRAY ENGAGED"})
                    base64_image = self.vision_master.get_base64_snapshot()
                    if base64_image:
                        decision = self.brain.analyze_image(base64_image, user_input)
                    else:
                        decision = {"spoken_response": "My optical sensors appear to be offline.", "ui_action": "none"}
                else:
                    decision = self.brain.think(user_input)

                spoken_text = decision.get("spoken_response", "I encountered a cognitive error.")
                ui_action = decision.get("ui_action", "none")
                target = decision.get("target", "")
            
                logger.info(f"Brain Decision - UI Action: {ui_action} | Target: {target} | Spoken: {spoken_text}")
            
                if ui_action == "standby":
                    self.system_locked = True 
                    self.vision_master.set_vision_mode("SECURITY")
                    self.status_signal.emit({"log": "[SYSTEM]: ENTERING STANDBY. ARMING CAMERA.", "action": "minimize_dashboard"})
                    self.mouth.speak(spoken_text)
                    continue
                elif ui_action == "minimize":
                    self.status_signal.emit({"log": "[SYSTEM]: MINIMIZING DASHBOARD TO FLOATING ORB.", "action": "minimize_dashboard"})
                    self.mouth.speak(spoken_text)
                    continue
                elif ui_action == "maximize":
                    self.system_locked = False 
                    self.vision_master.set_vision_mode("IDLE")
                    self.status_signal.emit({"log": "[SYSTEM]: RESTORING UI", "action": "restore_dashboard"})
                    self.mouth.speak(spoken_text)
                    continue
                elif ui_action == "show_widget":
                    news_q = decision.get("news_query", "") if isinstance(decision, dict) else ""
                    self.status_signal.emit({
                        "log": f"[HUD]: REVEALING HOLOGRAPHIC COMPONENT: {str(target).upper()}",
                        "action": "show_widget",
                        "target": target,
                        "query": news_q
                    })
                    if target == "news":
                        hud_ref = getattr(IntelHub(), 'hud_ref', None)
                        is_already_open = bool(hud_ref and hasattr(hud_ref, 'news_widget') and hud_ref.news_widget.isVisible())
                        if news_q:
                            if not spoken_text or any(phrase in spoken_text for phrase in ["Deploying Global Situation Room", "Holographically revealing news", "revealing news"]):
                                briefing_res = IntelHub().execute_news_query(news_q, auto_speak=False, sync=True)
                                spoken_text = briefing_res.get("spoken", f"Here is the latest intelligence regarding {news_q}, sir.")
                        else:
                            if not is_already_open:
                                briefing_res = IntelHub().execute_news_query("", auto_speak=False, sync=True)
                                spoken_text = briefing_res.get("spoken", spoken_text)
                            else:
                                spoken_text = "Global situation room intelligence is active on your display, sir."

                    elif target == "weather":
                        w_res = IntelHub().execute_weather_query("what is the weather today")
                        spoken_text = w_res.get("spoken", spoken_text)
                    elif target == "map":
                        m_res = IntelHub().execute_map_query("")
                        spoken_text = m_res.get("spoken", spoken_text)
                    self.mouth.speak(spoken_text)
                    continue
                elif ui_action == "hide_widget":
                    self.status_signal.emit({
                        "log": f"[HUD]: DISMISSING COMPONENT: {str(target).upper()}",
                        "action": "hide_widget",
                        "target": target
                    })
                    self.mouth.speak(spoken_text)
                    continue
                elif ui_action == "recenter_reactor":
                    self.status_signal.emit({
                        "log": "[HUD]: RE-CENTERING ARC REACTOR CORE",
                        "action": "recenter_reactor"
                    })
                    self.mouth.speak(spoken_text)
                    continue
                elif ui_action == "combat_on":
                    self.status_signal.emit({"log": "[SYSTEM]: PROTOCOL OMEGA ACTIVATED", "action": "combat_on"})
                    self.mouth.speak(spoken_text)
                    continue
                elif ui_action == "combat_off":
                    self.status_signal.emit({"log": "[SYSTEM]: RETURNING TO STANDARD OPERATIONS", "action": "combat_off"})
                    self.mouth.speak(spoken_text)
                    continue
                elif ui_action == "antigravity_mode":
                    self.status_signal.emit({"log": "[SYSTEM]: QUANTUM COGNITIVE CORE ONLINE", "action": "antigravity_on"})
                    self.mouth.speak(spoken_text)
                    continue
                elif ui_action in ("antigravity_off", "standard_mode"):
                    self.status_signal.emit({"log": "[SYSTEM]: DISENGAGING QUANTUM CORE. RETURNING TO STANDARD OPERATIONS.", "action": "combat_off"})
                    self.mouth.speak(spoken_text)
                    continue

                elif ui_action == "kinetic_on":
                    self.status_signal.emit({"log": "[SYSTEM]: KINETIC INTERFACE ONLINE. RAISE YOUR HAND."})
                    self.vision_master.set_vision_mode("KINETIC")
                    self.mouth.speak(spoken_text)
                    continue
                elif ui_action == "kinetic_off":
                    self.status_signal.emit({"log": "[SYSTEM]: KINETIC INTERFACE OFFLINE."})
                    self.vision_master.set_vision_mode("IDLE")
                    self.mouth.speak(spoken_text)
                    continue
                elif ui_action == "lock_screen":
                    self.system_locked = True
                    self.vision_master.set_vision_mode("SECURITY")
                    self.status_signal.emit({"log": "[SECURITY]: WORKSTATION LOCKED. AWAITING BIOMETRICS.", "action": "combat_on"})
                    self.mouth.speak(spoken_text)
                    continue
                elif ui_action == "enable_mobile":
                    self.status_signal.emit({"log": "[SYSTEM]: INITIALIZING MOBILE UPLINK (PORT 8000)..."})
                    success, msg = self.automation.start_mobile_uplink()
                    self.status_signal.emit({"log": f"[MOBILE BRIDGE]: {msg.upper()}"})
                    self.mouth.speak(spoken_text if spoken_text else msg)
                    continue
                elif ui_action == "disable_mobile":
                    self.status_signal.emit({"log": "[SYSTEM]: TERMINATING MOBILE UPLINK..."})
                    success, msg = self.automation.stop_mobile_uplink()
                    self.status_signal.emit({"log": f"[MOBILE BRIDGE]: {msg.upper()}"})
                    self.mouth.speak(spoken_text if spoken_text else msg)
                    continue
                elif ui_action == "activate_watchdog":
                    target_str = target if target else "person"
                    self.status_signal.emit({
                        "log": f"[SYSTEM]: ROUTING CAMERA TO WATCHDOG: {target_str.upper()}",
                        "action": "watchdog_active",
                        "target": target_str
                    })
                    self.vision_master.set_vision_mode("WATCHDOG", target_str)
                    self.mouth.speak(spoken_text if spoken_text else f"Optical watchdog armed. Monitoring for {target_str}, sir.")
                    continue
                elif ui_action == "deactivate_watchdog":
                    self.status_signal.emit({
                        "log": "[SYSTEM]: DISARMING WATCHDOG",
                        "action": "watchdog_disarmed"
                    })
                    self.vision_master.set_vision_mode("IDLE")
                    self.mouth.speak(spoken_text if spoken_text else "Optical watchdog disarmed. Sensors returned to idle.")
                    continue
                elif ui_action == "sleep":
                    self.status_signal.emit({"log": "[SYSTEM]: INITIATING HIBERNATION..."})
                    self.mouth.speak(spoken_text) 
                    time.sleep(2)
                    self.automation.sleep_pc()

                elif ui_action == "check_calendar":
                    self.status_signal.emit({"log": "[SYSTEM]: QUERYING UPCOMING CALENDAR EVENTS..."})
                    events = workspace.get_upcoming_events()
                    if not events:
                        if not workspace.calendar_service:
                            cal_msg = "Google Calendar synchronization is currently offline or credentials unverified. No local meetings scheduled."
                        else:
                            cal_msg = "Your Google Calendar is synchronized. You have no meetings scheduled for the next 24 hours."
                    else:
                        event_summaries = []
                        for e in events[:5]:
                            name = e.get("summary", "Untitled Meeting")
                            st = e.get("start", {}).get("dateTime", e.get("start", {}).get("date", ""))
                            if "T" in st:
                                time_part = st.split("T")[1][:5]
                                event_summaries.append(f"{name} at {time_part}")
                            else:
                                event_summaries.append(name)
                    self.status_signal.emit({
                        "log": f"[CALENDAR CORE]: {cal_msg}",
                        "action": "update_calendar",
                        "message": cal_msg
                    })
                    self.mouth.speak(cal_msg)
                    continue

                elif ui_action == "whatsapp_message":
                    contact = target.get("contact", "") if isinstance(target, dict) else ""
                    message = target.get("message", "") if isinstance(target, dict) else ""
                    self.status_signal.emit({"log": f"[COMM]: DISPATCHING WHATSAPP TO {contact.upper()}..."})
                    self.mouth.speak(spoken_text)
                    success, res_msg = self.automation.send_whatsapp_message(contact, message)
                    self.status_signal.emit({"log": f"[COMM]: {res_msg}"})
                    continue

                elif ui_action == "check_emails":
                    self.status_signal.emit({"log": "[SYSTEM]: FETCHING UNREAD GMAIL MESSAGES..."})
                    email_summary = workspace.get_unread_emails(max_results=target)
                    self.status_signal.emit({"log": f"[GMAIL TELEMETRY]:\n{email_summary}"})
                
                    # Have Jarvis summarize what he found
                    prompt = f"Summarize these unread emails concisely in 1 or 2 sentences: {email_summary}"
                    summary_res = self.brain.think(prompt)
                    spoken_text = summary_res.get("spoken_response", "Email check complete.")
                    self.mouth.speak(spoken_text)
                    continue

                elif ui_action == "create_task":
                    title = target.get("title", "") if isinstance(target, dict) else str(target)
                    notes = target.get("notes", "") if isinstance(target, dict) else ""
                    self.status_signal.emit({"log": f"[SYSTEM]: SCHEDULING GOOGLE TASK: {title}"})
                    result_msg = workspace.create_task(title, notes)
                    self.status_signal.emit({"log": f"[TASK MANAGER]: {result_msg}"})
            
                elif ui_action == "schedule_alarm":
                    summary = target.get("summary", "") if isinstance(target, dict) else str(target)
                    start_time = target.get("start_time", "") if isinstance(target, dict) else ""
                    end_time = target.get("end_time", "") if isinstance(target, dict) else ""
                
                    self.status_signal.emit({"log": f"[SYSTEM]: ARMING TEMPORAL ALARM: {summary}"})
                    result_msg = workspace.create_calendar_event(summary, start_time, end_time)
                    self.status_signal.emit({"log": f"[CALENDAR CORE]: {result_msg}"})
            
                elif ui_action == "inject_keystroke":
                    try:
                        mode, payload = target.split("|", 1)
                        self.automation.inject_keystroke(mode, payload)
                    except ValueError:
                        print("[PC Error] Invalid keystroke target format.")

                # --- BROWSER EXECUTION ---
                elif ui_action == "open_website":
                    target_url = target if target else "https://google.com"
                    self.automation.open_website(target_url)

                elif ui_action == "execute_macro":
                    self.status_signal.emit({"log": "[SYSTEM]: EXECUTING MACRO ARRAY..."})
                    success, message = self.automation.execute_macro(target)

                    if not success:
                        # ==========================================
                        # PHASE 3: THE OPTICAL OVERRIDE
                        # ==========================================
                        self.status_signal.emit({"log": f"[SYSTEM ERROR]: {message}"})
                        self.status_signal.emit({"log": "[SYSTEM]: ENGAGING OPTICAL OVERRIDE..."})
                        self.mouth.speak("The automated sequence encountered an anomaly. Switching to optical targeting.")

                        # Inject the failure context back into the Brain's command queue
                        fallback_prompt = f"SYSTEM FAULT: The macro failed. Reason: {message}. You must now use 'vision_click' to manually find the UI element, or use 'analyze_screen' to read whatever is blocking the screen."
                        self.command_queue.put(fallback_prompt)

                    else:
                        self.status_signal.emit({"log": "[SYSTEM]: MACRO SEQUENCE COMPLETE."})

                elif ui_action == "pilot_desktop":
                    action_type = target.get("action", "") if isinstance(target, dict) else ""
                    app_name = target.get("app_name", "") if isinstance(target, dict) else ""
                    self.status_signal.emit({"log": f"[SYSTEM]: INTERFACING WITH OS KERNEL: {app_name.upper()}"})
                    if action_type == "scan_window":
                        self.mouth.speak(spoken_text) 
                        scan_data = self.automation.pilot_desktop("scan_window", app_name)
                        if "ACCESS DENIED" in scan_data or "SYSTEM ERROR" in scan_data:
                            self.status_signal.emit({"log": f"[JARVIS]: {scan_data}"})
                            self.mouth.speak(scan_data)
                            continue
                        prompt = f"I scanned the Windows application '{app_name}'. Here is the UIA Accessibility Tree: {scan_data}. Summarize the primary buttons or inputs available for the user in 1 or 2 sentences."
                        self.status_signal.emit({"log": "[SYSTEM]: ANALYZING UI AUTOMATION TREE..."})
                        follow_up = self.brain.think(prompt)
                        spoken_text = follow_up.get("spoken_response", "Application scan complete.")
                        self.status_signal.emit({"log": f"[JARVIS]: {spoken_text}"})
                        self.mouth.speak(spoken_text)
                        continue 
                    else:
                        element_name = target.get("element_name") if isinstance(target, dict) else None
                        text_val = target.get("text") if isinstance(target, dict) else None
                        response = self.automation.pilot_desktop(action_type, app_name=app_name, element_name=element_name, text=text_val)
                        self.status_signal.emit({"log": f"[SYSTEM]: {response}"})

                elif ui_action == "delegate_to_antigravity":
                    task_payload = target if isinstance(target, dict) else {"task": str(target), "task_type": "general"}
                    task_str = task_payload.get("task", "")
                    tasks_list = task_payload.get("tasks", [])
                    task_category = task_payload.get("task_type", "general")

                    agent_count = len(tasks_list) if (tasks_list and len(tasks_list) > 1) else 1
                    msg_suffix = f" ({agent_count} PARALLEL AGENTS)" if agent_count > 1 else ""
                    self.status_signal.emit({"log": f"[SYSTEM]: DELEGATING TASK TO ANTIGRAVITY AGENT ({task_category.upper()}){msg_suffix}", "action": "antigravity_start"})
                    self.mouth.speak(spoken_text)

                    def run_antigravity_worker():
                        def progress_hud(log_msg):
                            tool_name = None
                            if "Executing " in log_msg:
                                try:
                                    tool_name = log_msg.split("Executing ")[1].split("...")[0].strip()
                                except Exception:
                                    tool_name = None
                        
                            if tool_name:
                                self.status_signal.emit({"log": log_msg, "action": "antigravity_tool", "tool": tool_name})
                            else:
                                self.status_signal.emit({"log": log_msg})

                        if tasks_list and len(tasks_list) > 1:
                            res = self.brain.antigravity.execute_tasks_parallel(tasks_list, task_category, progress_callback=progress_hud)
                        else:
                            single_task = task_str if task_str else (tasks_list[0] if tasks_list else "")
                            res = self.brain.antigravity.execute_task(single_task, task_category, progress_callback=progress_hud)

                        if res.get("success"):
                            self.status_signal.emit({"log": f"[ANTIGRAVITY RESULT]: {res.get('output', '')}", "action": "antigravity_done"})
                            self.mouth.speak(res.get("summary", "Task completed."))
                        else:
                            self.status_signal.emit({"log": f"[ANTIGRAVITY ERROR]: {res.get('error', 'Execution error')}", "action": "antigravity_done"})
                            self.mouth.speak(res.get("summary", "An error occurred."))

                    threading.Thread(target=run_antigravity_worker, daemon=True).start()
                    continue

                elif ui_action == "open_app":
                    target_clean = target.lower().strip() if isinstance(target, str) else ""
                    if "news" in target_clean or "situation" in target_clean:
                        self.automation.dispatch_satellite_app("news", "CONFLICTS")
                    elif "weather" in target_clean or "radar" in target_clean:
                        self.automation.dispatch_satellite_app("weather", "Edakkunnam")
                    elif "map" in target_clean or "gps" in target_clean:
                        self.automation.dispatch_satellite_app("map", "Kerala")
                    else:
                        self.automation.open_app(target)
                    
                elif ui_action == "switch_app":
                    self.status_signal.emit({"log": "[SYSTEM]: SWITCHING ACTIVE WINDOW"})
                    self.automation.switch_app()
                elif ui_action == "close_current":
                    self.status_signal.emit({"log": "[SYSTEM]: TERMINATING ACTIVE WINDOW"})
                    self.automation.close_current_app()
                elif ui_action == "close_app":
                    self.status_signal.emit({"log": f"[SYSTEM]: HUNTING PROCESS: '{str(target).upper()}'"})
                    self.automation.close_named_app(target)

                elif ui_action == "deep_search":
                    self.status_signal.emit({"log": f"[SYSTEM]: INITIATING GLOBAL UPLINK: {target}"})
                    self.mouth.speak(spoken_text) 
                    search_results = self.automation.deep_search(target)
                    self.status_signal.emit({"log": search_results, "action": "show_news"})
                    self.status_signal.emit({"log": "[SYSTEM]: COMPILING SUMMARY..."})
                    prompt = f"Summarize these web search results concisely in 1 or 2 sentences for the user to hear: {search_results}"
                    summary_decision = self.brain.think(prompt)
                    summary_text = summary_decision.get("spoken_response", "Search operations concluded.")
                    self.status_signal.emit({"log": f"[JARVIS]: {summary_text}"})
                    self.mouth.speak(summary_text)
                    continue 

                elif ui_action == "vision_click":
                    self.status_signal.emit({"log": f"[SYSTEM]: TARGETING '{str(target).upper()}' INITIATED"})
                    self.mouth.speak(f"Targeting {target} now, sir.")
                
                    # --- TIER 1: DOM MANIPULATION (Web Core) ---
                    self.status_signal.emit({"log": "[SYSTEM]: ATTEMPTING DIRECT DOM INJECTION..."})
                    dom_success = self.automation.dom_click(target)
                
                    if dom_success:
                        self.status_signal.emit({"log": f"[JARVIS]: Executed structural click on {target}."})
                        continue
                    
                    # --- TIER 3: VISION FALLBACK (Canvas / Desktop) ---
                    self.status_signal.emit({"log": "[SYSTEM]: DOM FAILED. ENGAGING OPTICAL ARRAY..."})
                    base64_screen = self.automation.take_screenshot(return_base64=True)
                    self.status_signal.emit({"log": "[SYSTEM]: CALCULATING SPATIAL COORDINATES..."})
                    coords = self.brain.find_coordinates(base64_screen, target)
    
                    if coords and "x" in coords and "y" in coords:
                        rough_x, rough_y = int(coords["x"]), int(coords["y"])
                        self.status_signal.emit({"log": "[SYSTEM]: ENGAGING EDGE-DETECTION AUTO-AIM..."})
                        exact_x, exact_y = self.automation.magnetic_snap(rough_x, rough_y)
                        self.status_signal.emit({"log": f"[SYSTEM]: TARGET LOCKED AT X:{exact_x} Y:{exact_y}"})
                    
                        import pyautogui
                        pyautogui.moveTo(exact_x, exact_y, duration=0.6, tween=pyautogui.easeOutQuad)
                        pyautogui.click()
                        self.status_signal.emit({"log": f"[JARVIS]: Executed visual click on {target}."})
                    else:
                        self.status_signal.emit({"log": "[CRITICAL]: TARGET NOT FOUND ON SCREEN."})
                        self.mouth.speak(f"I could not locate the {target} systematically or visually, sir.")
                    continue 
            
                elif ui_action == "read_screen":
                    self.status_signal.emit({"log": "[SYSTEM]: DUAL-LAYER PERCEPTION SCANNING MONITOR..."})
                    # Asynchronously speak acknowledgment so screen capture and vision analysis execute concurrently
                    threading.Thread(target=self.mouth.speak, args=("Scanning the active screen, sir.",), daemon=True).start()
                    screen_info = self.screen_reader.read_screen(user_prompt=target if target else None, brain=self.brain)
                    spoken_text = screen_info.get("spoken_response", "I could not decipher the contents of the screen.")
                    win_title = screen_info.get("window_title", "Desktop")
                    proc = screen_info.get("process", "unknown")
                    self.status_signal.emit({"log": f"[SCREEN PERCEPTION]: App: {proc} | Window: {win_title}"})
                    self.status_signal.emit({"log": f"[JARVIS]: {spoken_text}"})
                    self.mouth.speak(spoken_text)
                    continue 

                elif ui_action == "vol_up":
                    self.status_signal.emit({"log": "[SYSTEM]: INCREASING AUDIO GAIN"})
                    self.automation.set_volume("up")
                elif ui_action == "vol_down":
                    self.status_signal.emit({"log": "[SYSTEM]: DECREASING AUDIO GAIN"})
                    self.automation.set_volume("down")
                elif ui_action == "mute":
                    self.status_signal.emit({"log": "[SYSTEM]: MUTING SYSTEM AUDIO"})
                    self.automation.set_volume("mute")
                elif ui_action == "screenshot":
                    self.status_signal.emit({"log": "[SYSTEM]: CAPTURING SCREEN STATE"})
                    self.automation.take_screenshot()

                self.status_signal.emit({"log": f"[JARVIS]: {spoken_text}"})

                if ui_action not in ["sleep", "deep_search", "read_screen", "pilot_browser", "vision_click"]:
                    self.mouth.speak(spoken_text)
            except Exception as e:
                logger.error("Error in worker loop", exc_info=True)
                self.status_signal.emit({"log": f"[ERROR]: COMMAND EXECUTION ANOMALY: {str(e)}", "action": "standby"})

class AsyncBootWorker(QThread):
    progress_signal = pyqtSignal(dict)
    boot_complete_signal = pyqtSignal(dict)

    def stop(self):
        self.requestInterruption()
        self.quit()
        self.wait(1000)

    def run(self):
        t_start = time.perf_counter()
        self.progress_signal.emit({"log": "[INIT]: POWER ON SELF TEST..."})
        time.sleep(0.04)

        self.progress_signal.emit({"log": "[INIT]: INITIALIZING COGNITIVE BRAIN..."})
        try:
            brain = JarvisBrain()
            self.progress_signal.emit({"log": "[INIT]: NEURAL NETWORK ONLINE."})
        except Exception as e:
            logger.critical(f"Critical fault initializing JarvisBrain: {e}", exc_info=True)
            brain = None

        self.progress_signal.emit({"log": "[INIT]: CALIBRATING OPTICAL BIOMETRIC ARRAY..."})
        try:
            security = BiometricSecurity()
            self.progress_signal.emit({"log": "[INIT]: BIOMETRIC SHIELD ARMED."})
        except Exception as e:
            logger.critical(f"Critical fault initializing BiometricSecurity: {e}", exc_info=True)
            security = None

        self.progress_signal.emit({"log": "[INIT]: ACOUSTIC PERCEPTION ACTIVE..."})
        try:
            ears = JarvisEars()
        except Exception as e:
            logger.critical(f"Critical fault initializing JarvisEars: {e}", exc_info=True)
            ears = None

        self.progress_signal.emit({"log": "[INIT]: NEURAL SPEECH SYNTHESIS ONLINE."})
        try:
            mouth = JarvisMouth()
        except Exception as e:
            logger.critical(f"Critical fault initializing JarvisMouth: {e}", exc_info=True)
            mouth = None

        try:
            automation = JarvisAutomation()
        except Exception as e:
            logger.critical(f"Critical fault initializing JarvisAutomation: {e}", exc_info=True)
            automation = None

        total_boot_s = time.perf_counter() - t_start
        self.progress_signal.emit({"log": ">> J.A.R.V.I.S. SYSTEM FULLY OPERATIONAL."})

        self.boot_complete_signal.emit({
            "brain": brain,
            "security": security,
            "ears": ears,
            "mouth": mouth,
            "automation": automation
        })

def main():
    for arg in ["--use-angle=d3d11", "--mute-audio", "--enable-zero-copy", "--num-raster-threads=4"]:
        if arg not in sys.argv:
            sys.argv.append(arg)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
    app = QApplication(sys.argv)
    
    # Instant UI Presentation: Show HUD immediately at t=0
    hud = JarvisHUD()
    hud.show()
    app.processEvents() # Render HUD immediately to screen

    # State container for active worker and pending commands during async boot
    active_worker = {"worker": None}
    pending_commands = []

    def dispatch_text_command(text):
        if active_worker["worker"] is not None:
            active_worker["worker"].receive_text_command(text)
        else:
            pending_commands.append(text)

    def dispatch_mute_state(val):
        if active_worker["worker"] is not None:
            active_worker["worker"].set_mute_state(val)

    def dispatch_intercept_audio():
        if active_worker["worker"] is not None:
            active_worker["worker"].intercept_audio()

    def dispatch_hud_state(val):
        if active_worker["worker"] is not None:
            active_worker["worker"].handle_hud_state(val)

    # Wire user HUD signals immediately so UI interactions are never dropped
    hud.text_command_signal.connect(dispatch_text_command)
    hud.mute_signal.connect(dispatch_mute_state)
    hud.interrupt_speech_signal.connect(dispatch_intercept_audio)
    hud.hud_state_signal.connect(dispatch_hud_state)

    # Launch Asynchronous Subsystem Boot Worker in background QThread
    boot_worker = AsyncBootWorker()
    boot_worker.progress_signal.connect(hud.update_text)

    def on_subsystems_ready(subsystems):
        brain = subsystems.get("brain")
        ears = subsystems.get("ears")
        mouth = subsystems.get("mouth")
        automation = subsystems.get("automation")
        security = subsystems.get("security")

        try:
            worker = JarvisWorker(ears, brain, mouth, automation, security, hud=hud)
            active_worker["worker"] = worker
            worker.status_signal.connect(hud.update_text)
            
            # Drain any manual override commands queued during boot
            for cmd in pending_commands:
                worker.receive_text_command(cmd)
            pending_commands.clear()

            worker.start(QThread.Priority.LowPriority)
            app.aboutToQuit.connect(worker.stop)
            logger.info("JarvisWorker successfully bound and running.")
        except Exception as e:
            logger.critical(f"Failed to start JarvisWorker after boot: {e}", exc_info=True)

    boot_worker.boot_complete_signal.connect(on_subsystems_ready)
    boot_worker.start()
    app.aboutToQuit.connect(boot_worker.stop)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()