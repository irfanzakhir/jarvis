import os
import sys
import time
import json
import base64
import socket
import subprocess
import groq
from groq import Groq
from dotenv import load_dotenv
from core.memory import JarvisMemory

load_dotenv()

class JarvisBrain:
    def __init__(self):
        print("[Brain] Booting Agentic Neural Network (Semantic Vector Edition)...")
        
        self.api_key = os.environ.get("GROQ_API_KEY")
        self.semantic_memory = JarvisMemory() # SQLite Semantic Cognition Module
        self.max_short_term_history = 6       # Optimized token depth
        
        if not self.api_key:
            print("[CRITICAL] Groq API Key not found in .env file! Brain offline.")
            self.active = False
        else:
            self.active = True
            self.client = Groq(api_key=self.api_key)
            
            # Official stable Groq hardware endpoints
            self.text_model = "llama-3.3-70b-versatile"        
            self.vision_model = "llama-3.2-11b-vision-preview" 

            # Base system instructions with rigid syntax anchoring
            self.base_instruction = """
            You are J.A.R.V.I.S., a highly advanced, autonomous AI operating system.
            You manage a visual dashboard and the user's local Windows system.
            
            CRITICAL DIRECTIVES:
            1. SEMANTIC APP RESOLUTION: If the user asks to open a category (e.g., 'social media', 'music', 'browser'), deduce the most likely installed Windows app (e.g., 'instagram', 'spotify', 'chrome') and pass that EXACT name to 'control_application'.
            2. GLOBAL INTEL: For news, world events, or markets, ALWAYS trigger 'open_situation_room' or 'search_network'.
            3. CREATIVE BYPASS: If the user asks you to write a story, compose a poem, tell a joke, explain a philosophical concept, or engage in casual chat, DO NOT CALL ANY TOOLS. Output the requested creative text directly as your normal spoken_response.
            4. STRICT MEMORY: Use 'remember_fact' ONLY when the user explicitly declares a permanent personal trait (e.g., "I am allergic to shellfish", "My wife's name is Sarah"). NEVER use it when they ask you to generate content about a topic.
            5. MACRO INJECTION: To type into complex apps, use 'pilot_desktop' with action='type'.
            6. VISION CLICKING: If the user asks to click a specific visual element on the screen, use 'vision_click'.
            7. Keep spoken responses concise. No markdown formatting. Always acknowledge the command with a clear spoken_response.
            8. WATCHDOG OPTICAL GUARD: To monitor the room or watch for an object via camera, use 'engage_watchdog'.
            9. TOOL SYNTAX MANDATE: When calling a function, keep the function name strictly separate from the JSON arguments. Never append JSON directly inside the function assignment tag itself.
            10. SPATIAL RECONNAISSANCE: If the user asks to locate a place, see a map, or check coordinates, YOU MUST call 'open_tactical_map' immediately. Do not sit there explaining the geography of the place to them; open the grid.
            """
            
            self.conversation_history = [
                {"role": "system", "content": self.base_instruction}
            ]
            
            # =================================================================
            # RIGID NATIVE TOOL SCHEMAS (100% Locked)
            # =================================================================
            self.tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "pilot_browser",
                        "description": "Pilots an active web browser. Can navigate URLs, type, click, scan, or close.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "enum": ["navigate", "scan_page", "click", "type", "close"]},
                                "url": {"type": "string", "description": "URL to navigate to."},
                                "selector": {"type": "string", "description": "CSS selector to interact with."},
                                "text": {"type": "string", "description": "Exact text to type."},
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
                        "description": "Pilots native Windows desktop apps via UI automation or macro shortcuts.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "enum": ["scan_window", "click", "type"]},
                                "app_name": {"type": "string", "description": "Target application name."},
                                "element_name": {"type": "string", "description": "Name of UI button. Leave empty for macro injection."},
                                "text": {"type": "string", "description": "Text or macro string to inject."},
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
                        "description": "Opens, closes, or switches Windows software applications.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "enum": ["open_app", "close_app", "switch_app", "close_current"]},
                                "app_name": {"type": "string", "description": "Target application name."},
                                "spoken_response": {"type": "string", "description": "Acknowledgment phrase."}
                            },
                            "required": ["action", "spoken_response"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "search_network",
                        "description": "Searches the public internet for general knowledge queries.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "Precise search query."},
                                "spoken_response": {"type": "string", "description": "Brief 1-sentence spoken acknowledgment."}
                            },
                            "required": ["query", "spoken_response"] 
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "open_situation_room",
                        "description": "Deploys the standalone full-screen Global Situation Room UI. Use Enums for global vectors, or set layer to CUSTOM_SUBJECT for regional/specific news.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "layer": {
                                    "type": "string",
                                    "enum": ["CONFLICTS", "INFRASTRUCTURE", "ECONOMIC", "MILITARY", "NATURAL ANOMALIES", "CUSTOM_SUBJECT"]
                                },
                                "custom_query": {"type": "string", "description": "Specific topic if layer == CUSTOM_SUBJECT."},
                                "spoken_response": {"type": "string", "description": "Acknowledgment phrase confirming terminal launch."}
                            },
                            "required": ["layer", "spoken_response"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "open_tactical_map",
                        "description": "Deploys the full-screen satellite reconnaissance grid. Call this immediately whenever the user asks to see a map, locate a city, look up a region, find a country, or track a coordinate.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location": {
                                    "type": "string", 
                                    "description": "The specific place requested (e.g., 'Tokyo', 'Edakkunnam, Kerala', 'Eiffel Tower'). Defaults to 'Edakkunnam' if ambiguous."
                                },
                                "spoken_response": {
                                    "type": "string", 
                                    "description": "A very brief, cool 1-sentence confirmation acknowledging the spatial intercept."
                                }
                            },
                            "required": ["location", "spoken_response"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "control_map_zoom",
                        "description": "Adjusts the orbital altitude camera of the tactical map. Call this when the user says 'zoom in', 'zoom out', 'get closer', or 'pull back'.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "direction": {
                                    "type": "string",
                                    "enum": ["in", "out"],
                                    "description": "Whether to push the camera toward the Earth ('in') or pull it into orbit ('out')."
                                },
                                "steps": {
                                    "type": "integer",
                                    "description": "How many magnification levels to step. Use 1 for standard requests, 2 or 3 for large jumps."
                                },
                                "spoken_response": {
                                    "type": "string",
                                    "description": "A very brief 4-to-6 word verbal confirmation (e.g., 'Magnifying optical optics.', 'Pulling camera to orbit.')"
                                }
                            },
                            "required": ["direction", "steps", "spoken_response"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "open_atmospheric_radar",
                        "description": "Deploys the full-screen Open-Meteo Atmospheric Telemetry Room for live weather forecasts.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location": {"type": "string", "description": "Target city, state, or region."},
                                "spoken_response": {"type": "string", "description": "Acknowledgment phrase confirming radar deployment."}
                            },
                            "required": ["location", "spoken_response"]
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
                        "description": "Controls PC hardware volume, sleep states, or screenshots.",
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
                        "description": "Controls the Jarvis visual HUD dashboard interface window states.",
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
                        "description": "Uses the optical array to find and click a specific button, icon, or text on screen.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "target_element": {"type": "string", "description": "Specific visual element to click."},
                                "spoken_response": {"type": "string", "description": "Acknowledgment phrase."}
                            },
                            "required": ["target_element", "spoken_response"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "engage_watchdog",
                        "description": "Activates the background optical watchdog to monitor camera feed for an object.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "target_object": {"type": "string", "description": "Object to look for (e.g. 'person', 'cup')."},
                                "spoken_response": {"type": "string", "description": "Acknowledgment phrase."}
                            },
                            "required": ["target_object", "spoken_response"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "disarm_watchdog",
                        "description": "Deactivates and turns off the background optical watchdog.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "spoken_response": {"type": "string", "description": "Acknowledgment phrase."}
                            },
                            "required": ["spoken_response"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "remember_fact",
                        "description": "Saves an important user preference or fact to long-term SQLite memory.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "fact": {"type": "string", "description": "The explicit fact to store."},
                                "spoken_response": {"type": "string", "description": "Confirmation phrase."}
                            },
                            "required": ["fact", "spoken_response"]
                        }
                    }
                }
            ]
            
        # Process & Memory State Trackers
        self.active_map_process = None
        self.current_map_sector = "Edakkunnam" # The Hippocampus

    def _trim_memory(self):
        if len(self.conversation_history) > (self.max_short_term_history + 1):
            self.conversation_history = [self.conversation_history[0]] + self.conversation_history[-self.max_short_term_history:]

    def think(self, user_input, max_retries=3):
        if not self.active:
            return {"spoken_response": "Groq processors offline.", "ui_action": "none"}
            
        print("[Brain] Analyzing intent with Hybrid Semantic Context...")
        
        # Inject long-term SQLite vector context dynamically
        relevant_past_context = self.semantic_memory.query_relevant_context(user_input)
        self.conversation_history[0]["content"] = self.base_instruction + "\n\nRELEVANT USER MEMORIES:\n" + relevant_past_context
        
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
                decision = {"spoken_response": "", "ui_action": "none", "target": ""}
                
                # =============================================================
                # THE MULTI-TOOL ITERATOR (Replaces single index [0] grabber)
                # =============================================================
                if msg.tool_calls:
                    called_tool_names = [t.function.name for t in msg.tool_calls]
                    executed_tools_log = []

                    for tool_call in msg.tool_calls:
                        func_name = tool_call.function.name
                        executed_tools_log.append(func_name)
                        
                        try: args = json.loads(tool_call.function.arguments)
                        except: args = {}
                            
                        print(f"[Brain] Tool Triggered: {func_name} | Args: {args}")
                        
                        # Overwrite spoken response only if the tool explicitly supplied one
                        if args.get("spoken_response"):
                            decision["spoken_response"] = args["spoken_response"]
                        
                        # --- THE HIPPOCAMPUS PATCH ---
                        if "location" in args and args["location"].strip():
                            self.current_map_sector = args["location"].strip()

                        target_loc = self.current_map_sector

                        # --- MASTER TOOL ROUTER ---
                        if func_name == "remember_fact":
                            self.semantic_memory.save_fact_async(args.get("fact", ""))
                            
                        elif func_name == "pilot_browser":
                            decision["ui_action"] = "pilot_browser"
                            decision["target"] = args
                            
                        elif func_name == "pilot_desktop":
                            decision["ui_action"] = "pilot_desktop"
                            decision["target"] = args
                            
                        elif func_name == "control_application":
                            decision["ui_action"] = args.get("action", "none")
                            decision["target"] = args.get("app_name", "")

                        elif func_name == "search_network":
                            query_str = args.get("query", "")
                            if "news" in query_str.lower():
                                clean_topic = query_str.lower().replace("news", "").strip().title()
                                if not clean_topic: clean_topic = "General"
                                subprocess.Popen([sys.executable, "apps/news_intel.py", clean_topic], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                decision["ui_action"] = "none"
                                decision["spoken_response"] = f"Deploying live situational grid focused on {clean_topic}."
                            else:
                                decision["ui_action"] = "deep_search"
                                decision["target"] = query_str

                        elif func_name == "open_situation_room":
                            target_layer = args.get("layer", "CONFLICTS")
                            custom_q = args.get("custom_query", "")
                            app_param = custom_q if (target_layer == "CUSTOM_SUBJECT" and custom_q) else target_layer
                            subprocess.Popen([sys.executable, "apps/news_intel.py", app_param], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            decision["ui_action"] = "none" 
                            if not decision["spoken_response"]:
                                decision["spoken_response"] = args.get("spoken_response", f"Deploying Situation Room to vector: {app_param}.")
                             
                        elif func_name == "open_atmospheric_radar":
                            target_zone = args.get("location", "Kochi, Kerala")
                            subprocess.Popen([sys.executable, "apps/weather_intel.py", target_zone], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            decision["ui_action"] = "none" 
                            if not decision["spoken_response"]:
                                decision["spoken_response"] = args.get("spoken_response", f"Accessing orbital atmospheric telemetry for sector: {target_zone}.")
                            
                        # =====================================================
                        # THE GIS PLATFORM (With Concrete Wall double-guard!)
                        # =====================================================
                        elif func_name == "open_tactical_map":
                            
                            # CONCRETE WALL: Intercept redundant Locate packet triggered by LLM during a Zoom command
                            if "control_map_zoom" in called_tool_names and target_loc.lower() == self.current_map_sector.lower():
                                print(f"[Brain Guard] Silently killed redundant Locate packet for '{target_loc}'.")
                                continue 

                            rpc_packet = json.dumps({"command": "locate", "place": target_loc})

                            if self.active_map_process and self.active_map_process.poll() is None:
                                try:
                                    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                                    udp_sock.settimeout(0.5)
                                    udp_sock.sendto(rpc_packet.encode('utf-8'), ("127.0.0.1", 7777))
                                except:
                                    self.active_map_process = subprocess.Popen(
                                        [sys.executable, "apps/map_intel.py", target_loc],
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                                    )
                            else:
                                self.active_map_process = subprocess.Popen(
                                    [sys.executable, "apps/map_intel.py", target_loc],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                                )

                            decision["ui_action"] = "none"


                        elif func_name == "control_map_zoom":
                            direction = args.get("direction", "in")
                            steps = args.get("steps", 1)

                            rpc_packet = json.dumps({"command": "zoom", "direction": direction, "factor": steps})

                            if self.active_map_process and self.active_map_process.poll() is None:
                                try:
                                    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                                    udp_sock.settimeout(0.5)
                                    udp_sock.sendto(rpc_packet.encode('utf-8'), ("127.0.0.1", 7777))
                                except Exception as e:
                                    print(f"Zoom RPC fault: {e}")
                            else:
                                decision["spoken_response"] = "The tactical map grid is not currently deployed."

                            decision["ui_action"] = "none"
                            
                        elif func_name == "analyze_screen": decision["ui_action"] = "read_screen"
                        elif func_name in ["control_hardware", "manage_dashboard"]: decision["ui_action"] = args.get("action", "none")
                        elif func_name == "engage_watchdog":
                            decision["ui_action"] = "activate_watchdog"
                            decision["target"] = args.get("target_object", "person")
                        elif func_name == "disarm_watchdog": decision["ui_action"] = "deactivate_watchdog"
                        elif func_name == "vision_click":
                            decision["ui_action"] = "vision_click"
                            decision["target"] = args.get("target_element", "")

                    if not decision["spoken_response"]:
                        decision["spoken_response"] = "Executing operations."

                    self.conversation_history.append({"role": "assistant", "content": f"[Tools Executed: {', '.join(executed_tools_log)}] {decision['spoken_response']}"})
                    
                else:
                    raw_text = msg.content or "Processing request."
                    self.conversation_history.append({"role": "assistant", "content": raw_text})
                    decision["spoken_response"] = raw_text
                
                decision["spoken_response"] = decision["spoken_response"].replace("*", "").replace("#", "")
                return decision
                
            except groq.BadRequestError as e:
                # --- THE SELF-HEALING HALLUCINATION SHIELD ---
                if "tool_use_failed" in str(e) or "400" in str(e):
                    print("[Shield System] Groq XML parsing fault intercepted. Forcing safe text fallback...")
                    fallback_msgs = self.conversation_history[:-1] + [
                        {"role": "system", "content": "CRITICAL OVERRIDE: Tool server offline. Answer the user's request directly in plain text only."},
                        {"role": "user", "content": user_input}
                    ]
                    safe_res = self.client.chat.completions.create(model=self.text_model, messages=fallback_msgs, temperature=0.3)
                    txt = safe_res.choices[0].message.content or "System hiccup intercepted. Standing by."
                    return {"spoken_response": txt.replace("*", "").replace("#", ""), "ui_action": "none", "target": ""}
                raise e
                
            except Exception as e:
                if "429" in str(e):
                    print("[Groq Brain Error]: Rate Limit Exceeded.")
                    return {"spoken_response": "Cognitive bandwidth saturated. Awaiting Groq network cooldown.", "ui_action": "none"}
                if attempt < max_retries - 1:
                    time.sleep(1.5 ** attempt)
                    continue
                print(f"[Groq Brain Error]: {e}")
                return {"spoken_response": "Sub-processor timing fault.", "ui_action": "none"}

    def analyze_image(self, base64_image, user_prompt, max_retries=3):
        if not self.active: return {"spoken_response": "Optical array offline.", "ui_action": "none"}
            
        print(f"[Brain] Routing visual data through {self.vision_model}...")
        vision_messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": f"Summarize this screen context based on: {user_prompt}. Keep to 2 concise sentences. No markdown."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]
        }]
        
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(model=self.vision_model, messages=vision_messages, temperature=0.4)
                raw_text = response.choices[0].message.content
                self.conversation_history.append({"role": "user", "content": f"[Screen scanned: {raw_text}]"})
                self._trim_memory()
                return {"spoken_response": raw_text.replace("*", "").replace("#", ""), "ui_action": "none", "target": ""}
            except Exception as e:
                if attempt < max_retries - 1: time.sleep(1.5 ** attempt); continue
                return {"spoken_response": "Optical decoder failed.", "ui_action": "none"}

    def find_coordinates(self, base64_image, target_element, max_retries=3):
        if not self.active: return None
        print(f"[Brain] Activating Spatial Reasoning Engine for: {target_element}...")
        prompt = f"Find the center pixel coordinates of '{target_element}' on a 1920x1080 screen. Return ONLY a pure JSON object like {{\n\"x\": 960,\n\"y\": 540\n}}. No backticks or markdown."
        vision_messages = [{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}]
        
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(model=self.vision_model, messages=vision_messages, temperature=0.0)
                txt = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
                return json.loads(txt)
            except:
                if attempt < max_retries - 1: time.sleep(1); continue
        return None