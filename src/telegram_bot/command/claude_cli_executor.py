"""
Claude CLI Executor for Telegram Bot
Ported from the original Feishu version to work with Claude Code CLI
"""

import subprocess
import logging
import json
import os
from typing import Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    """Result of command execution"""
    token: str
    command: str
    success: bool
    method: str
    output: str = ""
    error: str = ""
    exec_time_ms: int = 0
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class ClaudeCliExecutor:
    """Claude CLI executor for running coding tasks"""

    def __init__(self, session_manager):
        self.session_manager = session_manager
        self._check_claude_cli()

    def _check_claude_cli(self):
        """Check if Claude CLI is available"""
        try:
            result = subprocess.run(
                ['claude', '--version'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"Claude CLI found: {result.stdout.strip()}")
            else:
                logger.warning("Claude CLI not found or not working")
        except Exception as e:
            logger.error(f"Failed to check Claude CLI: {e}")

    async def execute_command_async(self, token: str, command: str, user_id: int) -> CommandResult:
        """Execute command asynchronously via Claude CLI"""
        start_time = datetime.now()

        # Validate session
        session = self.session_manager.validate_session(token, user_id)
        if session is None:
            return CommandResult(
                token=token,
                command=command,
                success=False,
                method="failed",
                error="Session validation failed. Please start a new session with /start_session",
                exec_time_ms=self._calc_exec_time(start_time)
            )

        # Validate command (basic security)
        if not self._validate_command(command):
            return CommandResult(
                token=token,
                command=command,
                success=False,
                method="failed",
                error="Command validation failed (dangerous command blocked)",
                exec_time_ms=self._calc_exec_time(start_time)
            )

        # Get working directory
        working_dir = session.working_dir
        if not working_dir or working_dir == "{{cwd}}":
            working_dir = str(Path.cwd())

        # Execute command via Claude CLI
        result = await self._execute_with_claude_cli_async(command, working_dir)
        result.token = token
        result.command = command
        result.exec_time_ms = self._calc_exec_time(start_time)

        # Update session
        self.session_manager.update_session(token)

        logger.info(f"Command executed via Claude CLI: token={token}, success={result.success}")
        return result

    async def send_message_to_claude(self, user_id: int, message: str) -> CommandResult:
        """Send message directly to Claude CLI"""
        start_time = datetime.now()

        # Get active session for user
        session = self.session_manager.get_user_active_session(user_id)
        if not session:
            return CommandResult(
                token="",
                command=message,
                success=False,
                method="failed",
                error="No active Claude Code session found.\n\nPlease start a new session with /start_session first",
                exec_time_ms=self._calc_exec_time(start_time)
            )

        # Get working directory
        working_dir = session.working_dir
        if not working_dir or working_dir == "{{cwd}}":
            working_dir = str(Path.cwd())

        try:
            # Escape message for shell
            escaped_message = message.replace('"', '\\"')

            # Execute via Claude CLI
            result = subprocess.run(
                f'claude -p "{escaped_message}"',
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=120,
                cwd=working_dir,
                shell=True
            )

            # Update session
            self.session_manager.update_session(session.token)

            if result.returncode == 0:
                output = result.stdout.strip()
                return CommandResult(
                    token=session.token,
                    command=message,
                    success=True,
                    method="claude_cli_auto",
                    output=(
                        f"🤖 **Claude's Response:**\n\n{output}\n\n"
                        f"───────────────────\n"
                        f"🔑 **Session Token:** `{session.token}`\n"
                        f"📂 **Working Directory:** `{session.working_dir}`"
                    ),
                    exec_time_ms=self._calc_exec_time(start_time)
                )
            else:
                error = result.stderr.strip()
                return CommandResult(
                    token=session.token,
                    command=message,
                    success=False,
                    method="failed",
                    error=f"Claude execution failed:\n```\n{error}\n```",
                    exec_time_ms=self._calc_exec_time(start_time)
                )

        except subprocess.TimeoutExpired:
            return CommandResult(
                token=session.token,
                command=message,
                success=False,
                method="failed",
                error="⏱️ Execution timed out (120 seconds)\n\nThe task might be too complex. Please simplify and try again.",
                exec_time_ms=self._calc_exec_time(start_time)
            )
        except Exception as e:
            logger.error(f"Failed to send message via Claude CLI: {e}")
            return CommandResult(
                token=session.token,
                command=message,
                success=False,
                method="failed",
                error=f"Failed to send message: {str(e)}",
                exec_time_ms=self._calc_exec_time(start_time)
            )

    async def _execute_with_claude_cli_async(self, command: str, working_dir: str) -> CommandResult:
        """Execute command using Claude CLI asynchronously"""
        try:
            # Escape command for shell
            escaped_command = command.replace('"', '\\"')

            # Execute command via Claude CLI in a separate thread
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    f'claude -p "{escaped_command}"',
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='ignore',
                    timeout=120,
                    cwd=working_dir,
                    shell=True
                )
            )

            if result.returncode == 0:
                output = result.stdout.strip()
                return CommandResult(
                    token="",
                    command=command,
                    success=True,
                    method="claude_cli",
                    output=output if output else "Command executed successfully"
                )
            else:
                error = result.stderr.strip()
                return CommandResult(
                    token="",
                    command=command,
                    success=False,
                    method="failed",
                    error=f"Claude CLI error: {error}"
                )

        except subprocess.TimeoutExpired:
            return CommandResult(
                token="",
                command=command,
                success=False,
                method="failed",
                error="Command execution timed out (120s limit)"
            )
        except Exception as e:
            logger.error(f"Failed to execute with Claude CLI: {e}")
            return CommandResult(
                token="",
                command=command,
                success=False,
                method="failed",
                error=f"Execution failed: {str(e)}"
            )

    def _validate_command(self, command: str) -> bool:
        """Basic command validation for security"""
        dangerous_patterns = [
            'rm -rf /',
            'sudo rm',
            ':(){ :|:& };:',  # fork bomb
            'dd if=/dev/zero',
            'mkfs',
            'format',
            'del /f /s /q',
            'rmdir /s /q'
        ]

        command_lower = command.lower()
        for pattern in dangerous_patterns:
            if pattern in command_lower:
                logger.warning(f"Dangerous command blocked: {command}")
                return False

        return True

    def _calc_exec_time(self, start_time: datetime) -> int:
        """Calculate execution time in milliseconds"""
        delta = datetime.now() - start_time
        return int(delta.total_seconds() * 1000)


