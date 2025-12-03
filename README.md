# 🤖 Telegram Claude Code Bot

A powerful Telegram bot that allows you to interact with Claude Code CLI directly from your Telegram messages. This bot enables remote coding, file management, and AI-powered development assistance through Telegram's intuitive interface.

## ✨ Features

### 🚀 Core Functionality
- **Claude CLI Integration**: Execute coding tasks using Claude's powerful AI
- **Session Management**: Create and manage coding sessions per user
- **File Operations**: List, create, and manage files in working directories
- **Real-time Responses**: Get immediate feedback on your coding tasks

### 🛡️ Security & Administration
- **User Access Control**: Restrict bot access to authorized users
- **Admin Commands**: Advanced administrative features
- **Session Persistence**: Automatic session saving and recovery
- **Command Validation**: Built-in security for dangerous commands

### 📱 Telegram Features
- **Markdown Formatting**: Beautiful code blocks and formatted responses
- **Inline Keyboards**: Quick action buttons for common operations
- **Typing Indicators**: Visual feedback when bot is processing
- **Error Handling**: Clear error messages and suggestions

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.8 or higher
- Claude CLI installed and configured
- Telegram Bot Token (create via @BotFather)
- Server with internet access (for webhook)

### 2. Installation

```bash
# Clone the repository
git clone <repository-url>
cd py-telegram2cc

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env

# Edit configuration
nano .env
```

### 3. Configuration

Edit `.env` file with your settings:

```bash
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Optional
TELEGRAM_WEBHOOK_URL=https://your-server.com/webhook/telegram
ALLOWED_USERS=123456789,987654321  # Comma-separated user IDs
ADMIN_USERS=123456789  # Admin user IDs
DEFAULT_WORKING_DIR=/root/projects
LOG_LEVEL=INFO
```

### 4. Start the Bot

```bash
# Create logs directory
mkdir -p logs

# Start the bot
python main.py
```

## 📖 Usage Guide

### Basic Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the bot and get welcome message |
| `/help` | Show all available commands |
| `/start_session [dir]` | Create new coding session (optional working directory) |
| `/session_info` | Show current session details |
| `/end_session` | End current coding session |
| `/list_files` | List files in working directory |
| `/status` | Show bot status and your session info |

### Coding Tasks

Simply send any coding request as a regular message:

```
Create a Python script that scrapes weather data from an API

Fix this bug in my React component where the state isn't updating

Write a SQL query to find all users who registered in the last 30 days

Explain how to implement authentication in a Node.js application
```

### Admin Commands

| Command | Description |
|---------|-------------|
| `/admin_stats` | Show global bot statistics |
| `/admin_sessions` | List all sessions with details |

## 🏗️ Architecture

### Project Structure
```
py-telegram2cc/
├── main.py                     # Entry point
├── session_manager.py          # Session management
├── services/
│   └── bot_service.py         # Main bot logic
├── src/telegram_bot/
│   ├── bot/
│   │   └── client.py          # Telegram client
│   └── command/
│       └── claude_cli_executor.py  # Claude CLI integration
├── configs/                    # Configuration files
├── data/                       # Session storage
└── logs/                       # Log files
```

### Core Components

1. **TelegramClient**: Handles all Telegram messaging
2. **SessionManager**: Manages user sessions and data persistence
3. **ClaudeCliExecutor**: Executes commands via Claude CLI
4. **BotService**: Main bot logic and command handling

## 🔧 Advanced Configuration

### Working Directories

Each session has its own working directory. By default:
- Individual sessions: `/root/projects/session_<token>`
- Custom directories: `/start_session /path/to/my/project`

### Security Features

- **Command Validation**: Blocks dangerous system commands
- **User Access Control**: Optional user ID restrictions
- **Session Isolation**: Each user works in their own environment
- **Timeout Protection**: Commands limited to 3 minutes

### Session Persistence

Sessions are automatically saved to `data/sessions.json` and:
- Survive bot restarts
- Include user metadata and working directory
- Auto-expire after 24 hours of inactivity
- Can be manually ended with `/end_session`

## 🐛 Troubleshooting

### Common Issues

**Bot doesn't start:**
- Check `TELEGRAM_BOT_TOKEN` is correct
- Verify internet connection
- Check logs in `logs/telegram_bot.log`

**Claude CLI not working:**
- Ensure Claude CLI is installed: `claude --version`
- Check Claude CLI authentication
- Verify working directory permissions

**Session not found:**
- Create new session with `/start_session`
- Check session hasn't expired (24 hours)
- Verify you're using the correct user account

### Debug Mode

Enable debug logging by setting `LOG_LEVEL=DEBUG` in `.env`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Original inspiration from [py-feishu2cc](https://github.com/GeekQianJi-Lab/py-feishu2cc)
- [python-telegram-bot](https://python-telegram-bot.org/) for excellent Telegram library
- Claude Code team for the powerful CLI tool
- OpenAI for the Claude API

## 📞 Support

For support:
- Create an issue in the repository
- Check the troubleshooting section
- Review the logs for detailed error messages

---

**Happy Coding! 🚀**Edited with Telgram
