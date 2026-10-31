import sys
import sqlite3
import os
import json
import requests
from dotenv import load_dotenv
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTextEdit, QVBoxLayout, 
                             QHBoxLayout, QWidget, QLabel, QListWidget, QPushButton, QListWidgetItem)
from PyQt6.QtGui import QShortcut, QKeySequence
from PyQt6.QtCore import Qt

# Load API keys for live vector generation
load_dotenv()

class MemoryManagerConsole(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("J.A.R.V.I.S. Cognitive Memory Console")
        self.resize(900, 500)
        
        self.db_path = "assets/jarvis_memory.db"
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self._ensure_db()

        # ==========================================
        # UI CONSTRUCTION (J.A.R.V.I.S. THEME)
        # ==========================================
        main_layout = QVBoxLayout()
        
        # Header
        self.header_label = QLabel("COGNITIVE MEMORY MANAGEMENT CONSOLE")
        self.header_label.setStyleSheet("color: #00d4ff; font-family: 'Consolas', monospace; font-size: 16px; font-weight: bold;")
        self.header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.header_label)

        # Dual Pane Layout (List on left, Editor on right)
        pane_layout = QHBoxLayout()

        # Left Pane: Existing Memories
        self.memory_list = QListWidget()
        self.memory_list.setStyleSheet("""
            QListWidget { background-color: rgba(0, 10, 20, 0.85); color: #00d4ff; font-family: 'Consolas', monospace; font-size: 12px; border: 1px solid #00d4ff; padding: 5px; }
            QListWidget::item:selected { background-color: rgba(0, 212, 255, 0.3); }
        """)
        self.memory_list.itemClicked.connect(self.load_selected_memory)
        pane_layout.addWidget(self.memory_list, stretch=4)

        # Right Pane: Editor
        editor_layout = QVBoxLayout()
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Type a new fact or edit an existing one here...")
        self.text_input.setStyleSheet("""
            QTextEdit { background-color: rgba(0, 10, 20, 0.85); color: #00d4ff; font-family: 'Consolas', monospace; font-size: 14px; border: 1px solid #00d4ff; padding: 10px; }
            QTextEdit:focus { border: 1px solid #ffffff; }
        """)
        editor_layout.addWidget(self.text_input)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_style = """
            QPushButton { background-color: rgba(0, 50, 70, 0.8); color: #00d4ff; border: 1px solid #00d4ff; font-family: 'Consolas', monospace; font-weight: bold; padding: 8px; }
            QPushButton:hover { background-color: rgba(0, 212, 255, 0.3); color: white; }
        """
        btn_style_danger = btn_style.replace("#00d4ff", "#ff003c").replace("rgba(0, 212, 255, 0.3)", "rgba(255, 0, 60, 0.3)")

        self.btn_add = QPushButton("SAVE AS NEW (Ctrl+Enter)")
        self.btn_add.setStyleSheet(btn_style)
        self.btn_add.clicked.connect(self.add_memory)

        self.btn_update = QPushButton("UPDATE SELECTED")
        self.btn_update.setStyleSheet(btn_style)
        self.btn_update.clicked.connect(self.update_memory)

        self.btn_delete = QPushButton("DELETE SELECTED")
        self.btn_delete.setStyleSheet(btn_style_danger)
        self.btn_delete.clicked.connect(self.delete_memory)

        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_update)
        btn_layout.addWidget(self.btn_delete)
        editor_layout.addLayout(btn_layout)

        pane_layout.addLayout(editor_layout, stretch=6)
        main_layout.addLayout(pane_layout)

        # Status Bar
        self.status_label = QLabel("SYSTEM: ONLINE. AWAITING DIRECTIVES.")
        self.status_label.setStyleSheet("color: #aaaaaa; font-family: 'Consolas', monospace; font-size: 12px;")
        main_layout.addWidget(self.status_label)

        container = QWidget()
        container.setLayout(main_layout)
        container.setStyleSheet("background-color: #050505;")
        self.setCentralWidget(container)

        # Keyboard Shortcut
        self.shortcut_enter = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.shortcut_enter.activated.connect(self.add_memory)

        # Boot load
        self.refresh_list()

    # ==========================================
    # DATABASE & VECTOR ENGINE
    # ==========================================
    def _ensure_db(self):
        os.makedirs("assets", exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS long_term_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT, fact TEXT NOT NULL, vector TEXT NOT NULL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def _generate_vector(self, text):
        """Mathematically encodes the text so Jarvis can actually search for it later."""
        if not self.api_key:
            self.set_status("WARNING: No GEMINI_API_KEY found. Saving with dummy vector.", "#ffaa00")
            return "[]" # Safe fallback for memory.py's JSON loader
            
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key={self.api_key}"
            payload = {"model": "models/gemini-embedding-001", "content": {"parts": [{"text": text}]}}
            response = requests.post(url, json=payload, timeout=5) 
            if response.status_code == 200:
                return json.dumps(response.json()["embedding"]["values"])
        except Exception as e:
            print(f"Vector Error: {e}")
        
        self.set_status("WARNING: Vector generation failed. Saving with dummy vector.", "#ffaa00")
        return "[]"

    # ==========================================
    # CRUD OPERATIONS
    # ==========================================
    def refresh_list(self):
        self.memory_list.clear()
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id, fact FROM long_term_memory ORDER BY id DESC")
            for row in cursor.fetchall():
                item = QListWidgetItem(f"[{row[0]}] {row[1][:60]}...")
                item.setData(Qt.ItemDataRole.UserRole, row[0]) # Store the DB ID invisibly
                item.setData(Qt.ItemDataRole.UserRole + 1, row[1]) # Store the full text
                self.memory_list.addItem(item)
            conn.close()
        except Exception as e:
            self.set_status(f"CRITICAL: Failed to load memories -> {e}", "#ff003c")

    def load_selected_memory(self, item):
        full_text = item.data(Qt.ItemDataRole.UserRole + 1)
        self.text_input.setPlainText(full_text)
        self.set_status(f"Loaded memory ID: {item.data(Qt.ItemDataRole.UserRole)} for editing.", "#00d4ff")

    def add_memory(self):
        text = self.text_input.toPlainText().strip()
        if not text: return
        
        self.set_status("Synthesizing neural vector...", "#00d4ff")
        QApplication.processEvents() # Keep UI responsive
        
        vector_str = self._generate_vector(text)
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO long_term_memory (fact, vector) VALUES (?, ?)", (text, vector_str))
            conn.commit()
            conn.close()
            
            self.set_status("SUCCESS: Memory permanently archived.", "#00ff00")
            self.text_input.clear()
            self.refresh_list()
        except Exception as e:
            self.set_status(f"CRITICAL: Database write failure -> {e}", "#ff003c")

    def update_memory(self):
        selected_items = self.memory_list.selectedItems()
        if not selected_items: return
        
        db_id = selected_items[0].data(Qt.ItemDataRole.UserRole)
        new_text = self.text_input.toPlainText().strip()
        if not new_text: return
        
        self.set_status("Recalculating neural vector...", "#00d4ff")
        QApplication.processEvents()
        
        vector_str = self._generate_vector(new_text)
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("UPDATE long_term_memory SET fact = ?, vector = ? WHERE id = ?", (new_text, vector_str, db_id))
            conn.commit()
            conn.close()
            
            self.set_status(f"SUCCESS: Memory ID {db_id} updated.", "#00ff00")
            self.text_input.clear()
            self.refresh_list()
        except Exception as e:
            self.set_status(f"CRITICAL: Update failed -> {e}", "#ff003c")

    def delete_memory(self):
        selected_items = self.memory_list.selectedItems()
        if not selected_items: return
        
        db_id = selected_items[0].data(Qt.ItemDataRole.UserRole)
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM long_term_memory WHERE id = ?", (db_id,))
            conn.commit()
            conn.close()
            
            self.set_status(f"SUCCESS: Memory ID {db_id} purged from system.", "#00ff00")
            self.text_input.clear()
            self.refresh_list()
        except Exception as e:
            self.set_status(f"CRITICAL: Deletion failed -> {e}", "#ff003c")

    def set_status(self, text, color):
        self.status_label.setText(f"SYSTEM: {text}")
        self.status_label.setStyleSheet(f"color: {color}; font-family: 'Consolas', monospace; font-size: 12px;")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MemoryManagerConsole()
    window.show()
    sys.exit(app.exec())