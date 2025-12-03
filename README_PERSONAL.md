# 🤖 Personal Telegram Code Assistant

A private Telegram bot that lets you control your code repositories from your phone. **Your bot, your keys, your code.**

> **No cloud services, no OAuth, no multi-user complexity.** Just a personal assistant that runs on your machine and gives you phone access to your development workflow.

## ✨ What It Does

**Repository Management:**
- `/loadrepo owner/repo` - Clone any GitHub repo
- `/setrepo /path/to/local/repo` - Use local repos directly
- `/files` - Browse your codebase with emoji icons
- `/view filename.py` - View any file

**AI-Powered Coding:**
- Explain errors: *"Why is this React component not re-rendering?"*
- Refactor code: *"Make this Python function more efficient"*
- Add features: *"Add user authentication to this Express.js route"*
- Debug issues: *"Fix this SQL query that's returning duplicate rows"*

**Git Operations:**
- `/diff` - See what you've changed
- `/commit "message"` - Commit changes with AI-generated messages
- `/push` - Push to GitHub
- Full git workflow from your phone

## 🚀 5-Minute Setup

### Step 1: Create Your Telegram Bot
1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Name it something like "My Code Bot"
4. Get your **TELEGRAM_BOT_TOKEN**

### Step 2: Clone This Repo
```bash
git clone https://github.com/digitaladaption/telegram-claude-code-bot.git
cd telegram-claude-code-bot
```

### Step 3: Configure Your Bot
Create a `.env` file:
```bash
# Required - Your bot token from @BotFather
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Required - Your LLM API key (choose one)
ANTHROPIC_API_KEY=your_claude_key_here
# OR
OPENAI_API_KEY=your_openai_key_here

# Optional - For cloning GitHub repos via HTTPS
GITHUB_TOKEN=your_github_pat_here
```

### Step 4: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 5: Start Your Bot
```bash
python3 complete_cursor_bot.py
```

## 📱 Using Your Bot

### Load a Repository
```
/loadrepo microsoft/vscode
```
OR use a local repo:
```
/setrepo /home/user/my-project
```

### Browse Your Code
```
/files
```
📁 src/
  📄 app.js
  📁 components/
    📄 Button.tsx

/view src/components/Button.tsx
```

### Get AI Help
```
Explain this error: TypeError: Cannot read property 'map' of undefined

Refactor /src/utils/validation.js to be more readable

Add dark mode support to this React component
```

### Make Changes
```
/edit src/utils/api.js
# Bot shows you the file content, you reply with changes

# See what changed
/diff

# Commit with smart message
/commit "Fix API validation bug"

# Push to GitHub
/push
```

## 🏗️ How It Works

**Architecture:**
```
Your Phone (Telegram) ←→ Your Bot (Running on your machine) ←→ Your Code + LLM APIs
```

**What happens where:**
- **Telegram**: Just shows the chat interface
- **Your Machine**: All the real work (git, file operations, LLM calls)
- **LLM APIs**: Processes your coding requests
- **Your Repos**: Local files or GitHub clones

**Two ways to access your code:**

1. **Local repos**: Point to existing directories on your machine
2. **GitHub repos**: Clone them temporarily to your machine

## 🔧 Configuration Options

### Environment Variables
```bash
# Required
TELEGRAM_BOT_TOKEN=your_token
# Choose ONE LLM API key:
ANTHROPIC_API_KEY=your_claude_key_here
# OR
OPENAI_API_KEY=your_openai_key_here
# OR
MOONSHOT_API_KEY=your_kimi_k2_key_here

# Optional
GITHUB_TOKEN=github_pat_for_https_cloning
DEFAULT_WORKSPACE=/tmp/telegram_bot_workspaces
LOG_LEVEL=INFO
```

### Repository Access Methods

**Method 1: Local Directories** (Fast, no network needed)
```
/setrepo /Users/john/projects/my-app
/setrepo C:\Users\John\Documents\my-website
```

**Method 2: GitHub Clone** (Requires GITHUB_TOKEN)
```
/loadrepo facebook/react
/loadrepo https://github.com/microsoft/vscode
```

## 🛡️ Security & Privacy

✅ **Private**: Your code never leaves your machine
✅ **Secure**: Only you have access to your bot
✅ **Encrypted**: All Telegram messages are encrypted
✅ **Controlled**: Your API keys, your tokens

**No cloud services, no data sharing, no third parties.**

## 📋 Command Reference

### Repository Commands
| Command | What it does |
|---------|--------------|
| `/loadrepo owner/repo` | Clone GitHub repo to work on |
| `/setrepo /path/to/repo` | Use existing local repository |
| `/files [path]` | Browse files with tree view |
| `/view filename` | View any file contents |

### Git Commands
| Command | What it does |
|---------|--------------|
| `/diff` | Show unstaged changes |
| `/commit "message"` | Commit changes |
| `/push` | Push to remote branch |
| `/pull` | Pull latest changes |

### AI Commands
| Command | What it does |
|---------|--------------|
| Just send any coding request as a message |
| `/explain` | Get AI explanation of selected code |
| `/refactor` | Ask AI to improve code |
| `/debug` | Get help fixing bugs |

### Supported AI Models

**🤖 Available LLMs:**
- **Claude (Anthropic)** - Excellent reasoning and coding
- **GPT-4 (OpenAI)** - Great all-around coding assistant
- **Kimi K2 (Moonshot AI)** - Powerful Chinese-English bilingual model

**How it works:**
- The bot automatically detects which API key you configure
- Set only ONE LLM API key in your `.env` file
- Each model offers different strengths for coding tasks

## 🐛 Troubleshooting

**Bot doesn't start:**
- Check your TELEGRAM_BOT_TOKEN is correct
- Verify the token has no extra spaces

**LLM not responding:**
- Check ANTHROPIC_API_KEY or OPENAI_API_KEY
- Verify you have credits/usage available

**Git operations fail:**
- Add GITHUB_TOKEN for HTTPS cloning
- Check repo URLs are correct
- Verify write permissions for commits

**File not found:**
- Use `/files` to see available files
- Check your current repo with `/status`

## 🎯 Examples

### Debugging Session
```
You: My React app shows "Cannot read property 'state' of undefined"

Bot: I can help! Which component is causing the issue?
Can you show me the error location or share the component code?

You: /view src/components/UserProfile.tsx

Bot: [Analyzes the file] The issue is that you're trying to access
this.state in a functional component. Here's the fix...

You: /edit src/components/UserProfile.tsx
[Make the changes]

Bot: Changes saved! Use /diff to review, then /commit to save.
```

### Feature Development
```
You: Add user authentication to this Express.js route

Bot: I'll help you add JWT authentication to protect your API endpoints.
Here's what I'll implement:

1. Install required packages
2. Create auth middleware
3. Add login/logout routes
4. Protect existing endpoints

Should I proceed with this implementation?
```

## 🚀 Next Steps

Once you're comfortable:
- Add custom commands for your workflow
- Integrate with your deployment scripts
- Set up multiple workspaces for different projects
- Add team members to your private bot (if desired)

---

**That's it!** You now have a personal coding assistant that works from your phone.

**Happy coding from anywhere! 📱✨**