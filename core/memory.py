import os
import json
import sqlite3
import requests
import threading
import math
from dotenv import load_dotenv
import datetime
from core.json_healer import IDENTIFIER_PATTERN

load_dotenv()

class JarvisMemory:
    def __init__(self):
        self.db_path = "assets/jarvis_memory.db"
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.lock = threading.Lock()
        self._session = requests.Session()
        
        # Initialize the native SQLite database seamlessly
        if not os.path.exists("assets"):
            os.makedirs("assets")
        self._init_db()

    def _init_db(self):
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 1. SEMANTIC MEMORY (The Hippocampus - Vector DB with Layer Stratification)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS long_term_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fact TEXT NOT NULL,
                    vector TEXT NOT NULL,
                    source TEXT DEFAULT 'stated',
                    confidence REAL DEFAULT 1.0,
                    evidence_count INTEGER DEFAULT 1,
                    last_confirmed DATETIME DEFAULT CURRENT_TIMESTAMP,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Migration guard: Add columns if table already existed without them
            cursor.execute("PRAGMA table_info(long_term_memory)")
            existing_cols = {col[1] for col in cursor.fetchall()}
            if "source" not in existing_cols:
                cursor.execute("ALTER TABLE long_term_memory ADD COLUMN source TEXT DEFAULT 'stated'")
            if "confidence" not in existing_cols:
                cursor.execute("ALTER TABLE long_term_memory ADD COLUMN confidence REAL DEFAULT 1.0")
            if "evidence_count" not in existing_cols:
                cursor.execute("ALTER TABLE long_term_memory ADD COLUMN evidence_count INTEGER DEFAULT 1")
            if "last_confirmed" not in existing_cols:
                cursor.execute("ALTER TABLE long_term_memory ADD COLUMN last_confirmed DATETIME")
            
            # 2. TEMPORAL HABIT VAULT (The Circadian Rhythm - Deterministic SQL)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_baselines (
                    habit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    habit_name TEXT UNIQUE,
                    trigger_time TEXT,
                    context_payload TEXT,
                    is_active INTEGER DEFAULT 1
                )
            ''')
            
            conn.commit()
            conn.close()

    # ==============================================================
    # PHASE 2: TEMPORAL HABIT VAULT METHODS (Deterministic)
    # ==============================================================
    def add_temporal_habit(self, habit_name, trigger_time, context_payload):
        """Saves a hardcoded schedule to the Habit Vault."""
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO user_baselines (habit_name, trigger_time, context_payload, is_active)
                    VALUES (?, ?, ?, 1)
                ''', (habit_name, trigger_time, context_payload))
                conn.commit()
                conn.close()
            print(f"[Habit Vault]: Successfully locked temporal anchor '{habit_name}' for {trigger_time}.")
            return True
        except Exception as e:
            print(f"[Habit Vault Error]: Failed saving habit: {e}")
            return False

    def get_habits_for_current_time(self, current_time_str):
        """Retrieves any habits scheduled for the exact current minute (e.g. '08:30')."""
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT habit_name, context_payload FROM user_baselines 
                    WHERE trigger_time = ? AND is_active = 1
                ''', (current_time_str,))
                results = cursor.fetchall()
                conn.close()
            return results
        except Exception as e:
            print(f"[Habit Vault Error]: Failed fetching habits: {e}")
            return []

    # ==============================================================
    # EXISTING VECTOR MEMORY METHODS (Semantic)
    # ==============================================================
    def _get_embedding(self, text):
        """Fetches a high-dimensional vector representation from the cloud with zero local CPU load."""
        if not self.api_key:
            print("[Memory Engine Error]: GEMINI_API_KEY is missing from your .env file!")
            return None
            
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key={self.api_key}"
            payload = {
                "model": "models/gemini-embedding-001",
                "content": {"parts": [{"text": text}]}
            }
            response = self._session.post(url, json=payload, timeout=8) 
            
            if response.status_code == 200:
                return response.json()["embedding"]["values"]
            else:
                print(f"[Memory Engine Error]: Google API rejected the request. Status {response.status_code}: {response.text}")
                
        except Exception as e:
            print(f"[Memory Engine Error]: Failed to connect to Google servers: {e}")
            
        return None

    def _cosine_similarity(self, vec1, vec2):
        """Calculates mathematical conceptual closeness instantly in RAM."""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm_a = math.sqrt(sum(a * a for a in vec1))
        norm_b = math.sqrt(sum(b * b for b in vec2))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    def get_core_profile(self):
        """Tiered Core Profile compiler that reads directly from your SQLite memory tables."""
        print("[System] Compiling Cognitive Profile from SQLite Database...")
        try:
            # 1. Open a safe, thread-locked connection to your local DB
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Fetch recent high-confidence facts
                cursor.execute("""
                    SELECT fact FROM long_term_memory 
                    WHERE confidence >= 0.4
                    ORDER BY rowid DESC LIMIT 5
                """)
                rows = cursor.fetchall()
                conn.close()
            
            if not rows:
                print("[Memory Warning]: long_term_memory table is empty. Injecting baseline profile.")
                return self._get_baseline_profile()
                
            # 2. Extract and format the facts into Markdown strings
            profile_string = "CURRENT USER CONTEXT CACHE:\n"
            for row in rows:
                profile_string += f"- {row[0]}\n"
                
            print("[System] Cognitive Profile Compiled successfully via SQLite.")
            return profile_string
            
        except Exception as e:
            print(f"[Memory Error] SQLite compilation failed: {e}. Defaulting to hardcoded baseline.")
            return self._get_baseline_profile()

    def _get_baseline_profile(self):
        """Hardcoded fallback baseline if the SQLite table isn't populated yet."""
        return """CURRENT USER CONTEXT CACHE:
        - User is a Computer Science undergraduate student graduating in 2028.
        - Primary Tech Stack: Java, SQL, Android Studio, Python (Automation/AI).
        - Core Interests: AI-driven media creation, system architecture, competitive programming.
        - Operating Environment: Native Windows, Brave Browser (CDP Port 9222).
        - Location context: Kerala, India.
        """
    
    def save_fact_async(self, fact, source: str = "stated", confidence: float = 1.0):
        """Spawns a non-blocking thread to prevent local latency overhead."""
        if not fact or not fact.strip():
            return
        threading.Thread(target=self._save_fact_worker, args=(fact, source, confidence), daemon=True).start()

    def _save_fact_worker(self, fact: str, source: str = "stated", confidence: float = 1.0):
        vector = self._get_embedding(fact)
        if not vector:
            return
            
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                # Deduplication & Reinforcement check: if fact text matches, reinforce it
                cursor.execute("SELECT id, confidence, evidence_count FROM long_term_memory WHERE fact = ?", (fact,))
                existing = cursor.fetchone()
                if existing:
                    row_id, old_conf, count = existing
                    new_conf = min(1.0, old_conf + 0.1)
                    cursor.execute('''
                        UPDATE long_term_memory 
                        SET confidence = ?, evidence_count = ?, last_confirmed = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (new_conf, count + 1, row_id))
                    print(f"[Memory Engine]: Reinforced existing fact ID {row_id} (count={count+1}, conf={new_conf:.2f}).")
                else:
                    cursor.execute('''
                        INSERT INTO long_term_memory (fact, vector, source, confidence, evidence_count, last_confirmed)
                        VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                    ''', (fact, json.dumps(vector), source, confidence))
                    print(f"[Memory Engine]: New context vectorized and stored ({source}, conf={confidence:.2f}).")
                conn.commit()
            finally:
                conn.close()

    def query_relevant_context(self, user_query, limit=2):
        """Queries historical semantic associations based on conceptual relevance, filtering decayed entries."""
        if not user_query or not isinstance(user_query, str):
            return ""

        # Fast query intent check: action verbs & simple operational commands do not require cloud semantic search
        q = user_query.strip().lower()
        personal_keywords = (
            "who", "what", "where", "why", "when", "how", "my", "favourite", "favorite",
            "mom", "ammi", "mother", "father", "friend", "name", "email", "home",
            "town", "live", "address", "remember", "allergic", "preference", "like", "profile"
        )
        if not any(k in q for k in personal_keywords):
            return ""

        query_vector = self._get_embedding(user_query)
        if not query_vector:
            return ""

        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # Only pull facts whose confidence is >= 0.4 (temporal decay threshold)
            cursor.execute("SELECT fact, vector, confidence FROM long_term_memory WHERE confidence >= 0.4")
            rows = cursor.fetchall()
            conn.close()

        scored_memories = []
        for fact, vector_str, conf in rows:
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

    # ==============================================================
    # PHASE 3: TEMPORAL CONFIDENCE DECAY & CONTEXT COMPACTION
    # ==============================================================
    def run_temporal_decay(self, half_life_days: float = 45.0, min_display_confidence: float = 0.4) -> tuple:
        """
        Applies exponential confidence decay to inferred semantic facts (Friday Mark 2 design).
        Immune: source='stated' (explicit user statements) OR evidence_count >= 5.
        Decay formula: new_conf = max(0.1, conf * exp(-ln(2) / half_life * delta_days))
        Returns: (decayed_count, hidden_count)
        """
        now = datetime.datetime.now()
        decayed = 0
        hidden = 0

        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, confidence, last_confirmed 
                    FROM long_term_memory 
                    WHERE source != 'stated' AND evidence_count < 5
                """)
                rows = cursor.fetchall()

                lambda_rate = math.log(2) / half_life_days

                for row_id, conf, last_conf_str in rows:
                    try:
                        # Parse last confirmed timestamp
                        last_dt = datetime.datetime.fromisoformat(last_conf_str) if last_conf_str else now
                        delta_days = max(0.0, (now - last_dt).total_seconds() / 86400.0)
                        
                        if delta_days < 1.0:
                            continue  # Less than a day old, skip decay calculation

                        new_conf = max(0.1, conf * math.exp(-lambda_rate * delta_days))
                        if abs(new_conf - conf) > 0.01:
                            cursor.execute("UPDATE long_term_memory SET confidence = ? WHERE id = ?", (new_conf, row_id))
                            decayed += 1
                            if new_conf < min_display_confidence and conf >= min_display_confidence:
                                hidden += 1
                    except Exception:
                        continue

                conn.commit()
                conn.close()

            if decayed > 0:
                print(f"[Memory Engine]: Temporal decay applied to {decayed} inferred facts ({hidden} dropped below display threshold).")
        except Exception as e:
            print(f"[Memory Engine Warning]: Temporal decay cycle failed: {e}")

        return (decayed, hidden)

    def compact_conversation_history(self, history: list, max_messages: int = 14) -> list:
        """
        Token-aware history compaction preserving critical Windows/Unix paths, URLs, and UUIDs.
        Keeps system prompt [0] intact, summarizes middle turns, and preserves recent turns verbatim.
        """
        if len(history) <= max_messages:
            return history

        system_msg = history[0]
        # Keep the last 6 messages verbatim for immediate dialogue continuity
        recent_messages = history[-6:]
        middle_messages = history[1:-6]

        # Extract all file paths, UUIDs, URLs from middle messages before summarization
        preserved_identifiers = set()
        for msg in middle_messages:
            content = msg.get("content", "")
            matches = IDENTIFIER_PATTERN.findall(content)
            for m in matches:
                preserved_identifiers.add(m.strip())

        # Build a lean summary block
        summary_lines = ["[SESSION HISTORY COMPACTION SUMMARY]:"]
        if preserved_identifiers:
            summary_lines.append("Preserved File Paths & Active Identifiers:")
            for ident in list(preserved_identifiers)[:10]:
                summary_lines.append(f"  - {ident}")

        # Quick turn extraction for middle messages
        user_queries = [m.get("content", "")[:80] for m in middle_messages if m.get("role") == "user"]
        if user_queries:
            summary_lines.append(f"Prior Topics Discussed: {'; '.join(user_queries[-4:])}")

        summary_block = "\n".join(summary_lines)
        compacted_entry = {"role": "system", "content": summary_block}

        return [system_msg, compacted_entry] + recent_messages
