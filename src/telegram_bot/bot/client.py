"""
Telegram Bot Client
Handles all Telegram messaging functionality
"""

import logging
import asyncio
from typing import Optional, List
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

logger = logging.getLogger(__name__)


class TelegramClient:
    """Telegram Bot Client for messaging with users"""

    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.bot = Bot(token=bot_token)
        self.application = None
        logger.info(f"Telegram client initialized with bot token")

    async def send_text_message(self, chat_id: int, text: str, parse_mode: str = ParseMode.MARKDOWN) -> bool:
        """Send a text message to a user"""
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                disable_web_page_preview=True
            )
            logger.info(f"Message sent successfully to chat_id={chat_id}")
            return True
        except Exception as e:
            logger.error(f"Error sending message to {chat_id}: {e}")
            return False

    async def send_code_block(self, chat_id: int, code: str, language: str = "", caption: str = "") -> bool:
        """Send a code block message"""
        try:
            formatted_code = f"```{language}\n{code}\n```"
            if caption:
                formatted_code = f"{caption}\n\n{formatted_code}"

            await self.bot.send_message(
                chat_id=chat_id,
                text=formatted_code,
                parse_mode=ParseMode.MARKDOWN_V2
            )
            logger.info(f"Code block sent to chat_id={chat_id}")
            return True
        except Exception as e:
            logger.error(f"Error sending code block to {chat_id}: {e}")
            return False

    async def send_file(self, chat_id: int, file_path: str, caption: str = "") -> bool:
        """Send a file to a user"""
        try:
            with open(file_path, 'rb') as file:
                await self.bot.send_document(
                    chat_id=chat_id,
                    document=file,
                    caption=caption
                )
            logger.info(f"File sent to chat_id={chat_id}: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error sending file to {chat_id}: {e}")
            return False

    async def send_inline_keyboard(self, chat_id: int, text: str, keyboard: List[List[InlineKeyboardButton]]) -> bool:
        """Send a message with inline keyboard"""
        try:
            reply_markup = InlineKeyboardMarkup(keyboard)
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            logger.info(f"Inline keyboard message sent to chat_id={chat_id}")
            return True
        except Exception as e:
            logger.error(f"Error sending inline keyboard to {chat_id}: {e}")
            return False

    async def send_typing_action(self, chat_id: int) -> bool:
        """Send typing action to show bot is working"""
        try:
            await self.bot.send_chat_action(chat_id=chat_id, action="typing")
            return True
        except Exception as e:
            logger.error(f"Error sending typing action to {chat_id}: {e}")
            return False

    async def get_user_info(self, user_id: int) -> Optional[dict]:
        """Get user information"""
        try:
            user = await self.bot.get_chat(user_id)
            return {
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': user.full_name
            }
        except Exception as e:
            logger.error(f"Error getting user info for {user_id}: {e}")
            return None

    def setup_application(self) -> Application:
        """Setup the Telegram Application with handlers"""
        self.application = Application.builder().token(self.bot_token).build()
        return self.application


class TelegramMessageFormatter:
    """Helper class for formatting Telegram messages"""

    @staticmethod
    def format_command_result(command: str, output: str, success: bool = True, exec_time_ms: int = 0) -> str:
        """Format command execution result"""
        status_emoji = "✅" if success else "❌"
        exec_time = f"{exec_time_ms}ms" if exec_time_ms > 0 else "N/A"

        return (
            f"{status_emoji} **Command executed**\n\n"
            f"**Command:** `{command}`\n"
            f"**Execution time:** {exec_time}\n\n"
            f"**Output:**\n```\n{output}\n```"
        )

    @staticmethod
    def format_session_info(token: str, working_dir: str) -> str:
        """Format session information"""
        return (
            f"🔑 **Active Session**\n\n"
            f"**Token:** `{token}`\n"
            f"**Working Directory:** `{working_dir}`\n\n"
            f"Send me any coding task and I'll execute it using Claude CLI!"
        )

    @staticmethod
    def format_error_message(error: str, suggestion: str = "") -> str:
        """Format error message"""
        message = f"❌ **Error:** {error}"
        if suggestion:
            message += f"\n\n💡 **Suggestion:** {suggestion}"
        return message

    @staticmethod
    def format_welcome_message(user_name: str) -> str:
        """Format welcome message"""
        return (
            f"👋 Hello {user_name}! I'm your **Claude Coding Assistant**.\n\n"
            f"🚀 **What I can do:**\n"
            f"• Execute code using Claude CLI\n"
            f"• Manage coding sessions\n"
            f"• Handle file operations\n"
            f"• Provide coding assistance\n\n"
            f"📝 **Start by sending:**\n"
            f"`/start_session` - Create a new coding session\n"
            f"`/help` - See all commands\n\n"
            f"Let's start coding! 🎯"
        )

    @staticmethod
    def format_help_message() -> str:
        """Format help message"""
        return (
            "📖 **Help - Available Commands:**\n\n"
            "🔧 **Session Management:**\n"
            "• `/start_session` - Create new coding session\n"
            "• `/session_info` - Show current session details\n"
            "• `/end_session` - End current session\n\n"
            "💬 **Coding:**\n"
            "• Just send any coding task as a message!\n"
            "• Example: `Create a Python script to scrape websites`\n"
            "• Example: `Fix this bug in my React app`\n\n"
            "📁 **File Operations:**\n"
            "• `/list_files` - Show files in working directory\n"
            "• `/upload_file` - Upload a file to work with\n\n"
            "ℹ️ **Other:**\n"
            "• `/help` - Show this help message\n"
            "• `/status` - Check bot status\n\n"
            f"💡 **Tip:** Start a session first, then send your coding tasks!"
        )

    @staticmethod
    def create_session_keyboard() -> List[List[InlineKeyboardButton]]:
        """Create inline keyboard for session actions"""
        return [
            [
                InlineKeyboardButton("📁 List Files", callback_data="list_files"),
                InlineKeyboardButton("ℹ️ Session Info", callback_data="session_info")
            ],
            [
                InlineKeyboardButton("🔄 New Session", callback_data="new_session"),
                InlineKeyboardButton("❌ End Session", callback_data="end_session")
            ]
        ]

    @staticmethod
    def escape_markdown(text: str) -> str:
        """Escape special markdown characters"""
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        return text