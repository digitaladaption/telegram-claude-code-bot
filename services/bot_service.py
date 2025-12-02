"""
Main Telegram Bot Service
Handles all bot commands and message processing
"""

import asyncio
import logging
import os
from typing import List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

# Import our custom modules
from src.telegram_bot.bot.client import TelegramClient, TelegramMessageFormatter
from src.telegram_bot.command.claude_cli_executor import ClaudeCliDirectExecutor
from session_manager import SessionManager

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class TelegramBotService:
    """Main Telegram Bot Service"""

    def __init__(self):
        # Configuration
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

        # Initialize components
        self.telegram_client = TelegramClient(self.bot_token)
        self.session_manager = SessionManager()
        self.claude_executor = ClaudeCliDirectExecutor(self.session_manager)
        self.message_formatter = TelegramMessageFormatter()

        # Get security settings
        self.allowed_users = self._parse_user_list(os.getenv('ALLOWED_USERS', ''))
        self.admin_users = self._parse_user_list(os.getenv('ADMIN_USERS', ''))

        logger.info(f"Bot service initialized. Allowed users: {len(self.allowed_users)}, Admin users: {len(self.admin_users)}")

    def _parse_user_list(self, user_string: str) -> List[int]:
        """Parse comma-separated list of user IDs"""
        if not user_string.strip():
            return []
        try:
            return [int(uid.strip()) for uid in user_string.split(',')]
        except ValueError:
            logger.error(f"Invalid user list format: {user_string}")
            return []

    def _is_user_allowed(self, user_id: int) -> bool:
        """Check if user is allowed to use the bot"""
        if not self.allowed_users:
            return True  # Allow all if no restriction
        return user_id in self.allowed_users

    def _is_admin_user(self, user_id: int) -> bool:
        """Check if user is admin"""
        return user_id in self.admin_users

    def setup_handlers(self, application: Application):
        """Setup all command and message handlers"""
        # Command handlers
        application.add_handler(CommandHandler("start", self.handle_start))
        application.add_handler(CommandHandler("help", self.handle_help))
        application.add_handler(CommandHandler("start_session", self.handle_start_session))
        application.add_handler(CommandHandler("session_info", self.handle_session_info))
        application.add_handler(CommandHandler("end_session", self.handle_end_session))
        application.add_handler(CommandHandler("list_files", self.handle_list_files))
        application.add_handler(CommandHandler("status", self.handle_status))

        # Admin commands
        application.add_handler(CommandHandler("admin_stats", self.handle_admin_stats))
        application.add_handler(CommandHandler("admin_sessions", self.handle_admin_sessions))

        # Callback query handlers (for inline keyboards)
        application.add_handler(CallbackQueryHandler(self.handle_callback_query))

        # Message handler (for coding tasks)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_coding_task))

        logger.info("All handlers setup complete")

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        user_id = user.id

        if not self._is_user_allowed(user_id):
            await update.message.reply_text("❌ Access denied. You are not authorized to use this bot.")
            return

        welcome_message = self.message_formatter.format_welcome_message(user.first_name or user.username)
        await update.message.reply_text(welcome_message, parse_mode='Markdown')

        logger.info(f"User {user.full_name} ({user_id}) started the bot")

    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        user_id = update.effective_user.id

        if not self._is_user_allowed(user_id):
            return

        help_message = self.message_formatter.format_help_message()
        await update.message.reply_text(help_message, parse_mode='Markdown')

    async def handle_start_session(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start_session command"""
        user = update.effective_user
        user_id = user.id

        if not self._is_user_allowed(user_id):
            return

        # Show typing action
        await self.telegram_client.send_typing_action(update.effective_chat.id)

        # Check if user already has an active session
        existing_session = self.session_manager.get_user_active_session(user_id)
        if existing_session:
            session_info = self.message_formatter.format_session_info(
                existing_session.token, existing_session.working_dir
            )
            await update.message.reply_text(
                f"ℹ️ You already have an active session!\n\n{session_info}",
                parse_mode='Markdown'
            )
            return

        # Create new session
        try:
            session = self.session_manager.create_session(
                user_id=user_id,
                user_name=user.full_name or user.username,
                working_dir=context.args[0] if context.args else None
            )

            session_info = self.message_formatter.format_session_info(
                session.token, session.working_dir
            )

            # Create inline keyboard for session actions
            keyboard = self.message_formatter.create_session_keyboard()
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"✅ **Session Created Successfully!**\n\n{session_info}",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

            logger.info(f"New session created for user {user.full_name}: {session.token}")

        except Exception as e:
            error_message = self.message_formatter.format_error_message(
                f"Failed to create session: {str(e)}",
                "Please try again or contact admin"
            )
            await update.message.reply_text(error_message, parse_mode='Markdown')

    async def handle_session_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /session_info command"""
        user = update.effective_user
        user_id = user.id

        if not self._is_user_allowed(user_id):
            return

        session = self.session_manager.get_user_active_session(user_id)
        if not session:
            await update.message.reply_text(
                "❌ No active session found.\n\nStart a new session with `/start_session`",
                parse_mode='Markdown'
            )
            return

        session_info = self.message_formatter.format_session_info(
            session.token, session.working_dir
        )

        # Add additional session details
        details = (
            f"📊 **Session Details:**\n\n"
            f"{session_info}\n\n"
            f"⏰ **Created:** {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"🔄 **Last Used:** {session.last_used.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"👤 **User:** {session.user_name}"
        )

        keyboard = self.message_formatter.create_session_keyboard()
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(details, parse_mode='Markdown', reply_markup=reply_markup)

    async def handle_end_session(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /end_session command"""
        user = update.effective_user
        user_id = user.id

        if not self._is_user_allowed(user_id):
            return

        success = self.session_manager.end_user_session(user_id)
        if success:
            await update.message.reply_text(
                "✅ **Session Ended**\n\nYour coding session has been terminated. "
                "Start a new session anytime with `/start_session`",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "ℹ️ No active session to end.\n\nStart a new session with `/start_session`",
                parse_mode='Markdown'
            )

    async def handle_list_files(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list_files command"""
        user = update.effective_user
        user_id = user.id

        if not self._is_user_allowed(user_id):
            return

        session = self.session_manager.get_user_active_session(user_id)
        if not session:
            await update.message.reply_text(
                "❌ No active session found.\n\nStart a new session with `/start_session`",
                parse_mode='Markdown'
            )
            return

        await self.telegram_client.send_typing_action(update.effective_chat.id)

        try:
            # List files in working directory
            import os
            working_dir = session.working_dir
            files = os.listdir(working_dir)

            if not files:
                await update.message.reply_text(
                    f"📁 **Files in `{working_dir}`**\n\n*No files found*",
                    parse_mode='Markdown'
                )
                return

            file_list = []
            for file in sorted(files):
                file_path = os.path.join(working_dir, file)
                if os.path.isfile(file_path):
                    size = os.path.getsize(file_path)
                    file_list.append(f"📄 `{file}` ({self._format_file_size(size)})")
                else:
                    file_list.append(f"📁 `{file}/` (directory)")

            file_text = "\n".join(file_list[:20])  # Limit to 20 files

            if len(files) > 20:
                file_text += f"\n\n... and {len(files) - 20} more files"

            await update.message.reply_text(
                f"📁 **Files in `{working_dir}`**\n\n{file_text}",
                parse_mode='Markdown'
            )

        except Exception as e:
            error_message = self.message_formatter.format_error_message(f"Failed to list files: {str(e)}")
            await update.message.reply_text(error_message, parse_mode='Markdown')

    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        user = update.effective_user
        user_id = user.id

        if not self._is_user_allowed(user_id):
            return

        # Get session info
        session = self.session_manager.get_user_active_session(user_id)
        if session:
            session_status = f"✅ Active session: `{session.token}`\n📂 Directory: `{session.working_dir}`"
        else:
            session_status = "❌ No active session"

        # Get bot stats (for admins)
        if self._is_admin_user(user_id):
            stats = self.session_manager.get_session_stats()
            bot_status = (
                f"🤖 **Bot Status:** Online\n\n"
                f"📊 **Global Stats:**\n"
                f"• Total sessions: {stats['total_sessions']}\n"
                f"• Active sessions: {stats['active_sessions']}\n"
                f"• Unique users: {stats['unique_users']}\n\n"
                f"👤 **Your Status:**\n{session_status}"
            )
        else:
            bot_status = f"🤖 **Bot Status:** Online\n\n{session_status}"

        await update.message.reply_text(bot_status, parse_mode='Markdown')

    async def handle_coding_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle coding task messages"""
        user = update.effective_user
        user_id = user.id
        message_text = update.message.text

        if not self._is_user_allowed(user_id):
            return

        # Show typing action
        await self.telegram_client.send_typing_action(update.effective_chat.id)

        # Execute coding task
        result = await self.claude_executor.send_coding_task(user_id, message_text)

        # Send result
        if result.success:
            await update.message.reply_text(result.output, parse_mode='Markdown')
        else:
            await update.message.reply_text(result.error, parse_mode='Markdown')

        logger.info(f"Coding task executed for user {user.full_name}: {result.success}")

    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard callback queries"""
        query = update.callback_query
        user_id = update.effective_user.id

        if not self._is_user_allowed(user_id):
            await query.answer("Access denied", show_alert=True)
            return

        await query.answer()  # Acknowledge the callback

        data = query.data
        chat_id = query.message.chat_id
        message_id = query.message.message_id

        if data == "list_files":
            # Simulate list_files command
            await self.handle_list_files(update, context)
        elif data == "session_info":
            # Simulate session_info command
            await self.handle_session_info(update, context)
        elif data == "new_session":
            # Simulate start_session command
            await self.handle_start_session(update, context)
        elif data == "end_session":
            # Simulate end_session command
            await self.handle_end_session(update, context)
        else:
            await query.edit_message_text("❌ Unknown action", parse_mode='Markdown')

    async def handle_admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle admin stats command"""
        user = update.effective_user
        user_id = user.id

        if not self._is_admin_user(user_id):
            await update.message.reply_text("❌ Admin access required")
            return

        stats = self.session_manager.get_session_stats()
        active_sessions = self.session_manager.get_all_active_sessions()

        stats_text = (
            f"📊 **Admin Statistics**\n\n"
            f"📈 **Global Stats:**\n"
            f"• Total sessions: {stats['total_sessions']}\n"
            f"• Active sessions: {stats['active_sessions']}\n"
            f"• Unique users: {stats['unique_users']}\n\n"
            f"🕒 **Time Range:**\n"
            f"• Oldest: {stats['oldest_session'].strftime('%Y-%m-%d %H:%M') if stats['oldest_session'] else 'N/A'}\n"
            f"• Newest: {stats['newest_session'].strftime('%Y-%m-%d %H:%M') if stats['newest_session'] else 'N/A'}\n\n"
            f"👥 **Active Sessions:**\n"
        )

        for session in active_sessions[:10]:  # Show first 10
            stats_text += f"• `{session.token}` - {session.user_name}\n"

        if len(active_sessions) > 10:
            stats_text += f"... and {len(active_sessions) - 10} more"

        await update.message.reply_text(stats_text, parse_mode='Markdown')

    async def handle_admin_sessions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle admin sessions command - detailed session info"""
        user = update.effective_user
        user_id = user.id

        if not self._is_admin_user(user_id):
            await update.message.reply_text("❌ Admin access required")
            return

        all_sessions = self.session_manager.export_sessions()

        if not all_sessions:
            await update.message.reply_text("📄 No sessions found")
            return

        # Create session summary
        sessions_text = f"📄 **All Sessions ({len(all_sessions)} total)**\n\n"

        for session_data in all_sessions[:20]:  # Show first 20
            status = "✅ Active" if session_data['is_active'] else "❌ Inactive"
            created = session_data['created_at'][:19]  # Remove microseconds
            sessions_text += (
                f"• `{session_data['token']}` - {session_data['user_name']} "
                f"({session_data['user_id']}) - {status}\n"
                f"  Created: {created}\n"
                f"  📂 {session_data['working_dir']}\n\n"
            )

        if len(all_sessions) > 20:
            sessions_text += f"... and {len(all_sessions) - 20} more sessions"

        await update.message.reply_text(sessions_text, parse_mode='Markdown')

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes < 1024:
            return f"{size_bytes}B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes/1024:.1f}KB"
        else:
            return f"{size_bytes/(1024*1024):.1f}MB"


async def main():
    """Main function to run the bot"""
    # Setup logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    try:
        # Create bot service
        bot_service = TelegramBotService()

        # Setup Telegram application
        application = bot_service.telegram_client.setup_application()
        bot_service.setup_handlers(application)

        logger.info("Starting Telegram bot...")

        # Start the bot
        await application.run_polling(drop_pending_updates=True)

    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise


if __name__ == '__main__':
    asyncio.run(main())