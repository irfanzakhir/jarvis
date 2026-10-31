"""
core/json_healer.py - Battle-Hardened JSON & Markdown Healer for Jarvis 2.0
Inspired by Friday Mark 2's session_repair.py and OpenClaw transcript repair.

Guarantees 100% crash-free JSON parsing from cloud and local LLMs (Gemini, Groq, Ollama),
handles unquoted keys, single quotes, trailing commas, markdown blocks, and strips private
<thought> scratchpad reasoning blocks.
"""

import json
import re
import logging
from typing import Any, Optional, Dict, Tuple

logger = logging.getLogger(__name__)

# Strip <thought>...</thought> reasoning blocks from LLM responses
_THOUGHT_RE = re.compile(r'<thought>.*?</thought>\s*', re.DOTALL | re.IGNORECASE)

# Markdown JSON block matching
_MARKDOWN_JSON_RE = re.compile(r'```(?:json)?\s*\n?(.*?)\n?\s*```', re.DOTALL | re.IGNORECASE)

# Strict identifier preservation regex (UUIDs, SHA hashes, Windows/Unix paths, URLs, IPv4)
IDENTIFIER_PATTERN = re.compile(
    r'(?:'
    r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'  # UUID
    r'|[0-9a-fA-F]{40}'   # SHA-1
    r'|[0-9a-fA-F]{64}'   # SHA-256
    r'|\b\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?\b'  # IPv4 with optional port
    r'|https?://[^\s<>"\'\)]+'  # URLs
    r'|[A-Z]:\\[\w.\\/\-\s]+'  # Windows absolute paths
    r'|/[a-zA-Z0-9_\.\-]+(?:/[a-zA-Z0-9_\.\-]+)+'  # Unix absolute paths
    r')',
    re.MULTILINE
)


def strip_thought_block(text: str) -> str:
    """Strips <thought>...</thought> reasoning scratchpad before returning text to user or TTS."""
    if not text or not isinstance(text, str):
        return ""
    return _THOUGHT_RE.sub('', text).strip()


def extract_thought_block(text: str) -> Optional[str]:
    """Extracts internal <thought> reasoning for logging, auditing, or reflection."""
    if not text or not isinstance(text, str):
        return None
    match = _THOUGHT_RE.search(text)
    if match:
        content = match.group(0)
        # Strip the opening and closing tags
        cleaned = re.sub(r'</?thought>', '', content, flags=re.IGNORECASE).strip()
        return cleaned
    return None


def repair_json_string(raw_str: str) -> str:
    """
    Applies deterministic heuristics to fix malformed JSON strings:
      - Strips markdown code blocks
      - Fixes unquoted keys: {action: "open"} -> {"action": "open"}
      - Fixes single-quoted keys and values: {'key': 'val'} -> {"key": "val"}
      - Fixes trailing commas: {"a": 1,} -> {"a": 1}
    """
    if not raw_str or not isinstance(raw_str, str):
        return "{}"

    text = raw_str.strip()

    # 1. Extract content from markdown code block if present
    md_match = _MARKDOWN_JSON_RE.search(text)
    if md_match:
        text = md_match.group(1).strip()

    # 2. If text contains surrounding prose, extract the outer JSON structure
    start_brace = text.find('{')
    end_brace = text.rfind('}')
    if start_brace != -1 and end_brace != -1 and end_brace > start_brace:
        text = text[start_brace:end_brace + 1]
    else:
        start_bracket = text.find('[')
        end_bracket = text.rfind(']')
        if start_bracket != -1 and end_bracket != -1 and end_bracket > start_bracket:
            text = text[start_bracket:end_bracket + 1]

    # 3. Fix unquoted object keys: {key: -> {"key":
    # Looks for a word followed by ':' preceded by '{' or ','
    text = re.sub(r'([\{\,]\s*)([a-zA-Z0-9_]+)\s*:', r'\1"\2":', text)

    # 4. Convert single-quoted keys to double quotes: {'key': -> {"key":
    text = re.sub(r"([\{\,]\s*)'([^'\\]*(?:\\.[^'\\]*)*)'\s*:", r'\1"\2":', text)

    # 5. Convert single-quoted string values to double quotes: : 'value' -> : "value"
    # Handles escaped quotes safely
    def _fix_single_quoted_val(m):
        prefix = m.group(1)
        inner = m.group(2)
        inner_escaped = inner.replace('"', '\\"')
        return f'{prefix}"{inner_escaped}"'

    text = re.sub(r'(:\s*)\'([^\'\\]*(?:\\.[^\'\\]*)*)\'', _fix_single_quoted_val, text)

    # 6. Remove trailing commas before closing braces/brackets
    text = re.sub(r',\s*(\}|\])', r'\1', text)

    # 7. Convert Python booleans and None to JSON equivalents
    text = re.sub(r'\bTrue\b', 'true', text)
    text = re.sub(r'\bFalse\b', 'false', text)
    text = re.sub(r'\bNone\b', 'null', text)

    return text


def safe_json_loads(raw: Any, default: Any = None) -> Any:
    """
    Ultra-resilient JSON parser.
    Attempts standard json.loads(), and if it fails, invokes repair_json_string.
    Returns `default` (or empty dict) if unrecoverable, guaranteed never to crash.
    """
    if default is None:
        default = {}

    if raw is None:
        return default

    if isinstance(raw, (dict, list)):
        return raw

    if not isinstance(raw, str):
        try:
            return json.loads(str(raw))
        except Exception:
            return default

    # 1. Fast path: native parsing
    try:
        return json.loads(raw)
    except Exception:
        pass

    # 2. Heuristic repair path
    try:
        repaired = repair_json_string(raw)
        return json.loads(repaired)
    except Exception as e:
        logger.debug(f"[JSON Healer]: Could not parse raw string after repair: {e}")
        return default
