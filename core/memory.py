import os
import json
import sqlite3
import requests
import threading
import math
from dotenv import load_dotenv

load_dotenv()

class JarvisMemory:
    def __init__(self):
        self.db_path = "assets/jarvis_memory.db"
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.lock = threading.Lock()
        
        # Initialize the native SQLite database seamlessly
        if not os.path.exists("assets"):
            os.makedirs("assets")
        self._init_db()

    def _init_db(self):
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS long_term_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fact TEXT NOT NULL,
                    vector TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            conn.close()

    def _get_embedding(self, text):
        """Fetches a high-dimensional vector representation from the cloud with zero local CPU load."""
        if not self.api_key:
            return None
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={self.api_key}"
            payload = {
                "model": "models/text-embedding-004",
                "content": {"parts": [{"text": text}]}
            }
            response = requests.post(url, json=payload, timeout=4)
            if response.status_code == 200:
                return response.json()["embedding"]["values"]
        except Exception as e:
            print(f"[Memory Engine Error]: Failed to fetch embedding: {e}")
        return None

    def _cosine_similarity(self, vec1, vec2):
        """Calculates mathematical conceptual closeness instantly in RAM."""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm_a = math.sqrt(sum(a * a for a in vec1))
        norm_b = math.sqrt(sum(b * b for b in vec2))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    def save_fact_async(self, fact):
        """Spawns a non-blocking thread to prevent local latency overhead."""
        if not fact or not fact.strip():
            return
        threading.Thread(target=self._save_fact_worker, args=(fact,), daemon=True).start()

    def _save_fact_worker(self, fact):
        vector = self._get_embedding(fact)
        if not vector:
            return
            
        print(f"[Memory Engine]: Context vectorized and safely stored in SQLite.")
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO long_term_memory (fact, vector) VALUES (?, ?)",
                (fact, json.dumps(vector))
            )
            conn.commit()
            conn.close()

    def query_relevant_context(self, user_query, limit=2):
        """Queries historical semantic associations based on conceptual relevance."""
        query_vector = self._get_embedding(user_query)
        if not query_vector:
            return ""

        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT fact, vector FROM long_term_memory")
            rows = cursor.fetchall()
            conn.close()

        scored_memories = []
        for fact, vector_str in rows:
            try:
                vector = json.loads(vector_str)
                score = self._cosine_similarity(query_vector, vector)
                if score > 0.65:  # Only pull memories that cross a 65% structural conceptual match
                    scored_memories.append((score, fact))
            except:
                continue

        # Sort by best conceptual similarity match
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        top_memories = [mem[1] for mem in scored_memories[:limit]]
        
        if top_memories:
            print(f"[Memory Engine]: Successfully retrieved {len(top_memories)} semantic context blocks.")
            return "\nRELEVANT PAST CONTEXT:\n" + "\n".join(f"- {m}" for m in top_memories)
        return ""