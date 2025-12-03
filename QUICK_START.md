# 🚀 Quick Start Guide

**Get your personal code assistant running in 2 minutes!**

## Step 1: Create Your Bot (30 seconds)
1. Open Telegram → Search **@BotFather**
2. Send: `/newbot`
3. Name: "My Code Bot"
4. Username: "MyCodeBot" (must end in 'bot')
5. **Copy the TOKEN** it gives you

## Step 2: Clone & Setup (1 minute)
```bash
git clone https://github.com/digitaladaption/telegram-claude-code-bot.git
cd telegram-claude-code-bot

# Create your .env file
nano .env
```

Paste this into your `.env` file:
```bash
TELEGRAM_BOT_TOKEN=paste_your_token_here
# Choose ONE AI model:
ANTHROPIC_API_KEY=your_claude_key_here
# OR
OPENAI_API_KEY=your_openai_key_here
# OR
MOONSHOT_API_KEY=your_kimi_k2_key_here
GITHUB_TOKEN=your_github_token_here
```

## Step 3: Install & Start (30 seconds)
```bash
pip install -r requirements.txt
python3 personal_bot.py
```

## That's it! 🎉

Now open Telegram and talk to your bot:

### Try these commands:
```
/start
/loadrepo microsoft/vscode
/files
/view README.md
```

### Get AI help:
```
Explain this React hook bug

How do I optimize this SQL query?

Add error handling to this Python function
```

You now have **Cursor in your pocket**! 📱✨

---

**Your bot, your code, your keys - completely private!**