from core.brain import JarvisBrain

class MobileBridge:
    def __init__(self, brain_instance: JarvisBrain):
        self.brain = brain_instance
        print("[System] Mobile Bridge Shield Online.")

    def process_uplink(self, payload: dict):
        """
        Parses incoming JSON from the Android client and routes it to the Cerebras core.
        """
        user_text = payload.get("command", "")
        origin = payload.get("origin", "mobile_y12")
        mobile_image_base64 = payload.get("payload", {}).get("base64_image", None)

        print(f"\n[BRIDGE] Intercepted payload from {origin.upper()}. Routing to Core...")

        # Hand off to the brain with the origin metadata attached
        decision = self.brain.think(
            user_input=user_text, 
            origin=origin, 
            mobile_image=mobile_image_base64
        )
        
        return decision