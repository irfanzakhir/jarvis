import os
import subprocess
import webbrowser
import pyautogui
import win32com.client
import time
import psutil
import requests
import base64  # <--- THE MISSING LINK
from bs4 import BeautifulSoup
from googlesearch import search
from PIL import Image

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
        closed_any = False
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] and clean_name in proc.info['name'].lower():
                    proc.kill()
                    closed_any = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return closed_any

    def deep_search(self, query):
        webbrowser.open(f"https://search.brave.com/search?q={query}") 
        try:
            print(f"[Automation] Scraping top result for: {query}")
            for url in search(query, num_results=1):
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                response = requests.get(url, headers=headers, timeout=5)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                paragraphs = soup.find_all('p')
                text = " ".join([p.text for p in paragraphs[:4]]) 
                
                if text and len(text.strip()) > 20:
                    return text[:1500] 
        except Exception as e:
            print(f"[Automation] Scraper failed: {e}")
            pass
            
        return "I could not extract readable text from the target website."

    def set_volume(self, action):
        if action == "up":
            for _ in range(5): pyautogui.press("volumeup")
        elif action == "down":
            for _ in range(5): pyautogui.press("volumedown")
        elif action == "mute":
            pyautogui.press("volumemute")

    def take_screenshot(self, return_base64=False):
        # We change this to a JPG
        save_path = "assets/screenshot.jpg" 
        
        # Take the raw screenshot (Returns a PIL Image in RAM)
        img = pyautogui.screenshot()
        
        # Convert to RGB and compress it to a maximum of 1080p
        img = img.convert("RGB")
        img.thumbnail((1920, 1080)) # Shrinks 4K screens, ignores if already smaller
        
        # Save highly compressed JPEG
        img.save(save_path, "JPEG", quality=75)
        
        # If the brain needs to read it, encode it and return it instantly
        if return_base64:
            with open(save_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
                
        return "Screenshot captured and saved to the assets folder, sir."

    def sleep_pc(self):
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")