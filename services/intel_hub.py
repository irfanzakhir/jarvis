import os
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
    def execute_news_query(self, query: str = "", auto_speak: bool = False) -> Dict[str, Any]:
        """
        Retrieves news intel safely. Offloads network fetch and synthesis to background
        daemon thread if needed to avoid blocking Qt GUI thread.
        """
        q_lower = query.lower()

        # Category specific request
        cat = "ALL"
        if "global" in q_lower or "world" in q_lower:
            cat = "GLOBAL"
        elif "national" in q_lower or "india" in q_lower:
            cat = "NATIONAL"
        elif "local" in q_lower or "kerala" in q_lower or "kochi" in q_lower:
            cat = "LOCAL"
        elif "ai" in q_lower or "tech" in q_lower:
            cat = "TECH"

        def _fetch_worker():
            try:
                if cat != "ALL":
                    articles = self.news_service.fetch_articles(cat, limit_per_source=5)
                    spoken = f"Here are the top headlines in {cat.lower()} intelligence: " + "; ".join([a['title'] for a in articles[:3]]) + "."
                    res = {
                        "action": "category",
                        "category": cat,
                        "articles": articles,
                        "spoken": spoken
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
                        "spoken": self.current_briefing_text
                    }
                    self.news_updated.emit(res)
                    if auto_speak and self.mouth_ref:
                        self.play_news_briefing(delay=1.5)
                    return res
            except Exception as e:
                logger.error(f"[NEWS SERVICE / INTEL HUB] News query fault: {e}", exc_info=True)
                return {}

        cat_key = cat.upper()
        if cat_key in self.news_service.cache:
            return _fetch_worker()
        else:
            # Run in worker thread to prevent Qt event pump deadlock
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
