"""
core/tools/registry.py - Dynamic Tool Registry for Jarvis 2.0
Inspired by Friday Mark 2's ToolRegistry auto-discovery.

Holds registered BaseTool instances, generates complete schemas for LLM cognitive providers,
and provides unified execution dispatching.
"""

import logging
from typing import Dict, List, Any, Optional
from core.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Central registry for all Jarvis tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        """Registers a BaseTool instance."""
        if not tool.name:
            raise ValueError(f"Tool {tool} has no name specified.")
        self._tools[tool.name] = tool
        logger.debug(f"[ToolRegistry]: Registered tool '{tool.name}'")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Returns the list of all function schemas for LLM tools array."""
        return [tool.to_schema() for tool in self._tools.values()]

    def execute(self, name: str, **kwargs) -> Dict[str, Any]:
        """Dispatches execution to the registered tool."""
        tool = self.get_tool(name)
        if not tool:
            return {"error": f"Tool '{name}' not found in registry."}
        try:
            return tool.run(**kwargs)
        except Exception as e:
            logger.error(f"[ToolRegistry Error]: Tool '{name}' failed: {e}")
            return {"error": str(e)}