class ClaudeCliDirectExecutor:
    """Direct Claude CLI executor for simple messaging"""

    def __init__(self, session_manager):
        self.session_manager = session_manager

    async def send_coding_task(self, user_id: int, task_description: str) -> CommandResult:
        """Send coding task to Claude CLI"""
        start_time = datetime.now()

        # Get active session for user
        session = self.session_manager.get_user_active_session(user_id)
        if not session:
            return CommandResult(
                token="",
                command=task_description,
                success=False,
                method="failed",
                error=(
                    "❌ **No Active Session Found**\n\n"
                    "Please start a coding session first:\n"
                    "`/start_session`\n\n"
                    "Then send your coding task!"
                ),
                exec_time_ms=self._calc_exec_time(start_time)
            )

        # Get working directory
        working_dir = session.working_dir
        if not working_dir or working_dir == "{{cwd}}":
            working_dir = str(Path.cwd())

        try:
            # Prepare the task for Claude
            formatted_task = (
                f"Please help me with this coding task:\n\n"
                f"Task: {task_description}\n\n"
                f"Please provide:\n"
                f"1. Code solution if applicable\n"
                f"2. Explanation of the approach\n"
                f"3. Any files created or modified\n"
                f"4. Next steps or recommendations"
            )

            # Execute via Claude CLI
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    f'claude -p "{formatted_task.replace(\'"\', \'\\"\')}"',
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='ignore',
                    timeout=180,  # 3 minutes for coding tasks
                    cwd=working_dir,
                    shell=True
                )
            )

            # Update session
            self.session_manager.update_session(session.token)

            if result.returncode == 0:
                output = result.stdout.strip()
                return CommandResult(
                    token=session.token,
                    command=task_description,
                    success=True,
                    method="claude_cli_coding",
                    output=(
                        f"🎯 **Coding Task Completed**\n\n"
                        f"**Task:** {task_description}\n\n"
                        f"🤖 **Claude's Solution:**\n\n{output}\n\n"
                        f"───────────────────\n"
                        f"🔑 **Session:** `{session.token}`\n"
                        f"📂 **Working Directory:** `{session.working_dir}`"
                    ),
                    exec_time_ms=self._calc_exec_time(start_time)
                )
            else:
                error = result.stderr.strip()
                return CommandResult(
                    token=session.token,
                    command=task_description,
                    success=False,
                    method="failed",
                    error=f"❌ **Coding Task Failed:**\n\n```\n{error}\n```",
                    exec_time_ms=self._calc_exec_time(start_time)
                )

        except subprocess.TimeoutExpired:
            return CommandResult(
                token=session.token,
                command=task_description,
                success=False,
                method="failed",
                error=(
                    "⏱️ **Task Timed Out** (3 minutes)\n\n"
                    "The coding task might be too complex. Please:\n"
                    "1. Break it into smaller tasks\n"
                    "2. Provide more specific requirements\n"
                    "3. Try again with a simpler version"
                ),
                exec_time_ms=self._calc_exec_time(start_time)
            )
        except Exception as e:
            logger.error(f"Failed to execute coding task: {e}")
            return CommandResult(
                token=session.token,
                command=task_description,
                success=False,
                method="failed",
                error=f"❌ **Execution Failed:** {str(e)}",
                exec_time_ms=self._calc_exec_time(start_time)
            )

    def _calc_exec_time(self, start_time: datetime) -> int:
        """Calculate execution time in milliseconds"""
        delta = datetime.now() - start_time
        return int(delta.total_seconds() * 1000)