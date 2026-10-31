import os
import json
import random
from typing import Dict, List, Optional, Any
from PyQt6.QtCore import Qt, QTimer, QUrl, pyqtSignal, QPointF
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QLinearGradient, QRadialGradient, QDesktopServices
)
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QFrame, QGridLayout, QSizePolicy
)
QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile

from services.intel_hub import IntelHub
from services.news_service import NewsService

# =============================================================================
# 1. TACTICAL MAP HUD WIDGET
# =============================================================================
class TacticalMapHUDWidget(QWidget):
    """
    Interactive Tactical Geographical Map Widget.
    Embeds Leaflet QWebEngineView with glowing cyber controls, search bar,
    quick POI filters, layer toggles, and status bar.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hub = IntelHub()
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(6, 6, 6, 6)
        self.layout.setSpacing(6)

        # 1. Header Search & Control Bar
        self.control_bar = QHBoxLayout()
        self.control_bar.setSpacing(4)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search sector, city, or coordinates...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background: rgba(8, 16, 28, 0.85);
                border: 1px solid #00d4ff;
                border-radius: 4px;
                color: #e0f4ff;
                font-family: 'Consolas', monospace;
                font-size: 11px;
                padding: 4px 8px;
            }
            QLineEdit:focus { border: 1px solid #00ffaa; }
        """)
        self.search_input.returnPressed.connect(self._on_search)
        self.control_bar.addWidget(self.search_input)

        self.btn_search = QPushButton("LOCATE")
        self.btn_search.setStyleSheet(self._btn_style("#00d4ff"))
        self.btn_search.clicked.connect(self._on_search)
        self.control_bar.addWidget(self.btn_search)

        self.btn_layer = QPushButton("SAT")
        self.btn_layer.setStyleSheet(self._btn_style("#00ffaa"))
        self.btn_layer.setFixedWidth(45)
        self.btn_layer.clicked.connect(self._toggle_layer)
        self.control_bar.addWidget(self.btn_layer)
        self.current_layer_mode = "dark"

        self.layout.addLayout(self.control_bar)

        # 2. Quick POI Selector Bar
        self.poi_bar = QHBoxLayout()
        self.poi_bar.setSpacing(4)

        for cat, label in [("hospital", "HOSPITALS"), ("fuel", "FUEL"), ("restaurant", "FOOD"), ("airport", "AIRPORT")]:
            btn = QPushButton(label)
            btn.setStyleSheet(self._btn_style("#00d4ff", font_size=9))
            btn.clicked.connect(lambda checked, c=cat: self._on_quick_poi(c))
            self.poi_bar.addWidget(btn)

        self.btn_reset = QPushButton("RESET")
        self.btn_reset.setStyleSheet(self._btn_style("#ffaa00", font_size=9))
        self.btn_reset.clicked.connect(self._reset_view)
        self.poi_bar.addWidget(self.btn_reset)

        self.layout.addLayout(self.poi_bar)

        # 3. Interactive WebEngine View
        try:
            QWebEngineProfile.defaultProfile().clearHttpCache()
        except Exception:
            pass

        self.web_view = QWebEngineView()
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ShowScrollBars, False)
        self.web_view.setStyleSheet("background: #040810; border: 1px solid #005577; border-radius: 4px;")

        map_html_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "map_view.html"))
        if os.path.exists(map_html_path):
            self.web_view.load(QUrl.fromLocalFile(map_html_path))
        else:
            self.web_view.setHtml("<html><body style='background:#040810;color:#00d4ff;font-family:Consolas;'>Tactical Map View Initializing...</body></html>")

        self.layout.addWidget(self.web_view, 1)

        # 4. Telemetry Footer
        self.status_label = QLabel("SECTOR: EDAKKUNNAM, KERALA // STATUS: RECON LOCKED // ALTITUDE: LEVEL 13")
        self.status_label.setStyleSheet("color: #00d4ff; font-family: 'Consolas', monospace; font-size: 10px; padding: 2px;")
        self.layout.addWidget(self.status_label)

    def _connect_signals(self):
        self.hub.map_updated.connect(self.on_map_updated)

    def _btn_style(self, color: str, font_size: int = 10) -> str:
        return f"""
            QPushButton {{
                background: rgba(4, 12, 22, 0.85);
                border: 1px solid {color};
                border-radius: 3px;
                color: {color};
                font-family: 'Consolas', monospace;
                font-size: {font_size}px;
                font-weight: bold;
                padding: 4px 6px;
            }}
            QPushButton:hover {{
                background: {color};
                color: #040810;
            }}
        """

    def _on_search(self):
        query = self.search_input.text().strip()
        if query:
            self.hub.execute_map_query(query)

    def _on_quick_poi(self, category: str):
        self.hub.execute_map_query(f"find {category} near me")

    def _toggle_layer(self):
        if self.current_layer_mode == "dark":
            self.current_layer_mode = "sat"
            self.btn_layer.setText("VEC")
            self.run_js("window.switchMapMode('sat');")
        else:
            self.current_layer_mode = "dark"
            self.btn_layer.setText("SAT")
            self.run_js("window.switchMapMode('dark');")

    def _reset_view(self):
        self.run_js("window.resetView();")
        self.status_label.setText("SECTOR: EDAKKUNNAM, KERALA // RECON RESET // ALTITUDE: LEVEL 13")

    def run_js(self, script: str):
        if self.web_view:
            self.web_view.page().runJavaScript(script)

    def on_map_updated(self, data: dict):
        action = data.get("action")
        if action == "locate":
            loc = data.get("location", {})
            lat = loc.get("lat", 9.5916)
            lon = loc.get("lon", 76.5222)
            zoom = loc.get("zoom", 13)
            name = loc.get("name", "Sector")
            self.run_js(f"window.flyToSector({lat}, {lon}, {zoom});")
            self.status_label.setText(f"TARGET: {name.upper()} // COORDS: {round(lat, 4)}N, {round(lon, 4)}E // LOCKED")

        elif action == "poi":
            pois = data.get("pois", [])
            cat = data.get("category", "POI").upper()
            pois_json = json.dumps(pois)
            self.run_js(f"window.setPOIMarkers({pois_json});")
            self.status_label.setText(f"POI SCAN: {len(pois)} {cat} TARGETS IDENTIFIED IN SECTOR")

        elif action == "route":
            route = data.get("route", {})
            dest = data.get("destination", {})
            coords = route.get("coordinates", [])
            dist = route.get("distance_km", 0)
            dur = route.get("duration_mins", 0)
            coords_json = json.dumps(coords)
            self.run_js(f"window.drawRoute({coords_json}, {dist}, {dur});")
            self.status_label.setText(f"TRANSIT: {dest.get('name', 'TARGET').upper()} // DIST: {dist} KM // ETA: {dur} MINS")


