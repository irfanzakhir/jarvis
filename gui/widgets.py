from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PyQt6.QtCore import Qt, QPoint

class DraggableHUDWidget(QFrame):
    def __init__(self, title="SYSTEM COMPONENT", parent=None):
        # Set to Tool window so it floats above everything and doesn't clutter the taskbar
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
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
        self.minimize_btn.clicked.connect(self.toggle_minimize)

        self.title_layout.addWidget(self.title_label)
        self.title_layout.addStretch()
        self.title_layout.addWidget(self.minimize_btn)

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

        # Apply default cyan theme on boot
        self.set_theme(combat=False)
        
        # Memory for the accordion collapse
        self._expanded_height = None
        

    # ==========================================
    # DYNAMIC AESTHETIC ENGINE
    # ==========================================
    def set_theme(self, combat=False):
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

    # ==========================================
    # COLLAPSE / MINIMIZE LOGIC
    # ==========================================
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
            self.move(event.globalPosition().toPoint() - self._drag_start_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._is_dragging = False
        event.accept()