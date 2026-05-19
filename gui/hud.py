import sys
import psutil
import os
import json 
from PyQt6.QtWidgets import QMainWindow, QApplication, QPushButton, QSystemTrayIcon, QMenu, QStyle, QWidget
from PyQt6.QtGui import QColor, QAction, QPainter, QPen, QBrush
from PyQt6.QtCore import Qt, QTimer, QUrl, QPoint
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile, QWebEnginePage

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

class FloatingOrb(QWidget):
    def __init__(self, restore_callback):
        super().__init__()
        self.restore_callback = restore_callback
        
        # --- THE ULTIMATE WINDOWS 11 BYPASS ---
        # Classifying this as a SplashScreen forces Windows to treat it as a pure 
        # floating graphic, completely disabling the DWM glass/acrylic box effect.
        self.setWindowFlags(
            Qt.WindowType.SplashScreen | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.FramelessWindowHint
        )
        
        # Force pure transparency at the Qt memory level
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        # Force pure transparency at the CSS rendering level
        self.setStyleSheet("background: transparent; border: none; outline: none;")
        
        self.setFixedSize(140, 140)
        self.old_pos = None
        
        self.combat_mode = False
        self.is_active = False
        self.rotation = 0

        self.pulse_radius = 40
        self.pulse_growing = True
        
        self.current_scale = 0.5
        self.target_scale = 0.5

        self.timer = QTimer()
        self.timer.timeout.connect(self.animate_core)
        self.timer.start(30)

    def set_active(self, state):
        self.is_active = state
        self.target_scale = 1.0 if state else 0.5

    def animate_core(self):
        # Smooth interpolation for the physical size of the orb
        self.current_scale += (self.target_scale - self.current_scale) * 0.15

        if self.is_active:
            self.rotation = (self.rotation + 4) % 360  
        else:
            self.rotation = (self.rotation + 0.5) % 360 
            
        if self.pulse_growing:
            self.pulse_radius += 1
            if self.pulse_radius >= 55:
                self.pulse_growing = False
        else:
            self.pulse_radius -= 1
            if self.pulse_radius <= 40:
                self.pulse_growing = True
                
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(self.current_scale, self.current_scale)

        alpha_base = 255 if self.is_active else 80
        
        base_color = QColor(255, 0, 60, alpha_base) if self.combat_mode else QColor(0, 212, 255, alpha_base)
        dim_color = QColor(255, 0, 60, alpha_base // 2) if self.combat_mode else QColor(0, 212, 255, alpha_base // 2)
        glow_color = QColor(255, 0, 60, 40) if self.combat_mode else QColor(0, 212, 255, 40)

        painter.setPen(QPen(dim_color, 2, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(-45, -45, 90, 90)

        painter.rotate(self.rotation)

        painter.setPen(QPen(base_color, 4))
        painter.drawArc(-35, -35, 70, 70, 0 * 16, 80 * 16)
        painter.drawArc(-35, -35, 70, 70, 120 * 16, 80 * 16)
        painter.drawArc(-35, -35, 70, 70, 240 * 16, 80 * 16)

        painter.setPen(QPen(dim_color, 2, Qt.PenStyle.DotLine))
        painter.drawEllipse(-22, -22, 44, 44)

        painter.rotate(-self.rotation)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(base_color)
        painter.drawEllipse(-8, -8, 16, 16)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glow_color)
        radius = self.pulse_radius // 2 if self.is_active else 25
        painter.drawEllipse(-radius, -radius, radius * 2, radius * 2)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos is not None:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

    def mouseDoubleClickEvent(self, event):
        self.hide()
        self.restore_callback()


class JarvisHUD(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.page_loaded = False
        self.dashboard = QWebEngineView(self)
        
        self.ram_profile = QWebEngineProfile("", self.dashboard)
        self.ram_page = QWebEnginePage(self.ram_profile, self.dashboard)
        self.dashboard.setPage(self.ram_page)
        
        settings = self.dashboard.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ShowScrollBars, False)
        
        self.dashboard.page().setBackgroundColor(QColor(5, 5, 8))
        
        dashboard_path = resource_path(os.path.join('assets', 'dashboard.html'))
        self.dashboard.loadFinished.connect(self.on_load_finished)
        self.dashboard.setUrl(QUrl.fromLocalFile(dashboard_path))

        btn_style_payload = """
            QPushButton {{ 
                background-color: transparent; 
                color: {color}; 
                font-family: 'Consolas', monospace; 
                font-size: 26px; 
                font-weight: bold;
                border: none; 
            }}
            QPushButton:hover {{ 
                background-color: rgba({red_base}, {green_base}, {blue_base}, 0.1); 
                color: {hover_color};
                border: 1px solid rgba({red_base}, {green_base}, {blue_base}, 0.5);
                border-radius: 5px;
            }}
        """
        self.standard_btn_style = btn_style_payload.format(color="#00d4ff", hover_color="#ffffff", red_base="0", green_base="212", blue_base="255")
        self.combat_btn_style = btn_style_payload.format(color="#ff003c", hover_color="#ffffff", red_base="255", green_base="0", blue_base="60")

        self.close_btn = QPushButton("✕", self)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setStyleSheet(self.standard_btn_style)
        self.close_btn.clicked.connect(self.close)

        self.min_btn = QPushButton("—", self)
        self.min_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.min_btn.setStyleSheet(self.standard_btn_style)
        self.min_btn.clicked.connect(self.minimize_to_orb)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.showFullScreen()

        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.send_vitals_to_js)
        self.stats_timer.start(1000)

        self.setup_system_tray()
        self.orb = FloatingOrb(self.restore_from_orb)

    def setup_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self.tray_icon.setIcon(icon)

        tray_menu = QMenu()
        restore_action = QAction("Restore Dashboard", self)
        restore_action.triggered.connect(self.restore_from_orb)
        quit_action = QAction("Terminate System", self)
        quit_action.triggered.connect(self.close)
        
        tray_menu.addAction(restore_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

    def minimize_to_orb(self):
        self.hide() 
        self.orb.set_active(False)
        screen = QApplication.primaryScreen().geometry()
        self.orb.move(screen.width() - 150, 50)
        self.orb.show()

    def restore_from_orb(self):
        self.orb.hide()
        self.showFullScreen() 

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.restore_from_orb()

    def resizeEvent(self, event):
        w, h = self.width(), self.height()
        if hasattr(self, 'dashboard'):
            self.dashboard.setGeometry(0, 0, w, h)
        if hasattr(self, 'close_btn'):
            self.close_btn.setGeometry(w - 50, 15, 40, 40)
        if hasattr(self, 'min_btn'):
            self.min_btn.setGeometry(w - 90, 15, 40, 40)
        super().resizeEvent(event)

    def on_load_finished(self, ok):
        if ok:
            print("[HUD] Dashboard GUI Loaded Successfully.")
            self.page_loaded = True

    def send_vitals_to_js(self):
        if self.page_loaded:
            cpu = int(psutil.cpu_percent())
            ram = int(psutil.virtual_memory().percent)
            self.dashboard.page().runJavaScript(f"updateVitals({cpu}, {ram});")

    def update_text(self, data):
        if not data or not self.page_loaded:
            return
            
        log_text = data.get('log', '')
        action = data.get('action')
        
        # We check for [WARNING] and [CRITICAL] so system threats print to the comms link too
        if log_text and ("USER" in log_text or "JARVIS" in log_text or "SYSTEM" in log_text or "[WARNING]" in log_text or "[CRITICAL]" in log_text):
            safe_text = json.dumps(log_text) 
            self.dashboard.page().runJavaScript(f"updateComms({safe_text});")
            
        if action == 'show_news':
            safe_news = json.dumps(log_text)
            self.dashboard.page().runJavaScript(f"activatePanel('news', {safe_news});")
            
        # --- NEW: Catching the Wi-Fi Telemetry and sending it to JS ---
        elif action == 'update_wifi':
            wifi_data = data.get('data', {})
            safe_wifi = json.dumps(wifi_data)
            self.dashboard.page().runJavaScript(f"updateWifi({safe_wifi});")
            
        elif action == 'combat_on':
            self.orb.combat_mode = True
            self.close_btn.setStyleSheet(self.combat_btn_style)
            self.min_btn.setStyleSheet(self.combat_btn_style)
            self.dashboard.page().runJavaScript("setCombatMode(true);")
            
        elif action == 'combat_off':
            self.orb.combat_mode = False
            self.close_btn.setStyleSheet(self.standard_btn_style)
            self.min_btn.setStyleSheet(self.standard_btn_style)
            self.dashboard.page().runJavaScript("setCombatMode(false);")
            
        elif action == 'wake':
            self.orb.set_active(True)
        elif action == 'standby':
            self.orb.set_active(False)
            
        elif action == 'minimize_dashboard':
            self.minimize_to_orb()
        elif action == 'restore_dashboard':
            self.restore_from_orb()

    def closeEvent(self, event):
        if hasattr(self, 'ram_page'):
            self.dashboard.setPage(None)
            self.ram_page.deleteLater()
            self.ram_profile.deleteLater()
        event.accept()