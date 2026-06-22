import sys
import os
import json

# =========================================================================
# THE CHROMIUM DIET: Forces Qt to render in a single, silent, low-RAM thread
# =========================================================================
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--single-process --process-per-site --disable-logging --log-level=3"
os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.webenginecontext=false"

import requests
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QLabel, QFrame, QHBoxLayout, QPushButton, QGridLayout, QSizeGrip)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPoint
from PyQt6.QtGui import QCursor
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtNetwork import QUdpSocket, QHostAddress


class TacticalGeocodeWorker(QThread):
    coord_ready = pyqtSignal(float, float, str, int)
    error_signal = pyqtSignal(str)

    def __init__(self, location_query):
        super().__init__()
        self.raw_query = location_query.strip()

    def calculate_smart_altitude(self, addr_type):
        """The Altitude Matrix: Maps Esri ontology tags to Leaflet zoom levels"""
        ontology = {
            "Country": 5,        # Whole landmass view
            "State": 7,          # State / Province view
            "Province": 7,
            "Prefecture": 8,
            "County": 10,
            "City": 12,          # Metro area view
            "Subregion": 12,
            "Locality": 14,      # Town / Village view
            "Zone": 15,
            "Neighborhood": 16,  # Panchayat / Neighborhood level
            "StreetAddress": 17, # Pinpoint street level
            "PointAddress": 18,
            "POI": 18            # Specific monument/shop
        }
        return ontology.get(addr_type, 14)

    def run(self):
        headers = {'User-Agent': 'JarvisCommandCore/2.0'}
        esri_url = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates"
        base_params = {'f': 'json', 'maxLocations': 1, 'outFields': 'Addr_type'}

        # --- ATTEMPT 1: PURE GLOBAL RESOLUTION ---
        try:
            p = {**base_params, 'SingleLine': self.raw_query}
            res = requests.get(esri_url, params=p, headers=headers, timeout=4).json()
            if 'candidates' in res and len(res['candidates']) > 0:
                top = res['candidates'][0]
                if top['score'] >= 80:
                    tag = top.get('attributes', {}).get('Addr_type', 'Locality')
                    calculated_zoom = self.calculate_smart_altitude(tag)
                    self.coord_ready.emit(float(top['location']['y']), float(top['location']['x']), top['address'].upper(), calculated_zoom)
                    return
        except: pass

        # --- ATTEMPT 2: REGIONAL KERALA FALLBACK ---
        try:
            loc_query = self.raw_query if "," in self.raw_query else f"{self.raw_query}, Kottayam, Kerala, India"
            p = {**base_params, 'SingleLine': loc_query}
            res = requests.get(esri_url, params=p, headers=headers, timeout=4).json()
            if 'candidates' in res and len(res['candidates']) > 0:
                top = res['candidates'][0]
                tag = top.get('attributes', {}).get('Addr_type', 'Locality')
                calculated_zoom = self.calculate_smart_altitude(tag)
                self.coord_ready.emit(float(top['location']['y']), float(top['location']['x']), top['address'].upper(), calculated_zoom)
                return
        except Exception as e:
            self.error_signal.emit(f"GEO-ERROR: {str(e)}")
            return

        self.error_signal.emit(f"UNMAPPED: '{self.raw_query}'")


