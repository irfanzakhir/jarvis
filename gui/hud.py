import sys
import psutil
import os
import json 
from PyQt6.QtWidgets import QMainWindow, QApplication, QPushButton, QSystemTrayIcon, QMenu, QStyle, QWidget, QTextEdit, QLabel, QLineEdit, QHBoxLayout
from PyQt6.QtGui import QColor, QAction, QPainter, QPen, QBrush, QKeySequence, QShortcut
from PyQt6.QtCore import Qt, QTimer, QUrl, QPoint, pyqtSignal
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile, QWebEnginePage

from gui.widgets import DraggableHUDWidget

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
        self.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
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
        self.current_scale += (self.target_scale - self.current_scale) * 0.15
        if self.is_active: self.rotation = (self.rotation + 4) % 360  
        else: self.rotation = (self.rotation + 0.5) % 360 
            
        if self.pulse_growing:
            self.pulse_radius += 1
            if self.pulse_radius >= 55: self.pulse_growing = False
        else:
            self.pulse_radius -= 1
            if self.pulse_radius <= 40: self.pulse_growing = True
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
        painter.setBrush(glow_color)
        radius = self.pulse_radius // 2 if self.is_active else 25
        painter.drawEllipse(-radius, -radius, radius * 2, radius * 2)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton: self.old_pos = event.globalPosition().toPoint()
    def mouseMoveEvent(self, event):
        if self.old_pos is not None:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPosition().toPoint()
    def mouseReleaseEvent(self, event): self.old_pos = None
    def mouseDoubleClickEvent(self, event):
        self.hide()
        self.restore_callback()


