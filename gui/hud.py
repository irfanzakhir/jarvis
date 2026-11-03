import sys
import psutil
import os
import json
import math
import random
from PyQt6.QtWidgets import QMainWindow, QApplication, QPushButton, QSystemTrayIcon, QMenu, QStyle, QWidget, QTextEdit, QLabel, QLineEdit, QHBoxLayout
from PyQt6.QtGui import (
    QColor, QAction, QPainter, QPen, QBrush, QKeySequence, QShortcut,
    QRadialGradient, QLinearGradient, QPainterPath
)
from PyQt6.QtCore import Qt, QTimer, QUrl, QPoint, pyqtSignal
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile, QWebEnginePage
from PyQt6.QtWidgets import QGraphicsOpacityEffect
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve
import winsound
from gui.widgets import DraggableHUDWidget
from gui.intel_widgets import (
    TacticalMapHUDWidget, LiveNewsHUDWidget, DynamicWeatherHUDWidget,
    AudioSpectrumHUDWidget, CognitiveMemoryHUDWidget, HardwareHealthHUDWidget
)
from services.intel_hub import IntelHub
import ctypes

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
        
        # 1. The absolute OS-level flags
        self.setWindowFlags(
            Qt.WindowType.Tool | 
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.NoDropShadowWindowHint
        )
        
        # 2. Native C++ alpha channel requirements
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setStyleSheet("FloatingOrb { background: transparent; border: none; outline: none; }")
        
        self.setFixedSize(140, 140)
        self.old_pos = None
        self.combat_mode = False
        self.antigravity_mode = False
        self.is_active = False
        
        # Fluid & Animation Physics state
        self.rotation = 0.0
        self.wave_phase = 0.0
        self.pulse_phase = 0.0
        self.current_scale = 0.70
        self.target_scale = 0.70
        
        # Buoyant micro-bubbles inside the liquid chamber
        self.particles = []
        for _ in range(6):
            self.particles.append({
                "x": random.uniform(-25, 25),
                "y": random.uniform(-10, 35),
                "r": random.uniform(1.5, 3.2),
                "speed": random.uniform(0.3, 0.75),
                "wobble": random.uniform(0, math.pi * 2)
            })

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate_frame)

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, 'timer') and not self.timer.isActive():
            self.timer.start(25) # ~40 FPS, <1% CPU footprint

    def hideEvent(self, event):
        super().hideEvent(event)
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()

    def set_active(self, state):
        self.is_active = bool(state)
        self.target_scale = 0.95 if self.is_active else 0.70

    def animate_frame(self):
        self.current_scale += (self.target_scale - self.current_scale) * 0.14
        speed_mult = 2.4 if self.is_active else 1.0
        self.rotation = (self.rotation + 0.6 * speed_mult) % 360.0
        self.wave_phase = (self.wave_phase + 0.05 * speed_mult) % (2 * math.pi)
        self.pulse_phase = (self.pulse_phase + 0.06 * speed_mult) % (2 * math.pi)

        # Update bubbles
        R_inner = 45.0
        for p in self.particles:
            p["y"] -= p["speed"] * speed_mult
            if p["y"] < -R_inner * 0.4:
                p["y"] = R_inner * 0.6
                p["x"] = random.uniform(-25, 25)

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Erase inherited backgrounds/borders completely
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        w, h = self.width(), self.height()
        painter.translate(w / 2, h / 2)
        painter.scale(self.current_scale, self.current_scale)

        R = 52.0  # Outer glass sphere radius

        # Determine color palette based on mode
        if self.combat_mode:
            accent = QColor(255, 0, 60)
            glow_c = QColor(255, 0, 60, 55 if self.is_active else 35)
            glass_dark = QColor(35, 4, 12, 180)
            glass_mid = QColor(140, 10, 35, 80)
            rim_c = QColor(255, 0, 60, 220)
            fluid_top = QColor(255, 70, 95, 220)
            fluid_deep = QColor(130, 0, 25, 235)
            core_c = QColor(255, 40, 80, 240)
        elif self.antigravity_mode:
            accent = QColor(161, 66, 244)
            glow_c = QColor(161, 66, 244, 55 if self.is_active else 35)
            glass_dark = QColor(20, 5, 42, 175)
            glass_mid = QColor(90, 25, 160, 75)
            rim_c = QColor(161, 66, 244, 210)
            fluid_top = QColor(0, 229, 255, 220)
            fluid_deep = QColor(75, 15, 125, 235)
            core_c = QColor(0, 229, 255, 240)
        else:
            # Standard Mode: Frost Cyan & Electric Sapphire
            accent = QColor(0, 229, 255)
            glow_c = QColor(0, 212, 255, 50 if self.is_active else 30)
            glass_dark = QColor(4, 25, 45, 170)
            glass_mid = QColor(0, 130, 190, 75)
            rim_c = QColor(0, 229, 255, 200)
            fluid_top = QColor(110, 240, 255, 220)
            fluid_deep = QColor(0, 85, 140, 235)
            core_c = QColor(0, 240, 255, 240)

        # ----------------------------------------------------
        # PASS 1: Volumetric Ambient Glow & Breathing Drop Shadow
        # ----------------------------------------------------
        pulse_r = R * (1.18 + 0.08 * math.sin(self.pulse_phase))
        amb_grad = QRadialGradient(0, 0, pulse_r)
        amb_grad.setColorAt(0.0, glow_c)
        amb_grad.setColorAt(0.65, QColor(glow_c.red(), glow_c.green(), glow_c.blue(), int(glow_c.alpha() * 0.4)))
        amb_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(amb_grad))
        painter.drawEllipse(int(-pulse_r), int(-pulse_r), int(pulse_r * 2), int(pulse_r * 2))

        # ----------------------------------------------------
        # PASS 2: Frosted Glass Sphere Shell (Offset Top-Left Focal Light)
        # ----------------------------------------------------
        glass_grad = QRadialGradient(-R * 0.35, -R * 0.35, R * 1.35, -R * 0.35, -R * 0.35)
        glass_grad.setColorAt(0.0, QColor(255, 255, 255, 60))
        glass_grad.setColorAt(0.25, glass_mid)
        glass_grad.setColorAt(0.70, glass_dark)
        glass_grad.setColorAt(0.92, QColor(rim_c.red(), rim_c.green(), rim_c.blue(), 120))
        glass_grad.setColorAt(1.0, rim_c)
        
        painter.setBrush(QBrush(glass_grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(-R), int(-R), int(R * 2), int(R * 2))

        # ----------------------------------------------------
        # PASS 3: Internal Viscous Liquid Core (Harmonic Fluid Wave)
        # ----------------------------------------------------
        fluid_clip = QPainterPath()
        fluid_clip.addEllipse(-R * 0.88, -R * 0.88, R * 1.76, R * 1.76)
        painter.save()
        painter.setClipPath(fluid_clip)

        wave_path = QPainterPath()
        y_base = 2.0 if not self.is_active else -5.0
        amp1 = 4.0 if not self.is_active else 7.5
        amp2 = 2.5 if not self.is_active else 4.5
        
        pts = 28
        x_min, x_max = -R, R
        dx = (x_max - x_min) / pts

        y_first = y_base + amp1 * math.sin(x_min * 0.07 + self.wave_phase) + amp2 * math.cos(x_min * 0.14 - self.wave_phase)
        wave_path.moveTo(x_min, y_first)
        for i in range(1, pts + 1):
            curr_x = x_min + i * dx
            curr_y = y_base + amp1 * math.sin(curr_x * 0.07 + self.wave_phase) + amp2 * math.cos(curr_x * 0.14 - self.wave_phase)
            wave_path.lineTo(curr_x, curr_y)

        wave_path.lineTo(x_max, R)
        wave_path.lineTo(x_min, R)
        wave_path.closeSubpath()

        fluid_grad = QLinearGradient(0, y_base - 10, 0, R)
        fluid_grad.setColorAt(0.0, fluid_top)
        fluid_grad.setColorAt(0.45, fluid_deep)
        fluid_grad.setColorAt(1.0, QColor(fluid_deep.red() // 2, fluid_deep.green() // 2, fluid_deep.blue() // 2, 245))
        
        painter.setBrush(QBrush(fluid_grad))
        painter.setPen(QPen(QColor(fluid_top.red(), fluid_top.green(), fluid_top.blue(), 230), 1.5))
        painter.drawPath(wave_path)

        # ----------------------------------------------------
        # PASS 4: Buoyant Micro-Bubbles
        # ----------------------------------------------------
        for p in self.particles:
            cur_x = p["x"] + math.sin(self.wave_phase * 2.0 + p["wobble"]) * 2.5
            cur_y = p["y"]
            b_r = p["r"]
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, 80))
            painter.drawEllipse(int(cur_x - b_r), int(cur_y - b_r), int(b_r * 2), int(b_r * 2))
            painter.setBrush(QColor(255, 255, 255, 190))
            painter.drawEllipse(int(cur_x - b_r * 0.4), int(cur_y - b_r * 0.4), int(b_r * 0.8), int(b_r * 0.8))

        painter.restore() # Release fluid clip

        # ----------------------------------------------------
        # PASS 5: Concentric Caustic Reticle & Tactical Threat Ticks
        # ----------------------------------------------------
        painter.save()
        painter.rotate(self.rotation)
        if self.combat_mode:
            # Segmented tactical threat ticks
            painter.setPen(QPen(QColor(255, 0, 60, 180), 2, Qt.PenStyle.DashLine))
            painter.drawEllipse(int(-R * 0.70), int(-R * 0.70), int(R * 1.40), int(R * 1.40))
            # 4 Crosshair notches
            painter.setPen(QPen(QColor(255, 120, 140, 220), 2))
            tick_len = 5
            r_tick = R * 0.70
            painter.drawLine(int(-r_tick - tick_len), 0, int(-r_tick + tick_len), 0)
            painter.drawLine(int(r_tick - tick_len), 0, int(r_tick + tick_len), 0)
            painter.drawLine(0, int(-r_tick - tick_len), 0, int(-r_tick + tick_len))
            painter.drawLine(0, int(r_tick - tick_len), 0, int(r_tick + tick_len))
        else:
            # Concentric caustic loops
            caustic_pen = QPen(QColor(accent.red(), accent.green(), accent.blue(), 110), 1.5, Qt.PenStyle.DotLine)
            painter.setPen(caustic_pen)
            painter.drawEllipse(int(-R * 0.72), int(-R * 0.72), int(R * 1.44), int(R * 1.44))
            
            painter.rotate(-self.rotation * 2.0)
            arc_pen = QPen(QColor(accent.red(), accent.green(), accent.blue(), 175), 2.5)
            painter.setPen(arc_pen)
            painter.drawArc(int(-R * 0.58), int(-R * 0.58), int(R * 1.16), int(R * 1.16), 0 * 16, 75 * 16)
            painter.drawArc(int(-R * 0.58), int(-R * 0.58), int(R * 1.16), int(R * 1.16), 120 * 16, 75 * 16)
            painter.drawArc(int(-R * 0.58), int(-R * 0.58), int(R * 1.16), int(R * 1.16), 240 * 16, 75 * 16)
        painter.restore()

        # ----------------------------------------------------
        # PASS 6: Bioluminescent Core Glow
        # ----------------------------------------------------
        core_r = 14.0 if not self.is_active else 20.0
        core_grad = QRadialGradient(0, 0, core_r)
        core_grad.setColorAt(0.0, QColor(255, 255, 255, 235))
        core_grad.setColorAt(0.4, core_c)
        core_grad.setColorAt(1.0, QColor(core_c.red(), core_c.green(), core_c.blue(), 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(core_grad))
        painter.drawEllipse(int(-core_r), int(-core_r), int(core_r * 2), int(core_r * 2))

        # ----------------------------------------------------
        # PASS 7: Glass Thickness Bevel & Specular Glare
        # ----------------------------------------------------
        bevel_pen = QLinearGradient(-R, -R, R, R)
        bevel_pen.setColorAt(0.0, QColor(255, 255, 255, 200))
        bevel_pen.setColorAt(0.4, QColor(rim_c.red(), rim_c.green(), rim_c.blue(), 140))
        bevel_pen.setColorAt(0.7, QColor(rim_c.red(), rim_c.green(), rim_c.blue(), 40))
        bevel_pen.setColorAt(1.0, QColor(rim_c.red(), rim_c.green(), rim_c.blue(), 160))
        painter.setPen(QPen(QBrush(bevel_pen), 2.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(int(-R + 1), int(-R + 1), int((R - 1) * 2), int((R - 1) * 2))

        # Primary Convex Specular Glare (Curved top-left highlight)
        painter.save()
        painter.translate(-R * 0.22, -R * 0.38)
        painter.rotate(-28.0)
        
        glare_w, glare_h = R * 0.95, R * 0.42
        glare_grad = QLinearGradient(0, -glare_h / 2, 0, glare_h / 2)
        glare_grad.setColorAt(0.0, QColor(255, 255, 255, 220))
        glare_grad.setColorAt(0.45, QColor(255, 255, 255, 110))
        glare_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(glare_grad))
        painter.drawEllipse(int(-glare_w / 2), int(-glare_h / 2), int(glare_w), int(glare_h))
        painter.restore()

        # Secondary Ambient Bounce Glint (Bottom-right rim)
        painter.setPen(QPen(QColor(accent.red(), accent.green(), accent.blue(), 110), 1.5))
        painter.drawArc(int(-R + 3), int(-R + 3), int((R - 3) * 2), int((R - 3) * 2), 290 * 16, 50 * 16)

        painter.end()

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

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        restore_action = QAction("Restore Dashboard", self)
        restore_action.triggered.connect(self.restore_callback)
        quit_action = QAction("Terminate System", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(restore_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        menu.exec(event.globalPos())


class JarvisHUD(QMainWindow):
    text_command_signal = pyqtSignal(str)
    mute_signal = pyqtSignal(bool)
    interrupt_speech_signal = pyqtSignal()
    hud_state_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        
        # 1. Establish immediate full-screen geometry on parent & child view
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self.setStyleSheet("QMainWindow { background-color: #050508; }")
        
        self.page_loaded = False
        self.dashboard = QWebEngineView(self)
        self.dashboard.setGeometry(0, 0, screen.width(), screen.height())
        
        cache_root = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Jarvis_OS", "web_cache")
        storage_path = os.path.join(cache_root, "storage")
        http_cache_path = os.path.join(cache_root, "cache")
        try:
            os.makedirs(storage_path, exist_ok=True)
            os.makedirs(http_cache_path, exist_ok=True)
        except Exception:
            pass
        if not hasattr(JarvisHUD, "_shared_profile") or JarvisHUD._shared_profile is None:
            JarvisHUD._shared_profile = QWebEngineProfile("jarvis_profile", QApplication.instance())
            JarvisHUD._shared_profile.setPersistentStoragePath(storage_path)
            JarvisHUD._shared_profile.setCachePath(http_cache_path)
            JarvisHUD._shared_profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        self.ram_profile = JarvisHUD._shared_profile
        self.ram_page = QWebEnginePage(self.ram_profile, self.dashboard)
        self.dashboard.setPage(self.ram_page)
        
        settings = self.dashboard.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ShowScrollBars, False)
        
        self.dashboard.page().setBackgroundColor(QColor("#050508"))
        
        dashboard_path = resource_path(os.path.join('assets', 'dashboard.html'))
        self.dashboard.loadFinished.connect(self.on_load_finished)
        self.dashboard.setUrl(QUrl.fromLocalFile(dashboard_path))

        btn_style_payload = """
            QPushButton {{ background-color: transparent; color: {color}; font-family: 'Consolas', monospace; font-size: 26px; font-weight: bold; border: none; }}
            QPushButton:hover {{ background-color: rgba({red_base}, {green_base}, {blue_base}, 0.1); color: {hover_color}; border: 1px solid rgba({red_base}, {green_base}, {blue_base}, 0.5); border-radius: 5px; }}
        """
        self.standard_btn_style = btn_style_payload.format(color="#00d4ff", hover_color="#ffffff", red_base="0", green_base="212", blue_base="255")
        self.combat_btn_style = btn_style_payload.format(color="#ff003c", hover_color="#ffffff", red_base="255", green_base="0", blue_base="60")
        self.antigravity_btn_style = btn_style_payload.format(color="#a142f4", hover_color="#ffffff", red_base="161", green_base="66", blue_base="244")

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
        self.telemetry_widget = DraggableHUDWidget("SYSTEM TELEMETRY", parent=self)
        self.telemetry_widget.setFixedSize(280, 120)
        self.telemetry_label = QLabel("CPU Load: 0%\nRAM Usage: 0%\nNetwork: SECURE")
        self.telemetry_label.setStyleSheet("color: #00d4ff; font-family: 'Consolas', monospace; font-size: 13px; line-height: 1.5;")
        self.telemetry_widget.content_layout.addWidget(self.telemetry_label)
        self.telemetry_widget.move(50, 50)
        self.telemetry_widget.hide()

        self.optical_widget = DraggableHUDWidget("OPTICAL ARRAY", parent=self)
        self.optical_widget.setFixedSize(280, 120)
        self.optical_label = QLabel("Watchdog: DISARMED\nTarget: NONE\nFPS: 30")
        self.optical_label.setStyleSheet("color: #00d4ff; font-family: 'Consolas', monospace; font-size: 13px; line-height: 1.5;")
        self.optical_widget.content_layout.addWidget(self.optical_label)
        self.optical_widget.move(50, 200)
        self.optical_widget.hide()

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
        self.log_widget.hide()

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
        self.command_widget.hide()

        self.admin_widget = DraggableHUDWidget("SYS.ADMIN [OK]", parent=self)
        self.admin_widget.setFixedSize(280, 140)
        self.admin_label = QLabel("USER: IRFAN\nACCESS: TIER 1 OMNI\nUPLINK: SECURE")
        self.admin_label.setStyleSheet("color: #00d4ff; font-family: 'Consolas', monospace; font-size: 14px; line-height: 1.5;")
        self.admin_widget.content_layout.addWidget(self.admin_label)
        self.admin_widget.move(50, 50)
        self.admin_widget.hide()

        self.security_widget = DraggableHUDWidget("SECURITY CENTER SHIELD", parent=self)
        self.security_widget.setFixedSize(300, 140)
        self.security_label = QLabel("FIREWALL: ACTIVE\nTHREATS DETECTED: 0\nENCRYPTION: AES-256")
        self.security_label.setStyleSheet("color: #00d4ff; font-family: 'Consolas', monospace; font-size: 14px; line-height: 1.5;")
        self.security_widget.content_layout.addWidget(self.security_label)
        self.security_widget.move(50, 500)
        self.security_widget.hide()

        self.network_widget = DraggableHUDWidget("NETWORK HUB", parent=self)
        self.network_widget.setFixedSize(280, 150)
        self.network_label = QLabel("SIGNAL STR: --\nDOWNLINK: 0.0 KB/s\nUPLINK: 0.0 KB/s\n\nGATEWAY: INITIALIZING...")
        self.network_label.setStyleSheet("color: #00d4ff; font-family: 'Consolas', monospace; font-size: 13px; line-height: 1.5;")
        self.network_widget.content_layout.addWidget(self.network_label)
        self.network_widget.move(screen.width() - 330, 50)
        self.network_widget.hide()

        self.diagnostics_widget = DraggableHUDWidget("DIAGNOSTICS SYS", parent=self)
        self.diagnostics_widget.setFixedSize(280, 120)
        self.diagnostics_label = QLabel("[OK] MEMORY ALLOC\n[OK] KERNEL INTEGRITY")
        self.diagnostics_label.setStyleSheet("color: #00d4ff; font-family: 'Consolas', monospace; font-size: 14px; line-height: 1.5;")
        self.diagnostics_widget.content_layout.addWidget(self.diagnostics_label)
        self.diagnostics_widget.move(screen.width() - 330, 300)
        self.diagnostics_widget.hide()
        
        self.antigravity_widget = DraggableHUDWidget("ANTIGRAVITY COGNITIVE CORE", parent=self)
        self.antigravity_widget.setFixedSize(280, 150)
        self.antigravity_label = QLabel("AGENT: STANDBY [IDLE]\nMODEL: gemini-3.5-flash-lite\nMODE: AUTONOMOUS\nTOOL: NONE\nSTATUS: ONLINE")
        self.antigravity_label.setStyleSheet("color: #00e5ff; font-family: 'Consolas', monospace; font-size: 13px; line-height: 1.5;")
        self.antigravity_widget.content_layout.addWidget(self.antigravity_label)
        self.antigravity_widget.move(screen.width() - 330, 440)
        self.antigravity_widget.hide()

        self.events_widget = DraggableHUDWidget("CALENDAR & EVENTS", parent=self)
        self.events_widget.setFixedSize(280, 130)
        self.events_label = QLabel("CALENDAR: SYNCHRONIZED\nSCHEDULE: NO CONFLICTS\nSTATUS: ACTIVE")
        self.events_label.setStyleSheet("color: #00d4ff; font-family: 'Consolas', monospace; font-size: 13px; line-height: 1.5;")
        self.events_widget.content_layout.addWidget(self.events_label)
        self.events_widget.move(screen.width() - 330, 600)
        self.events_widget.hide()

        # Native Atmospheric Weather Radar Widget (Dynamic Atmospheric Canvas)
        self.weather_widget = DraggableHUDWidget("ATMOSPHERIC WEATHER RADAR", parent=self)
        self.weather_widget.setFixedSize(400, 310)
        self._weather_intel_view = None
        self.weather_label = QLabel()
        self.weather_label.hide()
        self.weather_widget.move(screen.width() - 640, 45)
        self.weather_widget.hide()

        # Native Global Situation Room (Live AI News Intelligence) Widget
        self.news_widget = DraggableHUDWidget("GLOBAL SITUATION ROOM", parent=self)
        self.news_widget.setFixedSize(420, 330)
        self._news_intel_view = None
        self.news_label = QLabel()
        self.news_label.hide()
        self.news_widget.move(screen.width() - 640, 365)
        self.news_widget.hide()

        # Native Tactical Map Recon Widget (Interactive Leaflet Map Recon) - Deferred instantiation
        self.map_widget = DraggableHUDWidget("TACTICAL MAP RECON", parent=self)
        self.map_widget.setFixedSize(460, 340)
        self._map_intel_view = None  # Created lazily on first reveal/demand to prevent dual WebEngine cold boot
        self.map_label = QLabel()
        self.map_label.hide()
        self.map_widget.move(screen.width() - 640, 705)
        self.map_widget.hide()

        # Native Acoustic Spectrum & Vocal Processing Core
        self.audio_widget = DraggableHUDWidget("ACOUSTIC SPECTRUM & VOCAL CORE", parent=self)
        self.audio_widget.setFixedSize(360, 165)
        self._audio_intel_view = None
        self.audio_widget.move(screen.width() - 640, 150)
        self.audio_widget.hide()

        # Native Cognitive Memory Vault & Vector Telemetry
        self.memory_widget = DraggableHUDWidget("COGNITIVE MEMORY VAULT", parent=self)
        self.memory_widget.setFixedSize(360, 175)
        self._memory_intel_view = None
        self.memory_widget.move(screen.width() - 640, 330)
        self.memory_widget.hide()

        # Native Hardware Health & Thermal Matrix
        self.hardware_widget = DraggableHUDWidget("HARDWARE HEALTH & THERMAL MATRIX", parent=self)
        self.hardware_widget.setFixedSize(360, 175)
        self._hardware_intel_view = None
        self.hardware_widget.move(screen.width() - 640, 520)
        self.hardware_widget.hide()

        # Active center-focus & resting dock memory tracking
        self.active_centered_widget = None
        self.widget_resting_positions = {}

        IntelHub().bind_core_references(hud=self)

        
        # =====================================================================
        # APPLICATION SHORTCUT ARRAY (Replaces Win32 Keyboard Hooks)
        # =====================================================================
        self.shortcut_toggle = QShortcut(QKeySequence("Ctrl+Space"), self)
        self.shortcut_toggle.activated.connect(self.toggle_cmd)

        # Standard Return Key Intercept
        self.shortcut_return = QShortcut(QKeySequence("Return"), self)
        self.shortcut_return.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.shortcut_return.activated.connect(self.handle_global_enter)

        # Numeric Keypad Enter Intercept
        self.shortcut_enter = QShortcut(QKeySequence("Enter"), self)
        self.shortcut_enter.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.shortcut_enter.activated.connect(self.handle_global_enter)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.showFullScreen()

        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.send_vitals_to_js)
        self.stats_timer.start(1000)
        self.last_net_io = psutil.net_io_counters()

        self.setup_system_tray()
        self.orb = FloatingOrb(self.restore_from_orb)

        self.all_hud_widgets = [
            self.telemetry_widget, self.optical_widget, self.log_widget, 
            self.command_widget, self.admin_widget, self.security_widget, 
            self.network_widget, self.diagnostics_widget, self.antigravity_widget,
            self.events_widget, self.weather_widget, self.news_widget, self.map_widget
        ]
        self.all_hud_widgets.extend([self.audio_widget, self.memory_widget, self.hardware_widget])
        self.all_labels = [
            self.telemetry_label, self.optical_label, self.admin_label, 
            self.security_label, self.network_label, self.diagnostics_label, self.antigravity_label,
            self.events_label, self.weather_label, self.news_label, self.map_label
        ]

        self.widget_map = {
            "telemetry": self.telemetry_widget,
            "optical": self.optical_widget,
            "log": self.log_widget,
            "command": self.command_widget,
            "admin": self.admin_widget,
            "security": self.security_widget,
            "network": self.network_widget,
            "diagnostics": self.diagnostics_widget,
            "antigravity": self.antigravity_widget,
            "events": self.events_widget,
            "calendar": self.events_widget,
            "weather": self.weather_widget,
            "news": self.news_widget,
            "map": self.map_widget
        }
        self.reactor_docked = False
        self.widget_map.update({
            "audio": self.audio_widget,
            "sound": self.audio_widget,
            "spectrum": self.audio_widget,
            "voice": self.audio_widget,
            "microphone": self.audio_widget,
            "memory": self.memory_widget,
            "vault": self.memory_widget,
            "profile": self.memory_widget,
            "facts": self.memory_widget,
            "hardware": self.hardware_widget,
            "thermal": self.hardware_widget,
            "gpu": self.hardware_widget,
            "sensors": self.hardware_widget
        })

        # Connect closed_signal on all widgets for auto-recentering
        for widget in self.all_hud_widgets:
            widget.closed_signal.connect(self.on_widget_closed)

        # ==========================================
        # PHASE 2: CINEMATIC BOOT SETUP
        # ==========================================
        self.opacity_effects = []
        for widget in self.all_hud_widgets:
            effect = QGraphicsOpacityEffect(widget)
            effect.setOpacity(0.0)  # Start completely invisible
            widget.setGraphicsEffect(effect)
            self.opacity_effects.append(effect)
            
        # Protects animations from Python's garbage collector during runtime
        self.active_animations = []

        # Analyze screen size and automatically layout maximum of 5 core widgets on boot
        self.auto_layout_boot_widgets()

    def handle_global_enter(self):
        """Routes the Enter key intelligently based on user focus."""
        if self.cmd_input.hasFocus():
            self.submit_cmd()  # If typing, send the text to Jarvis!
        else:
            self.interrupt_speech_signal.emit() # If not typing, interrupt audio.
    
    def toggle_cmd(self):
        is_hidden_or_closing = (
            self.command_widget.isHidden() 
            or getattr(self.command_widget, '_is_closing', False)
            or (self.command_widget.graphicsEffect() and self.command_widget.graphicsEffect().opacity() < 0.1)
        )
        if is_hidden_or_closing:
            self.reveal_widget_with_scan("command")
            self.cmd_input.setFocus()
        else:
            if not self.cmd_input.hasFocus():
                self.cmd_input.setFocus()
            else:
                self.dismiss_widget("command")
                self.dashboard.setFocus()


    def submit_cmd(self):
        text = self.cmd_input.text()
        if text.strip():
            self.text_command_signal.emit(text) 
        self.cmd_input.clear()
        self.cmd_input.setFocus()
        
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
        if not self.isVisible() and self.orb.isVisible():
            return
        # Remember which widgets were visible before minimizing
        self._visible_widgets_before_min = [
            w for w in self.all_hud_widgets 
            if w.isVisible() and not getattr(w, '_is_closing', False) and (
                (w.graphicsEffect() and w.graphicsEffect().opacity() > 0.05) or getattr(w, '_is_opening', False)
            )
        ]
        # Explicitly hide child widgets so Qt's showFullScreen doesn't force all visible on restore
        for w in self.all_hud_widgets:
            w.hide()
        self.hide() 
        self.orb.set_active(False)
        screen = QApplication.primaryScreen().geometry()
        self.orb.move(screen.width() - 150, 50)
        self.orb.show()
        self.hud_state_signal.emit("minimized")

    def restore_from_orb(self):
        already_restored = self.isVisible() and not self.orb.isVisible()
        self.orb.hide()
        self.showFullScreen()
        self.raise_()
        self.activateWindow()
        if not already_restored:
            # Keep widgets that were closed hidden; only restore widgets that were visible
            visible_set = set(getattr(self, '_visible_widgets_before_min', []))
            for w in self.all_hud_widgets:
                if w not in visible_set:
                    w.hide()
                    eff = w.graphicsEffect()
                    if eff and isinstance(eff, QGraphicsOpacityEffect):
                        eff.setOpacity(0.0)
                else:
                    w.show()
                    eff = w.graphicsEffect()
                    if eff and isinstance(eff, QGraphicsOpacityEffect):
                        eff.setOpacity(1.0)
        if hasattr(self, 'close_btn'):
            self.close_btn.raise_()
        if hasattr(self, 'min_btn'):
            self.min_btn.raise_()
        self.check_auto_recenter()
        self.hud_state_signal.emit("restored")

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.restore_from_orb()

    def resizeEvent(self, event):
        w, h = self.width(), self.height()
        if hasattr(self, 'dashboard'):
            self.dashboard.setGeometry(0, 0, w, h)
        if hasattr(self, 'close_btn'):
            self.close_btn.setGeometry(w - 50, 15, 40, 40)
            self.close_btn.raise_()
        if hasattr(self, 'min_btn'):
            self.min_btn.setGeometry(w - 90, 15, 40, 40)
            self.min_btn.raise_()
        super().resizeEvent(event)

    def on_load_finished(self, ok):
        if ok:
            print("[HUD] Dashboard GUI Loaded Successfully.")
            self.page_loaded = True
            # Sync pending state that may have been emitted before DOM was ready
            if self.orb.combat_mode:
                self.dashboard.page().runJavaScript("setCombatMode(true);")
            elif self.orb.antigravity_mode:
                self.dashboard.page().runJavaScript("setAntigravityMode(true);")
            if self.reactor_docked:
                self.dashboard.page().runJavaScript("setReactorDocked(true);")


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
        if not data: return
        if isinstance(data, str):
            log_text = data
            action = None
        else:
            log_text = data.get('log', '')
            action = data.get('action')
        
        if log_text and ("USER" in log_text or "JARVIS" in log_text or "SYSTEM" in log_text or "[WARNING]" in log_text or "[CRITICAL]" in log_text or "[INIT]" in log_text or ">>" in log_text):
            self.log_output.append(log_text)
            self.log_output.verticalScrollBar().setValue(self.log_output.verticalScrollBar().maximum())
        
        if action == 'cinematic_boot':
            self.execute_cinematic_boot()
            
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

        elif action in ('antigravity_start', 'antigravity_on'):
            self.orb.combat_mode = False
            self.orb.antigravity_mode = True
            self.close_btn.setStyleSheet(self.antigravity_btn_style)
            self.min_btn.setStyleSheet(self.antigravity_btn_style)
            self.cmd_input.setStyleSheet(self.standard_input_style.replace("#00d4ff", "#a142f4"))
            if self.page_loaded and hasattr(self, 'dashboard'):
                self.dashboard.page().runJavaScript("setAntigravityMode(true);")
            
            for widget in self.all_hud_widgets: 
                widget.set_theme(combat=False, antigravity=True)
                
            ag_css = "color: #00e5ff; font-family: 'Consolas', monospace; font-size: 13px; line-height: 1.5;"
            for label in self.all_labels: 
                label.setStyleSheet(ag_css)
            self.log_output.setStyleSheet("QTextEdit { background-color: transparent; color: #a142f4; font-family: 'Consolas', monospace; font-size: 12px; border: none; }")
            self.antigravity_label.setText("AGENT: ACTIVE [THINKING]\nMODEL: gemini-3.5-flash-lite\nMODE: AUTONOMOUS\nTOOL: INITIALIZING...\nSTATUS: COGNITIVE REFLECTION")

        elif action == 'antigravity_tool':
            tool_name = data.get("tool", "unknown")
            self.antigravity_label.setText(f"AGENT: EXECUTING\nMODEL: gemini-3.5-flash-lite\nMODE: AUTONOMOUS\nTOOL: {tool_name.upper()}\nSTATUS: OPERATING FILESYSTEM")
            if self.page_loaded and hasattr(self, 'dashboard'):
                self.dashboard.page().runJavaScript(f"updateAgentTool('{tool_name}');")

        elif action in ('antigravity_done', 'combat_off', 'antigravity_off', 'standard_mode'):
            self.orb.combat_mode = False
            self.orb.antigravity_mode = False
            self.close_btn.setStyleSheet(self.standard_btn_style)
            self.min_btn.setStyleSheet(self.standard_btn_style)
            self.cmd_input.setStyleSheet(self.standard_input_style)
            if self.page_loaded and hasattr(self, 'dashboard'):
                self.dashboard.page().runJavaScript("setCombatMode(false);")
                self.dashboard.page().runJavaScript("setAntigravityMode(false);")
            
            for widget in self.all_hud_widgets: 
                widget.set_theme(combat=False, antigravity=False)
                
            standard_css = "color: #00d4ff; font-family: 'Consolas', monospace; font-size: 13px; line-height: 1.5;"
            for label in self.all_labels: 
                label.setStyleSheet(standard_css)
            self.log_output.setStyleSheet("QTextEdit { background-color: transparent; color: #00d4ff; font-family: 'Consolas', monospace; font-size: 12px; border: none; }")
            self.antigravity_label.setText("AGENT: STANDBY [IDLE]\nMODEL: gemini-3.5-flash-lite\nMODE: AUTONOMOUS\nTOOL: NONE\nSTATUS: ONLINE")

        elif action == 'combat_on':
            self.orb.combat_mode = True
            self.orb.antigravity_mode = False
            self.close_btn.setStyleSheet(self.combat_btn_style)
            self.min_btn.setStyleSheet(self.combat_btn_style)
            self.cmd_input.setStyleSheet(self.combat_input_style) 
            if self.page_loaded and hasattr(self, 'dashboard'):
                self.dashboard.page().runJavaScript("setCombatMode(true);")
            
            for widget in self.all_hud_widgets: 
                widget.set_theme(combat=True, antigravity=False)
                widget.hide()
                eff = widget.graphicsEffect()
                if eff and isinstance(eff, QGraphicsOpacityEffect):
                    eff.setOpacity(0.0)
            self.recenter_reactor()
            if hasattr(self, '_visible_widgets_before_min'):
                self._visible_widgets_before_min = []
                
            combat_css = "color: #ff003c; font-family: 'Consolas', monospace; font-size: 13px; line-height: 1.5;"
            for label in self.all_labels: 
                label.setStyleSheet(combat_css)
            self.log_output.setStyleSheet("QTextEdit { background-color: transparent; color: #ff003c; font-family: 'Consolas', monospace; font-size: 12px; border: none; }")


        elif action == 'wake': self.orb.set_active(True)
        elif action == 'standby': self.orb.set_active(False)
        elif action == 'minimize_dashboard': self.minimize_to_orb()
        elif action == 'restore_dashboard': self.restore_from_orb()
        elif action == 'watchdog_active':
            target_str = str(data.get('target', 'PERSON')).upper()
            if hasattr(self, 'optical_label'):
                self.optical_label.setText(f"Watchdog: ARMED\nTarget: {target_str}\nStatus: SCANNING MOTION")
            if hasattr(self, 'optical_widget'):
                self.optical_widget.title_label.setText(f"OPTICAL GUARD - {target_str}")
        elif action == 'watchdog_disarmed':
            if hasattr(self, 'optical_label'):
                self.optical_label.setText("Watchdog: DISARMED\nTarget: NONE\nFPS: 30")
            if hasattr(self, 'optical_widget'):
                self.optical_widget.title_label.setText("OPTICAL GUARD")
        elif action == 'update_calendar':
            cal_msg = data.get('message', 'CALENDAR: SYNCHRONIZED')
            if hasattr(self, 'events_label'):
                self.events_label.setText(f"CALENDAR: SYNCHRONIZED\n{cal_msg[:70]}")
        elif action == 'show_widget':
            self.reveal_widget_with_scan(data.get('target', ''), query=data.get('query', ''))
        elif action == 'hide_widget':
            self.dismiss_widget(data.get('target', ''))
        elif action == 'recenter_reactor':
            self.recenter_reactor()

    def update_weather_intel(self, sector="kochi"):
        """Loads atmospheric radar telemetry and syncs with IntelHub."""
        IntelHub().execute_weather_query(f"weather in {sector}")
        if not hasattr(self, 'weather_label'):
            return
        cache_path = resource_path("openmeteo_atmospheric_cache.json")
        if not os.path.exists(cache_path):
            cache_path = resource_path("atmospheric_cache.json")
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                matched = None
                sector_key = sector.lower().strip()
                for k, v in data.items():
                    if sector_key in k or k in sector_key:
                        matched = v
                        break
                if not matched and data:
                    matched = next(iter(data.values()))
                if matched and "current" in matched:
                    curr = matched["current"]
                    name = matched.get("meta_name", sector.upper())
                    temp = curr.get("temp", 28.0)
                    hum = curr.get("humidity", 75)
                    wind = curr.get("wind_spd", 10.0)
                    wind_dir = curr.get("wind_dir", "W")
                    cond = curr.get("condition", "OPTIMAL VISIBILITY")
                    self.weather_label.setText(
                        f"ATMOSPHERIC RADAR TELEMETRY\n"
                        f"SECTOR: {name[:24]} [ACTIVE]\n"
                        f"TEMP: {temp}°C // HUMIDITY: {hum}%\n"
                        f"WIND: {wind} KM/H [{wind_dir}]\n"
                        f"COND: {cond[:28]}"
                    )
            except Exception:
                pass

    def update_news_intel(self, query="", auto_speak=False):
        """Loads situation room headlines, updates LiveNewsHUDWidget, and triggers briefing."""
        IntelHub().execute_news_query(query, auto_speak=auto_speak)
        if hasattr(self, 'news_widget') and hasattr(self.news_widget, 'title_label'):
            if query:
                self.news_widget.title_label.setText(f"SITUATION ROOM // {query.upper()} INTEL")
            else:
                self.news_widget.title_label.setText("GLOBAL SITUATION ROOM")
        if not hasattr(self, 'news_label'):
            return
        cache_path = resource_path("news_cache.json")
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                topic = data.get("topic", "GLOBAL")
                articles = data.get("data", [])
                top_title = articles[0].get("title", "SECTORS MONITORED") if articles else "FEEDS NOMINAL"
                self.news_label.setText(
                    f"GLOBAL SITUATION ROOM // INTEL\n"
                    f"[TOPIC]: {topic.upper()}\n"
                    f"[ALERT]: {top_title[:36]}...\n"
                    f"[FINANCIAL]: S&P 500: $5,850 || BTC: $67,800\n"
                    f"STATUS: ACTIVE SURVEILLANCE"
                )
            except Exception:
                pass

    def _ensure_weather_intel_view(self):
        """Lazily instantiates the Dynamic Atmospheric Weather view on first demand."""
        if self._weather_intel_view is None:
            self._weather_intel_view = DynamicWeatherHUDWidget(self.weather_widget)
            self.weather_widget.content_layout.addWidget(self._weather_intel_view)

    def _ensure_news_intel_view(self):
        """Lazily instantiates the Live News Situation Room view on first demand."""
        if self._news_intel_view is None:
            self._news_intel_view = LiveNewsHUDWidget(self.news_widget)
            self.news_widget.content_layout.addWidget(self._news_intel_view)

    def _ensure_map_intel_view(self):
        """Lazily instantiates the Tactical Map WebEngine view on first demand."""
        if self._map_intel_view is None:
            self._map_intel_view = TacticalMapHUDWidget(self.map_widget)
            self.map_widget.content_layout.addWidget(self._map_intel_view)

    def _ensure_audio_intel_view(self):
        """Lazily instantiates the Acoustic Spectrum & Vocal Core view on first demand."""
        if self._audio_intel_view is None:
            self._audio_intel_view = AudioSpectrumHUDWidget(self.audio_widget)
            self.audio_widget.content_layout.addWidget(self._audio_intel_view)

    def _ensure_memory_intel_view(self):
        """Lazily instantiates the Cognitive Memory Vault view on first demand."""
        if self._memory_intel_view is None:
            self._memory_intel_view = CognitiveMemoryHUDWidget(self.memory_widget)
            self.memory_widget.content_layout.addWidget(self._memory_intel_view)

    def _ensure_hardware_intel_view(self):
        """Lazily instantiates the Hardware Health & Thermal Matrix view on first demand."""
        if self._hardware_intel_view is None:
            self._hardware_intel_view = HardwareHealthHUDWidget(self.hardware_widget)
            self.hardware_widget.content_layout.addWidget(self._hardware_intel_view)

    @property
    def weather_intel_view(self):
        if self._weather_intel_view is None:
            self._ensure_weather_intel_view()
        return self._weather_intel_view

    @weather_intel_view.setter
    def weather_intel_view(self, val):
        self._weather_intel_view = val

    @property
    def news_intel_view(self):
        if self._news_intel_view is None:
            self._ensure_news_intel_view()
        return self._news_intel_view

    @news_intel_view.setter
    def news_intel_view(self, val):
        self._news_intel_view = val

    @property
    def map_intel_view(self):
        if self._map_intel_view is None:
            self._ensure_map_intel_view()
        return self._map_intel_view

    @map_intel_view.setter
    def map_intel_view(self, val):
        self._map_intel_view = val

    @property
    def audio_intel_view(self):
        if self._audio_intel_view is None:
            self._ensure_audio_intel_view()
        return self._audio_intel_view

    @audio_intel_view.setter
    def audio_intel_view(self, val):
        self._audio_intel_view = val

    @property
    def memory_intel_view(self):
        if self._memory_intel_view is None:
            self._ensure_memory_intel_view()
        return self._memory_intel_view

    @memory_intel_view.setter
    def memory_intel_view(self, val):
        self._memory_intel_view = val

    @property
    def hardware_intel_view(self):
        if self._hardware_intel_view is None:
            self._ensure_hardware_intel_view()
        return self._hardware_intel_view

    @hardware_intel_view.setter
    def hardware_intel_view(self, val):
        self._hardware_intel_view = val

    def update_map_intel(self, location="EDAKKUNNAM"):
        """Updates tactical map recon coordinates and syncs with TacticalMapHUDWidget."""
        self._ensure_map_intel_view()
        IntelHub().execute_map_query(f"show map of {location}")
        if not hasattr(self, 'map_label'):
            return
        loc_str = str(location).upper()
        self.map_label.setText(
            f"TACTICAL MAP RECONNAISSANCE GRID\n"
            f"SECTOR: {loc_str[:22]} [RECON]\n"
            f"COORDINATES: 9.5916° N, 76.5222° E\n"
            f"ORBITAL ALTITUDE: LEVEL 14 [TACTICAL]\n"
            f"GRID VECTOR: LOCKED & NOMINAL"
        )

    def auto_layout_boot_widgets(self):
        """
        Analyzes active screen resolution and dynamically positions the 7 core HUD widgets
        in clean, non-overlapping symmetrical bays for the cinematic boot sequence:
        Left Column:
          1. System Telemetry (Top Left)
          2. Sys.Admin Identity (Mid Left)
          3. Neural Activity Log (Bottom Left)
        Center Dock:
          4. Command Override Uplink (Bottom Center)
        Right Column:
          5. Atmospheric Weather Radar (Top Right)
          6. Hardware Health & Thermal Matrix (Mid Right)
          7. Security Center Shield (Bottom Right)
        All widgets start cleanly hidden, ready to pop in on facial recognition and collapse after boot.
        """
        screen = QApplication.primaryScreen().availableGeometry()
        sw = screen.width()
        sh = screen.height()

        # 1. Command Override Uplink (Bottom Center)
        cmd_w = min(620, sw - 100)
        cmd_h = 95
        self.command_widget.setFixedSize(cmd_w, cmd_h)
        self.command_widget.move((sw - cmd_w) // 2, sh - cmd_h - 25)

        # 2. System Telemetry (Top Left)
        telem_w = min(280, max(240, sw // 4))
        telem_h = 115
        self.telemetry_widget.setFixedSize(telem_w, telem_h)
        self.telemetry_widget.move(40, 40)

        # 3. Sys.Admin Identity (Mid Left below telemetry)
        admin_w = min(280, max(240, sw // 4))
        admin_h = 125
        self.admin_widget.setFixedSize(admin_w, admin_h)
        self.admin_widget.move(40, 40 + telem_h + 15)

        # 4. Neural Activity Log (Bottom Left)
        log_w = min(480, max(360, (sw - 140) // 2))
        avail_h = (sh - cmd_h - 40) - (40 + telem_h + admin_h + 30)
        log_h = max(180, min(240, avail_h))
        self.log_widget.setFixedSize(log_w, log_h)
        self.log_widget.move(40, sh - cmd_h - 35 - log_h)

        # 5. Atmospheric Weather Radar (Top Right)
        weather_w = min(400, max(320, sw // 3))
        weather_h = min(270, max(230, (sh - cmd_h - 140) // 2))
        self.weather_widget.setFixedSize(weather_w, weather_h)
        self.weather_widget.move(sw - weather_w - 40, 40)

        # 6. Hardware Health & Thermal Matrix (Mid Right)
        hw_w = min(360, max(280, weather_w))
        hw_h = 165
        self.hardware_widget.setFixedSize(hw_w, hw_h)
        self.hardware_widget.move(sw - hw_w - 40, 40 + weather_h + 15)

        # 7. Security Center Shield (Bottom Right)
        sec_w = min(320, max(260, weather_w))
        sec_h = 130
        self.security_widget.setFixedSize(sec_w, sec_h)
        self.security_widget.move(sw - sec_w - 40, sh - cmd_h - 35 - sec_h)

        # Base geometry for perimeter bays for remaining on-demand widgets
        news_w = min(420, max(340, sw // 3))
        news_h = min(330, max(260, sh // 2))
        self.news_widget.setFixedSize(news_w, news_h)
        self.news_widget.move(sw - news_w - 40, 40)

        map_w = min(460, max(360, sw // 3))
        map_h = min(340, max(260, sh // 2))
        self.map_widget.setFixedSize(map_w, map_h)
        self.map_widget.move(sw - map_w - 40, 40)

        audio_w = 360
        audio_h = 165
        self.audio_widget.setFixedSize(audio_w, audio_h)
        self.audio_widget.move(sw - audio_w - 40, 40)

        mem_w = 360
        mem_h = 175
        self.memory_widget.setFixedSize(mem_w, mem_h)
        self.memory_widget.move(sw - mem_w - 40, 220)

        opt_w = 280
        opt_h = 120
        self.optical_widget.setFixedSize(opt_w, opt_h)
        self.optical_widget.move(40, 200)

        net_w = 280
        net_h = 150
        self.network_widget.setFixedSize(net_w, net_h)
        self.network_widget.move(sw - net_w - 40, 50)

        diag_w = 280
        diag_h = 120
        self.diagnostics_widget.setFixedSize(diag_w, diag_h)
        self.diagnostics_widget.move(sw - diag_w - 40, 300)

        ag_w = 280
        ag_h = 150
        self.antigravity_widget.setFixedSize(ag_w, ag_h)
        self.antigravity_widget.move(sw - ag_w - 40, 440)

        events_w = 280
        events_h = 130
        self.events_widget.setFixedSize(events_w, events_h)
        self.events_widget.move(sw - events_w - 40, 600)

        # Record docking resting coordinates for all widgets
        for w in self.all_hud_widgets:
            self.widget_resting_positions[w] = QPoint(w.x(), w.y())

        # Exact 7 core widgets shown during facial recognition boot sequence
        self.boot_widgets = [
            self.telemetry_widget,
            self.admin_widget,
            self.security_widget,
            self.weather_widget,
            self.hardware_widget,
            self.log_widget,
            self.command_widget
        ]

        # Ensure all widgets start cleanly hidden with 0.0 opacity
        for w in self.all_hud_widgets:
            w.hide()
            eff = w.graphicsEffect()
            if eff and isinstance(eff, QGraphicsOpacityEffect):
                eff.setOpacity(0.0)

        self._visible_widgets_before_min = []

    def execute_cinematic_boot(self):
        """Fires the boot sound and starts the fast-paced staggered reveal for the 7 boot widgets timed to jarvis_boot.wav, then hides everything."""
        sound_path = resource_path(os.path.join('assets', 'jarvis_boot.wav'))
        if os.path.exists(sound_path):
            winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        else:
            print("[SYSTEM WARNING]: 'assets/jarvis_boot.wav' missing. Skipping audio.")

        self.auto_layout_boot_widgets()

        for w in self.boot_widgets:
            eff = w.graphicsEffect()
            if not eff or not isinstance(eff, QGraphicsOpacityEffect):
                eff = QGraphicsOpacityEffect(w)
                w.setGraphicsEffect(eff)
            eff.setOpacity(0.0)

        # Precise fast-paced timing synchronized to jarvis_boot.wav waveform
        chime_delays = [250, 600, 1000, 1400, 1800, 2200, 2650]
        for w, delay in zip(self.boot_widgets, chime_delays):
            QTimer.singleShot(delay, lambda target=w: self._pop_in_boot_widget(target))

        # Completion chord at 4.3s: announce nominal status, trigger scan sweep, and hide everything
        def _on_boot_complete():
            if self.page_loaded and hasattr(self, 'dashboard'):
                self.dashboard.page().runJavaScript("if (typeof triggerScanSweep === 'function') triggerScanSweep();")
            print("[SYSTEM]: Boot audio sequence completed. HUD Nominal. Collapsing peripheral widgets to core.")
            self.collapse_to_reactor_core()

        QTimer.singleShot(4300, _on_boot_complete)

    def _pop_in_boot_widget(self, widget):
        """Crisply pops in a boot widget with fast-paced opacity and position easing."""
        if widget == self.weather_widget:
            self._ensure_weather_intel_view()
        elif widget == self.hardware_widget:
            self._ensure_hardware_intel_view()

        eff = widget.graphicsEffect()
        if not eff or not isinstance(eff, QGraphicsOpacityEffect):
            eff = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(eff)

        resting_pos = self.widget_resting_positions.get(widget, widget.pos())
        pop_start_pos = QPoint(resting_pos.x(), resting_pos.y() + 12)
        widget.move(pop_start_pos)
        widget.show()
        widget.raise_()

        anim_op = QPropertyAnimation(eff, b"opacity")
        anim_op.setDuration(220)
        anim_op.setStartValue(eff.opacity())
        anim_op.setEndValue(1.0)
        anim_op.setEasingCurve(QEasingCurve.Type.OutCubic)

        anim_pos = QPropertyAnimation(widget, b"pos")
        anim_pos.setDuration(220)
        anim_pos.setStartValue(pop_start_pos)
        anim_pos.setEndValue(resting_pos)
        anim_pos.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.active_animations.extend([anim_op, anim_pos])
        def _cleanup(ao=anim_op, ap=anim_pos):
            if ao in self.active_animations:
                self.active_animations.remove(ao)
            if ap in self.active_animations:
                self.active_animations.remove(ap)

        anim_pos.finished.connect(_cleanup)
        anim_op.start()
        anim_pos.start()

    def collapse_to_reactor_core(self):
        """Fades out all peripheral widgets over 450ms, leaving only the central Arc Reactor."""
        for widget in self.all_hud_widgets:
            widget._is_opening = False
            effect = widget.graphicsEffect()
            current_op = effect.opacity() if effect and isinstance(effect, QGraphicsOpacityEffect) else 0.0
            
            if not widget.isVisible() or current_op <= 0.05:
                widget._is_closing = False
                widget.hide()
                if effect:
                    effect.setOpacity(0.0)
                continue

            widget._is_closing = True
            anim = QPropertyAnimation(effect, b"opacity")
            anim.setDuration(450)
            anim.setStartValue(current_op)
            anim.setEndValue(0.0)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            
            def _on_collapse_finished(w=widget, a=anim):
                w._is_closing = False
                w.hide()
                if a in self.active_animations:
                    self.active_animations.remove(a)

            anim.finished.connect(_on_collapse_finished)
            self.active_animations.append(anim)
            anim.start()

        if hasattr(self, '_visible_widgets_before_min'):
            self._visible_widgets_before_min = []
        self.recenter_reactor()
        
        self.recenter_reactor()


    def _normalize_widget_key(self, key):
        if not key:
            return ""
        k = str(key).lower().strip()
        words = set(k.split())
        if "all" in words or "widgets" in words or "every" in words or any(w in k for w in ["everything", "grid", "components"]):
            return "all"
        if any(w in k for w in ["optical", "guard", "camera", "webcam", "vision", "array", "feed"]):
            return "optical"
        if any(w in k for w in ["audio", "spectrum", "vocal", "microphone", "sound", "equalizer", "mic"]):
            return "audio"
        if any(w in k for w in ["memory", "vault", "profile", "facts", "recall"]):
            return "memory"
        if any(w in k for w in ["hardware", "gpu", "vram", "thermal", "sensor", "temperatures"]):
            return "hardware"
        if any(w in k for w in ["telemetry", "vital", "cpu", "ram", "performance", "stat"]):
            return "telemetry"
        if any(w in k for w in ["log", "neural", "activity", "console"]):
            return "log"
        if any(w in k for w in ["command", "override", "uplink", "input", "prompt"]):
            return "command"
        if any(w in k for w in ["admin", "credentials", "user", "sysadmin"]):
            return "admin"
        if any(w in k for w in ["security", "shield", "firewall", "protection", "antivirus"]):
            return "security"
        if any(w in k for w in ["network", "wifi", "bandwidth", "hub", "internet", "connection"]):
            return "network"
        if any(w in k for w in ["diagnostic", "integrity", "kernel"]):
            return "diagnostics"
        if any(w in k for w in ["antigravity", "quantum", "cognitive", "agent"]):
            return "antigravity"
        if any(w in k for w in ["calendar", "event", "schedule"]):
            return "events"
        if any(w in k for w in ["weather", "meteo", "forecast", "radar", "atmospheric"]):
            return "weather"
        if any(w in k for w in ["news", "situation", "headline", "intel"]):
            return "news"
        if any(w in k for w in ["map", "tactical", "satellite", "recon"]):
            return "map"
        return k

    def reveal_widget_with_scan(self, widget_key, query=""):
        """Triggers laser scan sweep, docks reactor to side, and fades in requested widget."""
        if not self.isVisible():
            self.restore_from_orb()

        norm_key = self._normalize_widget_key(widget_key)
        targets = []
        if norm_key == "all":
            targets = self.all_hud_widgets
        elif norm_key in self.widget_map:
            targets = [self.widget_map[norm_key]]
        else:
            for key, w in self.widget_map.items():
                if widget_key and str(widget_key).lower() in key:
                    targets = [w]
                    break

        if not targets:
            return

        if norm_key in ("weather", "all") or self.weather_widget in targets:
            self._ensure_weather_intel_view()
            self.update_weather_intel()
        if norm_key in ("news", "all") or self.news_widget in targets:
            self._ensure_news_intel_view()
            if norm_key == "news" and hasattr(self, 'news_widget') and self.news_widget.isVisible():
                self.update_news_intel(query=query, auto_speak=False)
                return
            self.update_news_intel(query=query, auto_speak=False)
        if norm_key in ("map", "all") or self.map_widget in targets:
            self._ensure_map_intel_view()
            self.update_map_intel()
        if norm_key in ("audio", "all") or self.audio_widget in targets:
            self._ensure_audio_intel_view()
        if norm_key in ("memory", "all") or self.memory_widget in targets:
            self._ensure_memory_intel_view()
        if norm_key in ("hardware", "all") or self.hardware_widget in targets:
            self._ensure_hardware_intel_view()

        # Keep persistence memory updated
        if hasattr(self, '_visible_widgets_before_min'):
            for widget in targets:
                if widget not in self._visible_widgets_before_min:
                    self._visible_widgets_before_min.append(widget)

        # 1. Trigger laser scan sweep & dock Arc Reactor in WebEngine
        self.reactor_docked = True
        if self.page_loaded and hasattr(self, 'dashboard'):
            self.dashboard.page().runJavaScript("triggerScanSweep();")
            self.dashboard.page().runJavaScript("setReactorDocked(true);")

        # 2. Auto-Focus Center: If a specific single widget was requested, center it prominently
        screen = QApplication.primaryScreen().availableGeometry()
        sw = screen.width()
        sh = screen.height()

        if norm_key != "all" and len(targets) == 1:
            target_widget = targets[0]

            # Auto-Docking Return: If another widget was previously centered, glide it back to resting bay
            if self.active_centered_widget and self.active_centered_widget != target_widget:
                prev_widget = self.active_centered_widget
                dock_pos = self.widget_resting_positions.get(prev_widget)
                if dock_pos and prev_widget.pos() != dock_pos:
                    dock_anim = QPropertyAnimation(prev_widget, b"pos")
                    dock_anim.setDuration(450)
                    dock_anim.setStartValue(prev_widget.pos())
                    dock_anim.setEndValue(dock_pos)
                    dock_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                    self.active_animations.append(dock_anim)
                    def _cleanup_dock(a=dock_anim):
                        if a in self.active_animations:
                            self.active_animations.remove(a)
                    dock_anim.finished.connect(_cleanup_dock)
                    dock_anim.start()
                self.active_centered_widget = None

            # Remember target resting position before centering if not stored
            if target_widget not in self.widget_resting_positions:
                self.widget_resting_positions[target_widget] = QPoint(target_widget.x(), target_widget.y())

            # Smoothly glide target widget into center
            cx = max(30, (sw - target_widget.width()) // 2)
            cy = max(40, (sh - target_widget.height() - 70) // 2)
            center_pt = QPoint(cx, cy)

            if target_widget.pos() != center_pt:
                center_anim = QPropertyAnimation(target_widget, b"pos")
                center_anim.setDuration(500)
                center_anim.setStartValue(target_widget.pos())
                center_anim.setEndValue(center_pt)
                center_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                self.active_animations.append(center_anim)
                def _cleanup_center(a=center_anim):
                    if a in self.active_animations:
                        self.active_animations.remove(a)
                center_anim.finished.connect(_cleanup_center)
                center_anim.start()

            target_widget.raise_()
            self.active_centered_widget = target_widget

        # 3. Holographically materialize each target widget
        for widget in targets:
            widget._is_closing = False
            widget._is_opening = True
            if hasattr(widget, '_close_anim') and widget._close_anim and widget._close_anim.state() == QPropertyAnimation.State.Running:
                widget._close_anim.stop()

            widget.show()
            effect = widget.graphicsEffect()
            if not effect or not isinstance(effect, QGraphicsOpacityEffect):
                effect = QGraphicsOpacityEffect(widget)
                widget.setGraphicsEffect(effect)
            
            anim = QPropertyAnimation(effect, b"opacity")
            anim.setDuration(500)
            anim.setStartValue(effect.opacity())
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            widget._open_anim = anim

            def _on_reveal_finished(w=widget, a=anim):
                w._is_opening = False
                if a in self.active_animations:
                    self.active_animations.remove(a)

            anim.finished.connect(_on_reveal_finished)
            self.active_animations.append(anim)
            anim.start()

    def dismiss_widget(self, widget_key):
        """Dismisses the specified widget (or all) and auto-recenters reactor if none visible."""
        norm_key = self._normalize_widget_key(widget_key)
        if norm_key == "all":
            self.dismiss_all_widgets()
            return

        target = self.widget_map.get(norm_key)
        if not target:
            for key, w in self.widget_map.items():
                if widget_key and str(widget_key).lower() in key:
                    target = w
                    break

        if target:
            target.close_widget()
            if hasattr(self, '_visible_widgets_before_min') and target in self._visible_widgets_before_min:
                self._visible_widgets_before_min.remove(target)
            
        QTimer.singleShot(270, self.check_auto_recenter)

    def dismiss_all_widgets(self):
        """Dismisses all draggable HUD widgets and recenters the Arc Reactor."""
        for w in self.all_hud_widgets:
            w.close_widget()
        if hasattr(self, '_visible_widgets_before_min'):
            self._visible_widgets_before_min = []
        self.recenter_reactor()

    def check_auto_recenter(self):
        """Checks if any HUD widget remains visible on screen; if not, recenters Arc Reactor."""
        any_visible = False
        for w in self.all_hud_widgets:
            if w.isVisible() and not getattr(w, '_is_closing', False):
                effect = w.graphicsEffect()
                if (effect and effect.opacity() > 0.05) or getattr(w, '_is_opening', False):
                    any_visible = True
                    break
        if not any_visible:
            self.recenter_reactor()


    def recenter_reactor(self):
        """Smoothly returns Arc Reactor to screen center via Chromium."""
        self.reactor_docked = False
        if self.page_loaded and hasattr(self, 'dashboard'):
            self.dashboard.page().runJavaScript("setReactorDocked(false);")

    def on_widget_closed(self, widget):
        """Slot invoked whenever a DraggableHUDWidget is closed."""
        if self.active_centered_widget == widget:
            self.active_centered_widget = None
        self.check_auto_recenter()

    
    def closeEvent(self, event):
        if hasattr(self, 'dashboard') and self.dashboard:
            self.dashboard.page().deleteLater()
            self.dashboard.setPage(None)
        event.accept()