class CyberTitleBar(QFrame):
    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self.setFixedHeight(38)
        self.setStyleSheet("background-color: rgba(5, 7, 12, 245); border-bottom: 1px solid rgba(0, 212, 255, 0.3);")
        self.is_dragging = False
        self.drag_start_pos = QPoint()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 10, 0)
        self.title_lbl = QLabel("GOOGLE SPATIAL COMMAND // ORBITAL RECONNAISSANCE")
        self.title_lbl.setStyleSheet("color: #00d4ff; font: bold 13px 'Consolas'; border: none;")

        self.btn_pin = QPushButton("📌") 
        btn_min = QPushButton("🗕")
        self.btn_max = QPushButton("🗗") 
        btn_close = QPushButton("✕")

        for btn in [self.btn_pin, btn_min, self.btn_max, btn_close]:
            btn.setFixedSize(32, 26)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.btn_pin.setStyleSheet("QPushButton { color: rgba(255,255,255,0.4); background: transparent; border: none; font-size: 13px; } QPushButton:hover { background: rgba(0,255,170,0.2); color: #00ffaa; }")
        btn_min.setStyleSheet("QPushButton { color: #00ffaa; background: transparent; border: none; font-size: 13px; } QPushButton:hover { background: rgba(0,255,170,0.2); }")
        self.btn_max.setStyleSheet("QPushButton { color: #00d4ff; background: transparent; border: none; font-size: 13px; } QPushButton:hover { background: rgba(0,212,255,0.2); }")
        btn_close.setStyleSheet("QPushButton { color: #ff003c; background: transparent; border: none; font-size: 13px; } QPushButton:hover { background: #ff003c; color: white; }")

        self.btn_pin.clicked.connect(self.toggle_always_on_top)
        btn_min.clicked.connect(self.parent_window.showMinimized)
        self.btn_max.clicked.connect(self.toggle_window_mode)
        btn_close.clicked.connect(self.parent_window.close)

        layout.addWidget(self.title_lbl)
        layout.addStretch()
        layout.addWidget(self.btn_pin)
        layout.addWidget(btn_min)
        layout.addWidget(self.btn_max)
        layout.addWidget(btn_close)

    def toggle_always_on_top(self):
        flags = self.parent_window.windowFlags()
        if bool(flags & Qt.WindowType.WindowStaysOnTopHint):
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
            self.btn_pin.setStyleSheet("QPushButton { color: rgba(255,255,255,0.4); background: transparent; border: none; font-size: 13px; }")
        else:
            flags |= Qt.WindowType.WindowStaysOnTopHint
            self.btn_pin.setStyleSheet("QPushButton { color: #00ffaa; background: rgba(0,255,170,0.15); border: 1px solid #00ffaa; font-size: 13px; border-radius: 4px; }")
        self.parent_window.setWindowFlags(flags)
        self.parent_window.show()

    def toggle_window_mode(self):
        if self.parent_window.isFullScreen():
            self.parent_window.showNormal()   
            self.btn_max.setText("🗖")          
        else:
            self.parent_window.showFullScreen() 
            self.btn_max.setText("🗗")          

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.parent_window.isFullScreen():
            self.is_dragging = True
            self.drag_start_pos = event.globalPosition().toPoint() - self.parent_window.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self.is_dragging: self.parent_window.move(event.globalPosition().toPoint() - self.drag_start_pos)

    def mouseReleaseEvent(self, event): self.is_dragging = False


