"""
Repository Commands for Telegram Bot
Handles /loadrepo and /files commands for GitHub repository management
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from src.utils.repo_manager import RepoManager
from src.utils.diff_helper import DiffHelper
from session_manager import SessionManager

logger = logging.getLogger(__name__)


class RepoCommands:
    """Handles repository-related commands for the Telegram bot"""

    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self.repo_manager = RepoManager()
        self.diff_helper = DiffHelper()

    async def handle_loadrepo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /loadrepo command - Load a GitHub repository"""
        user = update.effective_user
        user_id = user.id

        # Check if user has an active session
        session = self.session_manager.get_user_active_session(user_id)
        if not session:
            await update.message.reply_text(
                "❌ **No Active Session**\n\n"
                "Please start a coding session first with `/start_session`",
                parse_mode='Markdown'
            )
            return

        # Check if a URL was provided
        if not context.args:
            await update.message.reply_text(
                "📥 **Load Repository**\n\n"
                "Please provide a GitHub repository URL:\n\n"
                "Usage: `/loadrepo <github_url>`\n\n"
                "Examples:\n"
                "• `/loadrepo https://github.com/owner/repo`\n"
                "• `/loadrepo owner/repo`\n\n"
                "🔧 *Clones the repo to your workspace and makes it "
                "available for file browsing and editing*",
                parse_mode='Markdown'
            )
            return

        github_url = context.args[0]

        # Show typing action
        await update.message.reply_text("🔄 Cloning repository...", parse_mode='Markdown')

        try:
            # Clone or update the repository
            result = await self.repo_manager.clone_or_update_repo(user_id, github_url)

            if result['success']:
                # Update session with active repository
                self.session_manager.set_active_repo(
                    user_id,
                    result['owner'],
                    result['repo'],
                    result['url']
                )

                # Create success message
                success_message = (
                    f"✅ **Repository {result['action']} successfully!**\n\n"
                    f"📁 **Repository:** {result['owner']}/{result['repo']}\n"
                    f"🔗 **URL:** {result['url']}\n"
                    f"📂 **Local Path:** `{result['path']}`\n\n"
                )

                # Add repository info if available
                repo_info = result.get('info', {})
                if repo_info and 'error' not in repo_info:
                    success_message += (
                        f"📊 **Repository Stats:**\n"
                        f"• Files: {repo_info.get('total_files', 'N/A')}\n"
                        f"• Languages: {', '.join(repo_info.get('languages', []))}\n\n"
                    )

                success_message += (
                    "🔍 *Use `/files` to browse the repository structure*\n"
                    "✏️ *Use `/edit <file_path>` to edit files*\n"
                    "📋 *Use `/diff <file_path>` to see changes*"
                )

                # Create inline keyboard for repository actions
                keyboard = [
                    [
                        InlineKeyboardButton("📁 Browse Files", callback_data="browse_files"),
                        InlineKeyboardButton("📊 Repo Info", callback_data="repo_info")
                    ],
                    [
                        InlineKeyboardButton("🔄 Update Repo", callback_data="update_repo"),
                        InlineKeyboardButton("🚫 Close Repo", callback_data="close_repo")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.edit_text(
                    success_message,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )

                logger.info(f"Repository {result['owner']}/{result['repo']} loaded for user {user.full_name}")

            else:
                # Handle different error types
                error_messages = {
                    'invalid_url': "❌ **Invalid URL**\n\nPlease provide a valid GitHub repository URL.",
                    'git_missing': "❌ **Git Not Available**\n\nGit is not installed on this system.",
                    'clone_error': "❌ **Clone Failed**\n\nFailed to clone the repository.",
                    'update_error': "❌ **Update Failed**\n\nFailed to update the repository.",
                    'system_error': "❌ **System Error**\n\nAn unexpected error occurred."
                }

                error_type = result.get('error_type', 'system_error')
                base_message = error_messages.get(error_type, error_messages['system_error'])
                error_details = result.get('error', '')

                await update.message.edit_text(
                    f"{base_message}\n\n**Details:** {error_details}\n\n"
                    f"🔧 *Please check the URL and try again*",
                    parse_mode='Markdown'
                )

        except Exception as e:
            logger.error(f"Error in handle_loadrepo: {e}")
            await update.message.edit_text(
                f"❌ **Unexpected Error**\n\n"
                f"An error occurred while processing your request:\n`{str(e)}`\n\n"
                f"🔧 *Please try again or contact support*",
                parse_mode='Markdown'
            )

    async def handle_files(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /files command - List files in the active repository"""
        user = update.effective_user
        user_id = user.id

        # Check if user has an active session
        session = self.session_manager.get_user_active_session(user_id)
        if not session:
            await update.message.reply_text(
                "❌ **No Active Session**\n\n"
                "Please start a coding session first with `/start_session`",
                parse_mode='Markdown'
            )
            return

        # Check if user has an active repository
        active_repo = self.session_manager.get_active_repo(user_id)
        if not active_repo:
            await update.message.reply_text(
                "❌ **No Repository Loaded**\n\n"
                "Please load a repository first with `/loadrepo <github_url>`\n\n"
                "Example: `/loadrepo https://github.com/owner/repo`",
                parse_mode='Markdown'
            )
            return

        # Get path from context arguments or use root
        relative_path = " ".join(context.args) if context.args else ""

        # Show typing action
        await update.message.reply_text("📁 Scanning files...", parse_mode='Markdown')

        try:
            # List files in the repository
            files = self.repo_manager.list_files_in_repo(user_id, relative_path)

            if files is None:
                await update.message.edit_text(
                    "❌ **Repository Error**\n\n"
                    "Could not access the repository. Please try loading it again.",
                    parse_mode='Markdown'
                )
                return

            if not files:
                if relative_path:
                    await update.message.edit_text(
                        f"📁 **Empty Directory**\n\n"
                        f"The directory `{relative_path}` is empty.\n\n"
                        f"🔍 *Use `/files` to return to the root directory*",
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.edit_text(
                        "📁 **Repository Empty**\n\n"
                        "This repository appears to be empty or contains no visible files.",
                        parse_mode='Markdown'
                    )
                return

            # Format the file list
            file_list_message = self._format_file_list(
                files,
                active_repo['owner'],
                active_repo['repo'],
                relative_path
            )

            await update.message.edit_text(
                file_list_message,
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Error in handle_files: {e}")
            await update.message.edit_text(
                f"❌ **Error Listing Files**\n\n"
                f"Could not list files in `{relative_path}`:\n`{str(e)}`\n\n"
                f"🔧 *Please check the path and try again*",
                parse_mode='Markdown'
            )

    async def handle_repo_callbacks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard callbacks for repository operations"""
        query = update.callback_query
        user_id = update.effective_user.id

        await query.answer()  # Acknowledge the callback

        data = query.data
        session = self.session_manager.get_user_active_session(user_id)

        if not session:
            await query.edit_message_text(
                "❌ **Session Expired**\n\nPlease start a new session with `/start_session`",
                parse_mode='Markdown'
            )
            return

        active_repo = self.session_manager.get_active_repo(user_id)
        if not active_repo and data not in ["browse_files"]:
            await query.edit_message_text(
                "❌ **No Repository Loaded**\n\nPlease load a repository with `/loadrepo`",
                parse_mode='Markdown'
            )
            return

        try:
            if data == "browse_files":
                # Simulate /files command
                context.args = []
                await self.handle_files(update, context)

            elif data == "repo_info":
                # Show detailed repository information
                repo_info = await self._get_detailed_repo_info(user_id)
                await query.edit_message_text(repo_info, parse_mode='Markdown')

            elif data == "update_repo":
                # Update the repository
                await query.edit_message_text("🔄 Updating repository...", parse_mode='Markdown')
                result = await self.repo_manager.clone_or_update_repo(user_id, active_repo['url'])

                if result['success']:
                    await query.edit_message_text(
                        f"✅ **Repository Updated Successfully!**\n\n"
                        f"📁 {result['owner']}/{result['repo']}\n"
                        f"🔄 Action: {result['action']}\n\n"
                        f"📋 *Latest changes have been pulled from GitHub*",
                        parse_mode='Markdown'
                    )
                else:
                    await query.edit_message_text(
                        f"❌ **Update Failed**\n\n{result['error']}\n\n"
                        f"🔧 *Please check your connection and try again*",
                        parse_mode='Markdown'
                    )

            elif data == "close_repo":
                # Close the repository
                self.session_manager.clear_active_repo(user_id)
                await query.edit_message_text(
                    "🚫 **Repository Closed**\n\n"
                    "The active repository has been closed.\n\n"
                    "📋 *Load a new repository with `/loadrepo <url>`*",
                    parse_mode='Markdown'
                )

        except Exception as e:
            logger.error(f"Error in handle_repo_callbacks: {e}")
            await query.edit_message_text(
                f"❌ **Error**\n\nAn error occurred: `{str(e)}`",
                parse_mode='Markdown'
            )

    def _format_file_list(self, files: List[dict], owner: str, repo: str, current_path: str) -> str:
        """Format file list for Telegram display"""
        # Header with repository info
        header = f"📁 **{owner}/{repo}**\n\n"

        if current_path:
            header += f"📂 **Directory:** `{current_path}`\n\n"

        # Build file list
        file_items = []
        dir_items = []

        for file_info in files:
            icon = self._get_file_icon(file_info)
            name = file_info['name']
            path = file_info['path']

            if file_info['is_dir']:
                dir_items.append(f"{icon} `{name}/`")
            else:
                # Add size for files
                size_str = self._format_file_size(file_info['size'])
                file_items.append(f"{icon} `{name}` ({size_str})")

        # Combine directories and files
        all_items = dir_items + file_items

        if not all_items:
            content = "*No files to display*"
        else:
            # Limit to first 30 items to avoid message length issues
            if len(all_items) > 30:
                content = "\n".join(all_items[:30])
                content += f"\n\n... and {len(all_items) - 30} more items"
            else:
                content = "\n".join(all_items)

        # Add navigation and help info
        navigation = ""
        if current_path:
            parent_path = str(Path(current_path).parent) if Path(current_path).parent != Path('.') else ""
            navigation = f"\n🔍 *Navigation:* `/files` for root | `/files {parent_path}` for parent"
        else:
            navigation = f"\n🔍 *Navigation:* `/files <directory>` to explore"

        help_text = (
            f"\n\n💡 **Commands:**\n"
            f"• `/files <path>` - Browse directory\n"
            f"• `/view <file_path>` - View file content\n"
            f"• `/edit <file_path>` - Edit file\n"
            f"• `/diff <file_path>` - See changes"
        )

        return header + content + navigation + help_text

    async def _get_detailed_repo_info(self, user_id: int) -> str:
        """Get detailed repository information"""
        active_repo = self.session_manager.get_active_repo(user_id)
        if not active_repo:
            return "❌ **No Repository Loaded**"

        # Get repo directory
        repo_dir = self.repo_manager.get_user_repo_dir(
            user_id,
            active_repo['owner'],
            active_repo['repo']
        )

        # Get indexed info from repo manager
        user_repo = self.repo_manager.get_user_active_repo(user_id)

        info_message = (
            f"📊 **Repository Information**\n\n"
            f"📁 **Name:** {active_repo['owner']}/{active_repo['repo']}\n"
            f"🔗 **URL:** {active_repo['url']}\n"
            f"📂 **Path:** `{repo_dir}`\n\n"
        )

        if user_repo and 'info' in user_repo:
            repo_info = user_repo['info']
            if 'error' not in repo_info:
                info_message += (
                    f"📈 **Statistics:**\n"
                    f"• Total Files: {repo_info.get('total_files', 'N/A')}\n"
                    f"• Total Directories: {repo_info.get('total_dirs', 'N/A')}\n"
                    f"• File Types: {len(repo_info.get('extensions', []))}\n\n"
                    f"🔧 **Languages:**\n"
                )

                languages = repo_info.get('languages', [])
                if languages:
                    info_message += f" {', '.join(languages)}\n\n"
                else:
                    info_message += " No programming languages detected\n\n"

        info_message += (
            f"🕒 **Session Info:**\n"
            f"• Loaded at: {self._format_timestamp(repo_dir.stat().st_mtime if repo_dir.exists() else 0)}\n"
            f"• Status: ✅ Active\n\n"
            f"💡 **Available Actions:**\n"
            f"• Browse files with `/files`\n"
            f"• Update with repo button below\n"
            f"• Close with repo button below"
        )

        return info_message

    def _get_file_icon(self, file_info: dict) -> str:
        """Get appropriate icon for file or directory"""
        if file_info['is_dir']:
            return "📁"

        extension = file_info.get('extension', '').lower()
        language = file_info.get('language', '')

        # Language-based icons
        if language:
            icon_map = {
                'Python': '🐍',
                'JavaScript': '📜',
                'TypeScript': '📘',
                'React': '⚛️',
                'Java': '☕',
                'C++': '⚙️',
                'C': '⚙️',
                'C#': '🔷',
                'PHP': '🐘',
                'Ruby': '💎',
                'Go': '🐹',
                'Rust': '🦀',
                'Swift': '🍎',
                'Kotlin': '🎯',
                'HTML': '🌐',
                'CSS': '🎨',
                'Sass': '🎨',
                'SQL': '🗃️',
                'Shell': '🐚',
                'JSON': '📋',
                'XML': '📄',
                'YAML': '📄',
                'Markdown': '📝',
                'Docker': '🐳',
                'Git': '📦',
            }
            return icon_map.get(language, '📄')

        # Extension-based icons
        ext_icon_map = {
            '.py': '🐍',
            '.js': '📜',
            '.ts': '📘',
            '.jsx': '⚛️',
            '.tsx': '⚛️',
            '.java': '☕',
            '.cpp': '⚙️',
            '.c': '⚙️',
            '.cs': '🔷',
            '.php': '🐘',
            '.rb': '💎',
            '.go': '🐹',
            '.rs': '🦀',
            '.swift': '🍎',
            '.kt': '🎯',
            '.html': '🌐',
            '.css': '🎨',
            '.scss': '🎨',
            '.less': '🎨',
            '.sql': '🗃️',
            '.sh': '🐚',
            '.json': '📋',
            '.xml': '📄',
            '.yaml': '📄',
            '.yml': '📄',
            '.md': '📝',
            '.txt': '📄',
            '.pdf': '📕',
            '.doc': '📘',
            '.docx': '📘',
            '.xls': '📗',
            '.xlsx': '📗',
            '.png': '🖼️',
            '.jpg': '🖼️',
            '.jpeg': '🖼️',
            '.gif': '🖼️',
            '.svg': '🎨',
            '.mp4': '🎬',
            '.mp3': '🎵',
            '.zip': '🗜️',
            '.tar': '🗜️',
            '.gz': '🗜️',
        }
        return ext_icon_map.get(extension, '📄')

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes < 1024:
            return f"{size_bytes}B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes/1024:.1f}KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes/(1024*1024):.1f}MB"
        else:
            return f"{size_bytes/(1024*1024*1024):.1f}GB"

    def _format_timestamp(self, timestamp: float) -> str:
        """Format timestamp for display"""
        import datetime
        dt = datetime.datetime.fromtimestamp(timestamp)
        return dt.strftime('%Y-%m-%d %H:%M:%S')