class JarvisHUD(QMainWindow):
    text_command_signal = pyqtSignal(str)
    mute_signal = pyqtSignal(bool)

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
        
        self.dashboard.page().setBackgroundColor(Qt.GlobalColor.transparent)
        
        dashboard_path = resource_path(os.path.join('assets', 'dashboard.html'))
        self.dashboard.loadFinished.connect(self.on_load_finished)
        self.dashboard.setUrl(QUrl.fromLocalFile(dashboard_path))

        btn_style_payload = """
            QPushButton {{ background-color: transparent; color: {color}; font-family: 'Consolas', monospace; font-size: 26px; font-weight: bold; border: none; }}
            QPushButton:hover {{ background-color: rgba({red_base}, {green_base}, {blue_base}, 0.1); color: {hover_color}; border: 1px solid rgba({red_base}, {green_base}, {blue_base}, 0.5); border-radius: 5px; }}
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
        
        # ==========================================
        # DRAGGABLE WIDGETS
        # ==========================================
        
        # --- WIDGET 1: LIVE SYSTEM TELEMETRY ---
        self.telemetry_widget = DraggableHUDWidget("SYSTEM TELEMETRY", parent=self)
        self.telemetry_widget.setFixedSize(280, 120)
        self.telemetry_label = QLabel("CPU Load: 0%\nRAM Usage: 0%\nNetwork: SECURE")
        self.telemetry_label.setStyleSheet("color: #00d4ff; font-family: 'Consolas', monospace; font-size: 13px; line-height: 1.5;")
        self.telemetry_widget.content_layout.addWidget(self.telemetry_label)
        self.telemetry_widget.move(50, 50)
        self.telemetry_widget.show()

        # --- WIDGET 2: OPTICAL ARRAY STATUS ---
        self.optical_widget = DraggableHUDWidget("OPTICAL ARRAY", parent=self)
        self.optical_widget.setFixedSize(280, 120)
        self.optical_label = QLabel("Watchdog: DISARMED\nTarget: NONE\nFPS: 30")
        self.optical_label.setStyleSheet("color: #00d4ff; font-family: 'Consolas', monospace; font-size: 13px; line-height: 1.5;")
        self.optical_widget.content_layout.addWidget(self.optical_label)
        self.optical_widget.move(50, 200)
        self.optical_widget.show()

        # --- WIDGET 3: LIVE COGNITIVE COMMUNICATIONS LOG ---
        self.log_widget = DraggableHUDWidget("NEURAL ACTIVITY LOG", parent=self)
        self.log_widget.setFixedSize(500, 320)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("""
            QTextEdit {
                background-color: transparent; 
                color: #00d4ff; 
                font-family: 'Consolas', monospace; 
                font-size: 12px;
                border: none;
            }
        """)
        self.log_widget.content_layout.addWidget(self.log_output)
        self.log_widget.move(50, 350)
        self.log_widget.show()

        # --- WIDGET 4: MANUAL OVERRIDE CONSOLE UPLINK ---
        self.command_widget = DraggableHUDWidget("MANUAL OVERRIDE UPLINK", parent=self)
        self.command_widget.setFixedSize(600, 95)
        
        self.cmd_wrapper = QWidget()
        self.cmd_layout = QHBoxLayout(self.cmd_wrapper)
        self.cmd_layout.setContentsMargins(0, 0, 0, 0)
        self.cmd_layout.setSpacing(10)

        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("AWAITING MANUAL OVERRIDE...")
        self.standard_input_style = """
            QLineEdit {
                background-color: rgba(0, 10, 20, 0.85);
                color: #00d4ff; border: 1px solid #00d4ff;
                font-family: 'Consolas', monospace; font-size: 16px; font-weight: bold;
                padding-left: 10px; border-radius: 4px;
            }
            QLineEdit:focus { border: 1px solid #ffffff; background-color: rgba(0, 20, 40, 0.95); }
        """
        self.combat_input_style = self.standard_input_style.replace("#00d4ff", "#ff003c")
        self.cmd_input.setStyleSheet(self.standard_input_style)
        self.cmd_input.returnPressed.connect(self.submit_cmd)
        
        self.mic_btn = QPushButton("🎙️")
        self.mic_btn.setFixedSize(40, 40)
        self.mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mic_btn.setCheckable(True)
        self.mic_btn.setStyleSheet("background: transparent; color: #00d4ff; font-size: 24px; border: none;")
        self.mic_btn.clicked.connect(self.toggle_mic)

        self.cmd_layout.addWidget(self.cmd_input)
        self.cmd_layout.addWidget(self.mic_btn)
        self.command_widget.content_layout.addWidget(self.cmd_wrapper)
        
        screen = QApplication.primaryScreen().geometry()
        self.command_widget.move((screen.width() - 600) // 2, screen.height() - 160)
        self.command_widget.show()

        # --- WIDGET 5: SYS ADMIN ---
        self.admin_widget = DraggableHUDWidget("SYS.ADMIN [OK]", parent=self)
        self.admin_widget.setFixedSize(280, 140)
        self.admin_label = QLabel("USER: IRFAN\nACCESS: TIER 1 OMNI\nUPLINK: SECURE")
        self.admin_label.setStyleSheet("color: #00d4ff; font-family: 'Consolas', monospace; font-size: 14px; line-height: 1.5;")
        self.admin_widget.content_layout.addWidget(self.admin_label)
        self.admin_widget.move(50, 50)
        self.admin_widget.show()

        # --- WIDGET 6: SECURITY CENTER ---
        self.security_widget = DraggableHUDWidget("SECURITY CENTER SHIELD", parent=self)
        self.security_widget.setFixedSize(300, 140)
        self.security_label = QLabel("FIREWALL: ACTIVE\nTHREATS DETECTED: 0\nENCRYPTION: AES-256")
        self.security_label.setStyleSheet("color: #00d4ff; font-family: 'Consolas', monospace; font-size: 14px; line-height: 1.5;")
        self.security_widget.content_layout.addWidget(self.security_label)
        self.security_widget.move(50, 500)
        self.security_widget.show()

        # --- WIDGET 7: NETWORK HUB ---
        self.network_widget = DraggableHUDWidget("NETWORK HUB", parent=self)
        self.network_widget.setFixedSize(280, 150)
        self.network_label = QLabel("SIGNAL STR: --\nDOWNLINK: 0.0 KB/s\nUPLINK: 0.0 KB/s\n\nGATEWAY: INITIALIZING...")
        self.network_label.setStyleSheet("color: #00d4ff; font-family: 'Consolas', monospace; font-size: 13px; line-height: 1.5;")
        self.network_widget.content_layout.addWidget(self.network_label)
        self.network_widget.move(screen.width() - 330, 50)
        self.network_widget.show()

        # --- WIDGET 8: DIAGNOSTICS ---
        self.diagnostics_widget = DraggableHUDWidget("DIAGNOSTICS SYS", parent=self)
        self.diagnostics_widget.setFixedSize(280, 120)
        self.diagnostics_label = QLabel("[OK] MEMORY ALLOC\n[OK] KERNEL INTEGRITY")
        self.diagnostics_label.setStyleSheet("color: #00d4ff; font-family: 'Consolas', monospace; font-size: 14px; line-height: 1.5;")
        self.diagnostics_widget.content_layout.addWidget(self.diagnostics_label)
        self.diagnostics_widget.move(screen.width() - 330, 300)
        self.diagnostics_widget.show()
        
        # Hotkey Setup
        self.shortcut_toggle = QShortcut(QKeySequence("Ctrl+Space"), self)
        self.shortcut_toggle.activated.connect(self.toggle_cmd)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.showFullScreen()

        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.send_vitals_to_js)
        self.stats_timer.start(1000)
        self.last_net_io = psutil.net_io_counters()

        self.setup_system_tray()
        self.orb = FloatingOrb(self.restore_from_orb)

        # ==========================================
        # THE WIDGET MASTER ARRAYS
        # ==========================================
        self.all_hud_widgets = [
            self.telemetry_widget, self.optical_widget, self.log_widget, 
            self.command_widget, self.admin_widget, self.security_widget, 
            self.network_widget, self.diagnostics_widget
        ]
        self.all_labels = [
            self.telemetry_label, self.optical_label, self.admin_label, 
            self.security_label, self.network_label, self.diagnostics_label
        ]

    def toggle_cmd(self):
        if self.command_widget.isHidden():
            self.command_widget.show()
            self.cmd_input.setFocus()
        else:
            if not self.cmd_input.hasFocus():
                self.cmd_input.setFocus()
            else:
                self.command_widget.hide()
                self.dashboard.setFocus()

    def submit_cmd(self):
        text = self.cmd_input.text()
        if text.strip():
            self.text_command_signal.emit(text) 
        self.cmd_input.clear()
        self.dashboard.setFocus()
        
    def toggle_mic(self):
        is_muted = self.mic_btn.isChecked()
        if is_muted:
            self.mic_btn.setText("🔇")
            self.mic_btn.setStyleSheet("background: transparent; color: #555555; font-size: 24px; border: none;")
        else:
            self.mic_btn.setText("🎙️")
            color = "#ff003c" if self.orb.combat_mode else "#00d4ff"
            self.mic_btn.setStyleSheet(f"background: transparent; color: {color}; font-size: 24px; border: none;")
            
        self.mute_signal.emit(is_muted)

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
            self.telemetry_label.setText(f"CPU Load: {cpu}%\nRAM Usage: {ram}%\nNetwork: SECURE")

            current_net_io = psutil.net_io_counters()
            dl_bps = current_net_io.bytes_recv - self.last_net_io.bytes_recv
            up_bps = current_net_io.bytes_sent - self.last_net_io.bytes_sent
            self.last_net_io = current_net_io

            dl_str = f"{dl_bps / 1024:.1f} KB/s" if dl_bps < 1024 * 1024 else f"{dl_bps / (1024*1024):.2f} MB/s"
            up_str = f"{up_bps / 1024:.1f} KB/s" if up_bps < 1024 * 1024 else f"{up_bps / (1024*1024):.2f} MB/s"

            if hasattr(self, 'network_label'):
                self.network_label.setText(f"SIGNAL STR: 100%\nDOWNLINK: {dl_str}\nUPLINK: {up_str}\n\nGATEWAY: R.A.W. SECURE")

    def update_text(self, data):
        if not data or not self.page_loaded: return
        log_text = data.get('log', '')
        action = data.get('action')
        
        if log_text and ("USER" in log_text or "JARVIS" in log_text or "SYSTEM" in log_text or "[WARNING]" in log_text or "[CRITICAL]" in log_text):
            
            self.log_output.append(log_text)
            self.log_output.verticalScrollBar().setValue(self.log_output.verticalScrollBar().maximum())
            
        
        if action == 'update_wifi':
            wifi_data = data.get('data', {})
            ssid = wifi_data.get("ssid", "OFFLINE")
            signal = wifi_data.get("signal", "--")
            dl = wifi_data.get("dl", "0.0 KB/s")
            up = wifi_data.get("up", "0.0 KB/s")
            status = "SECURE" if ssid != "DISCONNECTED" else "DISCONNECTED"
            
            if hasattr(self, 'network_label'):
                self.network_label.setText(f"SIGNAL STR: {signal}\nDOWNLINK: {dl}\nUPLINK: {up}\n\nGATEWAY: {status}")
                self.network_widget.title_label.setText(f"NETWORK HUB - {ssid}")

        elif action == 'combat_on':
            self.orb.combat_mode = True
            self.close_btn.setStyleSheet(self.combat_btn_style)
            self.min_btn.setStyleSheet(self.combat_btn_style)
            self.cmd_input.setStyleSheet(self.combat_input_style) 
            self.dashboard.page().runJavaScript("setCombatMode(true);")
            
            for widget in self.all_hud_widgets: 
                widget.set_theme(combat=True)
                
            combat_css = "color: #ff003c; font-family: 'Consolas', monospace; font-size: 13px; line-height: 1.5;"
            for label in self.all_labels: 
                label.setStyleSheet(combat_css)
            self.log_output.setStyleSheet("QTextEdit { background-color: transparent; color: #ff003c; font-family: 'Consolas', monospace; font-size: 12px; border: none; }")
            
        elif action == 'combat_off':
            self.orb.combat_mode = False
            self.close_btn.setStyleSheet(self.standard_btn_style)
            self.min_btn.setStyleSheet(self.standard_btn_style)
            self.cmd_input.setStyleSheet(self.standard_input_style) 
            self.dashboard.page().runJavaScript("setCombatMode(false);")
            
            for widget in self.all_hud_widgets: 
                widget.set_theme(combat=False)
                
            standard_css = "color: #00d4ff; font-family: 'Consolas', monospace; font-size: 13px; line-height: 1.5;"
            for label in self.all_labels: 
                label.setStyleSheet(standard_css)
            self.log_output.setStyleSheet("QTextEdit { background-color: transparent; color: #00d4ff; font-family: 'Consolas', monospace; font-size: 12px; border: none; }")

        elif action == 'wake': self.orb.set_active(True)
        elif action == 'standby': self.orb.set_active(False)
        elif action == 'minimize_dashboard': self.minimize_to_orb()
        elif action == 'restore_dashboard': self.restore_from_orb()

    # Add this inside the JarvisHUD class:
    def closeEvent(self, event):
        """Forces the Chromium WebEngine to drop its memory hooks instantly on close."""
        if hasattr(self, 'dashboard') and self.dashboard:
            self.dashboard.page().deleteLater()
            self.dashboard.setPage(None)
        event.accept()