class TacticalMapApp(QMainWindow):
    def __init__(self, target_sector="Edakkunnam"):
        super().__init__()
        self.target_sector = target_sector
        self.current_map_mode = "vec" 
        self.is_web_view_booted = False 
        
        self.setWindowTitle("Jarvis Tactical Navigation Grid")
        self.resize(1400, 800) 
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.showFullScreen()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.init_ui()
        self.locate_sector(self.target_sector)

    def init_ui(self):
        self.central_widget = QFrame()
        self.central_widget.setStyleSheet("QFrame { background-color: rgba(4, 5, 8, 0.99); border: 1px solid #00d4ff; }")
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(1, 1, 1, 15) 
        self.main_layout.setSpacing(0)

        self.title_bar = CyberTitleBar(self)
        self.main_layout.addWidget(self.title_bar)

        self.stack_container = QWidget()
        self.stack_grid = QGridLayout(self.stack_container)
        self.stack_grid.setContentsMargins(0, 0, 0, 0)

        self.web_view = QWebEngineView()
        self.web_view.titleChanged.connect(self.intercept_js_title_bridge)
        self.stack_grid.addWidget(self.web_view, 0, 0)

        self.hud_pill = QFrame()
        self.hud_pill.setFixedSize(680, 48)
        self.hud_pill.setStyleSheet("background-color: rgba(5, 7, 12, 230); border: 1px solid #00ffaa; border-radius: 24px;")
        
        pill_layout = QHBoxLayout(self.hud_pill)
        pill_layout.setContentsMargins(20, 0, 20, 0)
        pill_layout.setSpacing(12)

        self.lbl_sector = QLabel("TARGET: [ ACQUIRING... ]")
        self.lbl_sector.setStyleSheet("color: #00d4ff; font: bold 13px 'Consolas'; background: transparent; border: none;")
        
        self.lbl_coords = QLabel("LAT: 0.00000 // LON: 0.00000")
        self.lbl_coords.setStyleSheet("color: rgba(255,255,255,0.7); font: 12px 'Consolas'; background: transparent; border: none;")
        
        self.lbl_status = QLabel("● STANDBY")
        self.lbl_status.setStyleSheet("color: #ffbb00; font: bold 12px 'Consolas'; background: transparent; border: none;")

        self.btn_mode_sat = QPushButton("ORBITAL SAT")
        self.btn_mode_sat.setFixedHeight(28)
        self.btn_mode_sat.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_mode_sat.clicked.connect(lambda: self.trigger_shader_switch("sat"))
        
        self.btn_mode_vec = QPushButton("TRON VECTOR")
        self.btn_mode_vec.setFixedHeight(28)
        self.btn_mode_vec.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_mode_vec.clicked.connect(lambda: self.trigger_shader_switch("vec"))

        pill_layout.addWidget(self.lbl_sector)
        pill_layout.addWidget(self.create_pill_separator())
        pill_layout.addWidget(self.lbl_coords)
        pill_layout.addWidget(self.create_pill_separator())
        pill_layout.addWidget(self.lbl_status)
        pill_layout.addStretch()
        pill_layout.addWidget(self.btn_mode_sat)
        pill_layout.addWidget(self.btn_mode_vec)

        self.stack_grid.addWidget(self.hud_pill, 0, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)

        self.resizer = QSizeGrip(self)
        self.resizer.setFixedSize(20, 20)
        self.resizer.setStyleSheet("QSizeGrip { background: transparent; }")
        self.stack_grid.addWidget(self.resizer, 0, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)

        self.main_layout.addWidget(self.stack_container)
        self.update_switcher_buttons()

        self.udp_receiver = QUdpSocket(self)
        self.udp_receiver.bind(QHostAddress.SpecialAddress.LocalHost, 7777)
        self.udp_receiver.readyRead.connect(self.intercept_telemetry_packet)

    def intercept_telemetry_packet(self):
        """The JSON-RPC Router: Parses incoming UDP datagram envelopes"""
        while self.udp_receiver.hasPendingDatagrams():
            size = self.udp_receiver.pendingDatagramSize()
            datagram, host, port = self.udp_receiver.readDatagram(size)
            raw_payload = datagram.decode('utf-8').strip()
            
            try:
                packet = json.loads(raw_payload)
                cmd = packet.get("command")
                
                if cmd == "locate":
                    self.lbl_status.setText("● RPC: FLY")
                    self.lbl_status.setStyleSheet("color: #00ffaa; font: bold 12px 'Consolas';")
                    self.locate_sector(packet.get("place", "Edakkunnam"))
                
                elif cmd == "zoom":
                    direction = packet.get("direction", "in")
                    steps = packet.get("factor", 1)
                    self.lbl_status.setText(f"● RPC: ZOOM {direction.upper()}")
                    self.lbl_status.setStyleSheet("color: #ff00ff; font: bold 12px 'Consolas';")
                    self.web_view.page().runJavaScript(f"executeZoom('{direction}', {steps});")
            
            except json.JSONDecodeError:
                self.locate_sector(raw_payload)

    def intercept_js_title_bridge(self, title):
        if title.startswith("MANUAL_PIN:"):
            try:
                lat, lon = map(float, title.split(":")[1].split(","))
                self.lbl_coords.setText(f"LAT: {lat:.5f} // LON: {lon:.5f}")
                self.lbl_status.setText("● REFINED")
                self.lbl_status.setStyleSheet("color: #00ffaa; font: bold 12px 'Consolas';")
            except: pass

    def create_pill_separator(self):
        lbl = QLabel("|")
        lbl.setStyleSheet("color: rgba(0, 255, 170, 0.3); font-size: 14px; background: transparent; border: none;")
        return lbl

    def update_switcher_buttons(self):
        act_style = "QPushButton { color: #00ffaa; font-weight: bold; font-family: 'Consolas'; font-size: 11px; background: rgba(0,255,170,0.15); border: 1px solid #00ffaa; border-radius: 6px; padding: 0 10px; }"
        dim_style = "QPushButton { color: rgba(255,255,255,0.4); font-family: 'Consolas'; font-size: 11px; background: transparent; border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 0 10px; }"
        self.btn_mode_sat.setStyleSheet(act_style if self.current_map_mode == "sat" else dim_style)
        self.btn_mode_vec.setStyleSheet(act_style if self.current_map_mode == "vec" else dim_style)

    def trigger_shader_switch(self, mode):
        self.current_map_mode = mode
        self.update_switcher_buttons()
        self.web_view.page().runJavaScript(f"switchGoogleMode('{mode}');")

    def locate_sector(self, query):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.disconnect() 
            self.worker.terminate()
            self.worker.wait()

        self.worker = TacticalGeocodeWorker(query)
        self.worker.coord_ready.connect(self.render_tactical_map)
        self.worker.error_signal.connect(self.handle_fault)
        self.worker.start()

    def render_tactical_map(self, lat, lon, clean_name, zoom_level):
        short_name = clean_name.split(",")[0] if clean_name else "UNKNOWN"
        if len(short_name) > 16: short_name = short_name[:14] + ".."
        
        self.lbl_sector.setText(f"TARGET: [ {short_name} ]")
        self.lbl_coords.setText(f"LAT: {lat:.4f} // LON: {lon:.4f}")
        self.lbl_status.setText("● LOCKED")
        self.lbl_status.setStyleSheet("color: #00d4ff; font: bold 12px 'Consolas'; background: transparent; border: none;")

        if self.is_web_view_booted:
            self.web_view.page().runJavaScript(f"flyToSector({lat}, {lon}, {zoom_level});")
            return

        html_head = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <style>
                html, body, #map { width: 100%; height: 100%; margin: 0; padding: 0; background: #010204; }
                .leaflet-control-zoom, .leaflet-control-attribution { display: none !important; }
                .google-vector-dark { filter: invert(100%) hue-rotate(180deg) contrast(145%) brightness(95%) saturate(200%); }
                #map::after {
                    content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
                    pointer-events: none; box-shadow: inset 0 0 80px rgba(0, 212, 255, 0.25), inset 0 0 20px rgba(0, 255, 170, 0.3); z-index: 1000;
                }
                .radar-crosshair {
                    width: 80px; height: 80px; border: 1.5px dashed #00ffaa; border-radius: 50%;
                    position: absolute; margin-left: -40px; margin-top: -40px;
                    animation: pulseRadar 3s infinite linear; box-shadow: 0 0 15px rgba(0, 255, 170, 0.3);
                }
                .radar-center {
                    width: 10px; height: 10px; background: #00ffaa; border-radius: 50%;
                    position: absolute; margin-left: -5px; margin-top: -5px;
                    box-shadow: 0 0 12px #00d4ff, 0 0 22px #00ffaa; animation: nodeGlow 1.5s infinite ease-in-out;
                }
                @keyframes pulseRadar { 0% { transform: rotate(0deg) scale(0.85); opacity: 0.5; } 50% { transform: rotate(180deg) scale(1.1); opacity: 0.95; } 100% { transform: rotate(360deg) scale(0.85); opacity: 0.5; } }
                @keyframes nodeGlow { 0%, 100% { transform: scale(0.9); opacity: 0.7; } 50% { transform: scale(1.3); opacity: 1; } }
            </style>
        </head>
        <body>
            <div id="map"></div>
            <script>
        """

        html_body = f"""
                var map = L.map('map', {{ zoomControl: false }}).setView([{lat}, {lon}], {zoom_level});
                var satLayer = L.tileLayer('https://mt1.google.com/vt/lyrs=y&x={{x}}&y={{y}}&z={{z}}', {{ maxZoom: 20 }});
                var vecLayer = L.tileLayer('https://mt1.google.com/vt/lyrs=m&x={{x}}&y={{y}}&z={{z}}', {{ maxZoom: 20, className: 'google-vector-dark' }});

                var currentLayer = vecLayer;
                currentLayer.addTo(map);

                window.switchGoogleMode = function(targetMode) {{
                    map.removeLayer(satLayer); map.removeLayer(vecLayer);
                    if (targetMode === 'sat') {{ satLayer.addTo(map); }} else {{ vecLayer.addTo(map); }}
                }};

                var radarIcon = L.divIcon({{ className: 'custom-radar-container', html: '<div class="radar-crosshair"></div><div class="radar-center"></div>' }});
                var currentMarker = L.marker([{lat}, {lon}], {{icon: radarIcon}}).addTo(map);

                // --- THE SELF-AWARE 1.5KM FLIGHT GUARD ---
                window.flyToSector = function(newLat, newLon, newZoom) {{
                    var curr = map.getCenter();
                    var dLat = Math.abs(curr.lat - newLat), dLon = Math.abs(curr.lng - newLon);
                    
                    if (dLat < 0.015 && dLon < 0.015) {{
                        newZoom = map.getZoom(); 
                    }}

                    map.flyTo([newLat, newLon], newZoom, {{ duration: 1.8, easeLinearity: 0.25 }});
                    if (currentMarker) map.removeLayer(currentMarker);
                    currentMarker = L.marker([newLat, newLon], {{icon: radarIcon}}).addTo(map);
                }};

                window.executeZoom = function(direction, steps) {{
                    var currentZoom = map.getZoom();
                    var newZoom = (direction === 'in') ? (currentZoom + steps) : (currentZoom - steps);
                    map.setZoom(newZoom);
                }};

                map.on('click', function(e) {{
                    var lLat = e.latlng.lat, lLng = e.latlng.lng;
                    if (currentMarker) map.removeLayer(currentMarker);
                    currentMarker = L.marker([lLat, lLng], {{icon: radarIcon}}).addTo(map);
                    document.title = "MANUAL_PIN:" + lLat.toFixed(6) + "," + lLng.toFixed(6);
                }});
        """
        self.web_view.setHtml(html_head + html_body + """</script></body></html>""")
        self.is_web_view_booted = True

    def handle_fault(self, err_msg):
        self.lbl_status.setText("● FAULT")
        self.lbl_status.setStyleSheet("color: #ff003c; font: bold 12px 'Consolas'; background: transparent; border: none;")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    sector = sys.argv[1] if len(sys.argv) > 1 else "Edakkunnam"
    window = TacticalMapApp(sector)
    window.show()
    sys.exit(app.exec())