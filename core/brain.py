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
        
        # --- SHORT TERM MEMORY LIMIT ---
        # 10 means he remembers the last 5 things you said, and his last 5 answers.
        self.max_short_term_history = 10 
        
        if not self.api_key:
            print("[CRITICAL] Groq API Key not found in .env file! Brain offline.")
            self.active = False
        else:
            self.active = True
            self.client = Groq(api_key=self.api_key)
            
            # --- MODEL SELECTION ---
            self.text_model = "llama-3.3-70b-versatile"        
            self.vision_model = "meta-llama/llama-4-scout-17b-16e-instruct"  # The upgraded vision model!

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
                "ui_action": "none/minimize/maximize/combat_on/combat_off/show_news/open_code/open_browser/open_cmd/vol_up/vol_down/mute/screenshot/sleep",
                "memory_to_save": "fact to save, or empty string"
            }}
            *NOTE: If the user asks you to open VS Code, Chrome, or CMD, or asks you to change volume, take a screenshot, or sleep the PC, select the exact matching ui_action.*
            
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
        """Asynchronous Fire-and-Forget long-term memory."""
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
        """The Sliding Window: Keeps the system prompt + the most recent interactions."""
        # If history length exceeds our limit + 1 (for the system prompt)
        if len(self.conversation_history) > (self.max_short_term_history + 1):
            # Slice the list: Keep index 0, and the last N items
            self.conversation_history = [self.conversation_history[0]] + self.conversation_history[-self.max_short_term_history:]

    def think(self, user_input, max_retries=3):
        if not self.active:
            return {"spoken_response": "Groq processors offline.", "ui_action": "none"}
            
        print("[Brain] Analyzing intent at LPU speed...")
        
        self.conversation_history.append({"role": "user", "content": user_input})
        self._trim_memory() # Apply the sliding window before thinking
        
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
            
        print("[Brain] Analyzing visual data at LPU speed...")
        
        # We don't send the whole chat history to the vision model (to save tokens), just the system prompt
        vision_messages = [
            {"role": "system", "content": self.conversation_history[0]["content"]},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ]
        
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.vision_model,
                    messages=vision_messages,
                    temperature=0.2,
                    response_format={"type": "json_object"}
                )
                
                raw_text = response.choices[0].message.content
                decision = json.loads(raw_text)
                
                # --- CROSS-WIRING FIX ---
                # We inject what he saw and what he said back into his normal text memory!
                self.conversation_history.append({"role": "user", "content": f"[User showed an image to the optical array. User asked: {user_prompt}]"})
                self.conversation_history.append({"role": "assistant", "content": raw_text})
                self._trim_memory()
                
                decision["spoken_response"] = decision.get("spoken_response", "").replace("*", "").replace("#", "")
                return decision
                
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1.5 ** attempt)
                    continue
                print(f"[Groq Vision Error]: {e}")
                return {"spoken_response": "Visual array processing failed.", "ui_action": "none"}