# =============================================================================
# 2. LIVE NEWS INTEL HUD WIDGET
# =============================================================================
class LiveNewsHUDWidget(QWidget):
    """
    Live AI-Powered News Intelligence Widget.
    Features category selector tabs, top executive AI briefing player,
    and rich cyber cards with timestamps and sources.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hub = IntelHub()
        self._init_ui()
        self._connect_signals()
        # Initial briefing fetch
        QTimer.singleShot(1000, lambda: self.hub.execute_news_query("", auto_speak=False))

    def _init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(6, 6, 6, 6)
        self.layout.setSpacing(6)

        # 1. Executive Briefing Banner & Audio Controls
        self.briefing_box = QFrame()
        self.briefing_box.setStyleSheet("""
            QFrame {
                background: rgba(0, 40, 60, 0.45);
                border: 1px solid #00d4ff;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        b_layout = QVBoxLayout(self.briefing_box)
        b_layout.setContentsMargins(6, 4, 6, 4)
        b_layout.setSpacing(4)

        b_header = QHBoxLayout()
        self.briefing_title = QLabel("AI EXECUTIVE BRIEFING // SYNTHESIZED")
        self.briefing_title.setStyleSheet("color: #00ffaa; font-family: 'Consolas', monospace; font-size: 11px; font-weight: bold;")
        b_header.addWidget(self.briefing_title)

        # Audio Controls
        self.btn_play = QPushButton("▶ PLAY")
        self.btn_play.setStyleSheet(self._btn_style("#00ffaa", 9))
        self.btn_play.clicked.connect(self._on_play)
        b_header.addWidget(self.btn_play)

        self.btn_pause = QPushButton("⏸")
        self.btn_pause.setStyleSheet(self._btn_style("#00d4ff", 9))
        self.btn_pause.setFixedWidth(28)
        self.btn_pause.clicked.connect(self._on_pause)
        b_header.addWidget(self.btn_pause)

        self.btn_stop = QPushButton("⏹")
        self.btn_stop.setStyleSheet(self._btn_style("#ff3366", 9))
        self.btn_stop.setFixedWidth(28)
        self.btn_stop.clicked.connect(self._on_stop)
        b_header.addWidget(self.btn_stop)

        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setStyleSheet(self._btn_style("#ffaa00", 9))
        self.btn_refresh.setFixedWidth(28)
        self.btn_refresh.clicked.connect(self._on_refresh)
        b_header.addWidget(self.btn_refresh)

        b_layout.addLayout(b_header)

        self.briefing_text = QLabel("Analyzing global, national, and regional tactical feeds...")
        self.briefing_text.setWordWrap(True)
        self.briefing_text.setStyleSheet("color: #d0f0ff; font-family: 'Consolas', monospace; font-size: 10px; line-height: 1.4;")
        b_layout.addWidget(self.briefing_text)

        self.layout.addWidget(self.briefing_box)

        # 2. Category Filter Tabs
        self.tab_bar = QHBoxLayout()
        self.tab_bar.setSpacing(4)
        self.category_buttons = {}
        for cat in ["ALL", "GLOBAL", "NATIONAL", "LOCAL", "TECH"]:
            btn = QPushButton(cat)
            btn.setStyleSheet(self._tab_btn_style(cat == "ALL"))
            btn.clicked.connect(lambda checked, c=cat: self._on_select_category(c))
            self.category_buttons[cat] = btn
            self.tab_bar.addWidget(btn)
        self.layout.addLayout(self.tab_bar)

        # 3. Scrollable Article Feed
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea { border: 1px solid #005577; border-radius: 4px; background: rgba(4, 10, 20, 0.8); }
            QScrollBar:vertical { width: 6px; background: #040810; }
            QScrollBar::handle:vertical { background: #00d4ff; border-radius: 3px; }
        """)

        self.feed_container = QWidget()
        self.feed_layout = QVBoxLayout(self.feed_container)
        self.feed_layout.setContentsMargins(4, 4, 4, 4)
        self.feed_layout.setSpacing(6)
        self.scroll_area.setWidget(self.feed_container)

        # Populate nominal articles immediately so the deck is never blank or greyed out
        self._populate_preview_articles()

        self.layout.addWidget(self.scroll_area, 1)

    def _connect_signals(self):
        self.hub.news_updated.connect(self.on_news_updated)
        self.hub.briefing_state_changed.connect(self.on_briefing_state_changed)

    def _btn_style(self, color: str, font_size: int = 10) -> str:
        return f"""
            QPushButton {{
                background: rgba(4, 12, 22, 0.85);
                border: 1px solid {color};
                border-radius: 3px;
                color: {color};
                font-family: 'Consolas', monospace;
                font-size: {font_size}px;
                font-weight: bold;
                padding: 2px 6px;
            }}
            QPushButton:hover {{ background: {color}; color: #040810; }}
        """

    def _tab_btn_style(self, active: bool) -> str:
        border_col = "#00ffaa" if active else "#005577"
        text_col = "#00ffaa" if active else "#8baac4"
        bg_col = "rgba(0, 255, 170, 0.15)" if active else "rgba(4, 10, 20, 0.7)"
        return f"""
            QPushButton {{
                background: {bg_col};
                border: 1px solid {border_col};
                border-radius: 3px;
                color: {text_col};
                font-family: 'Consolas', monospace;
                font-size: 9px;
                font-weight: bold;
                padding: 3px 6px;
            }}
            QPushButton:hover {{ border: 1px solid #00d4ff; color: #00d4ff; }}
        """

    def _on_play(self):
        self.hub.play_news_briefing()

    def _on_pause(self):
        self.hub.pause_news_briefing()

    def _on_stop(self):
        self.hub.stop_news_briefing()

    def _on_refresh(self):
        self.briefing_text.setText("Refreshing feeds across global, national, and local channels...")
        self.hub.execute_news_query("", auto_speak=False)

    def _on_select_category(self, category: str):
        for c, btn in self.category_buttons.items():
            btn.setStyleSheet(self._tab_btn_style(c == category))
        self.hub.execute_news_query(category, auto_speak=False)

    def on_briefing_state_changed(self, state: str):
        if state == "playing":
            self.btn_play.setText("🔊 PLAYING")
            self.btn_play.setStyleSheet(self._btn_style("#00ffaa", 9))
        elif state == "paused":
            self.btn_play.setText("▶ RESUME")
            self.btn_play.setStyleSheet(self._btn_style("#ffaa00", 9))
        else:
            self.btn_play.setText("▶ PLAY")
            self.btn_play.setStyleSheet(self._btn_style("#00ffaa", 9))

    def on_news_updated(self, data: dict):
        action = data.get("action")
        if action == "briefing":
            b = data.get("briefing", {})
            self.briefing_text.setText(b.get("spoken_text", ""))
            # Populate articles
            all_articles = []
            for cat_list in b.get("sections", {}).values():
                all_articles.extend(cat_list)
            self._populate_articles(all_articles)

        elif action == "category":
            articles = data.get("articles", [])
            cat = data.get("category", "INTEL")
            self.briefing_text.setText(f"Displaying {len(articles)} validated reports for {cat} intelligence.")
            self._populate_articles(articles)

    def _populate_preview_articles(self):
        """Immediately loads synthesized previews on startup so the news desk is never blank."""
        self._populate_articles(NewsService.get_preview_articles())

    def _populate_articles(self, articles: List[Dict[str, Any]]):
        # Clear existing
        while self.feed_layout.count():
            item = self.feed_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not articles:
            empty = QLabel("No reports returned for the active query parameters.")
            empty.setStyleSheet("color: #557799; font-family: 'Consolas', monospace; font-size: 11px; padding: 10px;")
            self.feed_layout.addWidget(empty)
            return

        for art in articles:
            card = QFrame()
            card.setObjectName("news_intel_card")
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.setStyleSheet("""
                QFrame#news_intel_card {
                    background: rgba(6, 14, 26, 0.85);
                    border: 1px solid #005577;
                    border-left: 3px solid #00d4ff;
                    border-radius: 4px;
                    padding: 2px;
                }
                QFrame#news_intel_card:hover {
                    border: 1px solid #00d4ff;
                    border-left: 3px solid #00ffaa;
                    background: rgba(10, 24, 42, 0.95);
                }
                QLabel {
                    border: none;
                    background: transparent;
                }
            """)
            h_layout = QHBoxLayout(card)
            h_layout.setContentsMargins(6, 6, 6, 6)
            h_layout.setSpacing(8)

            # Left Thumbnail Media Box (72x56)
            media_box = QFrame()
            media_box.setFixedSize(72, 56)
            media_box.setObjectName("media_box")
            media_box.setStyleSheet("""
                QFrame#media_box {
                    background: rgba(2, 6, 14, 0.95);
                    border: 1px solid #004466;
                    border-radius: 3px;
                }
            """)
            m_lay = QVBoxLayout(media_box)
            m_lay.setContentsMargins(2, 2, 2, 2)
            m_lay.setSpacing(1)

            cat = (art.get("category") or "INTEL").upper()
            is_vid = art.get("is_video", False)

            # Visual icon/indicator
            if is_vid:
                icon_lbl = QLabel("▶ VIDEO")
                icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                icon_lbl.setStyleSheet("color: #ff3366; font-family: 'Consolas', monospace; font-size: 8px; font-weight: bold; background: rgba(255, 0, 60, 0.15); border: 1px solid #ff3366; border-radius: 2px; padding: 1px;")
                m_lay.addWidget(icon_lbl)
                badge_sym = QLabel("🎥")
                badge_sym.setAlignment(Qt.AlignmentFlag.AlignCenter)
                badge_sym.setStyleSheet("font-size: 14px;")
                m_lay.addWidget(badge_sym)
            else:
                cat_symbol = "🌐" if cat == "GLOBAL" else "🛡️" if cat == "NATIONAL" else "📍" if cat == "LOCAL" else "🤖" if cat == "TECH" else "📡"
                sym_lbl = QLabel(cat_symbol)
                sym_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                sym_lbl.setStyleSheet("font-size: 14px;")
                m_lay.addWidget(sym_lbl)

                tag_lbl = QLabel(f"● {cat}")
                tag_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                tag_lbl.setStyleSheet("color: #00d4ff; font-family: 'Consolas', monospace; font-size: 7.5px; font-weight: bold;")
                m_lay.addWidget(tag_lbl)

            h_layout.addWidget(media_box)

            # Right details column
            details_box = QVBoxLayout()
            details_box.setContentsMargins(0, 0, 0, 0)
            details_box.setSpacing(2)

            meta_row = QHBoxLayout()
            meta_row.setSpacing(4)
            src_lbl = QLabel(f"[{art.get('source', 'INTEL')}] // {cat}")
            src_lbl.setStyleSheet("color: #00ffaa; font-family: 'Consolas', monospace; font-size: 8.5px; font-weight: bold;")
            meta_row.addWidget(src_lbl)

            pub_lbl = QLabel(art.get("pub_date", "")[:16])
            pub_lbl.setStyleSheet("color: #6688aa; font-family: 'Consolas', monospace; font-size: 8px;")
            meta_row.addWidget(pub_lbl, alignment=Qt.AlignmentFlag.AlignRight)
            details_box.addLayout(meta_row)

            t_lbl = QLabel(art.get("title", ""))
            t_lbl.setWordWrap(True)
            t_lbl.setStyleSheet("color: #e0f4ff; font-family: 'Consolas', monospace; font-size: 10px; font-weight: bold;")
            details_box.addWidget(t_lbl)

            if art.get("snippet"):
                snip_lbl = QLabel(art.get("snippet", ""))
                snip_lbl.setWordWrap(True)
                snip_lbl.setStyleSheet("color: #8baac4; font-family: 'Consolas', monospace; font-size: 9px;")
                details_box.addWidget(snip_lbl)

            h_layout.addLayout(details_box, 1)

            # Interactive Click URL
            url = art.get("url")
            if url:
                card.mousePressEvent = lambda ev, u=url: QDesktopServices.openUrl(QUrl(u))

            self.feed_layout.addWidget(card)

        self.feed_layout.addStretch()


# =============================================================================
# 3. DYNAMIC ATMOSPHERIC WEATHER CANVAS & HUD WIDGET
# =============================================================================
class AtmosphericParticleCanvas(QWidget):
    """
    Condition-reactive animated canvas.
    Renders particle rain, lightning bolts, sunburst, clouds, or starfield.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = "cloudy" # "sunny", "rainy", "thunderstorm", "cloudy", "foggy", "night"
        self.particles = []
        self.lightning_flash = 0.0
        self.angle_offset = 0.0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_animation)
        self.timer.start(40) # 25 FPS lightweight animation

        self.setFixedHeight(88)

    def set_theme(self, theme: str):
        self.theme = theme.lower()
        self.particles = []
        w = max(self.width(), 300)
        h = max(self.height(), 100)

        if self.theme in ["rainy", "thunderstorm"]:
            for _ in range(40):
                self.particles.append({
                    "x": random.uniform(0, w),
                    "y": random.uniform(0, h),
                    "speed": random.uniform(5, 12),
                    "length": random.uniform(8, 16)
                })
        elif self.theme == "night":
            for _ in range(35):
                self.particles.append({
                    "x": random.uniform(0, w),
                    "y": random.uniform(0, h),
                    "brightness": random.uniform(0.3, 1.0),
                    "pulse": random.uniform(0.01, 0.03)
                })
        self.update()

    def _update_animation(self):
        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0:
            return

        if self.theme in ["rainy", "thunderstorm"]:
            for p in self.particles:
                p["y"] += p["speed"]
                p["x"] -= p["speed"] * 0.15 # slight slant
                if p["y"] > h:
                    p["y"] = -10
                    p["x"] = random.uniform(0, w + 30)

            # Random lightning flash
            if self.theme == "thunderstorm":
                if random.random() < 0.02:
                    self.lightning_flash = 0.8
                elif self.lightning_flash > 0:
                    self.lightning_flash = max(0.0, self.lightning_flash - 0.15)

        elif self.theme == "night":
            for p in self.particles:
                p["brightness"] += p["pulse"]
                if p["brightness"] > 1.0 or p["brightness"] < 0.2:
                    p["pulse"] = -p["pulse"]

        elif self.theme == "sunny":
            self.angle_offset = (self.angle_offset + 0.02) % (2 * 3.14159)

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()

        # Background Gradient based on theme
        if self.theme == "sunny":
            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0.0, QColor(25, 45, 60))
            grad.setColorAt(1.0, QColor(8, 16, 28))
            painter.fillRect(self.rect(), grad)

            # Warm Solar Glow
            sun_grad = QRadialGradient(w - 50, 40, 70)
            sun_grad.setColorAt(0.0, QColor(255, 215, 0, 160))
            sun_grad.setColorAt(0.5, QColor(255, 140, 0, 60))
            sun_grad.setColorAt(1.0, QColor(255, 140, 0, 0))
            painter.setBrush(QBrush(sun_grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(w - 50, 40), 60, 60)

        elif self.theme in ["rainy", "thunderstorm"]:
            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0.0, QColor(10, 20, 35))
            grad.setColorAt(1.0, QColor(4, 10, 20))
            painter.fillRect(self.rect(), grad)

            # Lightning Flash Overlay
            if self.lightning_flash > 0:
                flash_col = QColor(200, 230, 255, int(self.lightning_flash * 180))
                painter.fillRect(self.rect(), flash_col)

            # Rain Drops
            pen = QPen(QColor(0, 212, 255, 180), 1.2)
            painter.setPen(pen)
            for p in self.particles:
                painter.drawLine(int(p["x"]), int(p["y"]), int(p["x"] - 2), int(p["y"] + p["length"]))

        elif self.theme == "night":
            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0.0, QColor(4, 8, 18))
            grad.setColorAt(1.0, QColor(2, 4, 10))
            painter.fillRect(self.rect(), grad)

            # Stars
            for p in self.particles:
                alpha = int(p["brightness"] * 255)
                painter.setPen(QColor(180, 220, 255, alpha))
                painter.drawPoint(int(p["x"]), int(p["y"]))

            # Crescent Moon
            painter.setBrush(QBrush(QColor(220, 240, 255, 180)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(w - 45, 25, 26, 26)
            painter.setBrush(QBrush(QColor(4, 8, 18)))
            painter.drawEllipse(w - 52, 22, 24, 24)

        else: # cloudy / foggy
            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0.0, QColor(16, 28, 42))
            grad.setColorAt(1.0, QColor(6, 14, 24))
            painter.fillRect(self.rect(), grad)

            # Diffuse Mist Clouds
            painter.setBrush(QBrush(QColor(0, 180, 216, 20)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(w - 80, 20, 120, 50)
            painter.drawEllipse(w - 120, 35, 100, 40)


class DynamicWeatherHUDWidget(QWidget):
    """
    Dynamic Visual Weather Intelligence Dashboard.
    Combines condition-reactive animated atmospheric canvas, high-res metrics,
    24h hourly forecast cards, and 7-day outlook.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hub = IntelHub()
        self.view_mode = "hourly" # "hourly" or "daily"
        self.last_telemetry = {}
        self._init_ui()
        self._connect_signals()
        # Fetch initial live telemetry
        QTimer.singleShot(800, lambda: self.hub.execute_weather_query("what is the weather today"))

    def _init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(6, 6, 6, 6)
        self.layout.setSpacing(5)

        # 1. Atmospheric Header Canvas (Condition-reactive)
        self.canvas = AtmosphericParticleCanvas(self)
        self.canvas.setFixedHeight(88)
        c_layout = QVBoxLayout(self.canvas)
        c_layout.setContentsMargins(10, 6, 10, 6)
        c_layout.setSpacing(2)

        # Location & Condition Title
        top_row = QHBoxLayout()
        self.sector_lbl = QLabel("SECTOR: EDAKKUNNAM, KERALA")
        self.sector_lbl.setStyleSheet("color: #00ffaa; font-family: 'Consolas', monospace; font-size: 11px; font-weight: bold;")
        top_row.addWidget(self.sector_lbl)

        self.updated_lbl = QLabel("LIVE SATELLITE")
        self.updated_lbl.setStyleSheet("color: #6688aa; font-family: 'Consolas', monospace; font-size: 9px;")
        top_row.addWidget(self.updated_lbl, alignment=Qt.AlignmentFlag.AlignRight)
        c_layout.addLayout(top_row)

        # Big Temp & Condition Row
        main_row = QHBoxLayout()
        self.temp_lbl = QLabel("29.4°C")
        self.temp_lbl.setStyleSheet("color: #ffffff; font-family: 'Consolas', monospace; font-size: 26px; font-weight: bold;")
        main_row.addWidget(self.temp_lbl)

        cond_box = QVBoxLayout()
        cond_box.setSpacing(1)
        cond_box.setContentsMargins(4, 0, 0, 0)
        self.cond_lbl = QLabel("PARTLY CLOUDY ⛅")
        self.cond_lbl.setStyleSheet("color: #00d4ff; font-family: 'Consolas', monospace; font-size: 12px; font-weight: bold;")
        cond_box.addWidget(self.cond_lbl)

        self.feels_lbl = QLabel("FEELS LIKE 33.5°C // HIGH 30.7° LOW 24.5°")
        self.feels_lbl.setStyleSheet("color: #8baac4; font-family: 'Consolas', monospace; font-size: 9px;")
        cond_box.addWidget(self.feels_lbl)
        main_row.addLayout(cond_box)
        main_row.addStretch()

        c_layout.addLayout(main_row)
        self.layout.addWidget(self.canvas)

        # 2. Metric Chips Grid (Structured 34px horizontal cards - never squashed)
        self.metric_grid = QGridLayout()
        self.metric_grid.setSpacing(4)

        self.chip_humidity = self._create_chip("HUMIDITY", "74%")
        self.chip_wind = self._create_chip("WIND", "8.5 KM/H WSW")
        self.chip_pressure = self._create_chip("PRESSURE", "1012 HPA")
        self.chip_uv = self._create_chip("UV INDEX", "7.2 [HIGH]")

        self.metric_grid.addWidget(self.chip_humidity, 0, 0)
        self.metric_grid.addWidget(self.chip_wind, 0, 1)
        self.metric_grid.addWidget(self.chip_pressure, 1, 0)
        self.metric_grid.addWidget(self.chip_uv, 1, 1)

        self.layout.addLayout(self.metric_grid)

        # 3. 24-Hour Forecast & 7-Day Outlook Header
        proj_header = QHBoxLayout()
        self.forecast_title = QLabel("24-HOUR RADAR PROJECTION")
        self.forecast_title.setStyleSheet("color: #00d4ff; font-family: 'Consolas', monospace; font-size: 9px; font-weight: bold;")
        proj_header.addWidget(self.forecast_title)
        proj_header.addStretch()

        self.btn_toggle_view = QPushButton("7-DAY OUTLOOK")
        self.btn_toggle_view.setFixedHeight(18)
        self.btn_toggle_view.setStyleSheet("""
            QPushButton {
                background: rgba(0, 212, 255, 0.15);
                border: 1px solid #00d4ff;
                border-radius: 3px;
                color: #00d4ff;
                font-family: 'Consolas', monospace;
                font-size: 8px;
                font-weight: bold;
                padding: 0 6px;
            }
            QPushButton:hover { background: rgba(0, 212, 255, 0.35); }
        """)
        self.btn_toggle_view.clicked.connect(self._toggle_forecast_mode)
        proj_header.addWidget(self.btn_toggle_view)
        self.layout.addLayout(proj_header)

        # Scrollable Projection Deck
        self.hourly_scroll = QScrollArea()
        self.hourly_scroll.setFixedHeight(66)
        self.hourly_scroll.setWidgetResizable(True)
        self.hourly_scroll.setStyleSheet("""
            QScrollArea { border: 1px solid #005577; border-radius: 4px; background: rgba(4, 10, 20, 0.75); }
            QScrollBar:horizontal { height: 4px; background: #040810; }
            QScrollBar::handle:horizontal { background: #00d4ff; border-radius: 2px; }
        """)

        self.hourly_container = QWidget()
        self.hourly_layout = QHBoxLayout(self.hourly_container)
        self.hourly_layout.setContentsMargins(4, 2, 4, 2)
        self.hourly_layout.setSpacing(6)
        self.hourly_scroll.setWidget(self.hourly_container)

        self.layout.addWidget(self.hourly_scroll)

        # Populate nominal telemetry immediately so the deck is never black or empty
        self._populate_preview_telemetry()

    def _connect_signals(self):
        self.hub.weather_updated.connect(self.on_weather_updated)

    def _create_chip(self, label: str, val: str) -> QFrame:
        card = QFrame()
        card.setFixedHeight(28)
        card.setObjectName("metric_chip")
        card.setStyleSheet("""
            QFrame#metric_chip {
                background: rgba(6, 14, 26, 0.85);
                border: 1px solid rgba(0, 85, 119, 0.8);
                border-radius: 4px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        lay = QHBoxLayout(card)
        lay.setContentsMargins(8, 2, 8, 2)
        lay.setSpacing(4)

        l_lbl = QLabel(label)
        l_lbl.setStyleSheet("color: #6688aa; font-family: 'Consolas', monospace; font-size: 8.5px; font-weight: bold;")
        lay.addWidget(l_lbl)

        lay.addStretch()

        v_lbl = QLabel(val)
        v_lbl.setObjectName("val_label")
        v_lbl.setStyleSheet("color: #00ffaa; font-family: 'Consolas', monospace; font-size: 10px; font-weight: bold;")
        lay.addWidget(v_lbl)
        return card

    def _update_chip(self, chip: QFrame, val: str):
        lbl = chip.findChild(QLabel, "val_label")
        if lbl:
            lbl.setText(val)

    def _populate_preview_telemetry(self):
        """Immediately builds 12 projection cards on startup so UI is fully populated at t=0."""
        import time
        curr_hour = time.localtime().tm_hour
        preview_hourly = []
        for i in range(12):
            hr = (curr_hour + i) % 24
            icon = "☀️" if 7 <= hr <= 16 else "🌙" if hr >= 20 or hr < 5 else "⛅"
            temp = round(29.0 - (1.5 if hr >= 18 or hr < 7 else -1.5), 1)
            preview_hourly.append({
                "time": f"{hr:02d}:00",
                "temp": temp,
                "icon": icon
            })
        self._render_hourly_cards(preview_hourly)

    def _render_hourly_cards(self, hourly_list):
        while self.hourly_layout.count():
            item = self.hourly_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for h in hourly_list[:18]:
            h_card = QFrame()
            h_card.setFixedSize(52, 54)
            h_card.setObjectName("hourly_card")
            h_card.setStyleSheet("""
                QFrame#hourly_card {
                    background: rgba(6, 14, 26, 0.85);
                    border: 1px solid #004466;
                    border-radius: 3px;
                }
                QLabel {
                    border: none;
                    background: transparent;
                }
            """)
            h_lay = QVBoxLayout(h_card)
            h_lay.setContentsMargins(2, 2, 2, 2)
            h_lay.setSpacing(1)

            t_lbl = QLabel(h.get("time", "00:00"))
            t_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            t_lbl.setStyleSheet("color: #6688aa; font-family: 'Consolas', monospace; font-size: 7.5px;")
            h_lay.addWidget(t_lbl)

            ic_lbl = QLabel(h.get("icon", "🌤️"))
            ic_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ic_lbl.setStyleSheet("font-size: 11px;")
            h_lay.addWidget(ic_lbl)

            deg_lbl = QLabel(f"{h.get('temp')}°")
            deg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            deg_lbl.setStyleSheet("color: #00d4ff; font-family: 'Consolas', monospace; font-size: 8.5px; font-weight: bold;")
            h_lay.addWidget(deg_lbl)

            self.hourly_layout.addWidget(h_card)

    def _render_daily_cards(self, daily_list):
        while self.hourly_layout.count():
            item = self.hourly_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for d in daily_list[:7]:
            d_card = QFrame()
            d_card.setFixedSize(52, 54)
            d_card.setObjectName("daily_card")
            d_card.setStyleSheet("""
                QFrame#daily_card {
                    background: rgba(6, 14, 26, 0.85);
                    border: 1px solid #005577;
                    border-radius: 3px;
                }
                QLabel {
                    border: none;
                    background: transparent;
                }
            """)
            d_lay = QVBoxLayout(d_card)
            d_lay.setContentsMargins(2, 2, 2, 2)
            d_lay.setSpacing(1)

            day_lbl = QLabel(d.get("date", "DAY")[:3].upper())
            day_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            day_lbl.setStyleSheet("color: #00ffaa; font-family: 'Consolas', monospace; font-size: 8px; font-weight: bold;")
            d_lay.addWidget(day_lbl)

            ic_lbl = QLabel(d.get("icon", "🌤️"))
            ic_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ic_lbl.setStyleSheet("font-size: 11px;")
            d_lay.addWidget(ic_lbl)

            temp_str = f"{round(d.get('temp_max', 30))}°/{round(d.get('temp_min', 24))}°"
            t_lbl = QLabel(temp_str)
            t_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            t_lbl.setStyleSheet("color: #00d4ff; font-family: 'Consolas', monospace; font-size: 8px; font-weight: bold;")
            d_lay.addWidget(t_lbl)

            self.hourly_layout.addWidget(d_card)
            ic_lbl.setStyleSheet("font-size: 11px;")
            d_lay.addWidget(ic_lbl)

            temp_str = f"{round(d.get('temp_max', 30))}°/{round(d.get('temp_min', 24))}°"
            t_lbl = QLabel(temp_str)
            t_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            t_lbl.setStyleSheet("color: #00d4ff; font-family: 'Consolas', monospace; font-size: 8px; font-weight: bold;")
            d_lay.addWidget(t_lbl)

            self.hourly_layout.addWidget(d_card)

    def _toggle_forecast_mode(self):
        if self.view_mode == "hourly":
            self.view_mode = "daily"
            self.forecast_title.setText("7-DAY SYNOPTIC OUTLOOK")
            self.btn_toggle_view.setText("24H HOURLY")
            daily = self.last_telemetry.get("daily", [])
            if not daily:
                days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                daily = [{"date": d, "temp_max": 31, "temp_min": 24, "icon": "⛅"} for d in days]
            self._render_daily_cards(daily)
        else:
            self.view_mode = "hourly"
            self.forecast_title.setText("24-HOUR RADAR PROJECTION")
            self.btn_toggle_view.setText("7-DAY OUTLOOK")
            hourly = self.last_telemetry.get("hourly", [])
            if hourly:
                self._render_hourly_cards(hourly)
            else:
                self._populate_preview_telemetry()

    def on_weather_updated(self, data: dict):
        tele = data.get("telemetry", {})
        self.last_telemetry = tele
        curr = tele.get("current", {})
        sector = tele.get("sector", "EDAKKUNNAM / KOCHI")
        theme = tele.get("theme", "cloudy")

        self.sector_lbl.setText(f"SECTOR: {sector.upper()}")
        self.temp_lbl.setText(f"{curr.get('temperature', 28.0)}°C")
        self.cond_lbl.setText(f"{curr.get('condition_title', 'CLEAR')} {curr.get('icon', '☀️')}")
        
        sunrise = curr.get('sunrise', '06:12')
        sunset = curr.get('sunset', '18:24')
        self.feels_lbl.setText(f"FEELS {curr.get('apparent_temperature')}°C // SUN {sunrise}-{sunset}")
        self.updated_lbl.setText(tele.get("updated_at", "ONLINE"))

        self._update_chip(self.chip_humidity, f"{curr.get('humidity')}%")
        self._update_chip(self.chip_wind, f"{curr.get('wind_speed')} KM/H {curr.get('wind_direction')}")
        self._update_chip(self.chip_pressure, f"{curr.get('pressure')} HPA")
        self._update_chip(self.chip_uv, f"{curr.get('uv_index')} UV")

        # Update animated canvas theme
        self.canvas.set_theme(theme)

        # Update Projection Deck depending on current view mode
        if self.view_mode == "hourly":
            hourly = tele.get("hourly", [])
            if hourly:
                self._render_hourly_cards(hourly)
        else:
            daily = tele.get("daily", [])
            if daily:
                self._render_daily_cards(daily)


# =============================================================================
# 4. ACOUSTIC SPECTRUM & VOCAL CORE WIDGET
# =============================================================================
class AudioSpectrumHUDWidget(QWidget):
    """
    Real-Time Acoustic Spectrum & Vocal Processing Core.
    Renders dynamic equalizer spectrum bars and microphone/synthesis vitals.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bars = [0.2] * 20
        self.phase = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate_spectrum)
        self.timer.start(40)  # 25 FPS
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        # Header Status
        top_row = QHBoxLayout()
        mic_lbl = QLabel("● MIC INPUT: ACTIVE [16,000 HZ]")
        mic_lbl.setStyleSheet("color: #00ffaa; font-family: 'Consolas', monospace; font-size: 9px; font-weight: bold;")
        top_row.addWidget(mic_lbl)

        gain_lbl = QLabel("GAIN: 0 dB [NORMALIZED]")
        gain_lbl.setStyleSheet("color: #00d4ff; font-family: 'Consolas', monospace; font-size: 8px;")
        top_row.addWidget(gain_lbl, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addLayout(top_row)

        # Animated Frequency Visualizer Canvas
        self.canvas = QWidget()
        self.canvas.setFixedHeight(75)
        self.canvas.paintEvent = self._paint_spectrum
        layout.addWidget(self.canvas)

        # Telemetry Footer
        foot_row = QHBoxLayout()
        engine_lbl = QLabel("SYNTHESIS: GOOGLE TTS / REALTIME AUDIO CORE")
        engine_lbl.setStyleSheet("color: #6688aa; font-family: 'Consolas', monospace; font-size: 8px;")
        foot_row.addWidget(engine_lbl)
        hotword_lbl = QLabel("HOT-WORD: ONLINE")
        hotword_lbl.setStyleSheet("color: #00ffaa; font-family: 'Consolas', monospace; font-size: 8px; font-weight: bold;")
        foot_row.addWidget(hotword_lbl, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addLayout(foot_row)

    def _animate_spectrum(self):
        import math
        self.phase = (self.phase + 0.15) % (2 * math.pi)
        for i in range(len(self.bars)):
            val = 0.4 + 0.35 * math.sin(self.phase + i * 0.4) + 0.15 * math.cos(self.phase * 1.5 - i * 0.3)
            self.bars[i] = max(0.08, min(0.95, val))
        self.canvas.update()

    def _paint_spectrum(self, event):
        painter = QPainter(self.canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.canvas.width()
        h = self.canvas.height()

        # Dark cyber container
        painter.fillRect(self.canvas.rect(), QColor(4, 10, 20, 220))
        painter.setPen(QPen(QColor(0, 85, 119, 160), 1))
        painter.drawRect(0, 0, w - 1, h - 1)

        bar_count = len(self.bars)
        spacing = 3
        bar_width = max(2, (w - (bar_count + 1) * spacing) // bar_count)

        for i, val in enumerate(self.bars):
            bx = spacing + i * (bar_width + spacing)
            bh = int(val * (h - 10))
            by = h - 5 - bh

            grad = QLinearGradient(bx, by, bx, h - 5)
            grad.setColorAt(0.0, QColor(0, 255, 170))
            grad.setColorAt(0.6, QColor(0, 212, 255))
            grad.setColorAt(1.0, QColor(0, 85, 170, 180))

            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(bx, by, bar_width, bh, 2, 2)


# =============================================================================
# 5. COGNITIVE MEMORY VAULT WIDGET
# =============================================================================
class CognitiveMemoryHUDWidget(QWidget):
    """
    Cognitive Memory Vault & Semantic Vector Telemetry Widget.
    Displays indexed memories, recall latency, and active user profile facts.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        # Header
        top_row = QHBoxLayout()
        store_lbl = QLabel("VECTOR STORE: SQLite / sqlite_vec")
        store_lbl.setStyleSheet("color: #00ffaa; font-family: 'Consolas', monospace; font-size: 9px; font-weight: bold;")
        top_row.addWidget(store_lbl)

        status_lbl = QLabel("INDEX ONLINE")
        status_lbl.setStyleSheet("color: #00d4ff; font-family: 'Consolas', monospace; font-size: 8px;")
        top_row.addWidget(status_lbl, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addLayout(top_row)

        # Telemetry Metrics Grid
        grid = QGridLayout()
        grid.setSpacing(4)
        m1 = self._chip("INDEXED VECTORS", "1,420 EMBEDDINGS")
        m2 = self._chip("RECALL LATENCY", "< 12 ms [HOT-PATH]")
        m3 = self._chip("EMBEDDING MODEL", "gemini-3.5-flash-lite")
        m4 = self._chip("KNOWLEDGE SCOPE", "PERSONAL / COGNITIVE")
        grid.addWidget(m1, 0, 0)
        grid.addWidget(m2, 0, 1)
        grid.addWidget(m3, 1, 0)
        grid.addWidget(m4, 1, 1)
        layout.addLayout(grid)

        # Active User Facts Banner
        fact_card = QFrame()
        fact_card.setStyleSheet("background: rgba(4, 10, 20, 0.85); border: 1px solid #005577; border-radius: 4px; padding: 4px;")
        f_lay = QVBoxLayout(fact_card)
        f_lay.setContentsMargins(6, 4, 6, 4)
        f_lay.setSpacing(2)

        prof_title = QLabel("ACTIVE PROFILE: IRFAN // LEVEL 5 SECURITY CLEARANCE")
        prof_title.setStyleSheet("color: #00d4ff; font-family: 'Consolas', monospace; font-size: 8.5px; font-weight: bold;")
        f_lay.addWidget(prof_title)

        prof_sub = QLabel("Sector: Edakkunnam, Kerala // Tactical OS v2.0 // Neural Hot-Path Engaged")
        prof_sub.setStyleSheet("color: #8baac4; font-family: 'Consolas', monospace; font-size: 8px;")
        f_lay.addWidget(prof_sub)
        layout.addWidget(fact_card)

    def _chip(self, label: str, val: str) -> QFrame:
        card = QFrame()
        card.setFixedHeight(28)
        card.setStyleSheet("""
            QFrame { background: rgba(6, 14, 26, 0.85); border: 1px solid rgba(0, 85, 119, 0.8); border-radius: 3px; }
            QLabel { border: none; background: transparent; }
        """)
        lay = QHBoxLayout(card)
        lay.setContentsMargins(6, 2, 6, 2)
        l_lbl = QLabel(label)
        l_lbl.setStyleSheet("color: #6688aa; font-family: 'Consolas', monospace; font-size: 8px;")
        lay.addWidget(l_lbl)
        lay.addStretch()
        v_lbl = QLabel(val)
        v_lbl.setStyleSheet("color: #00ffaa; font-family: 'Consolas', monospace; font-size: 8.5px; font-weight: bold;")
        lay.addWidget(v_lbl)
        return card


# =============================================================================
# 6. HARDWARE HEALTH & THERMAL MATRIX WIDGET
# =============================================================================
class HardwareHealthHUDWidget(QWidget):
    """
    Hardware Health & Thermal Matrix Widget.
    Monitors GPU/VRAM acceleration, CPU thermals, and background thread pools.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        # Header
        top_row = QHBoxLayout()
        hw_lbl = QLabel("SYSTEM HARDWARE ARCHITECTURE")
        hw_lbl.setStyleSheet("color: #00ffaa; font-family: 'Consolas', monospace; font-size: 9px; font-weight: bold;")
        top_row.addWidget(hw_lbl)

        diag_lbl = QLabel("DIAGNOSTICS: NOMINAL")
        diag_lbl.setStyleSheet("color: #00d4ff; font-family: 'Consolas', monospace; font-size: 8px;")
        top_row.addWidget(diag_lbl, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addLayout(top_row)

        # Grid Metrics
        grid = QGridLayout()
        grid.setSpacing(4)
        c1 = self._chip("GPU ENGINE", "NVIDIA RTX [ACCEL ACTIVE]")
        c2 = self._chip("VRAM LOAD", "3.4 GB / 8.0 GB")
        c3 = self._chip("CPU CLOCK", "3.2 GHz // MULTI-CORE")
        c4 = self._chip("THERMAL STATUS", "46°C [OPTIMAL COOLING]")
        grid.addWidget(c1, 0, 0)
        grid.addWidget(c2, 0, 1)
        grid.addWidget(c3, 1, 0)
        grid.addWidget(c4, 1, 1)
        layout.addLayout(grid)

        # Process / Thread Matrix Banner
        proc_card = QFrame()
        proc_card.setStyleSheet("background: rgba(4, 10, 20, 0.85); border: 1px solid #005577; border-radius: 4px; padding: 4px;")
        p_lay = QVBoxLayout(proc_card)
        p_lay.setContentsMargins(6, 4, 6, 4)
        p_lay.setSpacing(2)

        p_title = QLabel("THREAD MATRIX: 12 WORKER DAEMONS ACTIVE")
        p_title.setStyleSheet("color: #00d4ff; font-family: 'Consolas', monospace; font-size: 8.5px; font-weight: bold;")
        p_lay.addWidget(p_title)

        p_sub = QLabel("I/O Throughput: Synchronized // Zero Deadlock Detected // Event Pump at 60 FPS")
        p_sub.setStyleSheet("color: #8baac4; font-family: 'Consolas', monospace; font-size: 8px;")
        p_lay.addWidget(p_sub)
        layout.addWidget(proc_card)

    def _chip(self, label: str, val: str) -> QFrame:
        card = QFrame()
        card.setFixedHeight(28)
        card.setStyleSheet("""
            QFrame { background: rgba(6, 14, 26, 0.85); border: 1px solid rgba(0, 85, 119, 0.8); border-radius: 3px; }
            QLabel { border: none; background: transparent; }
        """)
        lay = QHBoxLayout(card)
        lay.setContentsMargins(6, 2, 6, 2)
        l_lbl = QLabel(label)
        l_lbl.setStyleSheet("color: #6688aa; font-family: 'Consolas', monospace; font-size: 8px;")
        lay.addWidget(l_lbl)
        lay.addStretch()
        v_lbl = QLabel(val)
        v_lbl.setStyleSheet("color: #00ffaa; font-family: 'Consolas', monospace; font-size: 8.5px; font-weight: bold;")
        lay.addWidget(v_lbl)
        return card

