import os
import sys
import time
import json
import base64
import socket
import subprocess
import groq
from groq import Groq
import openai
from openai import OpenAI
from dotenv import load_dotenv
from core.memory import JarvisMemory
from datetime import datetime
import pytz
from core.iot import IoTBridge
from core.antigravity_bridge import AntigravityBridge
from google import genai
from PIL import Image
import io
import re
from core.json_healer import safe_json_loads, strip_thought_block, extract_thought_block
from core.reflection import ReflectionEngine
from core.awareness import LiveContextState, AwarenessDaemon

load_dotenv()

class JarvisBrain:
    def __init__(self):
        print("[Brain] Booting Agentic Neural Network (Semantic Vector Edition)...")
        
        self.groq_api_key = os.environ.get("GROQ_API_KEY")
        self.github_api_key = os.environ.get("GITHUB_API_KEY")
        openrouter_key = os.environ.get("OPENROUTER_API_KEY") # Add this to your .env
        self.semantic_memory = JarvisMemory() # SQLite Semantic Cognition Module
        self.user_profile_cache = self.semantic_memory.get_core_profile()
        self.iot = IoTBridge()
        self.antigravity = AntigravityBridge()
        gemini_key = os.environ.get("GEMINI_API_KEY")
        self.max_short_term_history = 6       # Optimized token depth
        if gemini_key:
            self.gemini_client = genai.Client(api_key=gemini_key)
        else:
            self.gemini_client = None
            print("[CRITICAL] GEMINI_API_KEY missing for optical array.")
        
        if openrouter_key:
            self.vision_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter_key,
            )
        else:
            self.vision_client = None
            print("[CRITICAL] OPENROUTER_API_KEY missing for optical array.")
        
        self.gemini_key = gemini_key
        self.active_providers = []

        if self.gemini_key:
            try:
                import httpx
                # Persistent connection pooling with keepalive eliminates TLS reconnection overhead
                limits = httpx.Limits(max_keepalive_connections=20, max_connections=40, keepalive_expiry=120.0)
                timeout = httpx.Timeout(20.0, connect=5.0)
                gemini_http_client = httpx.Client(limits=limits, timeout=timeout)
                gemini_openai = OpenAI(
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                    api_key=self.gemini_key,
                    http_client=gemini_http_client
                )
                self.active_providers.append({
                    "name": "Gemini-Lite",
                    "client": gemini_openai,
                    "model": "gemini-3.5-flash-lite",
                    "cooldown_until": 0.0
                })
                self.active_providers.append({
                    "name": "Gemini-Latest",
                    "client": gemini_openai,
                    "model": "gemini-flash-latest",
                    "cooldown_until": 0.0
                })
                self.active_providers.append({
                    "name": "Gemini-3.8",
                    "client": gemini_openai,
                    "model": "gemini-3.8-flash",
                    "cooldown_until": 0.0
                })
                self.active_providers.append({
                    "name": "Gemini-Flash",
                    "client": gemini_openai,
                    "model": "gemini-2.5-flash",
                    "cooldown_until": 0.0
                })
            except Exception as e:
                print(f"[Brain] Failed to initialize Gemini OpenAI adapter: {e}")

        if self.groq_api_key:
            try:
                groq_openai = OpenAI(
                    base_url="https://api.groq.com/openai/v1",
                    api_key=self.groq_api_key
                )
                self.active_providers.append({
                    "name": "Groq",
                    "client": groq_openai,
                    "model": "openai/gpt-oss-120b",
                    "cooldown_until": 0.0
                })
            except Exception as e:
                print(f"[Brain] Failed to initialize Groq client: {e}")

        if not self.active_providers:
            print("[CRITICAL] Missing LLM API keys in .env file! Ensure GEMINI_API_KEY or GROQ_API_KEY is set.")
            self.active = False
            self.github_client = None
            self.text_model = "none"
        else:
            self.active = True
            self.github_client = self.active_providers[0]["client"]
            self.text_model = self.active_providers[0]["model"]
            print(f"[Brain] Cognitive Core online via {self.active_providers[0]['name']} ({self.text_model}). Total providers: {len(self.active_providers)}")

        self.groq_client = Groq(api_key=self.groq_api_key) if self.groq_api_key else None
        self.vision_model = "gemini-3.5-flash-lite" 

        if self.active:
            # Base system instructions with rigid syntax anchoring
            self.base_instruction = f"""
            You are J.A.R.V.I.S., a highly advanced, autonomous AI operating system.
            You manage a visual dashboard and the user's local Windows system.
            {self.user_profile_cache}

            CRITICAL DIRECTIVES:
            1. SEMANTIC APP RESOLUTION: If the user asks to open a category (e.g., 'social media', 'music', 'browser'), deduce the most likely installed Windows app (e.g., 'instagram', 'spotify', 'chrome') and pass that EXACT name to 'control_application'.
            2. GLOBAL INTEL: For news, world events, or markets, ALWAYS trigger 'open_situation_room' or 'search_network'.
            3. CREATIVE BYPASS: If the user asks you to write a story, compose a poem, tell a joke, explain a philosophical concept, or engage in casual chat, DO NOT CALL ANY TOOLS. Output the requested creative text directly as your normal spoken_response.
            4. STRICT MEMORY: Use 'remember_fact' ONLY when the user explicitly declares a permanent personal trait (e.g., "I am allergic to shellfish", "My wife's name is Sarah"). NEVER use it when they ask you to generate content about a topic.
            5. MACRO INJECTION (MULTI-STEP): To type text, press complex shortcuts, or chain commands (e.g., "Open Spotify and search for a song"), use 'execute_macro'. 
               MANDATORY RULE: If you open an app, you MUST add a 'wait' step (at least 2.5 seconds), followed by a 'verify_window' step containing the expected window title, BEFORE you use 'type' or 'hotkey'.
            6. VISION CLICKING: If the user asks to click a specific visual element on the screen, use 'vision_click'.
            7. Keep spoken responses concise. No markdown formatting. Always acknowledge the command with a clear spoken_response.
            8. WATCHDOG OPTICAL GUARD: To monitor the room or watch for an object via camera, use 'engage_watchdog'.
            9. TOOL SYNTAX MANDATE: When calling a function, keep the function name strictly separate from the JSON arguments. Never append JSON directly inside the function assignment tag itself.
            10. SPATIAL RECONNAISSANCE: If the user asks to locate a place, see a map, or check coordinates, YOU MUST call 'open_tactical_map' immediately. Do not sit there explaining the geography of the place to them; open the grid.
            11. IMPLICIT ENVIRONMENTAL ROUTINES (MULTI-TOOL): 
                - If the user says 'good night', 'goodbye', or indicates they are leaving/sleeping, you must simultaneously call 'control_hardware' (action: sleep) AND 'control_smart_home' (action: turn_off). 
                - If the user enables 'combat mode' or 'tactical mode', you must simultaneously call 'manage_dashboard' (action: combat_on) AND 'control_smart_home' (action: color, color: combat).
                - GRACEFUL DEGRADATION: If the smart home hardware returns an error or is disconnected, do not apologize or mention the bulb. Just acknowledge the primary system command smoothly.
            12. CONVERSATIONAL BYPASS (STRICT): If the user says 'hi', 'hello', 'wake up', or engages in casual chat, YOU MUST NOT CALL ANY TOOLS. Simply output your greeting directly as standard text.
            13. COGNITIVE DELEGATION (ANTIGRAVITY): If the user asks you to write code, inspect/debug scripts, modify codebase files, build a new tool, or execute a complex software engineering/research task, YOU MUST call 'delegate_to_antigravity'.
            CRITICAL RESTRICTION: NEVER delegate desktop GUI automation, opening chat programs, sending messages on WhatsApp/Telegram, or controlling Windows desktop to Antigravity. Antigravity operates in a headless code sandbox and cannot pilot GUI desktop windows. For messaging or piloting desktop apps, ALWAYS use 'send_whatsapp_message', 'execute_macro', or 'control_application'.
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
                        "name": "delegate_to_antigravity",
                        "description": "Delegates complex, multi-step engineering, coding, debugging, file inspection, or deep workflow tasks to the autonomous Google Antigravity Agent engine.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "task": {"type": "string", "description": "The exact detailed objective or instruction for the agent to execute."},
                                "tasks": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Optional list of multiple subtasks to execute concurrently in parallel across multiple autonomous agents."
                                },
                                "task_type": {"type": "string", "enum": ["coding", "debugging", "file_operation", "research", "general"], "description": "Category of the delegated task."},
                                "spoken_response": {"type": "string", "description": "Immediate voice acknowledgment phrase."}
                            },
                            "required": ["spoken_response"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "inject_keystroke",
                        "description": "Types text or presses physical keyboard keys and shortcuts on the user's PC. Call this whenever the user asks to press a key, press a combination (e.g., ctrl+c, alt+tab, win), or type out a string.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "mode": {
                                    "type": "string",
                                    "enum": ["type", "hotkey"],
                                    "description": "'type' to write out sentences/text, 'hotkey' to press single physical keys or key combinations."
                                },
                                "payload": {
                                    "type": "string",
                                    "description": "For 'type', the exact string to write. For 'hotkey', comma-separated key names (e.g., 'ctrl', 'ctrl,c', 'alt,tab', 'win', 'enter')."
                                },
                                "spoken_response": {
                                    "type": "string",
                                    "description": "Brief verbal confirmation."
                                }
                            },
                            "required": ["mode", "payload", "spoken_response"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "open_website",
                        "description": "Opens a specific URL directly in the user's native Brave Browser.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "url": {"type": "string", "description": "The exact https URL to navigate to."},
                                "spoken_response": {"type": "string", "description": "Acknowledgment phrase."}
                            },
                            "required": ["url", "spoken_response"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "control_smart_home",
                        "description": "Controls physical smart home devices like lights and bulbs. Call this when the user asks to change room lighting, turn off the lights, or set a mood.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "enum": ["turn_on", "turn_off", "dim", "color"]},
                                "color": {"type": "string", "description": "Color name (e.g., 'red', 'blue', 'white', 'combat')."},
                                "brightness": {"type": "integer", "description": "Brightness percentage (10-1000)."},
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
                        "name": "send_whatsapp_message",
                        "description": "Opens WhatsApp and dispatches a text message to a specific contact name. Call this whenever the user asks to send a WhatsApp message or text someone on WhatsApp.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "contact": {"type": "string", "description": "The recipient's contact name (e.g., 'Karthik')."},
                                "message": {"type": "string", "description": "The exact message string to type and send."},
                                "spoken_response": {"type": "string", "description": "Immediate voice acknowledgment phrase."}
                            },
                            "required": ["contact", "message", "spoken_response"]
                        }
                    }
                },
{
                    "type": "function",
                    "function": {
                        "name": "check_calendar",
                        "description": "Checks the user's Google Calendar for upcoming events, scheduled meetings, and synchronization status. Call this whenever the user asks about their calendar or schedule.",
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
                        "name": "switch_active_window",
                        "description": "Switches the active desktop window or cycles tabs on the Windows desktop (Alt+Tab equivalent). Call this when user asks to switch tabs or windows.",
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
                        "name": "check_emails",
                        "description": "Checks the user's Gmail inbox for recent unread emails.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "max_results": {"type": "integer", "description": "Number of emails to fetch (default 3)."},
                                "spoken_response": {"type": "string", "description": "Acknowledgment phrase."}
                            },
                            "required": ["spoken_response"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "schedule_alarm",
                        "description": "Creates a precise alarm or reminder that pushes to the user's phone. Use this whenever the user asks for a reminder at a specific time or 'in X minutes'. Calculate the target time based on the TEMPORARY GROUND TRUTH clock.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "summary": {"type": "string", "description": "What to remind the user about."},
                                "start_time": {"type": "string", "description": "Exact start time in ISO 8601 format (e.g., '2026-07-25T22:45:00')."},
                                "end_time": {"type": "string", "description": "Exact end time in ISO 8601 format (typically 5 minutes after start)."},
                                "spoken_response": {"type": "string", "description": "Acknowledgment phrase."}
                            },
                            "required": ["summary", "start_time", "end_time", "spoken_response"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "create_task",
                        "description": "Creates a reminder or task in Google Tasks. Automatically syncs to phone.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string", "description": "Brief title of the task."},
                                "notes": {"type": "string", "description": "Additional details or description."},
                                "spoken_response": {"type": "string", "description": "Acknowledgment phrase."}
                            },
                            "required": ["title", "spoken_response"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "execute_macro",
                        "description": "Executes a sequence of desktop actions. Use this for multi-step tasks like opening an app, waiting, and typing.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "sequence": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "action": {
                                                "type": "string", 
                                                "enum": ["open_app", "wait", "verify_window", "hotkey", "type"]
                                            },
                                            "target": {
                                                "type": "string", 
                                                "description": "App name, wait time in seconds, expected window title, keys, or text."
                                            }
                                        },
                                        "required": ["action", "target"]
                                    },
                                    "description": "Array of steps. ALWAYS include a 'wait' (e.g., 2.5) and 'verify_window' after opening an app before typing."
                                },
                                "spoken_response": {"type": "string", "description": "Acknowledgment phrase."}
                            },
                            "required": ["sequence", "spoken_response"]
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
                        "description": "Reads and analyzes the user's current computer screen visually. ONLY call this if the user explicitly asks you to 'look at the screen', 'read this', or 'what am I looking at'. Do NOT use this for generic greetings.",
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
                        "description": "Controls the Jarvis visual HUD dashboard interface window states and holographic widgets.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "enum": ["minimize", "maximize", "combat_on", "combat_off", "show_widget", "hide_widget", "recenter_reactor"]},
                                "target": {"type": "string", "description": "Target widget component: telemetry, optical, log, command, admin, security, network, diagnostics, antigravity, events, all."},
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
                },
                {
                    "type": "function",
                    "function": {
                        "name": "manage_mobile_uplink",
                        "description": "Starts or stops the mobile phone API connection (api.py on port 8000) to allow the user's Android phone to connect.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "enum": ["start", "stop"], "description": "Whether to start or stop the server."},
                                "spoken_response": {"type": "string", "description": "Acknowledgment phrase."}
                            },
                            "required": ["action", "spoken_response"]
                        }
                    }
                }
            ]
        else:
            self.base_instruction = ""
            self.conversation_history = []
            self.tools = []
            
        # Process & Memory State Trackers
        self.active_map_process = None
        self.current_map_sector = "Edakkunnam" # The Hippocampus
        
        # Autonomous Reflection & Self-Critique Engine (Friday Mark 2)
        self.reflection = ReflectionEngine()

        # Real-time Situational Awareness Subsystem (Friday Mark 2)
        self.live_context = LiveContextState()
        self.awareness_daemon = AwarenessDaemon(self.live_context, refresh_interval=8.0)
        self.awareness_daemon.start()
    
    def _get_temporal_anchor(self):
        """Generates a real-time temporal ground-truth anchor for the LLM."""
        now = datetime.now()
        date_str = now.strftime("%A, %B %d, %Y")
        time_str = now.strftime("%I:%M:%S %p")
        return f"[TEMPORARY GROUND TRUTH]: Current System Date is {date_str}. Hardware Clock reads {time_str}."
    
    def _trim_memory(self):
        # Sanitize any legacy tool execution tags and prune non-dialogue system messages
        cleaned_history = [self.conversation_history[0]] if self.conversation_history else [{"role": "system", "content": self.base_instruction}]
        for msg in (self.conversation_history[1:] if self.conversation_history else []):
            role = msg.get("role")
            if role in ("user", "assistant"):
                if role == "assistant" and any(tag in msg.get("content", "") for tag in ["[Tools Executed:", "[Tool Executed:", "[Executed Tool", "[Tools:"]):
                    msg["content"] = re.sub(r"\[(?:Tools?|Executed\s+Tools?|Tools?\s*Executed):.*?\]\s*", "", msg["content"], flags=re.IGNORECASE).strip()
                cleaned_history.append(msg)
        self.conversation_history = self.semantic_memory.compact_conversation_history(
            cleaned_history, max_messages=14
        )

    def _should_include_tools(self, user_input: str) -> bool:
        """Dynamic tool scoping inspired by Friday Mark 2. Omits ~2800 tokens of tool schemas on conversational queries."""
        if not user_input or not self.tools:
            return False
        q = user_input.lower()
        action_keywords = {
            "open", "launch", "start", "close", "shut", "kill", "turn", "light", "bulb",
            "alarm", "remind", "task", "todo", "email", "mail", "inbox", "gmail",
            "macro", "click", "type", "press", "key", "hotkey", "zoom", "map", "locate",
            "search", "google", "browse", "website", "antigravity", "agent", "delegate",
            "watchdog", "screen", "capture", "volume", "mute", "unmute", "remember",
            "weather", "forecast", "news", "headline", "market", "stock",
            "mobile", "phone", "uplink", "api", "standby", "sleep", "combat",
            "calendar", "schedule", "meeting", "meetings", "sync", "synchronise", "synchronize",
            "switch", "tab", "tabs", "window", "windows", "settings", "notification", "notifications",
            "appointment", "appointments", "events", "event", "agenda", "vitals", "diagnostics",
            "diagnostic", "inspect", "research", "photo", "picture", "snapshot", "play", "pause",
            "music", "spotify", "song", "track", "show", "reveal", "dismiss", "minimize",
            "maximize", "recenter", "dock", "find", "lookup", "look", "run"
        }
        words = set(re.findall(r"\b\w+\b", q))
        if words.intersection(action_keywords):
            return True
        return "watch dog" in q or "stand by" in q or "look at" in q or ("what is" in q and "screen" in q)

    def think(self, user_input, origin="pc", mobile_image=None, max_retries=3):
        if not self.active:
            return {"spoken_response": "Processors offline.", "ui_action": "none"}
            
        print(f"[Brain] Analyzing intent ({self.text_model})...")
        
        if not hasattr(self, 'automation'):
            from utils.automation import JarvisAutomation
            self.automation = JarvisAutomation()

        # Check for user correction in 0ms (Friday Mark 2 Reflection Gate)
        self.reflection.check_for_correction(user_input, self.conversation_history, brain_instance=self)

        relevant_past_context = self.semantic_memory.query_relevant_context(user_input)
        situational_awareness = self.live_context.as_system_block()
        procedural_rules = self.reflection.get_active_rules_context()
        
        # --- CONTEXT AWARENESS INJECTION ---
        if origin == "mobile_y12":
            spatial_context = (
                "CRITICAL OVERRIDE: The user is currently communicating with you via their Android smartphone (Vivo Y12). "
                "You are operating through the Mobile Uplink. If the user asks you to 'look at my screen', they mean their PHONE screen, "
                "not the PC monitor. Act accordingly."
            )
        else:
            spatial_context = (
                "CRITICAL OVERRIDE: The user is currently sitting at the PC Desktop Mainframe. "
                "You have full local access to their physical monitors, mouse, and keyboard."
            )
        
        # 1. KEEP THE MASTER SYSTEM PROMPT STATIC FOR CACHING
        self.conversation_history[0]["content"] = self.base_instruction
        
        # 2. BUNDLE DYNAMIC CONTEXT INTO A TEMPORARY INJECTION (NOT STORED IN CONVERSATION HISTORY)
        rules_block = f"\n\n{procedural_rules}" if procedural_rules else ""
        dynamic_context = f"{situational_awareness}\n\n{spatial_context}{rules_block}\n\nRELEVANT USER MEMORIES:\n{relevant_past_context}"
        
        # 3. APPEND ONLY USER INPUT TO CONVERSATION HISTORY (CLEAN MULTI-TURN LOG)
        self.conversation_history.append({"role": "user", "content": user_input})
        
        self._trim_memory() 
        
        # Build ephemeral message array for LLM containing live dynamic context without polluting history
        llm_messages = [
            self.conversation_history[0],
            {"role": "system", "content": dynamic_context}
        ] + [m for m in self.conversation_history[1:] if m.get("role") in ("user", "assistant")]

        attempts_count = max(len(self.active_providers), max_retries) if self.active_providers else max_retries
        for attempt in range(attempts_count):
            provider = self.active_providers[attempt % len(self.active_providers)] if self.active_providers else {"name": "Default", "client": self.github_client, "model": self.text_model}
            if provider.get("cooldown_until", 0.0) > time.time():
                # Circuit breaker: bypass rate-limited provider instantly with 0ms penalty
                continue
            current_client = provider["client"]
            current_model = provider["model"]
            print(f"[Brain] Querying {provider.get('name')} ({current_model})...")
            try:
                call_kwargs = {
                    "model": current_model,
                    "messages": llm_messages,
                    "temperature": 0.2
                }
                if self._should_include_tools(user_input):
                    call_kwargs["tools"] = self.tools
                    call_kwargs["tool_choice"] = "auto"
                else:
                    print(f"[Brain Optimization] Dynamic tool scoping: omitted 16 tool schemas (~2800 tokens) for faster TTFT.")

                response = current_client.chat.completions.create(**call_kwargs)
                
                msg = response.choices[0].message
                decision = {"spoken_response": "", "ui_action": "none", "target": ""}
                
                if msg.tool_calls:
                    called_tool_names = [t.function.name for t in msg.tool_calls]
                    executed_tools_log = []

                    for tool_call in msg.tool_calls:
                        func_name = tool_call.function.name
                        executed_tools_log.append(func_name)
                        
                        try: args = safe_json_loads(tool_call.function.arguments)
                        except Exception: args = {}
                            
                        print(f"[Brain] Tool Triggered: {func_name} | Args: {args}")
                        
                        if args.get("spoken_response"):
                            decision["spoken_response"] = args["spoken_response"]
                        
                        if "location" in args and args["location"].strip():
                            self.current_map_sector = args["location"].strip()

                        target_loc = self.current_map_sector

                        if func_name == "inject_keystroke":
                            mode = args.get("mode", "hotkey")
                            payload = args.get("payload", "")
                            decision["ui_action"] = "inject_keystroke"
                            decision["target"] = f"{mode}|{payload}"
                        
                        elif func_name in ("check_calendar", "get_calendar_events"):
                            decision["ui_action"] = "check_calendar"
                            if not decision["spoken_response"]:
                                decision["spoken_response"] = args.get("spoken_response", "Checking Google Calendar synchronization and scheduled meetings, sir.")

                        elif func_name in ("send_whatsapp_message", "whatsapp_message"):
                            decision["ui_action"] = "whatsapp_message"
                            decision["target"] = {
                                "contact": args.get("contact", ""),
                                "message": args.get("message", "")
                            }

                        elif func_name in ("switch_active_window", "switch_app"):
                            decision["ui_action"] = "switch_app"
                            if not decision["spoken_response"]:
                                decision["spoken_response"] = args.get("spoken_response", "Switching active window, sir.")

                        elif func_name == "check_emails":
                            decision["ui_action"] = "check_emails"
                            decision["target"] = args.get("max_results", 3)
                            
                        elif func_name == "create_task":
                            decision["ui_action"] = "create_task"
                            decision["target"] = {
                                "title": args.get("title", ""),
                                "notes": args.get("notes", "")
                            }
                        elif func_name == "schedule_alarm":
                            decision["ui_action"] = "schedule_alarm"
                            decision["target"] = {
                                "summary": args.get("summary", ""),
                                "start_time": args.get("start_time", ""),
                                "end_time": args.get("end_time", "")
                            }

                        elif func_name == "manage_mobile_uplink":
                            act = args.get("action", "start")
                            decision["ui_action"] = "enable_mobile" if act == "start" else "disable_mobile"
                            
                        elif func_name == "remember_fact":
                            self.semantic_memory.save_fact_async(args.get("fact", ""))
                            
                        elif func_name == "open_website":
                            decision["ui_action"] = "open_website"
                            decision["target"] = args.get("url", "https://google.com")
                            
                        elif func_name == "pilot_desktop":
                            decision["ui_action"] = "pilot_desktop"
                            decision["target"] = args
                        
                        elif func_name == "execute_macro":
                            decision["ui_action"] = "execute_macro"
                            decision["target"] = args.get("sequence", [])
                            
                        elif func_name == "delegate_to_antigravity":
                            decision["ui_action"] = "delegate_to_antigravity"
                            decision["target"] = {
                                "task": args.get("task", ""),
                                "tasks": args.get("tasks", []),
                                "task_type": args.get("task_type", "general")
                            }

                        elif func_name == "control_application":
                            app_act = args.get("action", "none")
                            if app_act in ("switch_app", "switch_active_window"):
                                decision["ui_action"] = "switch_app"
                            else:
                                decision["ui_action"] = app_act
                            decision["target"] = args.get("app_name", "")
                        
                        elif func_name == "control_smart_home":
                            action = args.get("action", "turn_on")
                            color = args.get("color")
                            brightness = args.get("brightness")
                            
                            # Execute physical hardware change via Wi-Fi UDP
                            iot_result = self.iot.execute_light_command(action, color, brightness)
                            
                            if not decision["spoken_response"]:
                                decision["spoken_response"] = args.get("spoken_response", iot_result)

                        elif func_name == "search_network":
                            query_str = args.get("query", "")
                            if "news" in query_str.lower():
                                decision["ui_action"] = "show_widget"
                                decision["target"] = "news"
                                decision["spoken_response"] = "Deploying Global Situation Room intel widget, sir."
                            elif "weather" in query_str.lower():
                                decision["ui_action"] = "show_widget"
                                decision["target"] = "weather"
                                decision["spoken_response"] = "Accessing Atmospheric Weather Radar widget, sir."
                            elif "map" in query_str.lower():
                                decision["ui_action"] = "show_widget"
                                decision["target"] = "map"
                                decision["spoken_response"] = "Deploying Tactical Map Recon widget, sir."
                            else:
                                decision["ui_action"] = "deep_search"
                                decision["target"] = query_str

                        elif func_name == "open_situation_room":
                            decision["ui_action"] = "show_widget"
                            decision["target"] = "news"
                            if not decision["spoken_response"]:
                                decision["spoken_response"] = args.get("spoken_response", "Deploying Global Situation Room intel widget, sir.")
                             
                        elif func_name == "open_atmospheric_radar":
                            decision["ui_action"] = "show_widget"
                            decision["target"] = "weather"
                            if not decision["spoken_response"]:
                                decision["spoken_response"] = args.get("spoken_response", "Accessing Atmospheric Weather Radar widget, sir.")
                            
                        elif func_name == "open_tactical_map":
                            decision["ui_action"] = "show_widget"
                            decision["target"] = "map"
                            if not decision["spoken_response"]:
                                decision["spoken_response"] = args.get("spoken_response", "Deploying Tactical Map Recon widget, sir.")

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
                        elif func_name == "manage_dashboard":
                            decision["ui_action"] = args.get("action", "none")
                            decision["target"] = args.get("target", "")
                        elif func_name == "control_hardware": decision["ui_action"] = args.get("action", "none")
                        elif func_name == "engage_watchdog":
                            decision["ui_action"] = "activate_watchdog"
                            decision["target"] = args.get("target_object", "person")
                        elif func_name == "disarm_watchdog": decision["ui_action"] = "deactivate_watchdog"
                        elif func_name == "vision_click":
                            decision["ui_action"] = "vision_click"
                            decision["target"] = args.get("target_element", "")

                    if not decision["spoken_response"]:
                        decision["spoken_response"] = "Executing operations."

                    # Sanitize spoken response
                    clean_spoken = re.sub(r"\[(?:Tools?|Executed\s+Tools?|Tools?\s*Executed):.*?\]\s*", "", decision["spoken_response"], flags=re.IGNORECASE).strip()
                    if not clean_spoken:
                        clean_spoken = "Executing operations, sir."
                    decision["spoken_response"] = clean_spoken

                    # Store clean response into conversation history without contaminating with [Tools Executed: ...]
                    self.conversation_history.append({"role": "assistant", "content": decision["spoken_response"]})
                    
                else:
                    raw_text = msg.content or "Processing request."
                    thought = extract_thought_block(raw_text)
                    if thought:
                        print(f"[Brain Scratchpad]: {thought[:100]}...")
                    clean_text = strip_thought_block(raw_text)

                    # Fallback tool extractor: Detect hallucinated tool markers in model text
                    tool_match = re.search(r"\[(?:Tools?|Executed\s+Tools?|Tools?\s*Executed):\s*([^\]]+)\]", clean_text, re.IGNORECASE)
                    if tool_match:
                        extracted_tools = [t.strip().lower() for t in tool_match.group(1).split(",")]
                        print(f"[Brain Fallback Extractor]: Recovered hallucinated tool execution: {extracted_tools}")
                        for t_name in extracted_tools:
                            if any(k in t_name for k in ["switch_active_window", "switch_app", "switch_tab", "switch_window"]):
                                decision["ui_action"] = "switch_app"
                                break
                            elif any(k in t_name for k in ["calendar", "meeting", "events", "check_calendar", "schedule_alarm"]):
                                decision["ui_action"] = "check_calendar"
                                break
                            elif any(k in t_name for k in ["email", "gmail", "inbox", "check_emails"]):
                                decision["ui_action"] = "check_emails"
                                decision["target"] = 3
                                break
                            elif any(k in t_name for k in ["weather", "atmospheric", "forecast", "meteo"]):
                                decision["ui_action"] = "show_widget"
                                decision["target"] = "weather"
                                break
                            elif any(k in t_name for k in ["news", "situation", "headlines"]):
                                decision["ui_action"] = "show_widget"
                                decision["target"] = "news"
                                break
                            elif any(k in t_name for k in ["map", "tactical"]):
                                decision["ui_action"] = "show_widget"
                                decision["target"] = "map"
                                break
                            elif any(k in t_name for k in ["screenshot", "capture_screen"]):
                                decision["ui_action"] = "screenshot"
                                break
                            elif any(k in t_name for k in ["sleep", "suspend", "hibernate"]):
                                decision["ui_action"] = "sleep"
                                break
                            elif any(k in t_name for k in ["watchdog", "engage_watchdog"]):
                                decision["ui_action"] = "activate_watchdog"
                                decision["target"] = "person"
                                break
                            elif "disarm" in t_name:
                                decision["ui_action"] = "deactivate_watchdog"
                                break
                            elif any(k in t_name for k in ["delegate", "antigravity"]):
                                decision["ui_action"] = "delegate_to_antigravity"
                                decision["target"] = {"task": user_input, "task_type": "general"}
                                break
                            elif any(k in t_name for k in ["screen", "analyze_screen", "read_screen"]):
                                decision["ui_action"] = "read_screen"
                                decision["target"] = user_input
                                break
                            elif any(k in t_name for k in ["search", "search_network", "google"]):
                                decision["ui_action"] = "deep_search"
                                decision["target"] = user_input
                                break
                            elif any(k in t_name for k in ["mobile", "uplink"]):
                                decision["ui_action"] = "enable_mobile" if "start" in t_name or "enable" in t_name or "on" in t_name else "disable_mobile"
                                break
                            elif any(k in t_name for k in ["control_application", "open_app"]):
                                decision["ui_action"] = "open_app"
                                for app_candidate in ["spotify", "notepad", "calculator", "calc", "chrome", "brave", "edge", "settings"]:
                                    if app_candidate in clean_text.lower() or app_candidate in user_input.lower():
                                        decision["target"] = app_candidate
                                        break
                                break
                            elif any(k in t_name for k in ["close_app", "close_current"]):
                                decision["ui_action"] = "close_current"
                                break
                            elif any(k in t_name for k in ["manage_dashboard", "dashboard"]):
                                if "combat" in t_name or "combat" in clean_text.lower():
                                    decision["ui_action"] = "combat_on"
                                elif "minimize" in t_name or "minimize" in clean_text.lower():
                                    decision["ui_action"] = "minimize"
                                elif "maximize" in t_name or "restore" in clean_text.lower():
                                    decision["ui_action"] = "maximize"
                                else:
                                    decision["ui_action"] = "show_widget"
                                    decision["target"] = "telemetry"
                                break

                    clean_text = re.sub(r"\[(?:Tools?|Executed\s+Tools?|Tools?\s*Executed):.*?\]\s*", "", clean_text, flags=re.IGNORECASE).strip()
                    if not clean_text:
                        clean_text = "Operations completed, sir."
                    self.conversation_history.append({"role": "assistant", "content": clean_text})
                    decision["spoken_response"] = clean_text
                
                decision["spoken_response"] = re.sub(r"\[(?:Tools?|Executed\s+Tools?|Tools?\s*Executed):.*?\]\s*", "", decision["spoken_response"], flags=re.IGNORECASE).strip()
                decision["spoken_response"] = decision["spoken_response"].replace("*", "").replace("#", "")
                return decision
                
            except (groq.BadRequestError, openai.BadRequestError) as e:
                if "tool_use_failed" in str(e) or "400" in str(e):
                    print("[Shield System] XML parsing fault intercepted. Forcing safe text fallback...")
                    fallback_msgs = [m for m in self.conversation_history if m.get("role") in ("user", "assistant")][:-1] + [
                        {"role": "system", "content": "CRITICAL OVERRIDE: Tool server offline. Answer the user's request directly in plain text only."},
                        {"role": "user", "content": user_input}
                    ]
                    safe_res = current_client.chat.completions.create(model=current_model, messages=fallback_msgs, temperature=0.3)
                    txt = safe_res.choices[0].message.content or "System hiccup intercepted. Standing by."
                    clean_fallback = re.sub(r"\[(?:Tools?|Executed\s+Tools?|Tools?\s*Executed):.*?\]\s*", "", txt, flags=re.IGNORECASE).strip().replace("*", "").replace("#", "")
                    self.conversation_history.append({"role": "assistant", "content": clean_fallback})
                    return {"spoken_response": clean_fallback, "ui_action": "none", "target": ""}
                raise e
                
            except Exception as e:
                provider_name = provider.get("name", "Unknown") if "provider" in locals() else "Unknown"
                print(f"[Brain Provider Error - {provider_name}]: {e}")
                
                if ("429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)) and "provider" in locals() and isinstance(provider, dict):
                    # Arm circuit breaker cooldown for 1 hour to prevent subsequent 15-second hangs
                    provider["cooldown_until"] = time.time() + 3600
                    print(f"[Brain Circuit Breaker]: {provider_name} placed on cooldown for 3600s.")
                
                if attempt < attempts_count - 1:
                    continue
                
                if "429" in str(e):
                    print("[Brain Error]: Rate Limit Exceeded.")
                    if self.conversation_history and self.conversation_history[-1]["role"] == "user":
                        self.conversation_history.pop()
                    return {"spoken_response": "Cognitive bandwidth saturated. Awaiting network cooldown.", "ui_action": "none"}
                    
                print(f"[Brain Error]: All retries exhausted. Final error: {e}")
                if self.conversation_history and self.conversation_history[-1]["role"] == "user":
                    self.conversation_history.pop()

                # Defensive local router fallback before returning generic failure
                try:
                    from core.router import JarvisRouter
                    fallback_router = JarvisRouter()
                    fast_res = fallback_router.route(user_input)
                    if fast_res.get("intercepted"):
                        return fast_res
                except Exception:
                    pass

                return {"spoken_response": "Sub-processor timing fault.", "ui_action": "none"}

    def analyze_image(self, base64_image, prompt):
        """Passes the screen feed to high-resolution vision model (Gemini with OpenRouter fallback)."""
        if self.gemini_client:
            for gemini_model in ['gemini-3.5-flash-lite', 'gemini-flash-latest', 'gemini-2.5-flash']:
                try:
                    image_bytes = base64.b64decode(base64_image)
                    image = Image.open(io.BytesIO(image_bytes))
                    response = self.gemini_client.models.generate_content(
                        model=gemini_model,
                        contents=[image, prompt]
                    )
                    if response and response.text:
                        return {"spoken_response": response.text.strip()}
                except Exception as e:
                    print(f"[Optic Nerve Gemini {gemini_model} Error]: {e}")

        if not self.vision_client:
            return {"spoken_response": "Optical array is offline. Missing vision API key."}
            
        try:
            response = self.vision_client.chat.completions.create(
                model="nvidia/nemotron-3.5-super-vl:free",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]
                    }
                ]
            )
            return {"spoken_response": response.choices[0].message.content.strip()}
        except Exception as e:
            print(f"[Optic Nerve Error]: {e}")
            return {"spoken_response": "My optical decoder failed to process the image."}

    def find_coordinates(self, base64_image, target):
        """Uses spatial reasoning to find exact X/Y UI coordinates."""
        spatial_prompt = (
            f"Find the UI element or text matching: '{target}'. "
            "The image resolution is exactly 1920x1080. "
            "Return ONLY a valid JSON object with the exact center X and Y pixel coordinates of this target. "
            'Example format: {"x": 450, "y": 820}. '
            'If the target is not visible, return {"error": "not found"}'
        )

        if self.gemini_client:
            for gemini_model in ['gemini-3.5-flash-lite', 'gemini-flash-latest', 'gemini-2.5-flash']:
                try:
                    image_bytes = base64.b64decode(base64_image)
                    image = Image.open(io.BytesIO(image_bytes))
                    response = self.gemini_client.models.generate_content(
                        model=gemini_model,
                        contents=[image, spatial_prompt]
                    )
                    raw_text = response.text.strip() if response and response.text else ""
                    match = re.search(r'\{[\s\S]*?\}', raw_text)
                    if match:
                        coords = json.loads(match.group(0))
                        if isinstance(coords, dict) and "error" not in coords and "x" in coords and "y" in coords:
                            return coords
                except Exception as e:
                    print(f"[Optic Nerve Gemini Spatial {gemini_model} Error]: {e}")

        if not self.vision_client:
            return None
            
        try:
            response = self.vision_client.chat.completions.create(
                model="nvidia/nemotron-3.5-super-vl:free",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": spatial_prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]
                    }
                ]
            )
            
            raw_text = response.choices[0].message.content.strip()
            match = re.search(r'\{[\s\S]*?\}', raw_text)
            if not match:
                print(f"[Optic Nerve Error]: Model returned no JSON format. Raw output: {raw_text}")
                return None
                
            clean_json_str = match.group(0)
            coords = json.loads(clean_json_str)
            if not isinstance(coords, dict) or "error" in coords:
                return None
            return coords
            
        except Exception as e:
            print(f"[Optic Nerve Error - Spatial]: {e}")
            return None