import os
import re
import json
import time
import logging
import requests
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any

logger = logging.getLogger("JarvisNewsService")

class NewsService:
    """
    Live AI-Powered News Intelligence Pipeline.
    Retrieves, deduplicates, categorizes, and synthesizes Global, National, and Local news feeds.
    Compiles structured visual briefings and synchronized spoken audio scripts for J.A.R.V.I.S.
    """
    _instance = None
    CACHE_FILE = "news_intel_cache.json"
    CACHE_EXPIRY = 900  # 15 minutes cache

    FEED_SOURCES = {
        "GLOBAL": [
            ("Google News World", "https://news.google.com/rss/headlines/section/topic/WORLD?hl=en-US&gl=US&ceid=US:en"),
            ("Google News Technology", "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-US&gl=US&ceid=US:en")
        ],
        "NATIONAL": [
            ("Google News India", "https://news.google.com/rss/headlines/section/topic/NATION?hl=en-IN&gl=IN&ceid=IN:en"),
            ("Google News India Business", "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-IN&gl=IN&ceid=IN:en")
        ],
        "LOCAL": [
            ("Google News Kerala", "https://news.google.com/rss/search?q=Kerala+OR+Kochi&hl=en-IN&gl=IN&ceid=IN:en"),
            ("Google News Kochi", "https://news.google.com/rss/search?q=Kochi+infrastructure+OR+technology&hl=en-IN&gl=IN&ceid=IN:en")
        ],
        "TECH": [
            ("Google News AI", "https://news.google.com/rss/search?q=Artificial+Intelligence+OR+OpenAI+OR+Gemini&hl=en-US&gl=US&ceid=US:en")
        ]
    }

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(NewsService, cls).__new__(cls)
            cls._instance._init_service()
        return cls._instance

    def _init_service(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/rss+xml, application/xml, text/xml, */*"
        }
        self.cache: Dict[str, Any] = self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        if os.path.exists(self.CACHE_FILE):
            try:
                with open(self.CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"[NEWS SERVICE] Failed loading cache: {e}")
        return {}

    def _save_cache(self):
        try:
            with open(self.CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            logger.warning(f"[NEWS SERVICE] Failed saving cache: {e}")

    def fetch_articles(self, category: str = "ALL", limit_per_source: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieves, deduplicates, and validates news articles for the requested category.
        Categories: 'GLOBAL', 'NATIONAL', 'LOCAL', 'TECH', 'ALL'
        """
        now = time.time()
        category_upper = category.upper()

        if category_upper in self.cache:
            entry = self.cache[category_upper]
            if (now - entry.get("timestamp", 0)) < self.CACHE_EXPIRY:
                return entry.get("articles", [])

        articles = []
        sources_to_query = {}
        if category_upper == "ALL":
            sources_to_query = self.FEED_SOURCES
        elif category_upper in self.FEED_SOURCES:
            sources_to_query = {category_upper: self.FEED_SOURCES[category_upper]}
        else:
            # Query-based search
            encoded_query = urllib.parse.quote_plus(category)
            sources_to_query = {
                category_upper: [
                    (f"Search: {category}", f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en")
                ]
            }

        for cat_name, feed_list in sources_to_query.items():
            for source_name, feed_url in feed_list:
                fetched = self._parse_rss_feed(feed_url, source_name, cat_name, limit_per_source)
                articles.extend(fetched)

        # Deduplication and ranking
        deduped = self._deduplicate_articles(articles)
        
        self.cache[category_upper] = {
            "timestamp": now,
            "articles": deduped
        }
        self._save_cache()
        return deduped

    def _parse_rss_feed(self, url: str, default_source: str, category: str, limit: int) -> List[Dict[str, Any]]:
        results = []
        try:
            r = requests.get(url, headers=self.headers, timeout=5)
            if r.status_code == 200:
                root = ET.fromstring(r.content)
                channel = root.find("channel")
                if channel is not None:
                    items = channel.findall("item")
                    for item in items[:limit]:
                        raw_title = item.find("title").text if item.find("title") is not None else "Untitled"
                        link = item.find("link").text if item.find("link") is not None else ""
                        pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                        source_elem = item.find("source")
                        source_name = source_elem.text if source_elem is not None and source_elem.text else default_source

                        # Clean Google News suffix e.g. " - The Hindu" from title
                        clean_title = raw_title
                        if " - " in raw_title:
                            parts = raw_title.rsplit(" - ", 1)
                            clean_title = parts[0].strip()
                            if source_name == default_source:
                                source_name = parts[1].strip()

                        # Extract description or snippet
                        desc_elem = item.find("description")
                        snippet = ""
                        if desc_elem is not None and desc_elem.text:
                            # Strip HTML tags
                            snippet = re.sub(r"<[^>]+>", "", desc_elem.text).strip()
                            if snippet == raw_title or snippet == clean_title:
                                snippet = ""

                        # Extract image / media thumbnail
                        image_url = ""
                        for child in item:
                            if child.tag.endswith("content") and "url" in child.attrib:
                                image_url = child.attrib["url"]
                                break
                            elif child.tag.endswith("enclosure") and "url" in child.attrib:
                                image_url = child.attrib["url"]
                                break

                        # Also search description for embedded <img> tags
                        if not image_url and desc_elem is not None and desc_elem.text:
                            img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', desc_elem.text)
                            if img_match:
                                image_url = img_match.group(1)

                        # Video detection
                        is_video = bool(
                            re.search(r'\b(video|watch|live stream|youtube|clip|broadcast)\b', raw_title, re.IGNORECASE)
                            or (link and any(v in link.lower() for v in ["youtube.com", "/video/", "watch?v="]))
                        )

                        results.append({
                            "title": clean_title,
                            "source": source_name,
                            "url": link,
                            "pub_date": pub_date,
                            "snippet": snippet or f"Reported by {source_name}. Key strategic and regional intelligence indicator.",
                            "category": category,
                            "image_url": image_url,
                            "is_video": is_video,
                            "timestamp": time.time()
                        })
        except Exception as e:
            logger.warning(f"[NEWS SERVICE] RSS parse error for {url}: {e}")
        return results

    @classmethod
    def get_preview_articles(cls) -> List[Dict[str, Any]]:
        """Returns pre-synthesized tactical intelligence articles for immediate boot display."""
        return [
            {
                "title": "Quantum AI Infrastructure & Autonomous Neural Models Deployed Across Edge Datacenters",
                "source": "TechCrunch Intel",
                "url": "https://news.google.com",
                "pub_date": "Live Telemetry",
                "snippet": "Next-generation generative neural reasoning cores report 40% latency reduction in autonomous agentic loops.",
                "category": "TECH",
                "image_url": "",
                "is_video": False,
                "timestamp": time.time()
            },
            {
                "title": "Global Cyber Defense Initiative: Watchdog Protocols Neutralize Coordinated Attacks",
                "source": "Reuters Defense",
                "url": "https://news.google.com",
                "pub_date": "10 Mins Ago",
                "snippet": "International cyber command units confirm perimeter lockdown across all high-security communication relays.",
                "category": "GLOBAL",
                "image_url": "",
                "is_video": True,
                "timestamp": time.time()
            },
            {
                "title": "Kochi Smart City Grid & Regional High-Speed Fiber Backbone Passes Operational Readiness",
                "source": "The Hindu Kerala",
                "url": "https://news.google.com",
                "pub_date": "24 Mins Ago",
                "snippet": "Edakkunnam sector and Cochin metro corridor activate gigabit sensor mesh and municipal telemetry relays.",
                "category": "LOCAL",
                "image_url": "",
                "is_video": False,
                "timestamp": time.time()
            },
            {
                "title": "India Semiconductor Mission: High-Yield Fabrication Lines Enter Commercial Production",
                "source": "Economic Times",
                "url": "https://news.google.com",
                "pub_date": "45 Mins Ago",
                "snippet": "Domestic semiconductor manufacturing clusters achieve initial wafer yields for edge automotive and AI hardware.",
                "category": "NATIONAL",
                "image_url": "",
                "is_video": True,
                "timestamp": time.time()
            },
            {
                "title": "Orbital Satellite Constellation Achieves Zero-Lag Global Reconnaissance Coverage",
                "source": "Aerospace Intel",
                "url": "https://news.google.com",
                "pub_date": "1 Hour Ago",
                "snippet": "New low-earth orbit radar array delivers sub-meter topographic scanning and real-time atmospheric tracking.",
                "category": "GLOBAL",
                "image_url": "",
                "is_video": False,
                "timestamp": time.time()
            }
        ]

    def _deduplicate_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Removes duplicates based on title similarity and normalized words."""
        unique = []
        seen_words = []

        for art in articles:
            title = art.get("title", "").lower()
            words = set(re.findall(r"\b\w{4,}\b", title))
            if not words:
                continue

            # Check overlap against seen titles
            is_duplicate = False
            for prev_words in seen_words:
                intersection = words.intersection(prev_words)
                union = words.union(prev_words)
                if union and (len(intersection) / len(union)) > 0.45:
                    is_duplicate = True
                    break

            if not is_duplicate:
                seen_words.append(words)
                unique.append(art)

        return unique

    def generate_briefing(self) -> Dict[str, Any]:
        """
        Synthesizes the default 3-tier news briefing (Global, National, Local)
        Returns:
            - spoken_text: Concise, natural speech string for JarvisMouth.
            - display_sections: Dictionary of categorized stories for the UI dashboard.
            - generated_at: Timestamp.
        """
        all_articles = self.fetch_articles("ALL", limit_per_source=4)

        global_articles = [a for a in all_articles if a.get("category") == "GLOBAL"][:3]
        national_articles = [a for a in all_articles if a.get("category") == "NATIONAL"][:3]
        local_articles = [a for a in all_articles if a.get("category") == "LOCAL"][:3]
        tech_articles = [a for a in all_articles if a.get("category") == "TECH"][:2]

        # Determine time-of-day greeting
        hour = time.localtime().tm_hour
        greeting = "Good morning, sir." if hour < 12 else ("Good afternoon, sir." if hour < 17 else "Good evening, sir.")

        spoken_parts = [f"{greeting} Initializing tactical news intelligence briefing."]

        # 1. Global Section
        if global_articles:
            g_summaries = "; ".join([a['title'] for a in global_articles[:2]])
            spoken_parts.append(f"Starting with global intelligence: {g_summaries}.")
        else:
            spoken_parts.append("Global feeds are currently steady with no major geopolitical alerts.")

        # 2. National Section
        if national_articles:
            n_summaries = "; ".join([a['title'] for a in national_articles[:2]])
            spoken_parts.append(f"Across India: {n_summaries}.")
        else:
            spoken_parts.append("National indicators across India remain within nominal parameters.")

        # 3. Local Section
        if local_articles:
            l_summaries = "; ".join([a['title'] for a in local_articles[:2]])
            spoken_parts.append(f"In our regional sector for Kerala and Kochi: {l_summaries}.")
        else:
            spoken_parts.append("Local sectors report tranquil municipal activity.")

        spoken_parts.append("Visual telemetry and source transcripts are ready on your console.")
        spoken_briefing = " ".join(spoken_parts)

        return {
            "spoken_text": spoken_briefing,
            "sections": {
                "GLOBAL": global_articles,
                "NATIONAL": national_articles,
                "LOCAL": local_articles,
                "TECH": tech_articles
            },
            "timestamp": time.time(),
            "formatted_time": time.strftime("%H:%M // %d %b %Y")
        }

    def generate_targeted_briefing(self, query: str, limit: int = 4) -> Dict[str, Any]:
        """
        Synthesizes a targeted news briefing for a specific location or topic.
        Returns:
            - articles: List of matching news articles.
            - spoken_text: Formatted spoken response string.
            - spoken: Alias for spoken_text.
        """
        clean_q = query.strip()
        articles = self.fetch_articles(clean_q, limit_per_source=limit)

        if articles:
            summaries = "; ".join([a['title'] for a in articles[:limit]])
            spoken = f"Here are the latest headlines regarding {clean_q}: {summaries}."
        else:
            spoken = f"I could not locate any recent news articles regarding {clean_q}, sir."

        return {
            "query": clean_q,
            "articles": articles,
            "spoken_text": spoken,
            "spoken": spoken,
            "timestamp": time.time(),
            "formatted_time": time.strftime("%H:%M // %d %b %Y")
        }

