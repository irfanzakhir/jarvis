"""
J.A.R.V.I.S. 2.0 - Windows Start Menu & Desktop Shortcut Setup
Updates existing Start Menu 'Jarvis.lnk' (which pointed to old ai_assistant)
so any existing Start Menu Pins immediately point to Jarvis 2.0!
Also creates 'J.A.R.V.I.S. 2.0.lnk' in Start Menu and Desktop.
"""

import os
import win32com.client

def setup_shortcuts():
    project_dir = os.path.abspath(r"C:\PROJECTS\Jarvis2.0")
    pythonw_path = os.path.join(project_dir, "venv", "Scripts", "pythonw.exe")
    main_py = os.path.join(project_dir, "main.py")
    icon_path = os.path.join(project_dir, "assets", "jarvis.ico")
    
    appdata = os.environ.get("APPDATA")
    start_menu = os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs")
    userprofile = os.environ.get("USERPROFILE")
    desktop = os.path.join(userprofile, "Desktop")

    targets = [
        # Overwrite existing legacy 'Jarvis.lnk' so pinned Start items instantly launch Jarvis 2.0
        os.path.join(start_menu, "Jarvis.lnk"),
        # Create dedicated modern J.A.R.V.I.S. 2.0 entries
        os.path.join(start_menu, "J.A.R.V.I.S. 2.0.lnk"),
        os.path.join(desktop, "J.A.R.V.I.S. 2.0.lnk")
    ]

    shell = win32com.client.Dispatch("WScript.Shell")

    for path in targets:
        sc = shell.CreateShortCut(path)
        sc.TargetPath = pythonw_path
        sc.Arguments = f'"{main_py}"'
        sc.WorkingDirectory = project_dir
        sc.IconLocation = f"{icon_path},0"
        sc.Description = "J.A.R.V.I.S. 2.0 Autonomous AI Operating System"
        sc.save()
        print(f"[SUCCESS] Updated/Created shortcut: {path}")

if __name__ == "__main__":
    setup_shortcuts()
