import sys
import os
import time
import json
import requests
import yfinance as yf
from dotenv import load_dotenv
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QLabel, QScrollArea, QFrame, QHBoxLayout, QPushButton, QGridLayout, QSizeGrip)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, pyqtProperty, QRectF, QPoint
from PyQt6.QtGui import QCursor, QPixmap, QImage, QPainter, QConicalGradient, QColor, QPen

load_dotenv()
API_KEY = os.getenv("WORLDNEWS_API_KEY") or os.getenv("NEWS_API_KEY")
CACHE_FILE = "news_matrix_cache.json"
CACHE_EXPIRY = 1800  

LAYER_QUERIES = {
    "CONFLICTS": "conflict OR geopolitics OR military OR war OR 'border dispute'",
    "INFRASTRUCTURE": "outage OR 'power grid' OR 'cyber attack' OR hacking OR telecom OR satellite",
    "ECONOMIC": "MARKET_DATA_ONLY",
    "MILITARY": "navy OR army OR 'air force' OR 'defense system' OR 'pentagon' OR 'hypersonic'",
    "NATURAL ANOMALIES": "earthquake OR hurricane OR 'extreme weather' OR wildfire OR eruption"
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
        
        painter.setBrush(QColor(5, 7, 12, 220))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(draw_rect, 6.0, 6.0)
        
        center = draw_rect.center()
        grad = QConicalGradient(center, self._angle)
        
        grad.setColorAt(0.0, QColor(0, 212, 255, 255))     
        grad.setColorAt(0.18, QColor(0, 212, 255, 0))      
        grad.setColorAt(0.85, QColor(0, 255, 170, 0))      
        grad.setColorAt(1.0, QColor(0, 255, 170, 255))     

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

        title_lbl = QLabel("GLOBAL SITUATION ROOM // SYNDICATE DECRYPTION")
        title_lbl.setStyleSheet("color: #00d4ff; font: bold 13px 'Consolas'; border: none;")

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

        layout.addWidget(title_lbl)
        layout.addStretch()
        layout.addWidget(self.btn_pin)
        layout.addWidget(btn_min)
        layout.addWidget(self.btn_max)
        layout.addWidget(btn_close)

    def toggle_always_on_top(self):
        """Dynamically injects or revokes the DWM Topmost hardware flag live"""
        flags = self.parent_window.windowFlags()
        if bool(flags & Qt.WindowType.WindowStaysOnTopHint):
            # Turn OFF
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
            self.btn_pin.setStyleSheet("QPushButton { color: rgba(255,255,255,0.4); background: transparent; border: none; font-size: 13px; }")
        else:
            # Turn ON
            flags |= Qt.WindowType.WindowStaysOnTopHint
            self.btn_pin.setStyleSheet("QPushButton { color: #00ffaa; background: rgba(0,255,170,0.15); border: 1px solid #00ffaa; font-size: 13px; border-radius: 4px; }")

        self.parent_window.setWindowFlags(flags)
        self.parent_window.show() # Qt mandate: forcing a live re-show applies the flag instantly

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


class TacticalWorker(QThread):
    data_ready = pyqtSignal(list, str, str) 
    error_signal = pyqtSignal(str)

    def __init__(self, layer):
        super().__init__()
        self.layer = layer

    def run(self):
        try:
            stock_str = "MARKET MATRIX OFFLINE"
            try:
                tickers = yf.Tickers('^GSPC AAPL NVDA TSLA BTC-USD crude-oil')
                prices = []
                sym_map = {'^GSPC': 'S&P500', 'AAPL': 'AAPL', 'NVDA': 'NVDA', 'TSLA': 'TSLA', 'BTC-USD': 'BTC'}
                for sym, label in sym_map.items():
                    data = tickers.tickers[sym].history(period="1d")
                    if not data.empty:
                        prices.append(f"{label}: ${data['Close'].iloc[-1]:.2f}")
                stock_str = "   ||   ".join(prices)
            except Exception as e: print(f"Telemetry stream interrupted: {e}")

            if self.layer.upper() == "ECONOMIC":
                self.data_ready.emit([], stock_str, self.layer)
                return

            news_items = []
            cache_valid = False
            search_query = LAYER_QUERIES.get(self.layer.upper(), self.layer)

            if os.path.exists(CACHE_FILE):
                try:
                    with open(CACHE_FILE, 'r') as f:
                        cache_store = json.load(f)
                        layer_cache = cache_store.get(self.layer, {})
                        if layer_cache and (time.time() - layer_cache.get('timestamp', 0) < CACHE_EXPIRY):
                            news_items = layer_cache.get('data', [])
                            cache_valid = True
                except: pass

            if not cache_valid:
                if not API_KEY:
                    self.error_signal.emit("CRITICAL ERR: API KEY MISSING IN .ENV")
                    return

                url = "https://api.worldnewsapi.com/search-news"
                headers = {'x-api-key': API_KEY}
                params = {'text': search_query, 'language': 'en', 'number': 10}
                
                response = requests.get(url, headers=headers, params=params)
                if response.status_code == 200:
                    news_items = response.json().get("news", [])
                    cache_store = {}
                    if os.path.exists(CACHE_FILE):
                        try:
                            with open(CACHE_FILE, 'r') as f: cache_store = json.load(f)
                        except: pass
                    
                    cache_store[self.layer] = {'timestamp': time.time(), 'data': news_items}
                    with open(CACHE_FILE, 'w') as f: json.dump(cache_store, f)
                else:
                    self.error_signal.emit(f"UPLINK DENIED: HTTP {response.status_code}")
                    return

            for item in news_items:
                if item.get("image"):
                    try: item['img_bytes'] = requests.get(item["image"], timeout=2).content
                    except: item['img_bytes'] = None

            self.data_ready.emit(news_items, stock_str, self.layer)

        except Exception as e: self.error_signal.emit(str(e))


class NewsIntelApp(QMainWindow):
    def __init__(self, default_layer="CONFLICTS"):
        super().__init__()
        self.current_layer = default_layer

        self.setWindowTitle("Global Situation Room")
        self.resize(1400, 800) 
        
        # --- THE JAILBREAK: Strictly standard frameless hint. Zero 'Always on Top' ---
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
        self.showFullScreen()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.init_ui()
        self.switch_layer(self.current_layer)

    def init_ui(self):
        self.central_widget = QFrame()
        self.central_widget.setStyleSheet("QFrame { background-color: rgba(4, 5, 8, 0.99); border: 1px solid #00d4ff; }")
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(1, 1, 1, 1) 
        self.main_layout.setSpacing(0)

        self.title_bar = CyberTitleBar(self)
        self.main_layout.addWidget(self.title_bar)

        self.body_container = QWidget()
        self.body_layout = QVBoxLayout(self.body_container)
        self.body_layout.setContentsMargins(30, 20, 30, 20)
        self.body_layout.setSpacing(15)

        self.ticker_card = CyberCard(sweep_speed=4500)
        self.ticker_card.setFixedHeight(48)
        ticker_inner = QVBoxLayout(self.ticker_card)
        ticker_inner.setContentsMargins(15, 0, 15, 0)
        
        self.ticker_label = QLabel("ESTABLISHING ENCRYPTED LINK TO FINANCIAL MARKETS...")
        self.ticker_label.setStyleSheet("color: #00ffaa; font: bold 14px 'Consolas'; border: none; background: transparent;")
        ticker_inner.addWidget(self.ticker_label)
        self.body_layout.addWidget(self.ticker_card)

        self.layer_panel = QHBoxLayout()
        self.layer_panel.setSpacing(10)
        self.layer_buttons = {}

        for layer_name in LAYER_QUERIES.keys():
            btn = QPushButton(layer_name)
            btn.setFixedHeight(36)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.clicked.connect(lambda checked, ln=layer_name: self.switch_layer(ln))
            self.layer_panel.addWidget(btn)
            self.layer_buttons[layer_name] = btn

        self.body_layout.addLayout(self.layer_panel)

        self.scroll_stack = QWidget()
        self.scroll_grid = QGridLayout(self.scroll_stack)
        self.scroll_grid.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { background: transparent; width: 8px; }
            QScrollBar::handle:vertical { background: rgba(0, 212, 255, 0.3); border-radius: 4px; }
            QScrollBar::handle:vertical:hover { background: rgba(0, 255, 170, 0.8); }
        """)
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent; border: none;")
        self.grid_layout = QGridLayout(self.scroll_content)
        self.grid_layout.setSpacing(20)
        
        self.scroll_area.setWidget(self.scroll_content)
        self.scroll_grid.addWidget(self.scroll_area, 0, 0)

        self.resizer = QSizeGrip(self)
        self.resizer.setFixedSize(20, 20)
        self.resizer.setStyleSheet("QSizeGrip { background: transparent; }")
        self.scroll_grid.addWidget(self.resizer, 0, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)

        self.body_layout.addWidget(self.scroll_stack, stretch=1)
        self.main_layout.addWidget(self.body_container, stretch=1)

    def switch_layer(self, target_name):
        self.current_layer = target_name
        
        for name, btn in self.layer_buttons.items():
            if name.upper() == target_name.upper():
                btn.setStyleSheet("QPushButton { color: #00ffaa; border: 1px solid #00ffaa; background: rgba(0, 255, 170, 0.15); font: bold 13px 'Consolas'; border-radius: 4px; }")
            else:
                btn.setStyleSheet("QPushButton { color: rgba(0, 212, 255, 0.5); border: 1px solid rgba(0, 212, 255, 0.2); background: rgba(0,212,255,0.02); font: bold 13px 'Consolas'; border-radius: 4px; }")

        for i in reversed(range(self.grid_layout.count())): 
            w = self.grid_layout.itemAt(i).widget()
            if w: w.deleteLater()

        status_lbl = QLabel(f"DECRYPTING SYNDICATE PACKETS FOR [{target_name}]...")
        status_lbl.setStyleSheet("color: #00d4ff; font: 18px 'Consolas'; border: none;")
        status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.grid_layout.addWidget(status_lbl, 0, 0, 1, 2)

        self.worker = TacticalWorker(target_name)
        self.worker.data_ready.connect(self.populate_ui)
        self.worker.error_signal.connect(self.show_error)
        self.worker.start()

    def populate_ui(self, news_items, stock_str, target_layer):
        if target_layer != self.current_layer: return
        self.ticker_label.setText(f"GLOBAL INDICES: {stock_str}")
        
        for i in reversed(range(self.grid_layout.count())): 
            w = self.grid_layout.itemAt(i).widget()
            if w: w.deleteLater()

        if target_layer.upper() == "ECONOMIC":
            msg = QLabel("ECONOMIC MATRIX STABLE // TICKER FEED STREAMING ACTIVE INDICES AT TOP VIEWPORT.")
            msg.setStyleSheet("color: #00ffaa; font: 16px 'Consolas'; border: none;")
            msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid_layout.addWidget(msg, 0, 0, 1, 2)
            return

        row, col = 0, 0
        for idx, item in enumerate(news_items):
            title = item.get("title", "UNVERIFIED SOURCE")
            text_body = item.get("text", "")
            snippet = text_body[:280] + "..." if len(text_body) > 280 else text_body
            
            sweep_speed = 2800 + (idx * 150)
            self.add_tactical_card(title, snippet, item.get('img_bytes'), row, col, sweep_speed)
            
            col += 1
            if col > 1: col = 0; row += 1

    def add_tactical_card(self, title, description, img_bytes, row, col, speed):
        card = CyberCard(sweep_speed=speed)
        card.setFixedHeight(220)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)

        img_label = QLabel()
        img_label.setFixedSize(180, 160)
        img_label.setStyleSheet("border: 1px solid rgba(0, 212, 255, 0.2); background: #010204;")
        img_label.setScaledContents(True)
        
        if img_bytes:
            image = QImage()
            image.loadFromData(img_bytes)
            img_label.setPixmap(QPixmap(image))
        else:
            img_label.setText("[ NO MEDIA ]")
            img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            img_label.setStyleSheet("color: rgba(0, 212, 255, 0.3); font: 11px 'Consolas'; border: 1px solid rgba(0, 212, 255, 0.1);")

        layout.addWidget(img_label)

        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(15, 0, 0, 0)
        
        title_lbl = QLabel(title)
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet("color: #ffffff; font: bold 14px 'Consolas'; border: none; background: transparent;")
        
        desc_lbl = QLabel(description)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.65); font: 12px 'Consolas'; border: none; background: transparent;")
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        text_layout.addWidget(title_lbl)
        text_layout.addWidget(desc_lbl)
        layout.addWidget(text_container)
        
        self.grid_layout.addWidget(card, row, col)

    def show_error(self, message):
        for i in reversed(range(self.grid_layout.count())): 
            w = self.grid_layout.itemAt(i).widget()
            if w: w.deleteLater()
        err = QLabel(f"CRITICAL FAULT: {message}")
        err.setStyleSheet("color: #ff003c; font: bold 16px 'Consolas'; border: none;")
        err.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.grid_layout.addWidget(err, 0, 0, 1, 2)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    initial_layer = sys.argv[1] if len(sys.argv) > 1 else "CONFLICTS"
    window = NewsIntelApp(initial_layer)
    window.show()
    sys.exit(app.exec())