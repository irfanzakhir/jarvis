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
            "whatsapp": "whatsapp:",
            "spotify": "spotify:"
        }
        
        self.playwright = None
        self.browser = None
        self.page = None

    # ==========================================
    # 1. ZERO-LATENCY DESKTOP AUTOMATION (UIA)
    # ==========================================
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
    
    def start_browser(self):
        # SELF-HEALING: Check if the user manually closed the browser
        try:
            if self.page and self.page.is_closed():
                self.playwright = None
                self.browser = None
                self.page = None
        except:
            # If the page object itself threw an error, it's definitely dead
            self.playwright = None
            self.browser = None
            self.page = None

        if not self.playwright:
            print("[Automation] Booting Playwright Chromium Engine...")
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=False)
            self.page = self.browser.new_page()

    def pilot_browser(self, action, url=None, selector=None, text=None):
        if action != "close":
            self.start_browser()
        try:
            if action == "navigate":
                self.page.goto(url)
                return "Navigation complete."
            elif action == "click":
                self.page.click(selector, timeout=4000)
                return "Click executed."
            elif action == "type":
                self.page.fill(selector, text, timeout=4000)
                self.page.press(selector, "Enter", timeout=4000) 
                return "Text entered."
            elif action == "scan_page":
                elements = self.page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('input, button, a, [role="button"], [aria-label]'))
                        .map(el => ({ tag: el.tagName, text: el.innerText || el.getAttribute('aria-label') || el.placeholder || el.value || '', id: el.id, class: el.className }))
                        .filter(e => e.text || e.id || e.class)
                        .slice(0, 25); 
                }''')
                return f"Interactive elements found: {elements}"
            elif action == "close":
                if self.browser: self.browser.close()
                if self.playwright: self.playwright.stop()
                self.playwright = None
                self.browser = None
                self.page = None
                return "Browser closed successfully."
        except Exception as e:
            error_msg = str(e)
            print(f"[Automation] Browser Error: {error_msg}")
            
            # Additional fallback: If Playwright crashed mid-action, reset state for next time
            if "closed" in error_msg.lower():
                self.playwright = None
                self.browser = None
                self.page = None
                
            return f"Action failed: {error_msg}"

    # ... [KEEP ALL OTHER EXISTING AUTOMATION FUNCTIONS BELOW EXACTLY THE SAME] ...
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

    def open_app(self, app_name):
        app_name = app_name.lower().strip()
        if app_name in self.system_aliases:
            os.system(f"start {self.system_aliases[app_name]}") 
            return
        if app_name in self.app_cache:
            os.startfile(self.app_cache[app_name])
            return
        found_path = self._scan_start_menu_for_app(app_name)
        if found_path:
            self.app_cache[app_name] = found_path 
            os.startfile(found_path)
            return
        pyautogui.press('win')
        time.sleep(0.5)
        pyautogui.write(app_name)
        time.sleep(0.8)
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

    def deep_search(self, query):
        """Headless Backend Search (True AI Data Pipeline using DDGS)"""
        print(f"[Automation] Hitting secure backend API for: {query}")
        
        try:
            # Hit the backend API silently (Bypasses Cloudflare/Bot-blockers)
            results = DDGS().text(query, max_results=3)
            
            if not results:
                return "I could not find any live intelligence on that topic."
            
            # Compile the top 3 results into a clean text block
            compiled_data = "LIVE GLOBAL INTEL:\n\n"
            for res in results:
                # Safely extract title and body
                title = res.get('title', 'Headline')
                body = res.get('body', 'No details available.')
                compiled_data += f"[{title}]\n{body}\n\n"
                
            return compiled_data[:2000] # Cap the token size to keep the system fast
            
        except Exception as e:
            print(f"[Automation] Search API Error: {e}")
            return f"Global uplink failed due to backend exception."

    def set_volume(self, action):
        if action == "up":
            for _ in range(5): pyautogui.press("volumeup")
        elif action == "down":
            for _ in range(5): pyautogui.press("volumedown")
        elif action == "mute":
            pyautogui.press("volumemute")

    def take_screenshot(self, return_base64=False):
        save_path = "assets/screenshot.jpg" 
        img = pyautogui.screenshot()
        img = img.convert("RGB")
        img.thumbnail((1920, 1080)) 
        img.save(save_path, "JPEG", quality=75)
        if return_base64:
            with open(save_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        return "Screenshot captured and saved to the assets folder, sir."

    def sleep_pc(self):
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")