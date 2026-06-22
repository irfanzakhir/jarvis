import sys
import os
import time
import json
import requests
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QLabel, QFrame, QHBoxLayout, QPushButton, QGridLayout, QSizeGrip)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, pyqtProperty, QRectF, QTimer, QPoint
from PyQt6.QtGui import QCursor, QPainter, QConicalGradient, QColor, QPen

CACHE_FILE = "openmeteo_atmospheric_cache.json"
CACHE_EXPIRY = 1800  # 30-Minute atmospheric data lock

WMO_CODES = {
    0: ("CLEAR SKY // OPTIMAL VISIBILITY", "☀️"),
    1: ("MAINLY CLEAR // STABLE AIRMASS", "🌤️"),
    2: ("PARTLY CLOUDY // SCATTERED IRRADIANCE", "⛅"),
    3: ("OVERCAST // DENSE CEILING", "☁️"),
    45: ("FOG // REDUCED KINETIC RANGE", "🌫️"),
    48: ("RIME FOG // THERMAL DEPOSITION", "🌁"),
    51: ("LIGHT DRIZZLE // MOISTURE PRECIP", "🌧️"),
    53: ("MODERATE DRIZZLE // SECTOR WET", "🌧️"),
    55: ("DENSE DRIZZLE // LOW VISIBILITY", "🌧️"),
    61: ("SLIGHT RAIN // ACTIVE PRECIPITATION", "🌦️"),
    63: ("MODERATE RAIN // SQUALL LINE", "🌧️"),
    65: ("HEAVY RAIN // SECTOR FLOOD WARNING", "⛈️"),
    71: ("SLIGHT SNOWFALL // ICE CRYSTAL DEPOSIT", "🌨️"),
    73: ("MODERATE SNOWFALL // THERMAL DROP", "❄️"),
    75: ("HEAVY SNOWFALL // BLIZZARD CONDITIONS", "❄️"),
    80: ("SLIGHT RAIN SHOWERS // LOCALIZED", "🌦️"),
    81: ("MODERATE RAIN SHOWERS // SQUALLS", "🌧️"),
    82: ("VIOLENT RAIN SHOWERS // MICROBURSTS", "⛈️"),
    95: ("THUNDERSTORM // ELECTRICAL ANOMALY", "🌩️"),
    96: ("THUNDERSTORM // SEVERE HAIL VECTOR", "⛈️"),
    99: ("HEAVY THUNDERSTORM // EXTREME HAIL", "⛈️")
}

# =========================================================================
# 1. NATIVE C++ HARDWARE SHADER: The CyberCard (Chasing Laser Border)
# =========================================================================
class CyberCard(QFrame):
    def __init__(self, parent=None, sweep_speed=3000):
        super().__init__(parent)
        self._angle = 0.0
        
        self._anim = QPropertyAnimation(self, b"glowAngle")
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(360.0)
        self._anim.setDuration(sweep_speed) 
        self._anim.setLoopCount(-1) 
        self._anim.start()

    @pyqtProperty(float)
    def glowAngle(self): return self._angle

    @glowAngle.setter
    def glowAngle(self, angle):
        self._angle = angle
        self.update() 

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        pad = 1.5
        draw_rect = QRectF(rect).adjusted(pad, pad, -pad, -pad)
        
        # Translucent dark glass core
        painter.setBrush(QColor(6, 8, 14, 210))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(draw_rect, 6.0, 6.0)
        
        center = draw_rect.center()
        grad = QConicalGradient(center, self._angle)
        
        grad.setColorAt(0.0, QColor(0, 212, 255, 255))     # Cyan tail
        grad.setColorAt(0.18, QColor(0, 212, 255, 0))      # Fade to void
        grad.setColorAt(0.85, QColor(0, 255, 170, 0))      # Void space
        grad.setColorAt(1.0, QColor(0, 255, 170, 255))     # Neon Green Beam Head

        pen = QPen(grad, 2.0)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(draw_rect, 6.0, 6.0)


