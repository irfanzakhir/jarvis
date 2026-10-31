import os
import json
import time
import math
import logging
import requests
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger("JarvisMapService")

class MapService:
    """
    Tactical Geographical Reconnaissance Service.
    Provides real geocoding, POI discovery, and turn-by-turn routing via Nominatim and OSRM.
    """
    _instance = None
    CACHE_FILE = "map_geo_cache.json"
    CACHE_EXPIRY = 86400  # 24 hours

    DEFAULT_SECTOR = {
        "name": "Edakkunnam, Kerala",
        "lat": 9.5916,
        "lon": 76.5222,
        "zoom": 13
    }

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(MapService, cls).__new__(cls)
            cls._instance._init_service()
        return cls._instance

    def _init_service(self):
        self.headers = {
            "User-Agent": "Jarvis-TacticalOS/2.0 (Tactical Recon Intelligence)",
            "Accept-Language": "en-US,en;q=0.9"
        }
        self.cache: Dict[str, Any] = self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        if os.path.exists(self.CACHE_FILE):
            try:
                with open(self.CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"[MAP SERVICE] Failed loading cache: {e}")
        return {"geocodes": {}, "routes": {}, "pois": {}}

    def _save_cache(self):
        try:
            with open(self.CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            logger.warning(f"[MAP SERVICE] Failed saving cache: {e}")

    def geocode(self, query: str, bias_region: str = "Kerala, India") -> Optional[Dict[str, Any]]:
        """
        Geocodes query to geographical coordinates.
        Uses Nominatim with regional bias, with Esri ArcGIS fallback.
        """
        query_clean = query.strip()
        if not query_clean:
            return self.DEFAULT_SECTOR

        cache_key = f"{query_clean.lower()}|{bias_region.lower()}"
        cached = self.cache.get("geocodes", {}).get(cache_key)
        if cached and (time.time() - cached.get("timestamp", 0)) < self.CACHE_EXPIRY:
            return cached.get("data")

        # 1. Primary: Nominatim with regional bias if not already present
        search_query = query_clean
        if bias_region and bias_region.lower() not in query_clean.lower():
            # Check if query already specifies a country/city
            common_countries = ["india", "usa", "uk", "japan", "germany", "france", "dubai", "china", "tokyo", "london", "new york", "delhi", "mumbai", "bengaluru", "chennai"]
            if not any(c in query_clean.lower() for c in common_countries):
                search_query = f"{query_clean}, {bias_region}"

        result = self._geocode_nominatim(search_query)
        if not result and search_query != query_clean:
            result = self._geocode_nominatim(query_clean)

        # 2. Fallback: Esri ArcGIS World Geocoding Service
        if not result:
            result = self._geocode_esri(query_clean)

        if result:
            if "geocodes" not in self.cache:
                self.cache["geocodes"] = {}
            self.cache["geocodes"][cache_key] = {
                "timestamp": time.time(),
                "data": result
            }
            self._save_cache()
            return result

        return None

    def _geocode_nominatim(self, query: str) -> Optional[Dict[str, Any]]:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": query,
            "format": "json",
            "addressdetails": 1,
            "limit": 1
        }
        try:
            r = requests.get(url, params=params, headers=self.headers, timeout=5)
            if r.status_code == 200:
                data = r.json()
                if data and len(data) > 0:
                    cand = data[0]
                    lat = float(cand.get("lat"))
                    lon = float(cand.get("lon"))
                    display_name = cand.get("display_name", query)
                    addr_type = cand.get("type", "locality")
                    zoom = self._determine_zoom(cand.get("class"), addr_type)
                    return {
                        "name": cand.get("name") or query,
                        "display_name": display_name,
                        "lat": lat,
                        "lon": lon,
                        "zoom": zoom,
                        "type": addr_type,
                        "provider": "OpenStreetMap"
                    }
        except Exception as e:
            logger.warning(f"[MAP SERVICE] Nominatim error: {e}")
        return None

    def _geocode_esri(self, query: str) -> Optional[Dict[str, Any]]:
        url = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates"
        params = {
            "f": "json",
            "singleLine": query,
            "outFields": "Addr_type,Match_addr",
            "maxLocations": 1
        }
        try:
            r = requests.get(url, params=params, headers=self.headers, timeout=5)
            if r.status_code == 200:
                data = r.json()
                cands = data.get("candidates", [])
                if cands:
                    cand = cands[0]
                    loc = cand.get("location", {})
                    lat = float(loc.get("y"))
                    lon = float(loc.get("x"))
                    addr_type = cand.get("attributes", {}).get("Addr_type", "Locality")
                    zoom = self._determine_zoom("esri", addr_type)
                    return {
                        "name": cand.get("address", query),
                        "display_name": cand.get("address", query),
                        "lat": lat,
                        "lon": lon,
                        "zoom": zoom,
                        "type": addr_type,
                        "provider": "Esri"
                    }
        except Exception as e:
            logger.warning(f"[MAP SERVICE] Esri error: {e}")
        return None

    def _determine_zoom(self, obj_class: Optional[str], obj_type: str) -> int:
        t = (obj_type or "").lower()
        if t in ["country", "continent"]:
            return 5
        elif t in ["state", "province", "region"]:
            return 8
        elif t in ["county", "district"]:
            return 11
        elif t in ["city", "town", "metro"]:
            return 13
        elif t in ["suburb", "neighborhood", "village", "locality"]:
            return 15
        elif t in ["amenity", "building", "hospital", "aeroway", "station"]:
            return 16
        return 14

    def search_pois(self, category: str, center_lat: float = None, center_lon: float = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Discovers points of interest around the target center.
        Supports: 'hospitals', 'restaurants', 'petrol pumps', 'atms', 'police', 'airports', etc.
        """
        if center_lat is None or center_lon is None:
            center_lat = self.DEFAULT_SECTOR["lat"]
            center_lon = self.DEFAULT_SECTOR["lon"]

        cache_key = f"{category.lower()}|{round(center_lat, 3)}|{round(center_lon, 3)}"
        cached = self.cache.get("pois", {}).get(cache_key)
        if cached and (time.time() - cached.get("timestamp", 0)) < self.CACHE_EXPIRY:
            return cached.get("data", [])

        # Map colloquial term to search query
        category_map = {
            "hospital": "hospitals",
            "clinic": "hospitals",
            "restaurant": "restaurants",
            "food": "restaurants",
            "hotel": "hotels",
            "petrol": "fuel",
            "gas station": "fuel",
            "fuel": "fuel",
            "atm": "atm",
            "bank": "banks",
            "police": "police station",
            "airport": "airport",
            "station": "railway station",
            "pharmacy": "pharmacy",
            "supermarket": "supermarket"
        }
        
        search_term = category_map.get(category.lower().rstrip("s"), category)
        url = "https://nominatim.openstreetmap.org/search"
        
        # Bounding box ~ 15km
        delta_lat = 0.15
        delta_lon = 0.15
        params = {
            "q": search_term,
            "format": "json",
            "limit": limit,
            "viewbox": f"{center_lon - delta_lon},{center_lat + delta_lat},{center_lon + delta_lon},{center_lat - delta_lat}",
            "bounded": 1,
            "addressdetails": 1
        }

        pois = []
        try:
            r = requests.get(url, params=params, headers=self.headers, timeout=6)
            if r.status_code == 200:
                results = r.json()
                if not results:
                    # Retry without bounded viewbox but appending regional context
                    p2 = {"q": f"{search_term} near Kerala", "format": "json", "limit": limit, "addressdetails": 1}
                    r2 = requests.get(url, params=p2, headers=self.headers, timeout=6)
                    results = r2.json() if r2.status_code == 200 else []

                for item in results:
                    plat = float(item.get("lat"))
                    plon = float(item.get("lon"))
                    dist = self.calculate_distance(center_lat, center_lon, plat, plon)
                    pois.append({
                        "name": item.get("name") or item.get("display_name", "").split(",")[0],
                        "display_name": item.get("display_name"),
                        "lat": plat,
                        "lon": plon,
                        "distance_km": round(dist, 2),
                        "type": item.get("type", category),
                        "category": category
                    })
        except Exception as e:
            logger.warning(f"[MAP SERVICE] POI search error: {e}")

        # Sort by distance
        pois.sort(key=lambda x: x.get("distance_km", 999))

        if pois:
            if "pois" not in self.cache:
                self.cache["pois"] = {}
            self.cache["pois"][cache_key] = {
                "timestamp": time.time(),
                "data": pois
            }
            self._save_cache()

        return pois

    def get_route(self, start_lat: float, start_lon: float, end_lat: float, end_lon: float) -> Optional[Dict[str, Any]]:
        """
        Calculates driving route between two points using OSRM.
        Returns distance in km, duration in minutes, and GeoJSON polyline coordinates.
        """
        cache_key = f"{round(start_lat, 4)},{round(start_lon, 4)}|{round(end_lat, 4)},{round(end_lon, 4)}"
        cached = self.cache.get("routes", {}).get(cache_key)
        if cached and (time.time() - cached.get("timestamp", 0)) < self.CACHE_EXPIRY:
            return cached.get("data")

        url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}?overview=full&geometries=geojson"
        try:
            r = requests.get(url, headers=self.headers, timeout=8)
            if r.status_code == 200:
                data = r.json()
                routes = data.get("routes", [])
                if routes:
                    primary = routes[0]
                    dist_km = round(primary.get("distance", 0) / 1000.0, 1)
                    duration_mins = round(primary.get("duration", 0) / 60.0, 1)
                    geometry = primary.get("geometry", {}).get("coordinates", []) # [[lon, lat], ...]
                    # Convert to Leaflet [[lat, lon], ...]
                    leaflet_coords = [[pt[1], pt[0]] for pt in geometry]

                    route_data = {
                        "distance_km": dist_km,
                        "duration_mins": duration_mins,
                        "coordinates": leaflet_coords,
                        "start": [start_lat, start_lon],
                        "end": [end_lat, end_lon]
                    }

                    if "routes" not in self.cache:
                        self.cache["routes"] = {}
                    self.cache["routes"][cache_key] = {
                        "timestamp": time.time(),
                        "data": route_data
                    }
                    self._save_cache()
                    return route_data
        except Exception as e:
            logger.warning(f"[MAP SERVICE] OSRM routing error: {e}")

        # Fallback: Straight line Euclidean estimate
        straight_dist = self.calculate_distance(start_lat, start_lon, end_lat, end_lon)
        return {
            "distance_km": round(straight_dist, 1),
            "duration_mins": round((straight_dist / 40.0) * 60.0, 1), # 40 km/h avg
            "coordinates": [[start_lat, start_lon], [end_lat, end_lon]],
            "start": [start_lat, start_lon],
            "end": [end_lat, end_lon],
            "note": "Estimated direct trajectory"
        }

    @staticmethod
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Haversine formula for great-circle distance in kilometers."""
        r = 6371.0 # Earth radius km
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return r * c
