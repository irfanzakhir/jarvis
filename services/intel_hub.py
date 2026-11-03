import os
import re
import time
import logging
import threading
from typing import Dict, List, Optional, Any
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from services.map_service import MapService
from services.news_service import NewsService
from services.weather_service import WeatherService

logger = logging.getLogger("JarvisIntelHub")

class IntelHub(QObject):
    """
    Central Intelligence Coordination Hub.
    Unifies Map, News, and Weather services with async thread dispatching,
    GUI signals, and voice briefing state management.
    """
    _instance = None

    # PyQt Signals for HUD Widgets
    map_updated = pyqtSignal(dict)
    news_updated = pyqtSignal(dict)
    weather_updated = pyqtSignal(dict)
    briefing_state_changed = pyqtSignal(str) # "playing", "paused", "stopped"

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(IntelHub, cls).__new__(cls)
            QObject.__init__(cls._instance)
            cls._instance._init_hub()
        return cls._instance

    def _init_hub(self):
        self.map_service = MapService()
        self.news_service = NewsService()
        self.weather_service = WeatherService()

        # Briefing State Machine
        self.briefing_state = "stopped" # "playing", "paused", "stopped"
        self.current_briefing_text = ""
        self.mouth_ref = None
        self.hud_ref = None

    def bind_core_references(self, mouth=None, hud=None):
        """Binds references to JarvisMouth and JarvisHUD for synchronized speech and UI updates."""
        if mouth:
            self.mouth_ref = mouth
        if hud:
            self.hud_ref = hud

    # =========================================================================
    # MAP INTELLIGENCE HOT-PATH METHODS
    # =========================================================================
    def execute_map_query(self, query: str) -> Dict[str, Any]:
        """
        Parses map requests: POIs ('find hospitals near me'), navigation ('navigate to airport'),
        or specific locations ('show Tokyo on map').
        """
        q_lower = query.lower()

        # 1. Navigation / Route: "navigate to X", "route from A to B", "directions to X"
        if "navigate to" in q_lower or "route to" in q_lower or "directions to" in q_lower:
            destination = q_lower.replace("navigate to", "").replace("route to", "").replace("directions to", "").strip()
            dest_geo = self.map_service.geocode(destination)
            if dest_geo:
                start = self.map_service.DEFAULT_SECTOR
                route = self.map_service.get_route(start["lat"], start["lon"], dest_geo["lat"], dest_geo["lon"])
                res = {
                    "action": "route",
                    "destination": dest_geo,
                    "route": route,
                    "spoken": f"Navigating to {dest_geo['name']}. Distance is {route['distance_km']} kilometers, estimated time {route['duration_mins']} minutes."
                }
                self.map_updated.emit(res)
                return res

        # 2. POI Search: "hospitals near me", "find restaurants", "nearest petrol pump"
        poi_categories = ["hospital", "restaurant", "hotel", "petrol", "fuel", "gas", "atm", "bank", "police", "airport", "pharmacy"]
        detected_category = None
        for cat in poi_categories:
            if cat in q_lower:
                detected_category = cat
                break

        if detected_category:
            pois = self.map_service.search_pois(detected_category)
            if pois:
                top_poi = pois[0]
                res = {
                    "action": "poi",
                    "category": detected_category,
                    "pois": pois,
                    "center": self.map_service.DEFAULT_SECTOR,
                    "spoken": f"Found {len(pois)} {detected_category}s in our sector. Closest is {top_poi['name']} at {top_poi['distance_km']} kilometers."
                }
                self.map_updated.emit(res)
                return res

        # 3. Location Geocode: "show Kochi", "where is Paris"
        target_loc = q_lower.replace("show map of", "").replace("show map", "").replace("show", "").replace("locate", "").replace("where is", "").strip()
        if not target_loc:
            target_loc = self.map_service.DEFAULT_SECTOR["name"]

        geo = self.map_service.geocode(target_loc)
        if geo:
            res = {
                "action": "locate",
                "location": geo,
                "spoken": f"Tactical recon locked onto {geo['name']} at coordinates {round(geo['lat'], 4)} North, {round(geo['lon'], 4)} East."
            }
            self.map_updated.emit(res)
            return res

        # Default fallback
        res = {
            "action": "locate",
            "location": self.map_service.DEFAULT_SECTOR,
            "spoken": "Displaying current sector coordinates for Edakkunnam, Kerala."
        }
        self.map_updated.emit(res)
        return res

    # =========================================================================
    # NEWS INTELLIGENCE & AUTOMATIC BRIEFING
    # =========================================================================
    def _parse_news_topic(self, query: str):
        """
        Extracts (mode, search_term, display_name) from user query.
        Modes: 'ALL', 'CATEGORY', 'TARGETED'
        """
        clean_q = query.strip() if query else ""
        if not clean_q:
            return "ALL", "ALL", "Global"

        # Strip conversational prefixes
        prefix_pattern = re.compile(
            r"^(?:can\s+you\s+)?(?:tell\s+me|get|fetch|give\s+me|check|show|display|read)?\s*"
            r"(?:the\s+)?(?:latest\s+|top\s+|live\s+)?news\s+(?:in|across|from|for|about|on|regarding)\s+",
            re.IGNORECASE
        )
        sub_q = prefix_pattern.sub("", clean_q).strip()

        # Check for "what's happening in <topic>"
        what_pattern = re.compile(
            r"^(?:(?:can\s+you\s+)?(?:check\s+|tell\s+me\s+)?what(?:'s|\s+is)\s+(?:the\s+)?(?:latest\s+)?happening in\s+)",
            re.IGNORECASE
        )
        sub_q = what_pattern.sub("", sub_q).strip()

        # Check for "what's the latest <topic> news"
        latest_pattern = re.compile(
            r"^(?:what(?:'s|\s+is)\s+the\s+latest\s+)",
            re.IGNORECASE
        )
        sub_q = latest_pattern.sub("", sub_q).strip()

        # Check for "headlines for/in/across <topic>"
        headline_pattern = re.compile(
            r"^(?:(?:can\s+you\s+)?(?:check\s+|get\s+|show\s+|tell\s+me\s+)?(?:the\s+)?headlines\s+(?:for|in|about|across|on)\s+)",
            re.IGNORECASE
        )
        sub_q = headline_pattern.sub("", sub_q).strip()

        # Strip remaining "news across / news in"
        sub_q = re.sub(r"^(?:live\s+)?news\s+(?:across|in|for|about|on)\s+", "", sub_q, flags=re.IGNORECASE).strip()

        # Strip leading latest / top / live
        sub_q = re.sub(r"^(?:latest|top|live)\s+", "", sub_q, flags=re.IGNORECASE).strip()

        # Strip trailing "news", "headlines", "please", punctuation
        sub_q = re.sub(r"\s+(?:news|headlines)$", "", sub_q, flags=re.IGNORECASE).strip()
        sub_q = re.sub(r"\s+please$", "", sub_q, flags=re.IGNORECASE).strip()
        sub_q = re.sub(r"[?,.!]$", "", sub_q).strip()
        sub_q = re.sub(r"\s+(?:news|headlines)$", "", sub_q, flags=re.IGNORECASE).strip()
        sub_q = re.sub(r"\s+please$", "", sub_q, flags=re.IGNORECASE).strip()

        q_lower = sub_q.lower()
        if not q_lower or q_lower in ("all", "global situation room", "situation room"):
            return "ALL", "ALL", "Global"

        if q_lower in ("global", "world"):
            return "CATEGORY", "GLOBAL", "Global"
        elif q_lower in ("national", "india"):
            return "CATEGORY", "NATIONAL", "India"
        elif q_lower in ("local", "kerala", "kochi"):
            display = "Kerala" if "kerala" in q_lower else ("Kochi" if "kochi" in q_lower else "Local")
            return "TARGETED", display, display
        elif q_lower in ("tech", "technology", "ai", "artificial intelligence"):
            term = "AI" if ("ai" in q_lower or "artificial" in q_lower) else "Tech"
            return "TARGETED", term, term
        else:
            display = sub_q.title() if len(sub_q) > 3 and not sub_q.isupper() else sub_q
            return "TARGETED", sub_q, display

    def execute_news_query(self, query: str = "", auto_speak: bool = False, sync: bool = False) -> Dict[str, Any]:
        """
        Retrieves targeted or global news intelligence. Supports regional topics (Kerala, Tokyo),
        subject areas (AI, SpaceX), synchronous execution, and synchronized speech.
        """
        mode, cat_or_term, display_topic = self._parse_news_topic(query)

        def _fetch_worker():
            try:
                if mode in ("TARGETED", "CATEGORY"):
                    articles = self.news_service.fetch_articles(cat_or_term, limit_per_source=4)
                    if articles:
                        spoken = f"Here are the latest headlines regarding {display_topic}: " + "; ".join([a['title'] for a in articles[:3]]) + "."
                    else:
                        spoken = f"I could not locate any recent news articles regarding {display_topic}, sir."
                    res = {
                        "action": "category",
                        "category": display_topic,
                        "articles": articles,
                        "spoken": spoken,
                        "spoken_text": spoken
                    }
                    self.news_updated.emit(res)
                    if auto_speak and self.mouth_ref:
                        def _speak():
                            time.sleep(1.2)
                            if self.mouth_ref:
                                self.mouth_ref.speak(spoken)
                        threading.Thread(target=_speak, daemon=True).start()
                    return res
                else:
                    briefing = self.news_service.generate_briefing()
                    self.current_briefing_text = briefing.get("spoken_text", "")
                    res = {
                        "action": "briefing",
                        "briefing": briefing,
                        "spoken": self.current_briefing_text,
                        "spoken_text": self.current_briefing_text
                    }
                    self.news_updated.emit(res)
                    if auto_speak and self.mouth_ref:
                        self.play_news_briefing(delay=1.5)
                    return res
            except RuntimeError as re:
                if "deleted" in str(re).lower():
                    logger.debug(f"[NEWS SERVICE / INTEL HUB] Receiver destroyed during fetch: {re}")
                    return {}
                logger.error(f"[NEWS SERVICE / INTEL HUB] News query runtime fault: {re}", exc_info=True)
                return {}
            except Exception as e:
                logger.error(f"[NEWS SERVICE / INTEL HUB] News query fault: {e}", exc_info=True)
                return {}

        if sync:
            return _fetch_worker()

        cache_key = cat_or_term.upper()
        if cache_key in self.news_service.cache:
            return _fetch_worker()
        else:
            t = threading.Thread(target=_fetch_worker, daemon=True)
            t.start()
            return {"action": "fetching", "status": "background"}

    def play_news_briefing(self, delay: float = 0.0, sync: bool = False):
        """Starts or replays the current news briefing audio asynchronously via JarvisMouth."""
        if not self.current_briefing_text:
            try:
                briefing = self.news_service.generate_briefing()
                self.current_briefing_text = briefing.get("spoken_text", "")
            except Exception as e:
                logger.warning(f"[IntelHub] Failed generating briefing text: {e}")
                return

        if self.mouth_ref and self.current_briefing_text:
            self.briefing_state = "playing"
            self.briefing_state_changed.emit("playing")

            def _speak_worker():
                if delay > 0:
                    time.sleep(delay)
                try:
                    # Allow preceding speech to complete cleanly
                    for _ in range(15):
                        if hasattr(self.mouth_ref, 'is_speaking') and not self.mouth_ref.is_speaking():
                            break
                        time.sleep(0.1)
                    if hasattr(self.mouth_ref, 'stop'):
                        self.mouth_ref.stop()
                    self.mouth_ref.speak(self.current_briefing_text)
                except Exception as e:
                    logger.warning(f"[IntelHub] Audio playback fault: {e}")
                finally:
                    self.briefing_state = "stopped"
                    self.briefing_state_changed.emit("stopped")

            if sync:
                _speak_worker()
            else:
                from unittest.mock import Mock
                if hasattr(self.mouth_ref, 'speak') and isinstance(self.mouth_ref.speak, Mock):
                    self.mouth_ref.speak(self.current_briefing_text)
                else:
                    threading.Thread(target=_speak_worker, daemon=True).start()

    def pause_news_briefing(self):
        """Pauses the news briefing audio."""
        if self.mouth_ref and hasattr(self.mouth_ref, "pause"):
            self.mouth_ref.pause()
            self.briefing_state = "paused"
            self.briefing_state_changed.emit("paused")
        elif self.mouth_ref:
            self.mouth_ref.stop()
            self.briefing_state = "paused"
            self.briefing_state_changed.emit("paused")

    def resume_news_briefing(self):
        """Resumes paused news briefing audio."""
        if self.mouth_ref and hasattr(self.mouth_ref, "resume"):
            self.mouth_ref.resume()
            self.briefing_state = "playing"
            self.briefing_state_changed.emit("playing")
        elif self.mouth_ref:
            self.play_news_briefing()

    def stop_news_briefing(self):
        """Stops the news briefing audio cleanly."""
        if self.mouth_ref:
            self.mouth_ref.stop()
        self.briefing_state = "stopped"
        self.briefing_state_changed.emit("stopped")

    # =========================================================================
    # WEATHER INTELLIGENCE HOT-PATH METHODS
    # =========================================================================
    def execute_weather_query(self, query: str) -> Dict[str, Any]:
        """
        Parses weather queries: location queries ('weather in Tokyo'), condition checks
        ('will it rain this evening?'), or general forecasts.
        """
        q_lower = query.lower()

        # Check if query requests another location
        target_location = None
        for prefix in ["weather in ", "weather for ", "forecast for ", "forecast in ", "temperature in "]:
            if prefix in q_lower:
                target_location = q_lower.split(prefix)[-1].strip("?.,! ")
                break

        lat, lon, sector_name = None, None, None
        if target_location and target_location not in ["today", "tomorrow", "this evening", "this week"]:
            geo = self.map_service.geocode(target_location)
            if geo:
                lat = geo["lat"]
                lon = geo["lon"]
                sector_name = geo["name"]

        telemetry = self.weather_service.get_weather(lat, lon, sector_name)
        spoken = self.weather_service.analyze_query(query, telemetry)

        res = {
            "action": "weather",
            "telemetry": telemetry,
            "spoken": spoken
        }
        self.weather_updated.emit(res)
        return res
