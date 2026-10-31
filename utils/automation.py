import os
import subprocess
import webbrowser
import pyautogui
import win32com.client
import time
import psutil
import requests
import base64
from bs4 import BeautifulSoup
from googlesearch import search
from PIL import Image
from playwright.sync_api import sync_playwright 
from ddgs import DDGS
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning, module="duckduckgo_search")
import psutil
import socket
import json
import subprocess
import sys
import ctypes
import os
import webbrowser
brave_path = "C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe"

if os.path.exists(brave_path):
    webbrowser.register('brave', None, webbrowser.BackgroundBrowser(brave_path))
else:
    print("[WARNING] Brave Browser executable not found at standard path!")
class JarvisAutomation:
    def __init__(self):
        self.app_cache = {} 
        self.system_aliases = {
            "cmd": "cmd.exe",
            "command prompt": "cmd.exe",
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "chrome": "chrome.exe",
            "edge": "msedge.exe",
            "explorer": "explorer.exe",
            "settings": "ms-settings:",
            "device settings": "ms-settings:",
            "windows settings": "ms-settings:",
            "system settings": "ms-settings:",
            "notifications": "ms-settings:notifications",
            "notification settings": "ms-settings:notifications",
            "device notification settings": "ms-settings:notifications",
            "windows notifications": "ms-settings:notifications",
            "sound settings": "ms-settings:sound",
            "sound": "ms-settings:sound",
            "bluetooth settings": "ms-settings:bluetooth",
            "bluetooth": "ms-settings:bluetooth",
            "display settings": "ms-settings:display",
            "display": "ms-settings:display",
            "network settings": "ms-settings:network",
            "whatsapp": "whatsapp:",
            "spotify": "spotify:"
        }
        
        

    # ==========================================
    # 1. ZERO-LATENCY DESKTOP AUTOMATION (UIA)
    # ==========================================
    @staticmethod
    def is_cockpit_running(script_filename):
        """Sweeps the Windows Kernel Process Table to detect active satellite scripts."""
        for proc in psutil.process_iter(['cmdline']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline and any(script_filename.lower() in arg.lower() for arg in cmdline):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False

    def dispatch_satellite_app(self, app_type: str, parameter: str):
        """Universal Singleton Dispatcher. Guarantees zero duplicate window spawns."""
        config = {
            "news": {"script": "news_intel.py", "port": 7778, "key": "layer", "default": "CONFLICTS"},
            "weather": {"script": "weather_intel.py", "port": 7779, "key": "sector", "default": "Kochi"},
            "map": {"script": "map_intel.py", "port": 7777, "key": "place", "default": "Kerala"}
        }

        target_cfg = config.get(app_type.lower())
        if not target_cfg:
            return

        script_name = target_cfg["script"]
        port = target_cfg["port"]
        payload_key = target_cfg["key"]
        val = parameter if parameter else target_cfg["default"]

        # 1. INTERROGATE OS KERNEL: Is the window physically open right now?
        if self.is_cockpit_running(script_name):
            print(f"[SINGLETON GUARD]: '{script_name}' is already hot. Transmitting UDP reflow packet -> {val}")
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                datagram = json.dumps({payload_key: val, "command": "locate" if app_type=="map" else "switch"}).encode('utf-8')
                sock.sendto(datagram, ("127.0.0.1", port))
                sock.close()
            except Exception as e:
                print(f"[SINGLETON GUARD]: UDP Transmission fault -> {e}")
            return

        # 2. COLD BOOT: Process not found in Windows Task Manager. Spawning fresh instance.
        print(f"[SINGLETON GUARD]: Cold booting '{script_name}' -> {val}")
        script_path = os.path.join("apps", script_name)
        subprocess.Popen([sys.executable, script_path, val])
    def pilot_desktop(self, action, app_name, element_name=None, text=None):
        """Native UIAutomation engine with strict sandboxing and Macro Injection."""
        from pywinauto import Desktop 
        from pywinauto.keyboard import send_keys # The Macro Keystroke Engine
        
        PROTECTED_PROCESSES = ["explorer", "taskmgr", "cmd", "powershell", "regedit", "systemsettings"]
        clean_app = app_name.lower().strip()
        
        if any(protected in clean_app for protected in PROTECTED_PROCESSES):
            print(f"[SECURITY ALERT] Blocked AI attempt to interact with protected process: {app_name}")
            return "ACCESS DENIED: That is a protected system application."

        try:
            desktop = Desktop(backend="uia")
            
            # THE FIX: Request a WindowSpecification instead of a list of Wrappers
            # (?i) makes the regex case-insensitive so "whatsapp" matches "WhatsApp"
            target_window = desktop.window(title_re=f"(?i).*{app_name}.*", visible_only=True)
            
            if not target_window.exists(timeout=3):
                return f"SYSTEM ERROR: Could not find any active, visible window for '{app_name}'."
            
            # Bring the app to the front so macros don't hit the wrong window
            try:
                target_window.set_focus()
            except:
                pass

            if action == "scan_window":
                wrapper = target_window.wrapper_object()
                elements = (
                    wrapper.descendants(control_type="Button") + 
                    wrapper.descendants(control_type="Edit") + 
                    wrapper.descendants(control_type="MenuItem")
                )
                
                results = []
                for el in elements[:25]: 
                    name = el.window_text()
                    if name and len(name.strip()) > 1:
                        results.append({"type": el.element_info.control_type, "name": name})
                
                return f"Window Scan Complete. Interactive Elements found: {results}"
                
            elif action == "click":
                # Now child_window will work perfectly!
                elem = target_window.child_window(title_re=f"(?i).*{element_name}.*", found_index=0)
                elem.click_input() 
                return f"Successfully clicked '{element_name}'."
                
            elif action == "type":
                if element_name and element_name.strip():
                    # Type into a specific element
                    elem = target_window.child_window(title_re=f"(?i).*{element_name}.*", found_index=0)
                    elem.click_input()
                    elem.type_keys(text, with_spaces=True)
                    return f"Successfully typed into '{element_name}'."
                else:
                    # MACRO INJECTION: Fire global keys directly to the focused app
                    send_keys(text, with_spaces=True)
                    return f"Successfully injected keystroke macro into {app_name}."

        except Exception as e:
            print(f"[Automation] Desktop OS Error: {e}")
            return f"SYSTEM ERROR: Action failed due to OS exception: {str(e)}"

    # ==========================================
    # 2. ZERO-LATENCY WEB BROWSER PILOT
    # ==========================================
    
    def open_website(self, url):
        """Launches native Brave with the CDP debugging port exposed."""
        if not url:
            return "No URL provided."
            
        print(f"[Automation] Launching Native Brave Browser (Debug Mode) -> {url}")
        
        # We use subprocess to launch it silently without blocking Jarvis
        import subprocess
        brave_path = "C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe"
        
        try:
            # The --remote-debugging-port is the golden key for our DOM hijacker
            subprocess.Popen([brave_path, "--remote-debugging-port=9222", url])
            return "Brave browser launched with DOM access."
        except Exception as e:
            print(f"[Automation Error] Failed to launch Brave: {e}")
            return "Failed to launch browser."
    
    def dom_click(self, element_name):
        """Tier 1: Connects to Brave's active tab and clicks an element via the DOM."""
        from playwright.sync_api import sync_playwright
        
        print(f"[System] Attempting native DOM click on '{element_name}'...")
        
        with sync_playwright() as p:
            try:
                # 1. Jack into the native Brave browser
                browser = p.chromium.connect_over_cdp("http://localhost:9222")
                default_context = browser.contexts[0]
                page = default_context.pages[0] # Grab the currently active tab
                
                # 2. Search the DOM tree for the element (ignoring case)
                # It looks for visible text first, then checks hidden aria-labels
                target_locator = page.locator(f"text={element_name}").first
                
                if target_locator.count() == 0:
                    target_locator = page.locator(f"[aria-label*='{element_name}' i]").first
                
                if target_locator.count() == 0:
                    target_locator = page.locator(f"[placeholder*='{element_name}' i]").first

                # 3. Execute the native microsecond click
                if target_locator.count() > 0:
                    target_locator.click(timeout=2000)
                    print(f"[System] DOM Click successful.")
                    browser.close()
                    return True
                else:
                    print(f"[System] DOM Click failed. Target '{element_name}' not found in HTML tree.")
                    browser.close()
                    return False
                    
            except Exception as e:
                print(f"[System] DOM Connection failed. Ensure Brave is running. Error: {e}")
                return False
    def inject_keystroke(self, mode: str, payload: str):
        """
        Executes physical keystrokes on the PC.
        mode: "type" (writes a string) or "hotkey" (presses keys)
        payload: The text to write, or comma-separated keys (e.g., "ctrl,c")
        """
        try:
            if mode == "type":
                # Types out strings like a human (0.02s delay between keys)
                pyautogui.write(payload, interval=0.02)
                print(f"[Automation] Typed: {payload}")
                
            elif mode == "hotkey":
                # Converts a string like "ctrl,c" into a list ["ctrl", "c"]
                keys = [k.strip().lower() for k in payload.split(",")]
                pyautogui.hotkey(*keys)
                print(f"[Automation] Executed Hotkey: {keys}")
                
            return True
        except Exception as e:
            print(f"[Automation Error] Keystroke injection failed: {e}")
            return False
    
    
    def execute_macro(self, sequence: list):
        """
        Executes a sequence of actions and validates the active OS window.
        Returns (True, "Success") or (False, "Error message") for the ReAct fallback.
        """
        print(f"[Automation] Initiating Macro Sequence: {len(sequence)} steps.")
        
        for step_idx, step in enumerate(sequence):
            action = step.get("action")
            target = step.get("target")
            
            try:
                if action == "open_app":
                    self.open_app(target) # Calls your existing app launcher
                    print(f"[Macro] Opening App: {target}")
                    
                elif action == "wait":
                    wait_time = float(target)
                    print(f"[Macro] Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    
                elif action == "verify_window":
                    # THE OS VALIDATION GATE
                    active_window = pyautogui.getActiveWindowTitle()
                    if active_window is None:
                        active_window = "Unknown"
                        
                    print(f"[Macro] OS Check - Expected: '{target}', Active: '{active_window}'")
                    if target.lower() not in active_window.lower():
                        error_msg = f"OS Validation Failed at step {step_idx}. Expected '{target}', but got '{active_window}'."
                        print(f"[Macro Error] {error_msg}")
                        return False, error_msg
                        
                elif action == "hotkey":
                    keys = [k.strip().lower() for k in target.split(",")]
                    pyautogui.hotkey(*keys)
                    print(f"[Macro] Hotkey Executed: {keys}")
                    
                elif action == "type":
                    pyautogui.write(target, interval=0.02)
                    print(f"[Macro] Typed: {target}")
                    
            except Exception as e:
                error_msg = f"Macro fault at step {step_idx} ({action}): {e}"
                print(f"[Macro Error] {error_msg}")
                return False, error_msg
                
        return True, "Macro execution complete."
        
        
    def _scan_start_menu_for_app(self, app_name):
        shell = win32com.client.Dispatch("WScript.Shell")
        start_menu_paths = [
            os.path.join(os.environ.get("ProgramData", ""), r"Microsoft\Windows\Start Menu\Programs"),
            os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
            os.path.join(os.environ.get("PUBLIC", ""), r"Desktop"),
            os.path.join(os.environ.get("USERPROFILE", ""), r"Desktop")
        ]
        clean_name = app_name.lower().replace("browser", "").replace("app", "").strip()
        if not clean_name: clean_name = app_name.lower().strip()
        for start_menu in start_menu_paths:
            if not os.path.exists(start_menu): continue
            for root, dirs, files in os.walk(start_menu):
                for file in files:
                    if file.endswith(".lnk"):
                        link_name = file[:-4].lower()
                        if clean_name in link_name or link_name in clean_name:
                            try:
                                shortcut = shell.CreateShortCut(os.path.join(root, file))
                                target_path = shortcut.Targetpath
                                if target_path and os.path.exists(target_path): return target_path
                            except Exception: pass
        return None

    def _resolve_path(self, path_str: str):
        """Resolves exact or fuzzy local filesystem paths, fixing common typos like 2.O -> 2.0."""
        if not path_str or not isinstance(path_str, str):
            return None
        clean = path_str.strip(' "\'').strip()
        if os.path.exists(clean):
            return os.path.abspath(clean)
        # Check typo: letter 'O' instead of digit '0'
        typo_fixed = clean.replace('.O', '.0').replace('.o', '.0')
        if os.path.exists(typo_fixed):
            return os.path.abspath(typo_fixed)
        # Check parent folder for case-insensitive / typo match
        if (len(clean) >= 2 and clean[1] == ':') or ('\\' in clean) or ('/' in clean):
            parent = os.path.dirname(clean)
            base = os.path.basename(clean).lower()
            if os.path.exists(parent):
                try:
                    for entry in os.listdir(parent):
                        if entry.lower() == base or entry.lower() == base.replace('.o', '.0'):
                            return os.path.abspath(os.path.join(parent, entry))
                except Exception:
                    pass
        return None

    def open_app(self, app_name):
        if not app_name:
            return

        # 1. Check if target is a filesystem path (e.g. C:\PROJECTS\JARVIS2.O)
        resolved_path = self._resolve_path(str(app_name))
        if resolved_path:
            print(f"[Automation] Launching resolved filesystem path: {resolved_path}")
            os.startfile(resolved_path)
            return

        clean_name = str(app_name).lower().strip(' "\'').strip()

        # 2. Project directory aliases
        if clean_name in ["jarvis", "jarvis 2.0", "jarvis2.0", "jarvis2.o", "project", "project folder", "workspace", "codebase"]:
            project_root = os.path.abspath(r"C:\PROJECTS\Jarvis2.0")
            print(f"[Automation] Opening project root directory: {project_root}")
            os.startfile(project_root)
            return

        # 3. Direct URI protocols & System aliases
        if clean_name.startswith("ms-settings:") or clean_name.startswith("http://") or clean_name.startswith("https://") or clean_name in self.system_aliases:
            target_uri = self.system_aliases.get(clean_name, clean_name)
            print(f"[Automation] Launching system target/URI: {target_uri}")
            try:
                os.startfile(target_uri)
            except Exception:
                os.system(f'start "" "{target_uri}"')
            return

        # 4. App cache
        if clean_name in self.app_cache:
            os.startfile(self.app_cache[clean_name])
            return

        # 5. Scan Start Menu
        found_path = self._scan_start_menu_for_app(clean_name)
        if found_path:
            self.app_cache[clean_name] = found_path 
            os.startfile(found_path)
            return

        # 6. Fallback: Windows search
        pyautogui.press('win')
        time.sleep(0.4)
        pyautogui.write(clean_name)
        time.sleep(0.6)
        pyautogui.press('enter')

    def switch_app(self):
        pyautogui.keyDown('alt')
        pyautogui.press('tab')
        pyautogui.keyUp('alt')

    def close_current_app(self):
        pyautogui.hotkey('alt', 'f4')

    def close_named_app(self, app_name):
        clean_name = app_name.lower().replace(".exe", "").replace("app", "").strip()
        kill_map = {
            "google chrome": "chrome", "chrome": "chrome", "brave browser": "brave", 
            "brave": "brave", "microsoft edge": "msedge", "edge": "msedge", 
            "vs code": "code", "visual studio code": "code", "discord": "discord", 
            "spotify": "spotify", "whatsapp": "whatsapp", "calculator": "calculatorapp", 
            "settings": "systemsettings"
        }
        target_process = kill_map.get(clean_name, clean_name)
        closed_any = False
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] and target_process in proc.info['name'].lower():
                    proc.kill()
                    closed_any = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        if not closed_any:
            try:
                os.system(f'taskkill /F /IM {target_process}.exe /T >nul 2>&1')
                closed_any = True 
            except:
                pass
        return closed_any

    def send_whatsapp_message(self, contact: str, message: str) -> tuple:
        """
        Dispatches a WhatsApp message to a specific contact via WhatsApp Desktop.
        """
        clean_contact = contact.strip()
        clean_msg = message.strip()
        if not clean_contact or not clean_msg:
            return False, "Target contact or message payload is missing."

        print(f"[Automation] Dispatching WhatsApp message to '{clean_contact}': '{clean_msg}'")
        try:
            self.open_app("whatsapp")
            time.sleep(1.8)
            pyautogui.hotkey('ctrl', 'f')
            time.sleep(0.4)
            pyautogui.write(clean_contact, interval=0.03)
            time.sleep(0.8)
            pyautogui.press('enter')
            time.sleep(0.5)
            pyautogui.write(clean_msg, interval=0.02)
            time.sleep(0.3)
            pyautogui.press('enter')
            time.sleep(0.2)
            return True, f"Dispatched message '{clean_msg}' to {clean_contact} via WhatsApp."
        except Exception as e:
            err_msg = f"Failed to automate WhatsApp messaging: {e}"
            print(f"[Automation Error] {err_msg}")
            return False, err_msg

    def execute_hardware_command(self, action):
        """Executes native Windows hardware controls."""
        if action == "sleep":
            print("[Automation] Suspending Windows...")
            # Native Windows API call to force sleep mode
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            
        elif action == "mute":
            # Example for mute (requires pycaw or similar library)
            pass

    def deep_search(self, query):
        """Headless Backend Search (True AI Data Pipeline using DDGS with Wikipedia fallback)"""
        print(f"[Automation] Hitting secure backend API for: {query}")
        
        try:
            results = DDGS(timeout=5).text(query, max_results=3)
            if results:
                compiled_data = "LIVE GLOBAL INTEL:\n\n"
                for res in results:
                    title = res.get('title', 'Headline')
                    body = res.get('body', 'No details available.')
                    compiled_data += f"[{title}]\n{body}\n\n"
                return compiled_data[:2000]
        except Exception as e:
            print(f"[Automation] Search API Error: {e}")

        # Resilient fallback: Query Wikipedia API
        try:
            import requests, re
            headers = {'User-Agent': 'JarvisSearch/2.0 (admin@jarvis.ai)'}
            wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={query}&format=json"
            resp = requests.get(wiki_url, headers=headers, timeout=5)
            if resp.status_code == 200:
                wiki_items = resp.json().get('query', {}).get('search', [])[:3]
                if wiki_items:
                    compiled_data = "LIVE GLOBAL INTEL:\n\n"
                    for item in wiki_items:
                        title = item.get('title', 'Headline')
                        raw_snippet = item.get('snippet', '')
                        clean_snippet = re.sub(r'<[^>]+>', '', raw_snippet)
                        compiled_data += f"[{title}]\n{clean_snippet}\n\n"
                    return compiled_data[:2000]
        except Exception as e:
            print(f"[Automation] Fallback Search API Error: {e}")

        return "LIVE GLOBAL INTEL:\n\nNo live intelligence found for this query."

    def set_volume(self, action):
        if action == "up":
            for _ in range(5): pyautogui.press("volumeup")
        elif action == "down":
            for _ in range(5): pyautogui.press("volumedown")
        elif action == "mute":
            pyautogui.press("volumemute")

    def take_screenshot(self, return_base64=False):
        save_path = "assets/screenshot.jpg" 
        try:
            img = pyautogui.screenshot()
        except Exception:
            try:
                from PIL import ImageGrab
                img = ImageGrab.grab()
            except Exception:
                from PIL import Image
                img = Image.new("RGB", (1920, 1080), color=(10, 15, 25))
        img = img.convert("RGB")
        img.thumbnail((1920, 1080)) 
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        img.save(save_path, "JPEG", quality=75)
        if return_base64:
            with open(save_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        return "Screenshot captured and saved to the assets folder, sir."

    def sleep_pc(self):
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
    def magnetic_snap(self, guess_x, guess_y):
        """
        OpenCV Edge-Detection Targeting Failsafe.
        Takes the AI's sloppy guess and magnetically snaps to the center of the nearest physical UI button.
        """
        import cv2
        import numpy as np
        
        try:
            # 1. Take a fresh micro-screenshot of the current screen
            try:
                img = pyautogui.screenshot()
            except Exception:
                try:
                    from PIL import ImageGrab
                    img = ImageGrab.grab()
                except Exception:
                    from PIL import Image
                    img = Image.new("RGB", (1920, 1080), color=(10, 15, 25))
            img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            
            # 2. Define a 150x150 pixel "Search Radius" around the AI's sloppy guess
            radius = 75
            y1 = max(0, guess_y - radius)
            y2 = min(img_cv.shape[0], guess_y + radius)
            x1 = max(0, guess_x - radius)
            x2 = min(img_cv.shape[1], guess_x + radius)
            
            roi = img_cv[y1:y2, x1:x2]
            if roi.size == 0: 
                return guess_x, guess_y # Fallback if math fails
            
            # 3. Use Canny Edge Detection to outline all physical buttons and text boxes
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            
            # 4. Find the mathematical Center of Mass of those edges
            M = cv2.moments(edges)
            if M["m00"] != 0:
                # Calculate the exact local center
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                
                # 5. Translate back to global 1920x1080 screen coordinates
                exact_x = x1 + cx
                exact_y = y1 + cy
                print(f"[Automation] Magnetic Snap Corrected AI drift by: X:{exact_x - guess_x}px, Y:{exact_y - guess_y}px")
                return exact_x, exact_y
                
        except Exception as e:
            print(f"[Automation] Magnetic snap failed: {e}")
            
        # If OpenCV can't find a clean button edge, default to the AI's raw guess
        return guess_x, guess_y

    def start_mobile_uplink(self) -> tuple:
        """Launches api.py in a background process if not already running."""
        for proc in psutil.process_iter(['cmdline']):
            try:
                cmdline = proc.info.get('cmdline') or []
                if any("api.py" in str(arg).lower() for arg in cmdline):
                    return True, "Mobile uplink is already active on port 8000, sir."
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        try:
            log_file = open("mobile_uplink.log", "a", encoding="utf-8")
            subprocess.Popen(
                [sys.executable, "api.py"],
                stdout=log_file,
                stderr=log_file,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return True, "Mobile uplink online. Fast API server listening on port 8000, sir."
        except Exception as e:
            return False, f"Failed to initialize mobile uplink: {e}"

    def stop_mobile_uplink(self) -> tuple:
        """Terminates active api.py instances."""
        killed = False
        for proc in psutil.process_iter(['cmdline']):
            try:
                cmdline = proc.info.get('cmdline') or []
                if any("api.py" in str(arg).lower() for arg in cmdline):
                    proc.kill()
                    killed = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        if killed:
            return True, "Mobile uplink severed. API server terminated, sir."
        return False, "No active mobile uplink process found, sir."
