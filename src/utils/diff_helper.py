"""
Diff Helper Utility
Creates unified diffs formatted for Telegram Markdown
"""

import difflib
import logging
from typing import List

logger = logging.getLogger(__name__)


class DiffHelper:
    """Helper class for creating and formatting diffs"""

    @staticmethod
    def create_unified_diff(old_content: str, new_content: str,
                           old_file: str = "old", new_file: str = "new",
                           context_lines: int = 3) -> str:
        """Create a unified diff between two content strings"""
        try:
            old_lines = old_content.splitlines(keepends=True)
            new_lines = new_content.splitlines(keepends=True)

            diff_lines = list(difflib.unified_diff(
                old_lines, new_lines,
                fromfile=old_file, tofile=new_file,
                lineterm='', n=context_lines
            ))

            if not diff_lines:
                return "✅ No changes detected - files are identical"

            formatted_diff = DiffHelper._format_for_telegram(diff_lines)
            return formatted_diff

        except Exception as e:
            logger.error(f"Error creating diff: {e}")
            return f"❌ Error creating diff: {str(e)}"

    @staticmethod
    def _format_for_telegram(diff_lines: List[str]) -> str:
        """Format diff lines for Telegram Markdown"""
        formatted_parts = []

        for line in diff_lines:
            escaped_line = DiffHelper._escape_markdown(line)

            if line.startswith('---') or line.startswith('+++'):
                formatted_parts.append(f"**{escaped_line}**")
            elif line.startswith('@@'):
                formatted_parts.append(f"*{escaped_line}*")
            elif line.startswith('-'):
                formatted_parts.append(f"-{escaped_line[1:]}")
            elif line.startswith('+'):
                formatted_parts.append(f"+{escaped_line[1:]}")
            else:
                formatted_parts.append(f" {escaped_line}")

        diff_content = "\n".join(formatted_parts)
        return f"```diff\n{diff_content}\n```"

    @staticmethod
    def _escape_markdown(text: str) -> str:
        """Escape special markdown characters"""
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '=', '|', '{', '}', '.', '!']
        for char in special_chars:
            if char not in ['-', '+']:
                text = text.replace(char, f'\\{char}')
        return text