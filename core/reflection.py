"""
core/reflection.py - Autonomous Self-Critique & Reflection Engine for Jarvis 2.0
Inspired by Friday Mark 2's ReflectionAgent and Layer 5 Procedural Memory.

Capabilities:
1. Zero-Cost Regex Gate: Intercepts user corrections ("that's wrong", "not what I asked", "wrong directory") in 0ms.
2. Background Asynchronous Diagnosis: Fires a deterministic (temp=0.0) diagnostic call to extract actionable lessons.
3. Procedural Memory Persistence: Stores behavioral patterns in SQLite (assets/jarvis_memory.db).
4. System Prompt Injection: Auto-injects learned behavioral rules into JarvisBrain prompts so mistakes are never repeated.
5. Tool Failure Learning: Captures tool execution faults and extracts preventive behavioral rules.
"""

import os
import re
import json
import sqlite3
import logging
import threading
from typing import List, Dict, Any, Optional
from core.json_healer import safe_json_loads

logger = logging.getLogger(__name__)

# ── Regex Gate: Detects explicit user corrections (0ms evaluation) ────────────
CORRECTION_PATTERNS = re.compile(
    r'\b('
    r"you(?:'re| are) wrong"
    r"|that(?:'s| is) (?:not right|wrong|incorrect|not what i)"
    r"|not what i (?:said|meant|asked|told you|wanted)"
    r"|you (?:got it|used the) wrong"
    r"|wrong (?:path|directory|folder|date|time|format|syntax|tool|approach|app)"
    r"|that(?:'s| is) not (?:how|what|the right|correct)"
    r"|no[,\s]+(?:i (?:said|meant|asked)|that(?:'s| is) not)"
    r"|you(?:'re| are) (?:using|doing) it wrong"
    r"|don(?:'t| not) (?:open|do|use) (?:that|this)"
    r"|that was (?:wrong|incorrect|not right)"
    r')\b',
    re.IGNORECASE,
)

REFLECTION_DIAGNOSTIC_PROMPT = """You are Jarvis's internal self-diagnostic reflection subsystem.
A correction or execution failure just occurred. Analyze what went wrong and extract ONE actionable behavioral lesson to prevent recurrence.

FAILURE CONTEXT:
Type: {failure_type}
Detail: {failure_detail}

RECENT CONVERSATION TURNS:
{conversation_history}

Return ONLY a single valid JSON object, with no markdown fences, no thought tags, and no conversational prose:
{{
  "lesson": "One sentence explaining the mistake",
  "trigger": "When [specific trigger situation - under 10 words]",
  "fix": "Always [specific corrected behavior - under 15 words]",
  "confidence": 0.75
}}

Rules:
- Focus on tool choice, target application, file paths, formatting, or conversational tone.
- Confidence: 0.5 for inferred tool failures, 0.8 for explicit user corrections, 0.9 for repeated corrections.
- If no actionable lesson can be extracted, output: {{"lesson": "", "trigger": "", "fix": "", "confidence": 0}}
"""


