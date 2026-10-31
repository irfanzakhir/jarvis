from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QPropertyAnimation, QEasingCurve

class DraggableHUDWidget(QFrame):
    closed_signal = pyqtSignal(object)

    def __init__(self, title="SYSTEM COMPONENT", parent=None):
        # Set to Tool window so it floats above everything and doesn't clutter the taskbar
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # ==========================================
        # BUILD THE TITLE BAR (Drag Area)
        # ==========================================
        self.title_bar = QFrame()
        self.title_bar.setFixedHeight(30)
        self.title_layout = QHBoxLayout(self.title_bar)
        self.title_layout.setContentsMargins(10, 0, 10, 0)

        self.title_label = QLabel(title)
        
        self.minimize_btn = QPushButton("-")
        self.minimize_btn.setFixedSize(20, 20)
        self.minimize_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.minimize_btn.clicked.connect(self.toggle_minimize)

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self.close_widget)

        self.title_layout.addWidget(self.title_label)
        self.title_layout.addStretch()
        self.title_layout.addWidget(self.minimize_btn)
        self.title_layout.addWidget(self.close_btn)

        # ==========================================
        # BUILD THE CONTENT AREA
        # ==========================================
        self.content_area = QFrame()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(15, 15, 15, 15)

        self.main_layout.addWidget(self.title_bar)
        self.main_layout.addWidget(self.content_area)

        # Variables for Drag Physics
        self._is_dragging = False
        self._drag_start_pos = QPoint()

        # State tracking for opening/closing animations
        self._is_opening = False
        self._is_closing = False
        self._close_anim = None

        # Apply default cyan theme on boot
        self.set_theme(combat=False)
        
        # Memory for the accordion collapse
        self._expanded_height = None


    # ==========================================
    # DYNAMIC AESTHETIC ENGINE
    # ==========================================
    def set_theme(self, combat=False, antigravity=False):
        if combat:
            # TACTICAL RED
            self.setStyleSheet("""
                DraggableHUDWidget { 
                    background-color: rgba(20, 0, 5, 220); 
                    border: 1px solid rgba(255, 0, 60, 100); 
                    border-radius: 5px; 
                }
                QLabel { color: #ff003c; font-family: 'Consolas', monospace; font-weight: bold; }
                QPushButton { background-color: transparent; color: #ff003c; border: none; font-weight: bold; font-size: 16px; }
                QPushButton:hover { color: white; background-color: rgba(255, 0, 60, 50); }
            """)
            self.title_bar.setStyleSheet("""
                background-color: rgba(70, 0, 10, 150); 
                border-bottom: 1px solid #ff003c; 
                border-top-left-radius: 5px; 
                border-top-right-radius: 5px;
            """)
            if hasattr(self, 'close_btn'):
                self.close_btn.setStyleSheet("""
                    QPushButton { color: #ff003c; border: none; font-weight: bold; font-size: 14px; background: transparent; }
                    QPushButton:hover { color: #ffffff; background-color: rgba(255, 0, 60, 100); border-radius: 3px; }
                """)
        elif antigravity:
            # ANTIGRAVITY QUANTUM VIOLET & ELECTRIC CYAN
            self.setStyleSheet("""
                DraggableHUDWidget { 
                    background-color: rgba(14, 10, 28, 230); 
                    border: 1px solid rgba(161, 66, 244, 150); 
                    border-radius: 6px; 
                }
                QLabel { color: #00e5ff; font-family: 'Consolas', monospace; font-weight: bold; }
                QPushButton { background-color: transparent; color: #a142f4; border: none; font-weight: bold; font-size: 16px; }
                QPushButton:hover { color: #ffffff; background-color: rgba(161, 66, 244, 60); }
            """)
            self.title_bar.setStyleSheet("""
                background-color: rgba(45, 15, 80, 180); 
                border-bottom: 1px solid #a142f4; 
                border-top-left-radius: 6px; 
                border-top-right-radius: 6px;
            """)
            if hasattr(self, 'close_btn'):
                self.close_btn.setStyleSheet("""
                    QPushButton { color: #a142f4; border: none; font-weight: bold; font-size: 14px; background: transparent; }
                    QPushButton:hover { color: #00e5ff; background-color: rgba(161, 66, 244, 100); border-radius: 3px; }
                """)
        else:
            # STANDARD CYAN
            self.setStyleSheet("""
                DraggableHUDWidget { 
                    background-color: rgba(10, 15, 20, 220); 
                    border: 1px solid rgba(0, 212, 255, 100); 
                    border-radius: 5px; 
                }
                QLabel { color: #00d4ff; font-family: 'Consolas', monospace; font-weight: bold; }
                QPushButton { background-color: transparent; color: #00d4ff; border: none; font-weight: bold; font-size: 16px; }
                QPushButton:hover { color: white; background-color: rgba(0, 212, 255, 50); }
            """)
            self.title_bar.setStyleSheet("""
                background-color: rgba(0, 50, 70, 150); 
                border-bottom: 1px solid #00d4ff; 
                border-top-left-radius: 5px; 
                border-top-right-radius: 5px;
            """)
            if hasattr(self, 'close_btn'):
                self.close_btn.setStyleSheet("""
                    QPushButton { color: #00d4ff; border: none; font-weight: bold; font-size: 14px; background: transparent; }
                    QPushButton:hover { color: #ffffff; background-color: rgba(0, 212, 255, 100); border-radius: 3px; }
                """)

    def close_widget(self):
        """Smoothly fades out opacity and emits closed_signal."""
        if self._is_closing:
            return

        effect = self.graphicsEffect()
        if not effect or not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(self)
            self.setGraphicsEffect(effect)
            effect.setOpacity(1.0)
            
        current_op = effect.opacity()
        if current_op <= 0.05 or not self.isVisible():
            self._is_opening = False
            self._is_closing = False
            self.hide()
            self.closed_signal.emit(self)
            return

        self._is_opening = False
        self._is_closing = True

        if hasattr(self, '_open_anim') and self._open_anim and self._open_anim.state() == QPropertyAnimation.State.Running:
            self._open_anim.stop()

        if self._close_anim and self._close_anim.state() == QPropertyAnimation.State.Running:
            self._close_anim.stop()

        self._close_anim = QPropertyAnimation(effect, b"opacity")
        self._close_anim.setDuration(250)
        self._close_anim.setStartValue(current_op)
        self._close_anim.setEndValue(0.0)
        self._close_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        def _finish():
            self._is_closing = False
            self.hide()
            self.closed_signal.emit(self)
            
        self._close_anim.finished.connect(_finish)
        self._close_anim.start()

    # ==========================================
    # COLLAPSE / MINIMIZE LOGIC
    # ==========================================
    def toggle_minimize(self):
        if self.content_area.isVisible():
            # 1. Capture the exact height before collapsing
            self._expanded_height = self.height()
            
            # 2. Hide the content
            self.content_area.hide()
            self.minimize_btn.setText("+")
            
            # 3. Force the parent frame to shrink to exactly the title bar height
            self.setFixedHeight(self.title_bar.height()) 
        else:
            # 1. Show the content
            self.content_area.show()
            self.minimize_btn.setText("-")
            
            # 2. Restore the original fixed height
            if self._expanded_height is not None:
                self.setFixedHeight(self._expanded_height)
            else:
                # Failsafe if it never had a fixed size
                self.setMinimumHeight(0)
                self.setMaximumHeight(16777215)
                self.adjustSize()

    # ==========================================
    # KINEMATIC DRAG LOGIC
    # ==========================================
    def mousePressEvent(self, event):
        # Only start dragging if left click is on the title bar
        if event.button() == Qt.MouseButton.LeftButton and self.title_bar.geometry().contains(event.pos()):
            self._is_dragging = True
            self._drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._is_dragging:
            new_pos = event.globalPosition().toPoint() - self._drag_start_pos
            if self.parent():
                parent_rect = self.parent().rect()
                # Ensure at least part of the widget stays inside parent visible area
                new_x = max(0, min(new_pos.x(), max(0, parent_rect.width() - 80)))
                new_y = max(0, min(new_pos.y(), max(0, parent_rect.height() - 35)))
                self.move(new_x, new_y)
            else:
                self.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._is_dragging = False
        event.accept()
