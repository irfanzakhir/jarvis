"""
core/tools/base_tool.py - Modular Base Tool Class for Jarvis 2.0
Inspired by Friday Mark 2's BaseTool & auto-schema generation.

Every tool in Jarvis subclasses BaseTool, providing clean self-documenting schemas
and unified execution semantics.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseTool(ABC):
    """
    Abstract base class for all Jarvis tools.
    """
    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = {}

    def to_schema(self) -> Dict[str, Any]:
        """Auto-generates the OpenAI / Gemini function-calling JSON schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters or {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }

    @abstractmethod
    def run(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool with supplied arguments."""
        pass
