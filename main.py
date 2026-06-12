import sys
import time
import keyboard
import logging
import threading
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread, pyqtSignal

from gui.hud import JarvisHUD
from core.brain import JarvisBrain
from core.ears import JarvisEars
from core.mouth import JarvisMouth
from core.eyes import JarvisEyes
from core.monitor import SystemMonitor 
from utils.automation import JarvisAutomation

# ==========================================
# 1. SYSTEM LOGGING & CRASH INTERCEPTOR
# ==========================================
logging.basicConfig(
    filename='jarvis_system.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("JarvisCore")
logger.info("=======================================")
logger.info("SYSTEM BOOT SEQUENCE INITIATED.")

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.critical("FATAL SYSTEM CRASH", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception

# ==========================================
# 2. CHROMIUM HARDWARE ACCELERATION
# ==========================================
sys.argv.append("--use-angle=d3d11")
sys.argv.append("--mute-audio")
sys.argv.append("--enable-zero-copy")
sys.argv.append("--num-raster-threads=4") 

class JarvisWorker(QThread):
    status_signal = pyqtSignal(dict)

    def __init__(self, ears, brain, mouth, eyes, automation):
        super().__init__()
        self.ears = ears
        self.brain = brain
        self.mouth = mouth
        self.eyes = eyes
        self.automation = automation
        
        keyboard.on_press_key("enter", self.intercept_audio)
        logger.info("Global audio intercept hook (Enter) initialized.")

    def intercept_audio(self, event):
        if self.mouth.is_speaking():
            self.mouth.stop()
            logger.info("User manually interrupted audio playback.")
            self.status_signal.emit({"log": "[SYSTEM]: VOCAL OUTPUT INTERRUPTED", "action": "standby"})

    def handle_system_alert(self, msg):
        if isinstance(msg, dict):
            if msg.get("type") == "wifi_telemetry":
                self.status_signal.emit({"action": "update_wifi", "data": msg})
            return

        self.status_signal.emit({"log": msg})
        logger.warning(msg)
        
        if "[WARNING]" in msg:
            threading.Thread(target=self.mouth.speak, args=("Warning. Anomaly detected in system resource telemetry.",), daemon=True).start()
        elif "[CRITICAL]" in msg:
            threading.Thread(target=self.mouth.speak, args=("Critical alert. Secure uplink to the global network has been severed.",), daemon=True).start()

    def run(self):
        time.sleep(1)
        boot_logs = [
            "[INIT]: POWER ON SELF TEST...",
            "[INIT]: MOUNTING LOCAL STORAGE...",
            "[INIT]: CALIBRATING OPTICAL ARRAY...",
            "[INIT]: ESTABLISHING SECURE UPLINK...",
            "[INIT]: NEURAL NETWORK ONLINE.",
            ">> J.A.R.V.I.S. SYSTEM FULLY OPERATIONAL."
        ]
        
        for log in boot_logs:
            self.status_signal.emit({"log": log})
            time.sleep(0.6) 

        self.monitor = SystemMonitor(alert_callback=self.handle_system_alert)
        logger.info("UI Cold Start complete. Agentic loop running.")
        
        vision_triggers = ["look", "see", "what is this", "who is", "describe this"]
        
        while True:
            self.status_signal.emit({"action": "standby"})
            time.sleep(0.05) 
            
            user_input = self.ears.listen()
            
            if user_input and len(user_input.strip()) > 3:
                self.status_signal.emit({"action": "wake"})
                self.status_signal.emit({"log": f"[USER]: {user_input}"})
                logger.info(f"User Input Received: {user_input}")
                
                user_lower = user_input.lower().replace(".", "").replace(",", "")
                
                if any(trigger in user_lower for trigger in vision_triggers):
                    self.status_signal.emit({"log": "[SYSTEM]: OPTICAL ARRAY ENGAGED"})
                    base64_image, img_path = self.eyes.capture_snapshot()
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
                
                # ==========================================
                # NEURAL EXECUTION & AUTOMATION ROUTING
                # ==========================================
                
                if ui_action == "minimize":
                    self.status_signal.emit({"log": "[SYSTEM]: MINIMIZING UI", "action": "minimize_dashboard"})
                elif ui_action == "maximize":
                    self.status_signal.emit({"log": "[SYSTEM]: RESTORING UI", "action": "restore_dashboard"})
                elif ui_action == "combat_on":
                    self.status_signal.emit({"log": "[SYSTEM]: PROTOCOL OMEGA ACTIVATED", "action": "combat_on"})
                elif ui_action == "combat_off":
                    self.status_signal.emit({"log": "[SYSTEM]: RETURNING TO STANDARD OPERATIONS", "action": "combat_off"})
                
                # --- RAG DEEP SEARCH (MULTI-TURN LOOP) ---
                elif ui_action == "deep_search":
                    self.status_signal.emit({"log": f"[SYSTEM]: INITIATING GLOBAL UPLINK: {target}"})
                    self.mouth.speak(spoken_text) 
                    
                    # 1. Execute the headless web scrape via DDGS
                    search_results = self.automation.deep_search(target)
                    
                    # 2. Push the scraped text directly to the Dashboard's floating News Overlay!
                    self.status_signal.emit({"log": search_results, "action": "show_news"})
                    
                    # 3. Have Jarvis summarize the raw text aloud
                    self.status_signal.emit({"log": "[SYSTEM]: COMPILING SUMMARY..."})
                    prompt = f"Summarize these web search results concisely in 1 or 2 sentences for the user to hear: {search_results}"
                    summary_decision = self.brain.think(prompt)
                    
                    summary_text = summary_decision.get("spoken_response", "Search operations concluded.")
                    self.status_signal.emit({"log": f"[JARVIS]: {summary_text}"})
                    self.mouth.speak(summary_text)
                    continue
                
                # --- ZERO-LATENCY WEB BROWSER PILOT ---
                elif ui_action == "pilot_browser":
                    action_type = target.get("action", "")
                    self.status_signal.emit({"log": f"[SYSTEM]: PILOTING BROWSER: {action_type.upper()}"})
                    
                    if action_type == "scan_page":
                        self.mouth.speak(spoken_text) 
                        
                        scan_data = self.automation.pilot_browser("scan_page")
                        prompt = f"I scanned the webpage. Here are the interactive HTML elements: {scan_data}. Summarize the primary buttons or text inputs available for the user to interact with in 2 sentences."
                        self.status_signal.emit({"log": "[SYSTEM]: ANALYZING DOM TREE..."})
                        
                        follow_up = self.brain.think(prompt)
                        spoken_text = follow_up.get("spoken_response", "Scan complete.")
                        self.status_signal.emit({"log": f"[JARVIS]: {spoken_text}"})
                        self.mouth.speak(spoken_text)
                        continue 
                    else:
                        self.automation.pilot_browser(
                            action_type, 
                            url=target.get("url"), 
                            selector=target.get("selector"), 
                            text=target.get("text")
                        )
                # --- ZERO-LATENCY NATIVE DESKTOP PILOT ---
                elif ui_action == "pilot_desktop":
                    action_type = target.get("action", "")
                    app_name = target.get("app_name", "")
                    self.status_signal.emit({"log": f"[SYSTEM]: INTERFACING WITH OS KERNEL: {app_name.upper()}"})
                    
                    if action_type == "scan_window":
                        self.mouth.speak(spoken_text) 
                        
                        scan_data = self.automation.pilot_desktop("scan_window", app_name)
                        
                        # Catch the sandbox denial and read it aloud
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
                        response = self.automation.pilot_desktop(
                            action_type, 
                            app_name=app_name, 
                            element_name=target.get("element_name"), 
                            text=target.get("text")
                        )
                        self.status_signal.emit({"log": f"[SYSTEM]: {response}"})

                # --- APP & WINDOW CONTROL ---
                elif ui_action == "open_app":
                    self.status_signal.emit({"log": f"[SYSTEM]: SCANNING FOR '{target.upper()}'"})
                    self.automation.open_app(target)
                elif ui_action == "switch_app":
                    self.status_signal.emit({"log": "[SYSTEM]: SWITCHING ACTIVE WINDOW"})
                    self.automation.switch_app()
                elif ui_action == "close_current":
                    self.status_signal.emit({"log": "[SYSTEM]: TERMINATING ACTIVE WINDOW"})
                    self.automation.close_current_app()
                elif ui_action == "close_app":
                    self.status_signal.emit({"log": f"[SYSTEM]: HUNTING PROCESS: '{target.upper()}'"})
                    self.automation.close_named_app(target)

                # --- THE GLOBAL UPLINK ROUTING ---
                elif ui_action == "deep_search":
                    self.status_signal.emit({"log": f"[SYSTEM]: INITIATING GLOBAL UPLINK: {target}"})
                    self.mouth.speak(spoken_text) 
                    
                    # 1. Execute the headless web scrape via DDGS
                    search_results = self.automation.deep_search(target)
                    
                    # 2. Push the scraped text directly to the Dashboard's floating News Overlay!
                    self.status_signal.emit({"log": search_results, "action": "show_news"})
                    
                    # 3. Have Jarvis summarize the raw text aloud
                    self.status_signal.emit({"log": "[SYSTEM]: COMPILING SUMMARY..."})
                    prompt = f"Summarize these web search results concisely in 1 or 2 sentences for the user to hear: {search_results}"
                    summary_decision = self.brain.think(prompt)
                    
                    summary_text = summary_decision.get("spoken_response", "Search operations concluded.")
                    self.status_signal.emit({"log": f"[JARVIS]: {summary_text}"})
                    self.mouth.speak(summary_text)
                    continue 

                # --- OPTICAL SCREEN READING ---
                elif ui_action == "read_screen":
                    self.status_signal.emit({"log": "[SYSTEM]: OPTICAL ARRAY SCANNING MONITOR..."})
                    self.mouth.speak("Scanning the screen now, sir.")
                    
                    base64_screen = self.automation.take_screenshot(return_base64=True)
                    
                    prompt = "Please read and summarize the primary text or content visible on this screen. Ignore the standard OS UI elements and focus on the main content the user is looking at."
                    self.status_signal.emit({"log": "[SYSTEM]: VISION MODEL PROCESSING PIXELS..."})
                    
                    vision_decision = self.brain.analyze_image(base64_screen, prompt)
                    
                    spoken_text = vision_decision.get("spoken_response", "I could not decipher the contents of the screen.")
                    self.status_signal.emit({"log": f"[JARVIS]: {spoken_text}"})
                    self.mouth.speak(spoken_text)
                    continue 
                # --- VISION-BASED COORDINATE CLICKING (LEVEL 5 AGENT) ---
                elif ui_action == "vision_click":
                    self.status_signal.emit({"log": f"[SYSTEM]: OPTICAL SCAN FOR '{target.upper()}' INITIATED"})
                    self.mouth.speak(spoken_text)

                    # 1. Take a screenshot from RAM
                    base64_screen = self.automation.take_screenshot(return_base64=True)

                    # 2. Ask Vision model for exact X/Y coordinates
                    self.status_signal.emit({"log": "[SYSTEM]: CALCULATING SPATIAL COORDINATES..."})
                    coords = self.brain.find_coordinates(base64_screen, target)

                    # 3. Execute physical mouse movement
                    if coords and "x" in coords and "y" in coords:
                        x, y = int(coords["x"]), int(coords["y"])
                        self.status_signal.emit({"log": f"[SYSTEM]: TARGET AQUIRED AT X:{x} Y:{y}"})
                        
                        import pyautogui
                        # The "Iron Man" effect: Glide the mouse smoothly to the target in 0.5 seconds
                        pyautogui.moveTo(x, y, duration=0.5, tween=pyautogui.easeInOutQuad)
                        pyautogui.click()
                        
                        self.status_signal.emit({"log": f"[JARVIS]: Executed visual click on {target}."})
                    else:
                        self.status_signal.emit({"log": "[CRITICAL]: TARGET NOT FOUND ON SCREEN."})
                        self.mouth.speak(f"I could not visually locate the {target} on your screen, sir.")
                    continue

                # --- HARDWARE CONTROL ---
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
                elif ui_action == "sleep":
                    self.status_signal.emit({"log": "[SYSTEM]: INITIATING HIBERNATION..."})
                    self.mouth.speak(spoken_text) 
                    time.sleep(2)
                    self.automation.sleep_pc()

                if ui_action != "show_news":
                    self.status_signal.emit({"log": f"[JARVIS]: {spoken_text}"})

                if ui_action not in ["sleep", "deep_search", "read_screen", "pilot_browser"]:
                    self.mouth.speak(spoken_text)
                
            else:
                time.sleep(0.5)

def main():
    app = QApplication(sys.argv)
    
    try:
        brain = JarvisBrain()
        ears = JarvisEars()
        mouth = JarvisMouth()
        eyes = JarvisEyes()
        automation = JarvisAutomation() 
        logger.info("All core modules initialized successfully.")
    except Exception as e:
        logger.critical("CRITICAL BUILD FAULT during initialization.", exc_info=True)
        print(f"[CRITICAL BUILD FAULT] Initializations suspended: {e}")
        return

    hud = JarvisHUD()
    hud.show()

    worker = JarvisWorker(ears, brain, mouth, eyes, automation)
    worker.status_signal.connect(hud.update_text)
    worker.start(QThread.Priority.LowPriority)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()