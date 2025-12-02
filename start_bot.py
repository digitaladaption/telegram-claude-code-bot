#!/usr/bin/env python3
"""
Bot launcher script with proper environment setup
"""

import os
import sys
import subprocess
from pathlib import Path

def setup_environment():
    """Setup necessary directories and environment"""
    # Create required directories
    directories = ['logs', 'data', 'configs']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)

    # Check if .env exists
    if not Path('.env').exists():
        print("❌ .env file not found!")
        print("Please copy .env.example to .env and configure it:")
        print("cp .env.example .env")
        return False

    return True

def install_dependencies():
    """Install required Python packages"""
    try:
        print("📦 Installing dependencies...")
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'],
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Dependencies installed successfully")
            return True
        else:
            print(f"❌ Failed to install dependencies: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

def check_claude_cli():
    """Check if Claude CLI is available"""
    try:
        result = subprocess.run(['claude', '--version'],
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ Claude CLI found: {result.stdout.strip()}")
            return True
        else:
            print("❌ Claude CLI not working properly")
            return False
    except subprocess.TimeoutExpired:
        print("❌ Claude CLI check timed out")
        return False
    except FileNotFoundError:
        print("❌ Claude CLI not found")
        print("Please install Claude CLI first: https://claude.ai/cli")
        return False
    except Exception as e:
        print(f"❌ Error checking Claude CLI: {e}")
        return False

def main():
    """Main launcher function"""
    print("🚀 Telegram Claude Code Bot Launcher")
    print("=" * 50)

    # Setup environment
    if not setup_environment():
        sys.exit(1)

    # Install dependencies
    if not install_dependencies():
        sys.exit(1)

    # Check Claude CLI
    if not check_claude_cli():
        print("\n⚠️  Claude CLI is not available, but the bot can still start")
        print("You'll need Claude CLI to execute coding tasks.")

    # Start the bot
    print("\n🤖 Starting Telegram bot...")
    try:
        # Import and run the bot
        from main import main as bot_main
        import asyncio
        asyncio.run(bot_main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"\n💥 Bot failed to start: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()