import os
import time
import base64
import json
from groq import Groq
from dotenv import load_dotenv
from core.memory import JarvisMemory # <--- THE NEW SEMANTIC COGNITION ENGINE

load_dotenv()

class JarvisBrain:
    def __init__(self):
        print("[Brain] Booting Agentic Neural Network (Semantic Vector Edition)...")
        
        self.api_key = os.environ.get("GROQ_API_KEY")
        self.semantic_memory = JarvisMemory() # Initialize SQLite Semantic Module
        self.max_short_term_history = 6  # Optimized down to save massive token overhead
        
        if not self.api_key:
            print("[CRITICAL] Groq API Key not found in .env file! Brain offline.")
            self.active = False
        else:
            self.active = True
            self.client = Groq(api_key=self.api_key)
            
            self.text_model = "llama-3.3-70b-versatile"        
            self.vision_model = "meta-llama/llama-4-scout-17b-16e-instruct" 

            # Base template instructions
            self.base_instruction = """
            You are J.A.R.V.I.S., a highly advanced, autonomous AI operating system.
            You manage a visual dashboard and the user's local system.
            
            CRITICAL DIRECTIVES:
            1. SEMANTIC APP RESOLUTION: If the user asks to open a category (e.g., 'social media', 'music', 'browser'), YOU must deduce the most likely installed Windows app (e.g., 'instagram', 'spotify', 'chrome') and pass that EXACT name to 'control_application'.
            2. GLOBAL INTEL: For news or general questions, ALWAYS use 'search_network'.
            3. CONVERSATION: If the user just says hello, DO NOT call any tools. Reply normally.
            4. MEMORY: If the user states a preference, use 'remember_fact'.
            5. MACRO INJECTION: To type into complex apps, use 'pilot_desktop' with action='type' (e.g., "^fName{ENTER}Msg{ENTER}").
            6. VISION CLICKING: If the user asks to click a specific button, icon, or visual element on the screen (e.g., "click the search bar", "click the new post button"), YOU MUST use the 'vision_click' tool.
            7. Keep spoken responses concise and professional.no markdown formatting. Always acknowledge the user's command with a clear spoken_response, even if the UI action is 'none'.
            """
            
            self.conversation_history = [
                {"role": "system", "content": self.base_instruction}
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
                        "description": "Searches the global internet for current events, news, or specific questions. THIS AUTOMATICALLY SHOWS THE NEWS WIDGET. Do NOT use manage_dashboard for news.",
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
                        "description": "Controls the Jarvis visual HUD dashboard interface layout window states.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "enum": ["minimize", "maximize", "combat_on", "combat_off"]},
                                "spoken_response": {"type": "string", "description": "Acknowledgment phrase."}
                            },
                            "required": ["action", "spoken_response"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "vision_click",
                        "description": "Uses the optical array to find and click a specific button, icon, or text on the screen.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "target_element": {"type": "string", "description": "The specific button or element to click (e.g., 'Search bar', 'New Post button', 'Login')."},
                                "spoken_response": {"type": "string", "description": "Acknowledgment phrase."}
                            },
                            "required": ["target_element", "spoken_response"]
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

    def _trim_memory(self):
        if len(self.conversation_history) > (self.max_short_term_history + 1):
            self.conversation_history = [self.conversation_history[0]] + self.conversation_history[-self.max_short_term_history:]

    def think(self, user_input, max_retries=3):
        if not self.active:
            return {"spoken_response": "Groq processors offline.", "ui_action": "none"}
            
        print("[Brain] Analyzing intent with Hybrid Semantic Context...")
        
        # 1. DYNAMIC INJECTION: Search SQLite for relevant context and inject it safely into the root prompt
        relevant_past_context = self.semantic_memory.query_relevant_context(user_input)
        self.conversation_history[0]["content"] = self.base_instruction + relevant_past_context
        
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
                        # ROUTE TO NON-BLOCKING SQLITE VECTOR BUFFER
                        self.semantic_memory.save_fact_async(args.get("fact"))
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
                    elif func_name == "vision_click":
                        decision["ui_action"] = "vision_click"
                        decision["target"] = args.get("target_element", "")

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
    def find_coordinates(self, base64_image, target_element, max_retries=3):
        """Asks the Vision model to map the screen into an exact X,Y pixel grid."""
        if not self.active: return None
            
        print(f"[Brain] Activating Spatial Reasoning Engine for: {target_element}...")
        
        prompt = f"Analyze this computer screen. Find the exact center pixel coordinates of the '{target_element}'. Assume the screen resolution is 1920x1080. Respond ONLY with a valid JSON object in this exact format: {{\n\"x\": 960,\n\"y\": 540\n}}. Do not include any other text, markdown, or backticks."
        
        vision_messages = [
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]}
        ]
        
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.vision_model,
                    messages=vision_messages,
                    temperature=0.1 # Kept extremely low for strict mathematical precision
                )
                
                raw_text = response.choices[0].message.content.strip()
                # Clean the response to ensure it's pure JSON
                raw_text = raw_text.replace("```json", "").replace("```", "").strip()
                
                coords = json.loads(raw_text)
                return coords # Returns a dict like {"x": 500, "y": 300}
                
            except Exception as e:
                print(f"[Groq Spatial Error]: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
        return None