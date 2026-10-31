import tinytuya
import logging

logger = logging.getLogger(__name__)

class IoTBridge:
    def __init__(self):
        # ⚠️ PASTE YOUR KEYS FROM THE TINYTUYA WIZARD HERE
        self.DEVICE_ID = "d7391d34fda34058b6zrbm"
        self.IP_ADDRESS = "10.197.248.71"       # e.g., 192.168.43.55
        self.LOCAL_KEY = ":qNHZk^e5/RZ(~@w"
        
        self.version = 3.5 # Tuya protocol version (usually 3.3 for modern bulbs)
        
        try:
            # Initialize the Bulb Device
            self.bulb = tinytuya.BulbDevice(
                self.DEVICE_ID, 
                self.IP_ADDRESS, 
                self.LOCAL_KEY
            )
            self.bulb.set_version(self.version)
            # Socket timeout (if bulb is off/unplugged, don't freeze Jarvis)
            self.bulb.set_socketTimeout(2) 
            print("[IoT Bridge] Smart Home LAN Interface Online.")
        except Exception as e:
            print(f"[IoT Bridge ERROR] Failed to connect to hardware: {e}")
            self.bulb = None

    def execute_light_command(self, action: str, color: str = None, brightness: int = None):
        """Translates Jarvis's intent into physical hardware commands."""
        if not self.bulb:
            return "Hardware disconnected."
            
        try:
            if action == "turn_on":
                self.bulb.turn_on()
                if color:
                    self._set_rgb_color(color.lower())
                return "Lights engaged."
                
            elif action == "turn_off":
                self.bulb.turn_off()
                return "Lights disengaged."
                
            elif action == "dim":
                # Havells/Tuya brightness is usually 10-1000
                safe_bright = max(10, min(1000, brightness if brightness else 100)) 
                self.bulb.set_brightness_percentage(safe_bright)
                return f"Brightness calibrated to {safe_bright}%."
                
            elif action == "color":
                if color:
                    self._set_rgb_color(color.lower())
                return f"Color matrix shifted to {color}."
                
        except Exception as e:
            logger.error(f"IoT Hardware Fault: {e}")
            return "Local network transmission failed."

    def _set_rgb_color(self, color_name):
        """Maps spoken colors to exact RGB values for the Havells Bulb."""
        color_map = {
            "red": (255, 0, 0),
            "combat": (255, 0, 0),
            "green": (0, 255, 0),
            "blue": (0, 0, 255),
            "purple": (128, 0, 128),
            "yellow": (255, 255, 0),
            "cyan": (0, 255, 255),
            "white": (255, 255, 255),
            "orange": (255, 165, 0)
        }
        rgb = color_map.get(color_name.lower() if color_name else "white", (255, 255, 255))
        try:
            self.bulb.set_mode('colour')
        except Exception:
            pass
        self.bulb.set_colour(rgb[0], rgb[1], rgb[2])