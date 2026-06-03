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
        print("[Brain] Booting Agentic Neural Network (Native Tool Calling Edition)...")
        
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
            1. ACTION REQUESTS: If the user asks to open/close a local application (INCLUDING browsers like Chrome, Brave, or Edge), use 'control_application'. ONLY use 'pilot_browser' if the user asks to navigate to a specific website or internet URL.
            2. CONVERSATION: If the user just says hello or makes general conversation, DO NOT call any tools. Reply normally.
            3. MEMORY: If the user states a preference, use the 'remember_fact' tool.
            4. ZERO-GUESSING RULE: WHEN piloting the Web Browser, NEVER guess HTML selectors. Use 'scan_page' FIRST.
            5. MACRO INJECTION PROTOCOL: Modern desktop apps (like WhatsApp or Spotify) have complex UI trees. The most reliable way to navigate them is to inject keyboard macros! Use 'pilot_desktop' with action='type' and NO element_name. You can string commands together using pywinauto shortcuts (e.g., '^f' for Ctrl+F, or '{{ENTER}}'). 
               -> EXAMPLE: To send a WhatsApp message, send the text string: "^fContactName{{ENTER}}Your message here{{ENTER}}". This will search, open the chat, and send the message instantly.
            6. Keep spoken responses concise and highly professional. No markdown.
            
            LONG TERM MEMORY:
            {self.long_term_memory}
            """
            
            self.conversation_history = [
                {"role": "system", "content": system_instruction}
            ]
            
            # ==========================================
            # NATIVE TOOL SCHEMA
            # ==========================================
            self.tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "pilot_browser",
                        "description": "Pilots an active web browser. Can navigate to URLs, type text, click elements, scan the page, or close the browser.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "enum": ["navigate", "scan_page", "click", "type", "close"]},
                                "url": {"type": "string", "description": "The URL to navigate to (e.g., https://github.com). Only used for navigate."},
                                "selector": {"type": "string", "description": "The CSS selector to click or type into (e.g., 'input#search')."},
                                "text": {"type": "string", "description": "The exact text to type. Only used for type action."},
                                "spoken_response": {"type": "string", "description": "Acknowledgment phrase."}
                            },
                            "required": ["action", "spoken_response"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "pilot_desktop",
                        "description": "Pilots native Windows desktop apps. You can scan for UI buttons, click them, or rapidly inject keyboard macro shortcuts.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "enum": ["scan_window", "click", "type"]},
                                "app_name": {"type": "string", "description": "The target application name (e.g., 'Notepad', 'WhatsApp')."},
                                "element_name": {"type": "string", "description": "The exact name of the button to interact with. LEAVE EMPTY if you are using global Macro Injection."},
                                "text": {"type": "string", "description": "The text to type. Supports standard text OR pywinauto macro keys like '{ENTER}' or '^f' (Ctrl+F)."},
                                "spoken_response": {"type": "string", "description": "Acknowledgment phrase."}
                            },
                            "required": ["action", "app_name", "spoken_response"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "control_application",
                        "description": "Opens, closes, or switches software applications on the PC.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "enum": ["open_app", "close_app", "switch_app", "close_current"]},
                                "app_name": {"type": "string", "description": "The target application name (e.g., spotify, discord, chrome, brave). Leave empty if not applicable."},
                                "spoken_response": {"type": "string", "description": "What you will say aloud to confirm the action."}
                            },
                            "required": ["action", "spoken_response"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "search_network",
                        "description": "Searches the global internet/web for information, news, or specific questions.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "The precise search query to look up."},
                                "spoken_response": {"type": "string", "description": "Acknowledgment phrase before searching."}
                            },
                            "required": ["query", "spoken_response"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "analyze_screen",
                        "description": "Reads and analyzes the user's current computer screen visually.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "spoken_response": {"type": "string", "description": "Acknowledgment phrase before scanning."}
                            },
                            "required": ["spoken_response"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "control_hardware",
                        "description": "Controls PC hardware like audio volume, power states, or taking screenshots.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "enum": ["vol_up", "vol_down", "mute", "screenshot", "sleep"]},
                                "spoken_response": {"type": "string", "description": "Acknowledgment phrase."}
                            },
                            "required": ["action", "spoken_response"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "manage_dashboard",
                        "description": "Controls the Jarvis visual HUD dashboard interface.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "enum": ["minimize", "maximize", "combat_on", "combat_off", "show_news"]},
                                "spoken_response": {"type": "string", "description": "Acknowledgment phrase."}
                            },
                            "required": ["action", "spoken_response"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "remember_fact",
                        "description": "Saves an important user preference or fact to long-term memory.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "fact": {"type": "string", "description": "The fact to remember."},
                                "spoken_response": {"type": "string", "description": "Confirmation of remembering."}
                            },
                            "required": ["fact", "spoken_response"]
                        }
                    }
                }
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
            
        print("[Brain] Analyzing intent with Native Tools...")
        
        self.conversation_history.append({"role": "user", "content": user_input})
        self._trim_memory() 
        
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.text_model,
                    messages=self.conversation_history,
                    temperature=0.2,
                    tools=self.tools,
                    tool_choice="auto"
                )
                
                msg = response.choices[0].message
                decision = {
                    "spoken_response": "",
                    "ui_action": "none",
                    "target": ""
                }
                
                if msg.tool_calls:
                    tool_call = msg.tool_calls[0]
                    func_name = tool_call.function.name
                    
                    try:
                        args = json.loads(tool_call.function.arguments)
                    except:
                        args = {}
                        
                    print(f"[Brain] Tool Triggered: {func_name} | Args: {args}")
                    decision["spoken_response"] = args.get("spoken_response", "Processing request, sir.")
                    
                    if func_name == "remember_fact":
                        self.save_to_memory(args.get("fact"))
                    elif func_name == "pilot_browser":
                        decision["ui_action"] = "pilot_browser"
                        decision["target"] = {
                            "action": args.get("action"),
                            "url": args.get("url"),
                            "selector": args.get("selector"),
                            "text": args.get("text")
                        }
                    elif func_name == "pilot_desktop":
                        decision["ui_action"] = "pilot_desktop"
                        decision["target"] = {
                            "action": args.get("action"),
                            "app_name": args.get("app_name"),
                            "element_name": args.get("element_name"),
                            "text": args.get("text")
                        }
                    elif func_name == "control_application":
                        decision["ui_action"] = args.get("action", "none")
                        decision["target"] = args.get("app_name", "")
                    elif func_name == "search_network":
                        decision["ui_action"] = "deep_search"
                        decision["target"] = args.get("query", "")
                    elif func_name == "analyze_screen":
                        decision["ui_action"] = "read_screen"
                    elif func_name == "control_hardware" or func_name == "manage_dashboard":
                        decision["ui_action"] = args.get("action", "none")

                    self.conversation_history.append({"role": "assistant", "content": f"[Tool Executed: {func_name}] {decision['spoken_response']}"})
                    
                else:
                    raw_text = msg.content or "I am processing your request."
                    self.conversation_history.append({"role": "assistant", "content": raw_text})
                    decision["spoken_response"] = raw_text
                
                decision["spoken_response"] = decision["spoken_response"].replace("*", "").replace("#", "")
                return decision
                
            except Exception as e:
                if "429" in str(e):
                    print(f"[Groq Brain Error]: Rate Limit Exceeded.")
                    return {"spoken_response": "I have temporarily exhausted my cognitive token limit on the Groq network. We will need to wait a few minutes for the system to reset.", "ui_action": "none"}
                
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
                
                self.conversation_history.append({"role": "user", "content": f"[User showed screen. You read: {raw_text}]"})
                self._trim_memory()
                
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