import os
import time
import base64
import json
import threading
from groq import Groq
from dotenv import load_dotenv

# --- LOAD ENVIRONMENT VARIABLES ---
load_dotenv()

class JarvisBrain:
    def __init__(self):
        print("[Brain] Booting Agentic Neural Network (Groq Speed Engine + Sliding Memory)...")
        
        self.api_key = os.environ.get("GROQ_API_KEY")
        self.memory_file = "assets/memory.json"
        self.long_term_memory = self.load_memory()
        
        self.max_short_term_history = 10 
        
        if not self.api_key:
            print("[CRITICAL] Groq API Key not found in .env file! Brain offline.")
            self.active = False
        else:
            self.active = True
            self.client = Groq(api_key=self.api_key)
            
            # --- STABLE MODELS ---
            self.text_model = "llama-3.3-70b-versatile"        
            self.vision_model = "meta-llama/llama-4-scout-17b-16e-instruct" 

            system_instruction = f"""
            You are J.A.R.V.I.S., a highly advanced, autonomous AI operating system.
            You manage a visual dashboard and the user's local system.
            
            CRITICAL DIRECTIVES:
            1. If a user asks you to perform an action but does not specify HOW, ask a clarifying question.
            2. If the user corrects you or states a preference, save it to your memory.
            3. Keep your spoken responses concise and highly professional. Do not include markdown asterisks or emojis.
            
            JSON OUTPUT REQUIREMENT:
            You MUST output your entire response as a raw JSON object matching this structure:
            {{
                "spoken_response": "The text you will speak",
                "ui_action": "none/minimize/maximize/combat_on/combat_off/show_news/open_app/close_app/close_current/switch_app/deep_search/read_screen/vol_up/vol_down/mute/screenshot/sleep",
                "target": "name of the app, the search query, or empty string",
                "memory_to_save": "fact to save, or empty string"
            }}
            *NOTE: Use 'close_current' to close whatever is currently on screen. Use 'switch_app' to alt-tab. Use 'deep_search' if the user asks you to look up or read about a specific topic online. Use 'read_screen' if the user asks you to read or analyze what is currently visible on their screen.*
            
            LONG TERM MEMORY:
            {self.long_term_memory}
            """
            
            self.conversation_history = [
                {"role": "system", "content": system_instruction}
            ]

    def load_memory(self):
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []

    def save_to_memory(self, new_fact):
        if not new_fact or new_fact.strip() == "":
            return
            
        print(f"[Brain] Saving to long-term memory: {new_fact}")
        self.long_term_memory.append(new_fact)
        
        def write_to_disk():
            if not os.path.exists("assets"):
                os.makedirs("assets")
            with open(self.memory_file, 'w') as f:
                json.dump(self.long_term_memory, f, indent=4)
                
        threading.Thread(target=write_to_disk, daemon=True).start()

    def _trim_memory(self):
        if len(self.conversation_history) > (self.max_short_term_history + 1):
            self.conversation_history = [self.conversation_history[0]] + self.conversation_history[-self.max_short_term_history:]

    def think(self, user_input, max_retries=3):
        if not self.active:
            return {"spoken_response": "Groq processors offline.", "ui_action": "none"}
            
        print("[Brain] Analyzing intent at LPU speed...")
        
        self.conversation_history.append({"role": "user", "content": user_input})
        self._trim_memory() 
        
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.text_model,
                    messages=self.conversation_history,
                    temperature=0.2,
                    response_format={"type": "json_object"} 
                )
                
                raw_text = response.choices[0].message.content
                decision = json.loads(raw_text)
                
                self.conversation_history.append({"role": "assistant", "content": raw_text})
                
                if decision.get("memory_to_save"):
                    self.save_to_memory(decision["memory_to_save"])
                
                decision["spoken_response"] = decision.get("spoken_response", "").replace("*", "").replace("#", "")
                return decision
                
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1.5 ** attempt)
                    continue
                print(f"[Groq Brain Error]: {e}")
                return {"spoken_response": "I encountered a cognitive delay processing that query.", "ui_action": "none"}

    def analyze_image(self, base64_image, user_prompt, max_retries=3):
        if not self.active:
            return {"spoken_response": "Optical array offline.", "ui_action": "none"}
            
        print(f"[Brain] Routing visual data through {self.vision_model}...")
        
        vision_messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Read and summarize this screen context based on this request: {user_prompt}. Keep it to 2 or 3 concise sentences. No markdown formatting."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ]
        
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.vision_model,
                    messages=vision_messages,
                    temperature=0.4
                )
                
                raw_text = response.choices[0].message.content
                
                # Cross-wire the visual memory into his main text brain
                self.conversation_history.append({"role": "user", "content": f"[User showed screen. You read: {raw_text}]"})
                self._trim_memory()
                
                # Manually construct the decision JSON so main.py doesn't crash
                decision = {
                    "spoken_response": raw_text.replace("*", "").replace("#", ""),
                    "ui_action": "none",
                    "target": ""
                }
                return decision
                
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1.5 ** attempt)
                    continue
                print(f"[Groq Vision Error]: {e}")
                return {"spoken_response": "Visual array processing failed.", "ui_action": "none"}