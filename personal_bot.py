#!/usr/bin/env python3
"""
Personal Telegram Code Assistant
A simple bot for controlling your code from Telegram
"""

import asyncio
import logging
import os
import uuid
import json
import subprocess
import difflib
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from dotenv import load_dotenv
import anthropic
import requests

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class PersonalCodeAssistant:
    """Personal code assistant with GitHub and LLM integration"""

    def __init__(self):
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.moonshot_key = os.getenv('MOONSHOT_API_KEY')  # Kimi K2 API key
        self.workspace_dir = Path(os.getenv('DEFAULT_WORKSPACE', '/tmp/telegram_bot_workspaces'))

        # Create workspace directory
        self.workspace_dir.mkdir(exist_ok=True)

        # User session data (for single user)
        self.session_file = self.workspace_dir / "personal_session.json"
        self.session_data = self.load_session()

        # LLM client
        self.llm_client = None
        self.llm_type = None
        self.setup_llm()

        logger.info(f"🚀 Personal Code Assistant initialized")
        logger.info(f"📁 Workspace: {self.workspace_dir}")
        logger.info(f"🤖 LLM: {self.llm_type if self.llm_type else 'None'}")
        logger.info(f"🔗 GitHub: {'✅' if self.github_token else '❌'}")

    def setup_llm(self):
        """Setup LLM client based on available keys"""
        if self.anthropic_key:
            try:
                self.llm_client = anthropic.Anthropic(api_key=self.anthropic_key)
                self.llm_type = "Claude"
                logger.info("✅ Claude API initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Claude: {e}")

        elif self.moonshot_key:
            # Kimi K2 uses OpenAI-compatible API with correct endpoint
            try:
                import openai
                self.llm_client = openai.OpenAI(
                    api_key=self.moonshot_key,
                    base_url="https://api.moonshot.ai/v1"  # Correct endpoint
                )
                self.llm_type = "Kimi K2"
                logger.info("✅ Kimi K2 API initialized")
            except ImportError:
                self.llm_type = "Kimi K2"
                logger.info("✅ Kimi K2 API configured (install openai package)")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Kimi K2: {e}")

        elif self.openai_key:
            try:
                import openai
                self.llm_client = openai.OpenAI(api_key=self.openai_key)
                self.llm_type = "OpenAI"
                logger.info("✅ OpenAI API initialized")
            except ImportError:
                self.llm_type = "OpenAI"
                logger.info("✅ OpenAI API configured (install openai package)")
            except Exception as e:
                logger.error(f"❌ Failed to initialize OpenAI: {e}")

        else:
            logger.warning("⚠️ No LLM API key found - AI features disabled")

    def load_session(self) -> Dict:
        """Load user session data"""
        try:
            if self.session_file.exists():
                with open(self.session_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading session: {e}")

        return {
            'user_id': None,
            'active_repo': None,
            'repo_path': None,
            'repo_url': None,
            'current_file': None,
            'last_command': None
        }

    def save_session(self):
        """Save user session data"""
        try:
            with open(self.session_file, 'w') as f:
                json.dump(self.session_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving session: {e}")

    def validate_github_url(self, url: str) -> Optional[str]:
        """Validate and normalize GitHub URL"""
        # Remove .git extension if present
        url = url.replace('.git', '')

        # Handle different GitHub URL formats
        patterns = [
            r'^https?://github\.com/([^/]+)/([^/]+)$',
            r'^([^/]+)/([^/]+)$'
        ]

        for pattern in patterns:
            match = re.match(pattern, url)
            if match:
                owner, repo = match.groups()
                return f"https://github.com/{owner}/{repo}"

        return None

    async def clone_repository(self, github_url: str) -> Dict:
        """Clone a GitHub repository"""
        try:
            # Validate URL
            normalized_url = self.validate_github_url(github_url)
            if not normalized_url:
                return {'success': False, 'error': 'Invalid GitHub URL format'}

            # Create unique directory for repo
            repo_name = normalized_url.split('/')[-1]
            repo_path = self.workspace_dir / f"repo_{uuid.uuid4().hex[:8]}_{repo_name}"

            # Clone command
            if self.github_token:
                # Use token for authentication
                auth_url = normalized_url.replace('https://github.com', f'https://oauth2:{self.github_token}@github.com')
            else:
                auth_url = normalized_url

            cmd = ['git', 'clone', auth_url, str(repo_path)]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                # Update session
                self.session_data.update({
                    'active_repo': repo_name,
                    'repo_path': str(repo_path),
                    'repo_url': normalized_url,
                    'last_command': 'clone'
                })
                self.save_session()

                return {
                    'success': True,
                    'repo_name': repo_name,
                    'repo_path': str(repo_path),
                    'message': f'Successfully cloned {repo_name}'
                }
            else:
                return {
                    'success': False,
                    'error': f'Clone failed: {result.stderr.strip()}'
                }

        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Clone timeout (5 minutes)'}
        except Exception as e:
            return {'success': False, 'error': f'Clone error: {str(e)}'}

    async def set_local_repo(self, repo_path: str) -> Dict:
        """Set a local repository path"""
        try:
            path = Path(repo_path).expanduser().resolve()

            if not path.exists():
                return {'success': False, 'error': 'Path does not exist'}

            if not path.is_dir():
                return {'success': False, 'error': 'Path is not a directory'}

            # Check if it's a git repository
            git_dir = path / '.git'
            if not git_dir.exists():
                return {'success': False, 'error': 'Not a git repository'}

            # Update session
            self.session_data.update({
                'active_repo': path.name,
                'repo_path': str(path),
                'repo_url': None,
                'last_command': 'set_local'
            })
            self.save_session()

            return {
                'success': True,
                'repo_name': path.name,
                'repo_path': str(path),
                'message': f'Using local repository: {path.name}'
            }

        except Exception as e:
            return {'success': False, 'error': f'Error setting repo: {str(e)}'}

    def list_files(self, path: str = None) -> List[Tuple[str, str]]:
        """List files in repository with emoji icons"""
        if not self.session_data['repo_path']:
            return []

        try:
            repo_path = Path(self.session_data['repo_path'])
            if path:
                repo_path = repo_path / path

            files = []
            for item in repo_path.iterdir():
                if item.name.startswith('.'):
                    continue

                if item.is_dir():
                    emoji = "📁"
                else:
                    # File type emojis
                    ext = item.suffix.lower()
                    emoji_map = {
                        '.py': '🐍',
                        '.js': '⚡',
                        '.ts': '📘',
                        '.jsx': '⚛️',
                        '.tsx': '⚛️',
                        '.html': '🌐',
                        '.css': '🎨',
                        '.json': '📄',
                        '.md': '📝',
                        '.txt': '📄',
                        '.yml': '⚙️',
                        '.yaml': '⚙️',
                        '.sql': '🗃️',
                        '.sh': '🐚',
                        '.env': '🔐',
                    }
                    emoji = emoji_map.get(ext, '📄')

                relative_path = item.relative_to(Path(self.session_data['repo_path']))
                files.append((f"{emoji} {item.name}", str(relative_path)))

            return sorted(files)

        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []

    def read_file(self, file_path: str) -> Dict:
        """Read file contents"""
        if not self.session_data['repo_path']:
            return {'success': False, 'error': 'No repository set'}

        try:
            full_path = Path(self.session_data['repo_path']) / file_path

            if not full_path.exists():
                return {'success': False, 'error': 'File not found'}

            if not full_path.is_file():
                return {'success': False, 'error': 'Not a file'}

            # Prevent reading binary files
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                return {'success': False, 'error': 'Binary file - cannot display'}

            # Truncate very large files
            if len(content) > 4000:
                content = content[:4000] + "\n\n... (file truncated, use /edit to see more)"

            return {
                'success': True,
                'content': content,
                'file_path': str(full_path),
                'size': len(content)
            }

        except Exception as e:
            return {'success': False, 'error': f'Error reading file: {str(e)}'}

    def edit_file(self, file_path: str, new_content: str) -> Dict:
        """Edit file contents"""
        if not self.session_data['repo_path']:
            return {'success': False, 'error': 'No repository set'}

        try:
            full_path = Path(self.session_data['repo_path']) / file_path

            if not full_path.exists():
                return {'success': False, 'error': 'File not found'}

            if not full_path.is_file():
                return {'success': False, 'error': 'Not a file'}

            # Write new content
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            return {
                'success': True,
                'message': f'File {file_path} updated successfully'
            }

        except Exception as e:
            return {'success': False, 'error': f'Error writing file: {str(e)}'}

    def get_git_diff(self) -> str:
        """Get git diff"""
        if not self.session_data['repo_path']:
            return "No repository set"

        try:
            os.chdir(self.session_data['repo_path'])
            result = subprocess.run(['git', 'diff'], capture_output=True, text=True)

            if result.returncode == 0 and result.stdout.strip():
                return result.stdout
            else:
                return "No changes to commit"

        except Exception as e:
            return f"Error getting diff: {str(e)}"

    def git_commit(self, message: str) -> Dict:
        """Commit changes"""
        if not self.session_data['repo_path']:
            return {'success': False, 'error': 'No repository set'}

        try:
            os.chdir(self.session_data['repo_path'])

            # Check if there are changes
            diff_result = subprocess.run(['git', 'diff'], capture_output=True, text=True)
            if not diff_result.stdout.strip():
                return {'success': False, 'error': 'No changes to commit'}

            # Add all changes
            add_result = subprocess.run(['git', 'add', '.'], capture_output=True, text=True)
            if add_result.returncode != 0:
                return {'success': False, 'error': 'Failed to stage changes'}

            # Commit
            commit_result = subprocess.run(['git', 'commit', '-m', message], capture_output=True, text=True)
            if commit_result.returncode == 0:
                return {'success': True, 'message': 'Changes committed successfully'}
            else:
                return {'success': False, 'error': f'Commit failed: {commit_result.stderr}'}

        except Exception as e:
            return {'success': False, 'error': f'Error committing: {str(e)}'}

    def git_push(self) -> Dict:
        """Push changes to remote"""
        if not self.session_data['repo_path']:
            return {'success': False, 'error': 'No repository set'}

        try:
            os.chdir(self.session_data['repo_path'])

            result = subprocess.run(['git', 'push'], capture_output=True, text=True, timeout=120)

            if result.returncode == 0:
                return {'success': True, 'message': 'Changes pushed successfully'}
            else:
                return {'success': False, 'error': f'Push failed: {result.stderr}'}

        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Push timeout (2 minutes)'}
        except Exception as e:
            return {'success': False, 'error': f'Error pushing: {str(e)}'}

# Global assistant instance
assistant = PersonalCodeAssistant()

# Telegram Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the bot"""
    user = update.effective_user
    assistant.session_data['user_id'] = user.id
    assistant.save_session()

    welcome_msg = f"""👋 Welcome {user.first_name}!

🤖 **Personal Code Assistant** - Control your code from Telegram!

**Quick Start:**
📁 Load a repo: `/loadrepo owner/repo` or `/setrepo /path/to/local`
📂 Browse files: `/files`
📖 View code: `/view filename.py`
🤖 Get AI help: Just ask me anything about your code!

**Git Operations:**
/diff - See changes
/commit "message" - Save changes
/push - Push to GitHub

Ready to code from your phone! 📱✨"""

    await update.message.reply_text(welcome_msg)

async def load_repo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Load a GitHub repository"""
    if not context.args:
        await update.message.reply_text("Usage: `/loadrepo owner/repo`")
        return

    repo_url = " ".join(context.args)
    await update.message.reply_text("🔄 Cloning repository...")

    result = await assistant.clone_repository(repo_url)

    if result['success']:
        await update.message.reply_text(
            f"✅ {result['message']}\n\n"
            f"📁 Repository: {result['repo_name']}\n"
            f"📂 Use `/files` to browse"
        )
    else:
        await update.message.reply_text(f"❌ Error: {result['error']}")

async def set_repo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set a local repository"""
    if not context.args:
        await update.message.reply_text("Usage: `/setrepo /path/to/repository`")
        return

    repo_path = " ".join(context.args)
    result = await assistant.set_local_repo(repo_path)

    if result['success']:
        await update.message.reply_text(
            f"✅ {result['message']}\n\n"
            f"📂 Use `/files` to browse"
        )
    else:
        await update.message.reply_text(f"❌ Error: {result['error']}")

async def files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List files in repository"""
    path = " ".join(context.args) if context.args else None

    if not assistant.session_data['repo_path']:
        await update.message.reply_text("❌ No repository loaded. Use `/loadrepo` or `/setrepo` first")
        return

    file_list = assistant.list_files(path)

    if not file_list:
        await update.message.reply_text("📁 No files found")
        return

    current_path = path if path else "root"

    msg = f"📁 **Files in {current_path}**:\n\n"
    for display_name, file_path in file_list:
        msg += f"{display_name}\n"

    await update.message.reply_text(msg)

async def view_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View file contents"""
    if not context.args:
        await update.message.reply_text("Usage: `/view filename`")
        return

    file_path = " ".join(context.args)
    result = assistant.read_file(file_path)

    if result['success']:
        await update.message.reply_text(
            f"📄 **{file_path}** ({result['size']} chars)\n\n"
            f"```\n{result['content']}\n```"
        )
    else:
        await update.message.reply_text(f"❌ Error: {result['error']}")

async def edit_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Edit file contents"""
    if not context.args:
        await update.message.reply_text("Usage: `/edit filename new_content`")
        return

    # Parse command: /edit filename rest_of_content
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: `/edit filename new_content`")
        return

    file_path = args[0]
    new_content = " ".join(args[1:])

    result = assistant.edit_file(file_path, new_content)

    if result['success']:
        await update.message.reply_text(
            f"✅ **File Updated:** {file_path}\n\n"
            f"📝 Changes saved. Use `/diff` to see changes or `/commit` to save to git."
        )
    else:
        await update.message.reply_text(f"❌ Error: {result['error']}")

async def git_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show git status"""
    if not assistant.session_data['repo_path']:
        await update.message.reply_text("❌ No repository loaded. Use `/loadrepo` or `/setrepo` first")
        return

    try:
        os.chdir(assistant.session_data['repo_path'])
        result = subprocess.run(['git', 'status'], capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            await update.message.reply_text(
                f"📊 **Git Status:**\n\n```\n{result.stdout}\n```"
            )
        else:
            await update.message.reply_text(f"❌ Git status error: {result.stderr}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def diff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show git diff"""
    diff_text = assistant.get_git_diff()

    if diff_text == "No changes to commit":
        await update.message.reply_text("ℹ️ No changes to commit")
    else:
        await update.message.reply_text(
            f"📝 **Git Diff**:\n\n```\n{diff_text}\n```"
        )

async def commit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commit changes"""
    if not context.args:
        await update.message.reply_text("Usage: `/commit \"your commit message\"`")
        return

    message = " ".join(context.args)
    result = assistant.git_commit(message)

    if result['success']:
        await update.message.reply_text(f"✅ {result['message']}")
    else:
        await update.message.reply_text(f"❌ Error: {result['error']}")

async def push(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Push to GitHub"""
    await update.message.reply_text("🔄 Pushing to GitHub...")

    result = assistant.git_push()

    if result['success']:
        await update.message.reply_text(f"✅ {result['message']}")
    else:
        await update.message.reply_text(f"❌ Error: {result['error']}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot status"""
    repo_info = assistant.session_data['active_repo'] or "None"
    repo_path = assistant.session_data['repo_path'] or "None"

    status_msg = f"""📊 **Bot Status**

🤖 Repository: {repo_info}
📁 Path: {repo_path}
🔗 GitHub: {'✅' if assistant.github_token else '❌'}
🤖 LLM: {assistant.llm_type or '❌ None'}

**Current Session:**
Last command: {assistant.session_data.get('last_command', 'None')}
"""

    await update.message.reply_text(status_msg)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular messages - AI coding assistance"""
    if not assistant.llm_client:
        await update.message.reply_text(
            "🤖 AI assistance not available - no LLM API key configured\n\n"
            "Set one of these in your .env file:\n"
            "• ANTHROPIC_API_KEY (for Claude)\n"
            "• OPENAI_API_KEY (for GPT)\n"
            "• MOONSHOT_API_KEY (for Kimi K2)"
        )
        return

    user_message = update.message.text

    await update.message.reply_text("🤔 Thinking...")

    try:
        if assistant.llm_type == "Claude":
            response = assistant.llm_client.messages.create(
                model="claude-3-sonnet-20241022",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": f"You are a helpful coding assistant. The user is working on a project called '{assistant.session_data.get('active_repo', 'unknown')}'. Help them with: {user_message}"
                }]
            )

            ai_response = response.content[0].text

        elif assistant.llm_type == "OpenAI":
            response = assistant.llm_client.chat.completions.create(
                model="gpt-4",
                max_tokens=1000,
                messages=[{
                    "role": "system",
                    "content": f"You are a helpful coding assistant. The user is working on a project called '{assistant.session_data.get('active_repo', 'unknown')}'."
                }, {
                    "role": "user",
                    "content": user_message
                }]
            )

            ai_response = response.choices[0].message.content

        elif assistant.llm_type == "Kimi K2":
            try:
                response = assistant.llm_client.chat.completions.create(
                    model="kimi-k2-0905-preview",  # New Kimi K2 model
                    max_tokens=1000,
                    messages=[{
                        "role": "system",
                        "content": f"""You are Kimi, an AI assistant provided by Moonshot AI. You are proficient in Chinese and English conversations. You provide users with safe, helpful, and accurate answers. You will reject any questions involving terrorism, racism, or explicit content. Moonshot AI is a proper noun and should not be translated.

CURRENT PROJECT STATUS:
- Repository: {assistant.session_data.get('active_repo', 'None loaded')}
- Path: {assistant.session_data.get('repo_path', 'No repository loaded')}
- Available commands: /loadrepo, /setrepo, /files, /view, /diff, /commit, /push

If a repository is loaded, you can help with code analysis, debugging, and explanations about the files in the project. The user can use /view filename to see file contents."""
                    }, {
                        "role": "user",
                        "content": user_message
                    }],
                    temperature=0.6,
                    timeout=30
                )

                ai_response = response.choices[0].message.content
            except Exception as e:
                # Fallback error handling for network issues
                logger.error(f"Kimi K2 API error: {e}")
                ai_response = f"🚀 Kimi K2 is thinking too hard! Network timeout.\n\nTry a simpler question or check your connection. Error: {str(e)[:100]}..."

        else:
            ai_response = f"{assistant.llm_type} integration not implemented yet"

        await update.message.reply_text(
            f"🤖 **{assistant.llm_type} Assistant**:\n\n{ai_response}"
        )

    except Exception as e:
        await update.message.reply_text(f"❌ AI Error: {str(e)}")

def main():
    """Main function"""
    if not assistant.telegram_token:
        logger.error("❌ TELEGRAM_BOT_TOKEN is required")
        return

    logger.info("🚀 Starting Personal Code Assistant...")

    # Create application
    application = Application.builder().token(assistant.telegram_token).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("loadrepo", load_repo))
    application.add_handler(CommandHandler("setrepo", set_repo))
    application.add_handler(CommandHandler("files", files))
    application.add_handler(CommandHandler("view", view_file))
    application.add_handler(CommandHandler("edit", edit_file))
    application.add_handler(CommandHandler("git_status", git_status))
    application.add_handler(CommandHandler("diff", diff))
    application.add_handler(CommandHandler("commit", commit))
    application.add_handler(CommandHandler("push", push))
    application.add_handler(CommandHandler("status", status))

    # Add message handler for AI assistance
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("✅ Personal Code Assistant ready!")

    # Start bot
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"💥 Bot crashed: {e}")
        import traceback
        traceback.print_exc()