# =========================================================================
# 2. THE KINETIC CHROME: Custom Title Bar with Hardware Pin Toggle
# =========================================================================
class CyberTitleBar(QFrame):
    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self.setFixedHeight(38)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(5, 7, 12, 245);
                border-bottom: 1px solid rgba(0, 212, 255, 0.3);
            }
        """)
        
        self.is_dragging = False
        self.drag_start_pos = QPoint()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 10, 0)

        self.title_lbl = QLabel("ATMOSPHERIC RADAR TELEMETRY // LINKING ORBITAL SHARDS")
        self.title_lbl.setStyleSheet("color: #00d4ff; font: bold 13px 'Consolas'; border: none;")

        # --- THE 4 WINDOW CONTROLLERS ---
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
        if self.is_dragging:
            self.parent_window.move(event.globalPosition().toPoint() - self.drag_start_pos)

    def mouseReleaseEvent(self, event):
        self.is_dragging = False


class OpenMeteoWorker(QThread):
    data_ready = pyqtSignal(dict, list, str) 
    error_signal = pyqtSignal(str)

    def __init__(self, target_location):
        super().__init__()
        self.target_location = target_location.strip()

    def run(self):
        try:
            cache_key = self.target_location.lower()
            if os.path.exists(CACHE_FILE):
                try:
                    with open(CACHE_FILE, 'r') as f:
                        cache = json.load(f)
                        loc_cache = cache.get(cache_key, {})
                        if loc_cache and (time.time() - loc_cache.get('timestamp', 0) < CACHE_EXPIRY):
                            self.data_ready.emit(loc_cache['current'], loc_cache['forecast'], loc_cache['meta_name'])
                            return
                except: pass

            geo_url = f"https://nominatim.openstreetmap.org/search?q={self.target_location}&format=json&limit=1"
            headers = {'User-Agent': 'JarvisCommandCenter/2.0 (TacticalAtmosphericApp)'}
            geo_res = requests.get(geo_url, headers=headers, timeout=5).json()

            if not geo_res:
                self.error_signal.emit(f"GEO-FAULT: Spatial grid unmapped for '{self.target_location}'.")
                return

            lat, lon = float(geo_res[0]['lat']), float(geo_res[0]['lon'])
            display_parts = geo_res[0]['display_name'].split(',')
            clean_name = f"{display_parts[0].strip()}"
            if len(display_parts) > 1: clean_name += f", {display_parts[1].strip()}"

            meteo_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m,surface_pressure&daily=weather_code,temperature_2m_max,temperature_2m_min,uv_index_max&timezone=auto"
            weather_data = requests.get(meteo_url, timeout=5).json()

            curr, daily = weather_data['current'], weather_data['daily']
            wmo_text, wmo_icon = WMO_CODES.get(curr['weather_code'], ("UNKNOWN ATMOSPHERIC ANOMALY", "🌀"))

            dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
            wind_dir_str = dirs[int((curr['wind_direction_10m'] / 22.5) + .5) % 16]

            current_vitals = {
                "temp": curr['temperature_2m'],
                "apparent": curr['apparent_temperature'],
                "condition": wmo_text,
                "icon": wmo_icon,
                "humidity": curr['relative_humidity_2m'],
                "wind_spd": curr['wind_speed_10m'],
                "wind_dir": wind_dir_str,
                "uv_index": daily['uv_index_max'][0],
                "pressure": curr['surface_pressure']
            }

            forecast_list = []
            for i in range(1, 6):
                w_text, w_icon = WMO_CODES.get(daily['weather_code'][i], ("ANOMALY", "🌀"))
                raw_date = daily['time'][i].split("-")
                forecast_list.append({
                    "date": f"{raw_date[2]}/{raw_date[1]}",
                    "min": daily['temperature_2m_min'][i],
                    "max": daily['temperature_2m_max'][i],
                    "cond": w_text.split("//")[0].strip(),
                    "icon": w_icon
                })

            cache_store = {}
            if os.path.exists(CACHE_FILE):
                try:
                    with open(CACHE_FILE, 'r') as f: cache_store = json.load(f)
                except: pass

            cache_store[cache_key] = {"timestamp": time.time(), "meta_name": clean_name.upper(), "current": current_vitals, "forecast": forecast_list}
            with open(CACHE_FILE, 'w') as f: json.dump(cache_store, f)

            self.data_ready.emit(current_vitals, forecast_list, clean_name.upper())

        except Exception as e: self.error_signal.emit(f"ORBITAL DISCONNECT: {str(e)}")


class WeatherIntelApp(QMainWindow):
    def __init__(self, target_sector):
        super().__init__()
        self.target_sector = target_sector
        
        self.setWindowTitle("Atmospheric Telemetry Room")
        self.resize(1400, 800) # Default floating window geometry
        
        # --- THE JAILBREAK: Purged WindowStaysOnTopHint from boot ---
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.showFullScreen()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.init_ui()
        
        self.worker = OpenMeteoWorker(self.target_sector)
        self.worker.data_ready.connect(self.render_telemetry)
        self.worker.error_signal.connect(self.show_error)
        self.worker.start()

    def init_ui(self):
        self.central_widget = QFrame()
        self.central_widget.setStyleSheet("QFrame { background-color: rgba(4, 5, 8, 0.99); border: 1px solid #00d4ff; }")
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(1, 1, 1, 1) # Seamless edge alignment
        self.main_layout.setSpacing(0)

        # Mount Custom Kinetic Title Bar Chrome
        self.title_bar = CyberTitleBar(self)
        self.main_layout.addWidget(self.title_bar)

        # Main view space wrapper
        self.body_container = QWidget()
        self.body_layout = QVBoxLayout(self.body_container)
        self.body_layout.setContentsMargins(40, 30, 40, 30)
        self.body_layout.setSpacing(20)

        # Header sub-layout containing status loops
        self.sub_header = QHBoxLayout()
        self.spinner_lbl = QLabel("⠋")
        self.spinner_lbl.setStyleSheet("color: #00ffaa; font-family: 'Consolas'; font-size: 24px; font-weight: bold;")
        
        self.sector_lbl = QLabel(f"ORBITAL METEO LINK // SECTOR: [{self.target_sector.upper()}]")
        self.sector_lbl.setStyleSheet("color: #00d4ff; font-family: 'Consolas'; font-size: 20px; font-weight: bold; margin-left: 10px;")
        
        self.sub_header.addWidget(self.spinner_lbl)
        self.sub_header.addWidget(self.sector_lbl)
        self.sub_header.addStretch()
        self.body_layout.addLayout(self.sub_header)

        # Radar Sweep Animation Logic
        self.radar_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.radar_idx = 0
        self.spinner_timer = QTimer(self)
        self.spinner_timer.timeout.connect(self.animate_radar_sweep)
        self.spinner_timer.start(100)

        # Master Display Viewport Stacking Grid
        self.viewport_stack = QWidget()
        self.viewport_grid = QGridLayout(self.viewport_stack)
        self.viewport_grid.setContentsMargins(0, 0, 0, 0)

        self.viewport = QWidget()
        self.viewport.setStyleSheet("border: none; background: transparent;")
        self.viewport_layout = QVBoxLayout(self.viewport)
        self.viewport_layout.setContentsMargins(0, 0, 0, 0)
        self.viewport_grid.addWidget(self.viewport, 0, 0)

        self.status_lbl = QLabel("ACQUIRING OPEN-METEO SATELLITE TELEMETRY...")
        self.status_lbl.setStyleSheet("color: #00d4ff; font-family: 'Consolas'; font-size: 20px;")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.viewport_layout.addWidget(self.status_lbl)

        # Append hardware resize grip anchor at the bottom-right corner layer
        self.resizer = QSizeGrip(self)
        self.resizer.setFixedSize(20, 20)
        self.resizer.setStyleSheet("QSizeGrip { background: transparent; }")
        self.viewport_grid.addWidget(self.resizer, 0, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)

        self.body_layout.addWidget(self.viewport_stack, stretch=1)
        self.main_layout.addWidget(self.body_container, stretch=1)

    def animate_radar_sweep(self):
        self.radar_idx = (self.radar_idx + 1) % len(self.radar_frames)
        self.spinner_lbl.setText(self.radar_frames[self.radar_idx])

    def render_telemetry(self, current, forecast, official_name):
        self.status_lbl.deleteLater()
        self.title_bar.title_lbl.setText(f"ATMOSPHERIC RADAR TELEMETRY // SPATIAL LOCK: [{official_name}]")
        self.sector_lbl.setText(f"METEO RADAR UPLINK SECURE // LOCK SECTOR: [{official_name.split(',')[0]}]")

        upper_container = QWidget()
        upper_layout = QHBoxLayout(upper_container)
        upper_layout.setContentsMargins(0, 0, 0, 0)
        upper_layout.setSpacing(30)

        # --- LEFT: CYBERCARD RECONNAISSANCE CORE ---
        self.temp_card = CyberCard(sweep_speed=2800)
        temp_layout = QVBoxLayout(self.temp_card)
        temp_layout.setContentsMargins(25, 25, 25, 25)
        
        t_lbl = QLabel(f"{round(current['temp'])}°C {current['icon']}")
        t_lbl.setStyleSheet("color: #ffffff; font-family: 'Consolas'; font-size: 72px; font-weight: bold; border: none; background: transparent;")
        
        c_lbl = QLabel(current['condition'])
        c_lbl.setStyleSheet("color: #00ffaa; font-family: 'Consolas'; font-size: 18px; font-weight: bold; letter-spacing: 1px; border: none; background: transparent;")
        
        rf_lbl = QLabel(f"APPARENT THERMAL FEEL: {round(current['apparent'])}°C\nBAROMETRIC SYSTEM: {current['pressure']} hPa")
        rf_lbl.setStyleSheet("color: rgba(255,255,255,0.6); font-family: 'Consolas'; font-size: 13px; border: none; background: transparent; margin-top: 10px;")

        temp_layout.addWidget(t_lbl)
        temp_layout.addWidget(c_lbl)
        temp_layout.addWidget(rf_lbl)
        temp_layout.addStretch()
        upper_layout.addWidget(self.temp_card, stretch=1)

        # --- RIGHT: 4-QUAD MATRIX SYSTEMS ---
        quad_container = QWidget()
        quad_layout = QGridLayout(quad_container)
        quad_layout.setContentsMargins(0, 0, 0, 0)
        quad_layout.setSpacing(15)

        stats = [
            ("RELATIVE MOISTURE HUMIDITY", f"{current['humidity']}%", "#00d4ff", 3200),
            ("PEAK UV SOLAR IRRADIANCE", f"INDEX {current['uv_index']}", "#ff003c" if current['uv_index'] > 6 else "#00ffaa", 3500),
            ("SURFACE WIND DIRECTIONAL VELOCITY", f"{current['wind_spd']} KM/H [{current['wind_dir']}]", "#00ffaa", 2900),
            ("UPLINK COMPLIANCE SECURITY", "ENCRYPTED [●]", "#00ffaa", 3800)
        ]

        for idx, (label, val, color, spd) in enumerate(stats):
            r, c = idx // 2, idx % 2
            box = CyberCard(sweep_speed=spd) 
            box_layout = QVBoxLayout(box)
            box_layout.setContentsMargins(15, 15, 15, 15)
            
            l1 = QLabel(label)
            l1.setStyleSheet("color: rgba(255,255,255,0.4); font-family: 'Consolas'; font-size: 11px; border: none; background: transparent;")
            
            l2 = QLabel(val)
            l2.setStyleSheet(f"color: {color}; font-family: 'Consolas'; font-size: 17px; font-weight: bold; border: none; background: transparent; margin-top: 4px;")
            
            box_layout.addWidget(l1)
            box_layout.addWidget(l2)
            quad_layout.addWidget(box, r, c)

        upper_layout.addWidget(quad_container, stretch=2)
        self.viewport_layout.addWidget(upper_container, stretch=2)

        # --- LOWER VIEWPORT: 5-DAY HORIZONTAL MATRIX FORECAST ---
        self.viewport_layout.addSpacing(15)
        fore_banner = QFrame()
        fore_banner.setStyleSheet("background: rgba(0,0,0,0.5); border: 1px solid rgba(0,212,255,0.15); border-top: 2px solid #00d4ff; padding: 12px;")
        fore_layout = QHBoxLayout(fore_banner)
        fore_layout.setContentsMargins(10, 10, 10, 10)
        fore_layout.setSpacing(12)

        for idx, day in enumerate(forecast):
            d_box = CyberCard(sweep_speed=3000 + (idx * 200))
            d_layout = QVBoxLayout(d_box)
            d_layout.setContentsMargins(10, 10, 10, 10)
            
            dt_lbl = QLabel(day['date'])
            dt_lbl.setStyleSheet("color: #00d4ff; font: bold 14px 'Consolas'; border: none; background: transparent;")
            dt_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            icon_lbl = QLabel(f"{day['icon']}\n{day['cond']}")
            icon_lbl.setStyleSheet("color: #ffffff; font: 11px 'Consolas'; border: none; background: transparent; margin-top: 3px;")
            icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            t_span = QLabel(f"↓{round(day['min'])}°  ↑{round(day['max'])}°")
            t_span.setStyleSheet("color: #00ffaa; font: bold 13px 'Consolas'; border: none; background: transparent; margin-top: 8px;")
            t_span.setAlignment(Qt.AlignmentFlag.AlignCenter)

            d_layout.addWidget(dt_lbl)
            d_layout.addWidget(icon_lbl)
            d_layout.addWidget(t_span)
            fore_layout.addWidget(d_box)

        self.viewport_layout.addWidget(fore_banner, stretch=1)

    def show_error(self, message):
        self.status_lbl.setText(f"CRITICAL OVERHEAT FAULT: {message}")
        self.status_lbl.setStyleSheet("color: #ff003c; font-family: 'Consolas'; font-size: 18px;")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    target = sys.argv[1] if len(sys.argv) > 1 else "Edakkunnam"
    window = WeatherIntelApp(target)
    window.show()
    sys.exit(app.exec())