"""
core/antigravity_bridge.py
==========================
Bridge interface connecting J.A.R.V.I.S. 2.0 with the Google Antigravity Agent Platform.
Provides asynchronous, guarded delegation for multi-step engineering, file automation,
and deep research workflows.
"""

import os
import sys
import asyncio
import re
import logging
from typing import Dict, Any, Optional, Callable
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("JarvisAntigravityBridge")

try:
    import google.antigravity as agy
    from google.antigravity import (
        Agent,
        LocalAgentConfig,
        CapabilitiesConfig,
        BuiltinTools,
        ToolOutputTruncationConfig,
        types
    )
    ANTIGRAVITY_AVAILABLE = True
except ImportError:
    ANTIGRAVITY_AVAILABLE = False
    logger.warning("[Antigravity Bridge] google-antigravity SDK not found. Delegation running in fallback mode.")


class AntigravityBridge:
    def __init__(self, model_name: str = "gemini-3.5-flash-lite", timeout_seconds: int = 120):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.is_enabled = ANTIGRAVITY_AVAILABLE and bool(self.api_key)

    def is_available(self) -> bool:
        """Returns True if the Antigravity SDK is loaded and API key is present."""
        return self.is_enabled

    async def execute_task_async(
        self,
        task: str,
        task_type: str = "general",
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Executes an agentic task via Google Antigravity SDK asynchronously.
        Enforces timeout guards, tool output truncation, and exception containment.
        """
        if not self.is_available():
            return {
                "success": False,
                "summary": "Google Antigravity engine is currently offline or unconfigured.",
                "output": "",
                "error": "SDK missing or GEMINI_API_KEY unset."
            }

        logger.info(f"[Antigravity Bridge] Spawning agent for [{task_type.upper()}]: {task[:80]}...")

                        # Fast OS Action Intercept: WhatsApp Messaging
        # WhatsApp Messaging Intercept
        wa_pattern = (
            r'''(?:open\s+whatsapp.*?locate\s+(?P<contact1>[\w\s]+?)\s+in\s+chats.*?type\s+['\"](?P<msg1>[^'\"]+?)['\"].*?send)|'''
            r'''(?:(?:open\s+whatsapp\s+and\s+)?(?:send|message|text)\s+['\"]?(?P<msg2>[^'\"]+?)['\"]?\s+to\s+(?P<contact2>[\w\s]+?)(?:\s+(?:on\s+whatsapp|please|in\s+whatsapp))?$)'''
        )
        wa_match = re.search(wa_pattern, task, re.IGNORECASE)
        if wa_match:
            contact = (wa_match.group("contact1") or wa_match.group("contact2") or "").strip().title()
            msg = (wa_match.group("msg1") or wa_match.group("msg2") or "").strip()
            if contact and msg:
                from utils.automation import JarvisAutomation
                auto = JarvisAutomation()
                success, detail = auto.send_whatsapp_message(contact, msg)
                if progress_callback:
                    progress_callback(f"[ANTIGRAVITY]: {detail.upper()}")
                return {
                    "success": success,
                    "summary": detail,
                    "output": detail,
                    "error": None if success else detail
                }

        # Fast OS Action Intercept: If task is opening a directory or file in Explorer
        folder_match = re.search(r"(?:open|launch|explore|show)\s+(?:the\s+)?(?:folder\s+|directory\s+)?([a-zA-Z]:[\\/][^\s]+|jarvis\s*2\.?0?|project)", task, re.IGNORECASE)
        if folder_match:
            raw_path = folder_match.group(1).strip().rstrip(".,;:'\"")
            from utils.automation import JarvisAutomation
            auto = JarvisAutomation()
            resolved = auto._resolve_path(raw_path)
            target_folder = resolved if resolved else os.path.abspath(r"C:\PROJECTS\Jarvis2.0")
            try:
                os.startfile(target_folder)
                if progress_callback:
                    progress_callback(f"[ANTIGRAVITY]: DIRECTORY LAUNCHED IN WINDOWS EXPLORER: {target_folder}")
                return {
                    "success": True,
                    "summary": f"Opened directory in Windows Explorer: {target_folder}",
                    "output": f"Directory opened: {target_folder}",
                    "error": None
                }
            except Exception as e:
                logger.error(f"[Antigravity Bridge] Failed to launch folder: {e}")

        if progress_callback:
            progress_callback(f"[ANTIGRAVITY]: SPAWNING COGNITIVE AGENT ({task_type.upper()})...")

        # Determine tools based on task category
        enabled_tools = [
            BuiltinTools.LIST_DIR,
            BuiltinTools.VIEW_FILE,
            BuiltinTools.SEARCH_DIR,
            BuiltinTools.FIND_FILE,
        ]

        if task_type in ["coding", "debugging", "file_operation"]:
            enabled_tools.extend([
                BuiltinTools.CREATE_FILE,
                BuiltinTools.EDIT_FILE,
                BuiltinTools.RUN_COMMAND
            ])

        system_instruction = (
            "You are the Google Antigravity Autonomous Subsystem operating on behalf of J.A.R.V.I.S. "
            "Execute the delegated task systematically and concisely. "
            "For directory inspection or listing files in known folders (such as assets, core, gui, apps), "
            "ALWAYS use list_dir directly on that relative directory path. "
            "Do NOT run slow whole-workspace searches or use find_file unless the directory location is completely unknown. "
            "NEVER search or traverse inside venv, build, dist, or .git directories. "
            "Inspect relevant files, produce concise, high-quality results, and return a clear summary of your findings or modifications. "
            "Do not dump massive raw JSON files; summarize the structure and key fields. "
            "CRITICAL TOOL INSTRUCTION: When calling write_file or create_file on project files, NEVER provide ArtifactMetadata. "
            "ArtifactMetadata is only valid for artifacts in the brain directory."
        )

        config = LocalAgentConfig(
            api_key=self.api_key,
            model=self.model_name,
            system_instructions=system_instruction,
            capabilities=CapabilitiesConfig(
                enabled_tools=enabled_tools,
                enable_subagents=True,
                agent_behavior=types.AgentBehavior.AUTONOMOUS
            )
        )

        try:
            async def _run_agent():
                async with Agent(config) as agent:
                    response = await agent.chat(task)
                    
                    # Track tool execution for telemetry HUD
                    async for tool in response.tool_calls:
                        tool_log = f"[ANTIGRAVITY]: Executing {tool.name}..."
                        logger.info(tool_log)
                        if progress_callback:
                            progress_callback(tool_log)

                    return (await response.text()).strip()

            result_text = await asyncio.wait_for(_run_agent(), timeout=self.timeout_seconds)
            
            # Extract first 2-3 sentences for spoken briefing
            summary_sentences = [s.strip() for s in result_text.split(".") if s.strip()]
            spoken_summary = ". ".join(summary_sentences[:2]) + "." if summary_sentences else result_text[:120]

            if progress_callback:
                progress_callback("[ANTIGRAVITY]: TASK EXECUTION COMPLETE.")

            return {
                "success": True,
                "summary": spoken_summary,
                "output": result_text,
                "error": None
            }

        except asyncio.TimeoutError:
            err_msg = f"Task timed out after {self.timeout_seconds} seconds."
            logger.error(f"[Antigravity Bridge] {err_msg}")
            if progress_callback:
                progress_callback(f"[ANTIGRAVITY TIMEOUT]: Operation exceeded {self.timeout_seconds}s limit.")
            return {
                "success": False,
                "summary": "Sir, the delegated Antigravity operation timed out.",
                "output": "",
                "error": err_msg
            }
        except Exception as e:
            err_msg = str(e)
            logger.error(f"[Antigravity Bridge] Execution fault: {err_msg}")
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                spoken = "Sir, the Antigravity agent reached its cloud API quota limit."
            else:
                spoken = "Sir, an anomaly occurred during agentic execution."
            if progress_callback:
                progress_callback(f"[ANTIGRAVITY FAULT]: {err_msg[:60]}")
            return {
                "success": False,
                "summary": spoken,
                "output": "",
                "error": err_msg
            }

    async def execute_tasks_parallel_async(
        self,
        tasks: list,
        task_type: str = "general",
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Executes multiple agentic tasks concurrently using parallel Google Antigravity agents.
        Reduces multi-agent turnaround time dramatically via asyncio.gather.
        """
        if not self.is_available():
            return {
                "success": False,
                "summary": "Google Antigravity engine is currently offline or unconfigured.",
                "output": "",
                "error": "SDK missing or GEMINI_API_KEY unset."
            }

        logger.info(f"[Antigravity Bridge] Spawning {len(tasks)} parallel agents for [{task_type.upper()}]...")
        if progress_callback:
            progress_callback(f"[ANTIGRAVITY]: SPAWNING {len(tasks)} PARALLEL COGNITIVE AGENTS ({task_type.upper()})...")

        async def _run_single(task_item, idx: int):
            t_str = task_item.get("task", str(task_item)) if isinstance(task_item, dict) else str(task_item)
            t_type = task_item.get("task_type", task_type) if isinstance(task_item, dict) else task_type
            cb = (lambda msg: progress_callback(f"[Agent {idx+1}]: {msg}")) if progress_callback else None
            return await self.execute_task_async(t_str, t_type, progress_callback=cb)

        results = await asyncio.gather(*[_run_single(t, i) for i, t in enumerate(tasks)], return_exceptions=True)

        combined_outputs = []
        combined_summaries = []
        all_success = True

        for i, r in enumerate(results):
            if isinstance(r, Exception):
                all_success = False
                combined_outputs.append(f"Agent {i+1} failed: {str(r)}")
            elif isinstance(r, dict):
                if not r.get("success"):
                    all_success = False
                combined_outputs.append(f"--- Agent {i+1} Output ---\n{r.get('output', '')}")
                if r.get("summary"):
                    combined_summaries.append(r.get("summary"))

        total_summary = " ".join(combined_summaries[:2]) if combined_summaries else "Parallel agent operations completed."
        return {
            "success": all_success,
            "summary": total_summary,
            "output": "\n\n".join(combined_outputs),
            "results": results,
            "error": None if all_success else "One or more parallel agent tasks failed."
        }

    def execute_tasks_parallel(
        self,
        tasks: list,
        task_type: str = "general",
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """Synchronous wrapper for executing multiple agent tasks concurrently in parallel."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            res = loop.run_until_complete(self.execute_tasks_parallel_async(tasks, task_type, progress_callback))
            loop.close()
            return res
        except Exception as e:
            logger.error(f"[Antigravity Parallel Sync] Error: {e}")
            return {
                "success": False,
                "summary": f"Parallel bridge error: {str(e)}",
                "output": "",
                "error": str(e)
            }

    def execute_task(
        self,
        task: str,
        task_type: str = "general",
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """Synchronous wrapper for thread-safe invocation from JarvisWorker."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            res = loop.run_until_complete(self.execute_task_async(task, task_type, progress_callback))
            loop.close()
            return res
        except Exception as e:
            logger.error(f"[Antigravity Bridge Sync] Error: {e}")
            return {
                "success": False,
                "summary": f"Bridge error: {str(e)}",
                "output": "",
                "error": str(e)
            }
