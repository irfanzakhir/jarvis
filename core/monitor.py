import psutil
import socket
import time
import threading
import subprocess

class SystemMonitor:
    def __init__(self, alert_callback):
        print("[Monitor] Initializing System Telemetry and Network Pings...")
        self.alert_callback = alert_callback
        self.running = True
        
        self.network_status = True
        self.threat_level = "GREEN" 

        # Launch the autonomous monitoring threads
        threading.Thread(target=self._ping_loop, daemon=True).start()
        threading.Thread(target=self._threat_monitor_loop, daemon=True).start()
        threading.Thread(target=self._wifi_monitor_loop, daemon=True).start() # --- NEW WIFI THREAD ---

    def _ping_loop(self):
        """Silently pings Google's DNS every 3 seconds to ensure uplink integrity."""
        while self.running:
            try:
                socket.setdefaulttimeout(3)
                # THE FIX: 'with' automatically closes the socket to prevent memory leaks
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect(("8.8.8.8", 53))
                
                if not self.network_status:
                    self.network_status = True
                    self.alert_callback("[SYSTEM]: UPLINK RESTORED.")
            except socket.error:
                if self.network_status:
                    self.network_status = False
                    self.alert_callback("[CRITICAL]: NETWORK CONNECTION LOST.")
            time.sleep(3)

    def _threat_monitor_loop(self):
        """Monitors hardware telemetry for anomalous resource spikes."""
        while self.running:
            cpu_usage = psutil.cpu_percent(interval=1)
            ram_usage = psutil.virtual_memory().percent

            if cpu_usage > 90 or ram_usage > 90:
                if self.threat_level != "RED":
                    self.threat_level = "RED"
                    self.alert_callback(f"[WARNING]: SYSTEM OVERLOAD. CPU: {cpu_usage}% | RAM: {ram_usage}%")
            elif cpu_usage > 75 or ram_usage > 75:
                if self.threat_level != "YELLOW":
                    self.threat_level = "YELLOW"
                    self.alert_callback(f"[ALERT]: ELEVATED RESOURCE DRAW. CPU: {cpu_usage}%")
            else:
                if self.threat_level != "GREEN":
                    self.threat_level = "GREEN"
                    self.alert_callback("[SYSTEM]: HARDWARE TELEMETRY NORMALIZED.")
            time.sleep(2)

    def _wifi_monitor_loop(self):
        """Pulls live SSID, Signal, and calculates real-time bandwidth."""
        last_io = psutil.net_io_counters()
        
        while self.running:
            ssid = "DISCONNECTED"
            signal = "0%"
            
            # 1. Grab SSID and Signal Strength using Windows netsh
            try:
                # We use creationflags=subprocess.CREATE_NO_WINDOW to prevent a black cmd box from flashing
                result = subprocess.check_output(
                    "netsh wlan show interfaces", 
                    shell=True, text=True, 
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                for line in result.split('\n'):
                    if "SSID" in line and "BSSID" not in line:
                        ssid = line.split(":")[1].strip()
                    elif "Signal" in line:
                        signal = line.split(":")[1].strip()
            except Exception:
                pass # Usually means Wi-Fi is off or using Ethernet

            # 2. Wait 1 second to calculate the exact bandwidth delta
            time.sleep(1)
            curr_io = psutil.net_io_counters()
            
            # Calculate KB/s
            dl_speed = (curr_io.bytes_recv - last_io.bytes_recv) / 1024 
            up_speed = (curr_io.bytes_sent - last_io.bytes_sent) / 1024 
            last_io = curr_io

            # 3. Send the formatted dictionary back to main.py
            self.alert_callback({
                "type": "wifi_telemetry",
                "ssid": ssid,
                "signal": signal,
                "dl": f"{dl_speed:.1f} KB/s",
                "up": f"{up_speed:.1f} KB/s"
            })