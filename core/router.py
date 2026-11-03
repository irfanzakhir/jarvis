from services.intel_hub import IntelHub
"""
J.A.R.V.I.S. 2.0 - Fast Intent Hot-Path Router
Inspired by Friday Mark 2's smart_router architecture.
Zero-cost, sub-10ms deterministic pattern matching for common queries,
system controls, temporal anchors, and screen reading triggers.
"""

import re
import datetime

class JarvisRouter:
    def __init__(self):
        # Pre-compile regex matchers for microsecond routing
        self._greetings = re.compile(
            r"^(?:hi|hello|hey|greetings|good\s+morning|good\s+afternoon|good\s+evening|wake\s+up|yo)(?:\s+(?:jarvis|sir|there|buddy|man))?$",
            re.IGNORECASE
        )
        self._identity = re.compile(
            r"^(who are you|what are you|what is your name|introduce yourself)\b",
            re.IGNORECASE
        )
        self._status = re.compile(
            r"^(status|system status|system report|diagnostics|are you online|are you there|ping)\b",
            re.IGNORECASE
        )
        self._time = re.compile(
            r"\b(what time is it|what's the time|tell me the time|current time|the time please)\b",
            re.IGNORECASE
        )
        self._date = re.compile(
            r"\b(what('s| is) the date|what is today's date|what date is it|what day is (it|today))\b",
            re.IGNORECASE
        )
        self._volume_up = re.compile(
            r"\b(volume up|increase volume|turn up the volume|louder|boost volume)\b",
            re.IGNORECASE
        )
        self._volume_down = re.compile(
            r"\b(volume down|decrease volume|turn down the volume|lower volume|quieter)\b",
            re.IGNORECASE
        )
        self._mute = re.compile(
            r"\b(mute|mute audio|silence audio|mute system|unmute|unmute audio)\b",
            re.IGNORECASE
        )
        self._screenshot = re.compile(
            r"\b(take a screenshot|capture screen|take screenshot|save screenshot)\b",
            re.IGNORECASE
        )
        self._sleep = re.compile(
            r"\b(sleep pc|put pc to sleep|hibernate pc|suspend system)\b",
            re.IGNORECASE
        )
        self._combat_on = re.compile(
            r"\b(combat mode on|engage combat mode|protocol omega|activate combat mode|enable combat mode|start combat mode|turn on combat mode|switch to combat mode|enter combat mode|combat mode)\b",
            re.IGNORECASE
        )
        self._combat_off = re.compile(
            r"\b(combat mode off|disengage combat mode|stand down|standard mode|combat off|disable combat mode|deactivate combat mode|stop combat mode|turn off combat mode|exit combat mode|leave combat mode)\b",
            re.IGNORECASE
        )
        self._minimize_dashboard = re.compile(
            r"\b(?:jarvis\s+|girls\s+)?(?:minimi[zs](?:e|ing|ed)?|hide|close|dismiss|collapse|dock)\s+(?:the\s+)?(?:dashboard|hud|mainframe|ui|window|interface|display)(?!\s+widgets?)(?:\s+(?:command|please|now|jarvis))?\b|"
            r"\b(?:jarvis\s+|girls\s+)?(?:minimi[zs](?:e|ing|ed)?\s+to\s+orb|minimi[zs](?:e|ing|ed)?\s+window|minimi[zs](?:e|ing|ed)?)(?:\s+(?:command|please|now|jarvis))?\b|"
            r"\b(?:jarvis\s+|girls\s+)?(?:standby|stand\s*by|enter\s+standby|go\s+to\s+standby)(?:\s+(?:command|please|now|jarvis))?\b",
            re.IGNORECASE
        )
        self._restore_dashboard = re.compile(
            r"\b(?:jarvis\s+|girls\s+)?(?:restore|maximi[zs](?:e|ing|ed)?|show|open|reveal|expand|bring\s+up|display|unhide|activate)\s+(?:the\s+)?(?:dashboard|hud|mainframe|ui|window|interface|display)(?!\s+widgets?)(?:\s+(?:command|please|now|jarvis))?\b|"
            r"\b(?:jarvis\s+|girls\s+)?(?:restore\s+from\s+orb|restore\s+window|restore\s+ui|restore|maximi[zs](?:e|ing|ed)?\s+window|maximi[zs](?:e|ing|ed)?|wake\s+up(?:\s+jarvis)?|wake\s+jarvis)(?:\s+(?:command|please|now|jarvis))?\b",
            re.IGNORECASE
        )
        self._watchdog_on = re.compile(
            r"\b(?:activate|enable|arm|start|turn on|engage)?\s*(?:watch\s*dog|watchdog)\b(?:\s+(?:and\s+)?(?:look for|watch for|monitor for|find|detect|for)\s+(?:a\s+|an\s+)?(?P<target>[\w\s]+?))?(?:\s+please)?$|\b(?:watch for|monitor for)\s+(?:a\s+|an\s+)?(?P<target2>[\w\s]+?)(?:\s+please)?$|\b(?:monitor|watch)\s+(?:the\s+)?room\b",
            re.IGNORECASE
        )
        self._watchdog_off = re.compile(
            r"\b(?:disable|deactivate|disarm|stop|turn off)\s+(?:the\s+)?(?:watch\s*dog|watchdog)\b|\b(?:watch\s*dog|watchdog)\s+(?:off|disarm|stop)\b|\bstand down\s+(?:the\s+)?(?:watch\s*dog|watchdog)\b",
            re.IGNORECASE
        )
        self._antigravity = re.compile(
            r"\b(antigravity mode on|enable antigravity|activate antigravity|quantum mode on|engage antigravity)\b|^(?:jarvis\s+)?antigravity(?:\s+mode)?$|^(?:jarvis\s+)?quantum\s+mode$",
            re.IGNORECASE
        )
        self._antigravity_off = re.compile(
            r"\b(antigravity mode off|disable antigravity|deactivate antigravity|antigravity off|quantum mode off|disengage antigravity)\b",
            re.IGNORECASE
        )

        self._kinetic_on = re.compile(
            r"\b(enable kinetic|kinetic mode on|activate kinetic|engage kinetic)\b",
            re.IGNORECASE
        )
        self._kinetic_off = re.compile(
            r"\b(disable kinetic|kinetic mode off|deactivate kinetic|disengage kinetic)\b",
            re.IGNORECASE
        )
        self._recenter_reactor = re.compile(
            r"\b(?:re-?center\s+(?:the\s+)?(?:arc\s+)?reactor|reactor\s+to\s+center|center\s+(?:the\s+)?(?:arc\s+)?reactor|reset\s+(?:the\s+)?(?:arc\s+)?reactor|dock\s+center)\b",
            re.IGNORECASE
        )
        self._clear_screen = re.compile(
            r"\b(?:jarvis\s+)?(?:hide|close|dismiss|collapse|shut|clear|remove)\s+(?:all\s+(?:the\s+)?(?:mainframe\s+|hud\s+|dashboard\s+)?widgets?|all\s+the\s+hud\s+widgets?|all\s+hud\s+widgets?|all\s+components?|every\s+widget|everything|the\s+grid|the\s+screen|the\s+display)(?:\s+(?:command|please|now))?\b|"
            r"\b(?:clear\s+(?:the\s+)?(?:screen|display|hud|grid))(?:\s+(?:command|please|now))?\b",
            re.IGNORECASE
        )

        # Unified widget identifiers group
        _WIDGET_RE = (
            r"(?P<widget>"
            r"optical(?:\s*(?:guard|array|feed|sensors?|camera|vision|display))?|"
            r"cameras?(?:\s*(?:feed|guard|array|view|sensor))?|"
            r"webcams?(?:\s*(?:feed|view|sensor))?|"
            r"video\s*feed|"
            r"vision(?:\s*(?:guard|array|feed|sensors?|camera|display))?|"
            r"(?:system\s+|hardware\s+)?telemetry|"
            r"(?:system\s+|hardware\s+)?vitals?(?:\s*stats?)?|"
            r"(?:system\s+|hardware\s+)?stats?|"
            r"hardware(?:\s*(?:telemetry|vitals|stats|info))?|"
            r"cpu(?:\s*(?:load|usage|stats|telemetry))?|"
            r"ram(?:\s*(?:load|usage|stats|telemetry))?|"
            r"performance(?:\s*telemetry)?|"
            r"(?:system\s+)?(?:neural\s+)?(?:activity\s+)?logs?|"
            r"activity\s*logs?|neural\s*logs?|system\s*logs?|console(?:\s*logs?)?|terminal\s*logs?|"
            r"manual\s*override(?:\s*uplink)?|"
            r"command(?:\s*uplink|\s*widget|\s*input|\s*line|\s*prompt)?|"
            r"override(?:\s*uplink)?|uplink|terminal(?:\s*input)?|manual\s*input|inputs?|"
            r"sys(?:\.|\s*)admin|sysadmin|admin(?:istrator)?|user(?:\s*credentials)?|credentials|"
            r"security(?:\s*center)?(?:\s*shield)?|shield|firewall(?:\s*shield)?|protection(?:\s*shield)?|antivirus|"
            r"network(?:\s*hub)?|wifi(?:\s*(?:widget|hub|network))?|bandwidth(?:\s*hub)?|internet(?:\s*hub)?|connection(?:\s*hub)?|"
            r"diagnostics?(?:\s*(?:sys|system))?|system\s*diagnostics?|(?:kernel\s+|system\s+)?integrity|"
            r"antigravity(?:\s*(?:core|cognitive\s*core|widget|agent))?|quantum(?:\s*(?:core|cognitive\s*core))?|cognitive\s*core|autonomous\s*agent|agent(?:\s*core)?|"
            r"calendar(?:\s*(?:widget|events?|matrix))?|events?(?:\s*(?:widget|calendar|matrix|monitor))?|schedule(?:\s*(?:widget|calendar|matrix))?|"
            r"weather(?:\s*(?:widget|radar|telemetry|forecast))?|atmospheric(?:\s*(?:radar|telemetry|weather))?|forecast(?:\s*radar)?|meteo(?:\s*radar)?|radar|"
            r"news(?:\s*(?:widget|room|intel|feed))?|situation(?:\s*room)?|headlines?|world\s*intel|intel(?:\s*room)?|"
            r"maps?(?:\s*(?:widget|recon|grid|intel))?|tactical\s*maps?|satellite(?:\s*(?:recon|grid|map))?|recon(?:\s*map)?|"
            r"audio(?:\s*(?:spectrum|core|widget|equalizer))?|spectrum(?:\s*(?:analyzer|widget))?|vocal(?:\s*core)?|microphone(?:\s*input)?|mic(?:\s*input)?|sound(?:\s*core)?|equalizer|"
            r"memory(?:\s*(?:vault|widget|matrix|core))?|vault(?:\s*(?:memory|core))?|profile(?:\s*(?:memory|vault))?|cognitive\s*memory|facts(?:\s*vault)?|"
            r"hardware(?:\s*(?:health|matrix|widget|telemetry))?|thermal(?:\s*(?:matrix|status))?|gpu(?:\s*(?:load|matrix|telemetry))?|sensors(?:\s*matrix)?|"
            r"(?:(?:all\s+(?:the\s+)?)?(?:mainframe\s+|hud\s+|dashboard\s+)?)?widgets?|all\s+components?|every\s*widget|everything|grid"
            r")"
        )

        self._show_widget = re.compile(
            rf"\b(?:jarvis\s+)?(?:show|open|reveal|display|expand|bring\s+up|view|launch|enable|unhide|dock)\s+(?:the\s+|my\s+)?(?:widget\s+|hud\s+)?{_WIDGET_RE}\b(?:\s+(?:widget|hud|window|display|component|feed|array|hub|core|system|panel|matrix))?(?:\s+(?:command|please|now))?",
            re.IGNORECASE
        )
        self._hide_widget = re.compile(
            rf"\b(?:jarvis\s+)?(?:hide|close|dismiss|collapse|shut|disable|remove|deactivate)\s+(?:the\s+|my\s+)?(?:widget\s+|hud\s+)?{_WIDGET_RE}\b(?:\s+(?:widget|hud|window|display|component|feed|array|hub|core|system|panel|matrix))?(?:\s+(?:command|please|now))?",
            re.IGNORECASE
        )
        self._screen_read = re.compile(
            r"\b(?:read|describe|analyze|summarize|check|scan|look at)\s+(?:the\s+|my\s+|this\s+|active\s+)?(?:screen|display|monitor)\b|\bwhat(?:'?s|\s+is)\s+on\s+(?:the\s+|my\s+|this\s+)?(?:screen|display|monitor)\b|\bwhat\s+am\s+i\s+looking\s+at\b|\bread\s+active\s+window\b",
            re.IGNORECASE
        )
        self._close_window = re.compile(
            r"\b(close window|close this window|close current window|terminate window)\b",
            re.IGNORECASE
        )
        self._switch_window = re.compile(
            r"\b(?:switch\s+(?:the\s+)?(?:active\s+)?(?:tabs?|windows?|apps?)|switch\s+to\s+(?:the\s+)?next\s+(?:tab|window|app)|swap\s+(?:tabs?|windows?)|next\s+(?:tab|window|app)|cycle\s+(?:tabs?|windows?|apps?)|alt\s*tab)\b",
            re.IGNORECASE
        )
        self._whatsapp_msg = re.compile(
            r'''(?:(?:can\s+you\s+)?(?:use\s+antigravity\s+to\s+)?(?:open\s+whatsapp\s+(?:and\s+|to\s+))?(?:send|message|text)\s+['\"]?(?P<msg>[^'\"]+?)['\"]?\s+to\s+(?P<contact>[a-zA-Z0-9_\s]+?)(?:\s+(?:on\s+whatsapp|via\s+whatsapp|in\s+whatsapp|please))?$)|'''
            r'''(?:(?:can\s+you\s+)?(?:use\s+antigravity\s+to\s+)?(?:open\s+whatsapp\s+(?:and\s+|to\s+))(?:message|text|send)\s+(?P<contact2>[a-zA-Z0-9_\s]+?)\s+['\"]?(?P<msg2>[^'\"]+?)['\"]?(?:\s+(?:on\s+whatsapp|via\s+whatsapp|in\s+whatsapp|please))?$)''',
            re.IGNORECASE
        )
        self._device_settings = re.compile(
            r"\b(?:(?:open|launch|show|view|check)\s+)?(?:device\s+|windows\s+|system\s+)?(?:notification\s+settings|notifications|device\s+settings|sound\s+settings|bluetooth\s+settings|display\s+settings|network\s+settings)\b",
            re.IGNORECASE
        )
        # Advanced Intelligence Intel Hub Hot-Paths (<1ms)
        self._map_route = re.compile(
            r"\b(?:navigate to|directions? to|route to)\s+(.+)",
            re.IGNORECASE
        )
        self._map_poi = re.compile(
            r"\b(?:find|show|locate)\s+(?:the\s+)?(?:nearest\s+)?(hospitals?|restaurants?|petrol\s+pumps?|fuel|gas\s+stations?|atms?|banks?|police\s+stations?|airports?|pharmacy|pharmacies)(?:\s+(?:near\s+me|nearby))?\b",
            re.IGNORECASE
        )
        self._weather_rain = re.compile(
            r"\b(?:will it rain|chance of rain|is it going to rain)(?:\s+(?:today|this evening|tonight|tomorrow))?\b",
            re.IGNORECASE
        )
        self._weather_general = re.compile(
            r"\b(?:what(?:'s|\s+is)\s+the\s+weather|how(?:'s|\s+is)\s+the\s+weather)(?:\s+(?:today|tomorrow|in\s+([a-zA-Z\s]+)))?\b",
            re.IGNORECASE
        )
        self._news_query = re.compile(
            r"\b(?:(?:can\s+you\s+)?(?:tell\s+me|get|fetch|give\s+me|check|show|display|read)\s+)?(?:the\s+)?(?:latest\s+|top\s+|live\s+)?news\s+(?:in|across|from|for|about|on|regarding)\s+(.+?)(?:\s+please)?$",
            re.IGNORECASE
        )
        self._news_topic_named = re.compile(
            r"\b(?:what(?:'s|\s+is)\s+(?:the\s+)?(?:latest\s+)?happening in\s+(.+?)(?:\s+please)?$|(?:what(?:'s|\s+is)\s+the\s+)?latest\s+([a-zA-Z0-9_\s]+)\s+(?:news|headlines)|([a-zA-Z0-9_\s]+)\s+(?:news|headlines)|(?:the\s+)?headlines\s+(?:for|in|across|about|on)\s+(.+?)(?:\s+please)?$)\b",
            re.IGNORECASE
        )
        self._check_calendar = re.compile(
            r"\b(?:(?:is|are)\s+(?:my\s+)?(?:google\s+)?calendars?\s+sync(?:hroni[zs]ed|ed)?|check\s+(?:my\s+|the\s+|google\s+)?(?:calendar|schedule)|check\s+(?:for\s+)?(?:any\s+)?scheduled\s+meetings?|upcoming\s+meetings?|calendar\s+sync(?:hroni[zs]ed|ed)?|(?:what|do\s+i\s+have\s+any)\s+(?:scheduled\s+)?meetings?)\b",
            re.IGNORECASE
        )
        self._open_app = re.compile(
            r"^(open|launch|start)\s+(notepad|calculator|calc|chrome|brave|spotify|file explorer|explorer|cmd|terminal(?!\s+(?:input|log|logs|prompt))|command prompt|settings)\b",
            re.IGNORECASE
        )
        self._open_folder = re.compile(
            r"^(?:open|launch|explore|show)\s+(?:the\s+)?(?:folder\s+|directory\s+)?([a-zA-Z]:[\\/][^\s]+|jarvis\s*(?:2\.?0?|folder|project|directory)?|project\s*(?:folder|directory)?|workspace)\b",
            re.IGNORECASE
        )
        self._enable_mobile = re.compile(
            r"\b(enable|start|activate|turn on|launch|open|connect)\s+(mobile|phone|android)\s*(connection|link|uplink|bridge|api)?\b|\b(mobile\s*(connection|link|uplink)\s*(on|enable|start|activate))\b",
            re.IGNORECASE
        )
        self._disable_mobile = re.compile(
            r"\b(disable|stop|deactivate|turn off|close|kill|disconnect)\s+(mobile|phone|android)\s*(connection|link|uplink|bridge|api)?\b|\b(mobile\s*(connection|link|uplink)\s*(off|disable|stop|deactivate))\b",
            re.IGNORECASE
        )
        # Clarify Auto-Escalation Gate (Friday Mark 2 architecture)
        self._clarify_strikes = 0
        self._ambiguous_queries = re.compile(
            r"^(fix it|do that|open it|start it again|try again|what about that|help me with that|do something|run it)\b",
            re.IGNORECASE
        )
        try:
            from core.event_engine import EventEngine
            self.event_engine = EventEngine()
        except Exception:
            self.event_engine = None

    def _map_widget_target(self, raw_str: str) -> str:
        s = raw_str.lower().strip()
        words = set(s.split())
        if "all" in words or "widgets" in words or "every" in words or any(w in s for w in ["everything", "grid", "components"]):
            return "all"
        if any(w in s for w in ["optical", "guard", "camera", "webcam", "array", "feed", "vision"]):
            return "optical"
        if any(w in s for w in ["hardware", "thermal", "gpu", "sensors"]):
            return "hardware"
        if any(w in s for w in ["telemetry", "vital", "cpu", "ram", "performance", "stat"]):
            return "telemetry"
        if any(w in s for w in ["log", "neural", "activity", "console"]):
            return "log"
        if any(w in s for w in ["command", "override", "uplink", "input", "prompt"]):
            return "command"
        if any(w in s for w in ["admin", "credentials", "user", "sysadmin"]):
            return "admin"
        if any(w in s for w in ["security", "shield", "firewall", "protection", "antivirus"]):
            return "security"
        if any(w in s for w in ["network", "wifi", "bandwidth", "hub", "internet", "connection"]):
            return "network"
        if any(w in s for w in ["diagnostic", "integrity", "kernel"]):
            return "diagnostics"
        if any(w in s for w in ["antigravity", "quantum", "cognitive", "agent"]):
            return "antigravity"
        if any(w in s for w in ["calendar", "event", "schedule"]):
            return "events"
        if any(w in s for w in ["weather", "meteo", "forecast", "radar", "atmospheric"]):
            return "weather"
        if any(w in s for w in ["news", "situation", "headline", "intel"]):
            return "news"
        if any(w in s for w in ["map", "tactical", "satellite", "recon"]):
            return "map"
        if any(w in s for w in ["audio", "spectrum", "vocal", "microphone", "sound", "equalizer", "mic"]):
            return "audio"
        if any(w in s for w in ["memory", "vault", "profile", "facts", "recall"]):
            return "memory"
        if any(w in s for w in ["hardware", "thermal", "gpu", "sensors"]):
            return "hardware"
        return s

    def route(self, user_input: str) -> dict:
        """
        Fast intent check. Returns a decision dict if intercepted,
        or {'intercepted': False} if the query requires full LLM cognition.
        Execution time: < 5ms.
        """
        if not user_input or not isinstance(user_input, str):
            return {"intercepted": False}

        text = user_input.strip()
        cleaned = re.sub(r"[^\w\s']", "", text).strip().lower()

        # Handle optional conversational prefixes iteratively (e.g. "hey bruh", "yo jarvis", "please", etc.)
        prefix_pattern = re.compile(
            r"^(?:hey\s+(?:jarvis|bruh|bro|buddy|there|man)|hello\s+(?:jarvis)?|hi\s+(?:jarvis)?|yo\s+(?:jarvis|bruh|bro)?|jarvis|bruh|bro|buddy|please|can\s+you\s+(?:please\s+)?|could\s+you\s+(?:please\s+)?|would\s+you\s+(?:please\s+)?)\b\s*",
            re.IGNORECASE
        )
        curr_eval = cleaned
        while True:
            stripped = prefix_pattern.sub("", curr_eval).strip()
            if stripped == curr_eval or not stripped:
                break
            curr_eval = stripped
        eval_text = curr_eval

        # 1. Temporal: Clock & Date
        if self._time.search(cleaned):
            now = datetime.datetime.now()
            time_str = now.strftime("%I:%M %p")
            return {
                "intercepted": True,
                "spoken_response": f"The current time is {time_str}, sir.",
                "ui_action": "none",
                "target": ""
            }

        if self._date.search(cleaned):
            now = datetime.datetime.now()
            date_str = now.strftime("%A, %B %d, %Y")
            return {
                "intercepted": True,
                "spoken_response": f"Today is {date_str}, sir.",
                "ui_action": "none",
                "target": ""
            }

        # 2. Perception: Live Screen Reading Trigger
        if self._screen_read.search(cleaned):
            return {
                "intercepted": True,
                "spoken_response": "Scanning active display telemetry now, sir.",
                "ui_action": "read_screen",
                "target": text
            }

        # 3. Audio & Hardware Volume
        if self._volume_up.search(cleaned):
            return {
                "intercepted": True,
                "spoken_response": "Increasing audio gain, sir.",
                "ui_action": "vol_up",
                "target": ""
            }

        if self._volume_down.search(cleaned):
            return {
                "intercepted": True,
                "spoken_response": "Decreasing audio gain, sir.",
                "ui_action": "vol_down",
                "target": ""
            }

        if self._mute.search(cleaned):
            return {
                "intercepted": True,
                "spoken_response": "Toggling system mute state.",
                "ui_action": "mute",
                "target": ""
            }

        # 4. OS Hardware Actions
        if self._screenshot.search(cleaned):
            return {
                "intercepted": True,
                "spoken_response": "Screen state captured and archived, sir.",
                "ui_action": "screenshot",
                "target": ""
            }

        if self._sleep.search(cleaned):
            return {
                "intercepted": True,
                "spoken_response": "Suspending system hardware. Good night, sir.",
                "ui_action": "sleep",
                "target": ""
            }

        if self._close_window.search(cleaned):
            return {
                "intercepted": True,
                "spoken_response": "Terminating active window, sir.",
                "ui_action": "close_current",
                "target": ""
            }

        # Tab / Window Switching Hot-Path (<1ms)
        if self._switch_window.search(cleaned) or self._switch_window.search(eval_text):
            return {
                "intercepted": True,
                "spoken_response": "Switching active window, sir.",
                "ui_action": "switch_app",
                "target": ""
            }

        # Advanced Intelligence Modules Fast-Path Routing (<1ms)
        map_route_m = self._map_route.search(cleaned) or self._map_route.search(eval_text)
        if map_route_m:
            dest = map_route_m.group(1).strip()
            res = IntelHub().execute_map_query(f"navigate to {dest}")
            return {
                "intercepted": True,
                "spoken_response": res.get("spoken", f"Navigating to {dest}, sir."),
                "ui_action": "show_widget",
                "target": "map"
            }

        map_poi_m = self._map_poi.search(cleaned) or self._map_poi.search(eval_text)
        if map_poi_m:
            poi_cat = map_poi_m.group(1).strip()
            res = IntelHub().execute_map_query(f"find {poi_cat} near me")
            return {
                "intercepted": True,
                "spoken_response": res.get("spoken", f"Scanning sector for nearby {poi_cat}, sir."),
                "ui_action": "show_widget",
                "target": "map"
            }



        # Regional & Topic News Intelligence Hot-Path (<1ms)
        news_topic = None
        nq_m = self._news_query.search(eval_text) or self._news_query.search(cleaned)
        if nq_m:
            candidate = nq_m.group(1).strip()
            if candidate.lower() not in ("widget", "intel", "component", "room"):
                news_topic = candidate
        else:
            nt_m = self._news_topic_named.search(eval_text) or self._news_topic_named.search(cleaned)
            if nt_m:
                candidate = (nt_m.group(1) or nt_m.group(2) or nt_m.group(3) or (nt_m.group(4) if len(nt_m.groups()) >= 4 else None) or "").strip()
                cand_lower = candidate.lower()
                cmd_verbs = {"open", "show", "launch", "reveal", "hide", "close", "dismiss", "widget", "intel", "component", "the"}
                if cand_lower not in cmd_verbs:
                    if not any(eval_text.lower().startswith(v) and any(w in eval_text.lower() for w in ["news", "headline"]) for v in ["open news", "show news", "hide news", "close news", "dismiss news"]):
                        news_topic = candidate

        if news_topic:
            news_topic = re.sub(r"\s+please$", "", news_topic, flags=re.IGNORECASE).strip("?.,! ")
            if news_topic.lower() == "ai":
                news_topic = "AI"
            elif len(news_topic) > 2 and not news_topic.isupper():
                news_topic = news_topic.title()
            res = IntelHub().execute_news_query(news_topic, auto_speak=False, sync=True)
            spoken = res.get("spoken", f"Fetching latest news regarding {news_topic}, sir.")
            return {
                "intercepted": True,
                "spoken_response": spoken,
                "ui_action": "show_widget",
                "target": "news",
                "news_query": news_topic
            }

        # Google Calendar Synchronization & Meetings Hot-Path (<1ms)
        if self._check_calendar.search(cleaned) or self._check_calendar.search(eval_text):
            return {
                "intercepted": True,
                "spoken_response": "Querying Google Calendar synchronization and upcoming meetings, sir.",
                "ui_action": "check_calendar",
                "target": ""
            }

                # Direct WhatsApp Messaging Fast-Path (<1ms)
        wa_match = self._whatsapp_msg.search(cleaned) or self._whatsapp_msg.search(eval_text)
        if wa_match:
            contact = (wa_match.group("contact") or wa_match.group("contact2") or "").strip().title()
            msg = (wa_match.group("msg") or wa_match.group("msg2") or "").strip()
            if contact and msg:
                return {
                    "intercepted": True,
                    "spoken_response": f"Opening WhatsApp and dispatching '{msg}' to {contact}, sir.",
                    "ui_action": "whatsapp_message",
                    "target": {"contact": contact, "message": msg}
                }

        # Direct Windows Settings & Notification Routing (<1ms)
        settings_match = self._device_settings.search(cleaned) or self._device_settings.search(eval_text)
        if settings_match:
            matched_phrase = settings_match.group(0).lower()
            if "notification" in matched_phrase:
                target_uri = "ms-settings:notifications"
                spoken = "Opening notification settings, sir."
            elif "sound" in matched_phrase:
                target_uri = "ms-settings:sound"
                spoken = "Opening sound settings, sir."
            elif "bluetooth" in matched_phrase:
                target_uri = "ms-settings:bluetooth"
                spoken = "Opening bluetooth settings, sir."
            elif "display" in matched_phrase:
                target_uri = "ms-settings:display"
                spoken = "Opening display settings, sir."
            elif "network" in matched_phrase:
                target_uri = "ms-settings:network"
                spoken = "Opening network settings, sir."
            else:
                target_uri = "ms-settings:"
                spoken = "Opening device settings, sir."
            return {
                "intercepted": True,
                "spoken_response": spoken,
                "ui_action": "open_app",
                "target": target_uri
            }

        # 5. Fast App & Directory Shortcuts
        folder_match = self._open_folder.match(text) or self._open_folder.match(eval_text)
        if folder_match:
            folder_target = folder_match.group(1).strip()
            return {
                "intercepted": True,
                "spoken_response": "Opening directory in Windows Explorer, sir.",
                "ui_action": "open_app",
                "target": folder_target
            }

        app_match = self._open_app.match(cleaned) or self._open_app.match(eval_text)
        if app_match:
            app_target = app_match.group(2).strip()
            return {
                "intercepted": True,
                "spoken_response": f"Launching {app_target.capitalize()}, sir.",
                "ui_action": "open_app",
                "target": app_target
            }

        # Mobile Uplink Server (api.py)
        if self._enable_mobile.search(cleaned):
            return {
                "intercepted": True,
                "spoken_response": "Establishing mobile uplink. Launching API server on port 8000, sir.",
                "ui_action": "enable_mobile",
                "target": ""
            }

        if self._disable_mobile.search(cleaned):
            return {
                "intercepted": True,
                "spoken_response": "Severing mobile uplink. Terminating API server, sir.",
                "ui_action": "disable_mobile",
                "target": ""
            }

        # 6. Optical Watchdog Protocols
        if self._watchdog_off.search(cleaned):
            return {
                "intercepted": True,
                "spoken_response": "Optical watchdog disarmed. Sensors returned to idle, sir.",
                "ui_action": "deactivate_watchdog",
                "target": ""
            }

        watchdog_match = self._watchdog_on.search(cleaned)
        if watchdog_match:
            target = "person"
            try:
                grp = watchdog_match.group("target") or watchdog_match.group("target2")
                if grp and grp.strip():
                    target = grp.strip()
            except Exception:
                pass
            return {
                "intercepted": True,
                "spoken_response": f"Optical watchdog armed. Monitoring for {target}, sir.",
                "ui_action": "activate_watchdog",
                "target": target
            }

        # 7. HUD / Theme Protocols
        if self._combat_off.search(cleaned):
            return {
                "intercepted": True,
                "spoken_response": "Disengaging Protocol Omega. Returning to standard operations.",
                "ui_action": "combat_off",
                "target": ""
            }

        if self._combat_on.search(cleaned):
            return {
                "intercepted": True,
                "spoken_response": "Protocol Omega initiated. Combat telemetry online.",
                "ui_action": "combat_on",
                "target": ""
            }

        min_match = self._minimize_dashboard.search(cleaned) or self._minimize_dashboard.search(eval_text)
        if min_match:
            is_standby = any(w in cleaned or w in eval_text for w in ["standby", "stand by"])
            spoken = "Standing by. Optical sensors armed, sir." if is_standby else "Minimizing dashboard to compact floating orb, sir."
            action = "standby" if is_standby else "minimize"
            return {
                "intercepted": True,
                "spoken_response": spoken,
                "ui_action": action,
                "target": ""
            }

        res_match = self._restore_dashboard.search(cleaned) or self._restore_dashboard.search(eval_text)
        if res_match:
            return {
                "intercepted": True,
                "spoken_response": "Restoring full HUD display interface, sir.",
                "ui_action": "maximize",
                "target": ""
            }

        # Holographic Reactor & Widget Grid Protocols (<5ms)
        if self._recenter_reactor.search(cleaned) or self._recenter_reactor.search(eval_text):
            return {
                "intercepted": True,
                "spoken_response": "Re-centering Arc Reactor core, sir.",
                "ui_action": "recenter_reactor",
                "target": ""
            }

        if self._antigravity_off.search(cleaned) or self._antigravity_off.search(eval_text):
            return {
                "intercepted": True,
                "spoken_response": "Disengaging quantum cognitive core. Returning to standard operations.",
                "ui_action": "antigravity_off",
                "target": ""
            }

        if self._antigravity.search(cleaned) or self._antigravity.search(eval_text):
            return {
                "intercepted": True,
                "spoken_response": "Antigravity cognitive core engaged. Quantum state active.",
                "ui_action": "antigravity_mode",
                "target": ""
            }

        hide_match = self._hide_widget.search(cleaned) or self._hide_widget.search(eval_text)
        if hide_match:
            raw_w = hide_match.group("widget") or ""
            target = self._map_widget_target(raw_w)
            spoken = "Clearing HUD display. All widgets dismissed, sir." if target == "all" else f"Dismissing {target} component, sir."
            return {
                "intercepted": True,
                "spoken_response": spoken,
                "ui_action": "hide_widget",
                "target": target
            }

        show_match = self._show_widget.search(cleaned) or self._show_widget.search(eval_text)
        if show_match:
            raw_w = show_match.group("widget") or ""
            target = self._map_widget_target(raw_w)
            spoken = "Holographically revealing all mainframe widgets, sir." if target == "all" else f"Holographically revealing {target} component, sir."
            return {
                "intercepted": True,
                "spoken_response": spoken,
                "ui_action": "show_widget",
                "target": target
            }

        if self._clear_screen.search(cleaned) or self._clear_screen.search(eval_text):
            return {
                "intercepted": True,
                "spoken_response": "Clearing HUD display. All widgets dismissed, sir.",
                "ui_action": "hide_widget",
                "target": "all"
            }


        if self._kinetic_on.search(cleaned):
            return {
                "intercepted": True,
                "spoken_response": "Kinetic interface online. Tracking optical hand landmarks.",
                "ui_action": "kinetic_on",
                "target": ""
            }

        if self._kinetic_off.search(cleaned):
            return {
                "intercepted": True,
                "spoken_response": "Kinetic tracking disabled, sir.",
                "ui_action": "kinetic_off",
                "target": ""
            }

        # 7. Greetings & Status (only if short query to avoid false positives on complex prompts)
        words = cleaned.split()
        eval_words = eval_text.split()
        if len(words) <= 4 or len(eval_words) <= 4:
            if self._identity.search(cleaned) or self._identity.search(eval_text):
                return {
                    "intercepted": True,
                    "spoken_response": "I am J.A.R.V.I.S., your autonomous operating system and personal AI assistant.",
                    "ui_action": "none",
                    "target": ""
                }

            if self._status.search(cleaned) or self._status.search(eval_text):
                return {
                    "intercepted": True,
                    "spoken_response": "All cognitive arrays and system diagnostics nominal, sir. Standing by.",
                    "ui_action": "none",
                    "target": ""
                }

            if not eval_text or self._greetings.match(cleaned) or self._greetings.match(eval_text):
                hour = datetime.datetime.now().hour
                greeting = "Good morning" if 5 <= hour < 12 else "Good afternoon" if 12 <= hour < 18 else "Good evening"
                return {
                    "intercepted": True,
                    "spoken_response": f"{greeting}, sir. Systems are fully functional.",
                    "ui_action": "none",
                    "target": ""
                }

        # 8. Clarify Auto-Escalation Gate (Friday Mark 2)
        if self._ambiguous_queries.match(cleaned):
            self._clarify_strikes += 1
            if self._clarify_strikes >= 3:
                self._clarify_strikes = 0
                return {
                    "intercepted": True,
                    "spoken_response": "Auto-escalating to Antigravity autonomous multi-agent engine to resolve the task directly, sir.",
                    "ui_action": "delegate_to_antigravity",
                    "target": {
                        "task": f"Investigate context and resolve request: '{text}'",
                        "task_type": "autonomous_investigation"
                    }
                }
            return {
                "intercepted": True,
                "spoken_response": "Could you clarify which application, file, or objective you would like me to target, sir?",
                "ui_action": "none",
                "target": ""
            }

        self._clarify_strikes = 0
        return {"intercepted": False}
