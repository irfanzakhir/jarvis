import os
import subprocess
import webbrowser
import pyautogui

class JarvisAutomation:
    def __init__(self):
        self.apps = {
            "code": r"C:\Users\irfan\AppData\Local\Programs\Microsoft VS Code\Code.exe", 
            "browser": "chrome",
            "cmd": "cmd.exe"
        }

    def open_app(self, app_name):
        app_path = self.apps.get(app_name.lower())
        if app_path:
            print(f"[Automation] Opening {app_name}...")
            if os.path.exists(app_path) or app_name in ["chrome", "cmd"]:
                os.startfile(app_path) if os.name == 'nt' else subprocess.call([app_path])
                return f"Opening {app_name} now, sir."
            return f"I found the path for {app_name}, but the executable is missing."
        return f"I do not have the system path for {app_name} in my database."

    def web_search(self, query):
        url = f"https://www.google.com/search?q={query}"
        webbrowser.open(url)
        return f"Searching the web for {query}."

    def set_volume(self, action):
        if action == "up":
            for _ in range(5): pyautogui.press("volumeup")
            return "Increasing system volume."
        elif action == "down":
            for _ in range(5): pyautogui.press("volumedown")
            return "Decreasing system volume."
        elif action == "mute":
            pyautogui.press("volumemute")
            return "System audio muted."

    def take_screenshot(self):
        save_path = "assets/screenshot.png"
        pyautogui.screenshot(save_path)
        return "Screenshot captured and saved to assets folder, sir."

    def sleep_pc(self):
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        return "Initiating sleep protocol. Goodnight."