class ReflectionEngine:
    """
    Self-critique engine that learns from user corrections and tool execution faults.
    Thread-safe and fully decoupled from the critical response hot-path.
    """

    def __init__(self, db_path: str = "assets/jarvis_memory.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS procedural_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trigger_text TEXT NOT NULL,
                    fix_text TEXT NOT NULL,
                    lesson TEXT,
                    confidence REAL DEFAULT 0.7,
                    source TEXT DEFAULT 'correction',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            conn.close()

    def check_for_correction(self, user_input: str, conversation_history: List[Dict[str, str]], brain_instance=None) -> bool:
        """
        Fast zero-cost gate.
        Returns True if a correction pattern was matched and launches diagnostic learning in the background.
        """
        if not user_input or not isinstance(user_input, str):
            return False

        if CORRECTION_PATTERNS.search(user_input):
            print(f"[Reflection Gate]: Intercepted user correction pattern in <0.1ms: '{user_input[:40]}...'")
            # Launch background diagnosis without blocking response pipeline
            history_snapshot = list(conversation_history) if conversation_history else []
            threading.Thread(
                target=self._diagnose_worker,
                args=("user_correction", user_input, history_snapshot, brain_instance),
                daemon=True
            ).start()
            return True
        return False

    def on_tool_failure(self, tool_name: str, args: dict, error_msg: str, conversation_history: List[Dict[str, str]], brain_instance=None):
        """Called when a tool execution encounters an exception or invalid parameter."""
        detail = f"Tool '{tool_name}' failed with args {args}. Error: {error_msg}"
        print(f"[Reflection System]: Recording tool failure for diagnostic reflection: {detail}")
        history_snapshot = list(conversation_history) if conversation_history else []
        threading.Thread(
            target=self._diagnose_worker,
            args=("tool_failure", detail, history_snapshot, brain_instance),
            daemon=True
        ).start()

    def _diagnose_worker(self, failure_type: str, failure_detail: str, conversation_history: List[Dict[str, str]], brain_instance):
        """Asynchronously queries the LLM at temperature=0.0 to synthesize a procedural rule."""
        try:
            # Format recent messages
            recent_turns = conversation_history[-6:] if conversation_history else []
            history_str = "\n".join(f"{m.get('role', 'user')}: {m.get('content', '')[:150]}" for m in recent_turns)

            prompt = REFLECTION_DIAGNOSTIC_PROMPT.format(
                failure_type=failure_type,
                failure_detail=failure_detail,
                conversation_history=history_str
            )

            response_text = ""
            # Use brain's active client if provided
            if brain_instance and hasattr(brain_instance, "active_providers") and brain_instance.active_providers:
                provider = brain_instance.active_providers[0]
                client = provider["client"]
                model = provider["model"]
                res = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a concise, structured JSON diagnostic agent."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.0
                )
                response_text = res.choices[0].message.content or ""
            else:
                # Direct fallback to GEMINI_API_KEY if brain instance is unavailable
                api_key = os.environ.get("GEMINI_API_KEY")
                if not api_key:
                    return
                from google import genai
                client = genai.Client(api_key=api_key)
                res = client.models.generate_content(
                    model="gemini-3.5-flash-lite",
                    contents=[prompt],
                    config={"temperature": 0.0}
                )
                response_text = res.text or ""

            data = safe_json_loads(response_text)
            trigger = data.get("trigger", "").strip()
            fix = data.get("fix", "").strip()
            confidence = float(data.get("confidence", 0.0))
            lesson = data.get("lesson", "").strip()

            if trigger and fix and confidence >= 0.5:
                self.record_rule(trigger, fix, lesson, confidence, source=failure_type)
                print(f"[Reflection Learned]: {lesson} | Trigger: '{trigger}' -> Fix: '{fix}' (Confidence: {confidence})")
        except Exception as e:
            logger.warning(f"[Reflection Worker Error]: Non-fatal diagnostic failure: {e}")

    def record_rule(self, trigger: str, fix: str, lesson: str = "", confidence: float = 0.75, source: str = "correction"):
        """Saves a learned behavioral pattern to SQLite."""
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                # Deduplication check: if a similar trigger exists, update confidence
                cursor.execute(
                    "SELECT id, confidence FROM procedural_rules WHERE trigger_text = ?",
                    (trigger,)
                )
                row = cursor.fetchone()
                if row:
                    new_conf = min(0.99, row[1] + 0.1)
                    cursor.execute(
                        "UPDATE procedural_rules SET fix_text = ?, confidence = ?, lesson = ? WHERE id = ?",
                        (fix, new_conf, lesson, row[0])
                    )
                else:
                    cursor.execute(
                        "INSERT INTO procedural_rules (trigger_text, fix_text, lesson, confidence, source) VALUES (?, ?, ?, ?, ?)",
                        (trigger, fix, lesson, confidence, source)
                    )
                conn.commit()
                conn.close()
        except Exception as e:
            logger.warning(f"[Reflection DB Error]: Failed to save procedural rule: {e}")

    def get_active_rules_context(self, min_confidence: float = 0.5, limit: int = 4) -> str:
        """
        Retrieves top learned behavioral rules from SQLite.
        Returns a formatted Markdown block ready for system prompt injection.
        """
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT trigger_text, fix_text, confidence FROM procedural_rules
                    WHERE confidence >= ?
                    ORDER BY confidence DESC, id DESC
                    LIMIT ?
                    """,
                    (min_confidence, limit)
                )
                rows = cursor.fetchall()
                conn.close()

            if not rows:
                return ""

            lines = ["[LEARNED PROCEDURAL PATTERNS & BEHAVIORAL LESSONS]:"]
            for trig, fix, conf in rows:
                lines.append(f"- {trig} -> {fix}")
            return "\n".join(lines)
        except Exception as e:
            logger.warning(f"[Reflection Error]: Failed reading procedural rules: {e}")
            return ""
