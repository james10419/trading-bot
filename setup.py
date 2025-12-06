import os
import sys
import subprocess

def install_dependencies():
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully.")
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies. Please check your internet connection or requirements.txt.")
        sys.exit(1)

def create_env_file():
    print("\n🔑 Configuration Setup")
    print("Enter your API keys. Press Enter to skip if you don't have them yet (Paper Trading works without keys for public data).")
    
    upbit_access = input("Upbit Access Key: ").strip()
    upbit_secret = input("Upbit Secret Key: ").strip()
    telegram_token = input("Telegram Bot Token: ").strip()
    telegram_chat_id = input("Telegram Chat ID: ").strip()
    rapidapi_key = input("RapidAPI Key (Optional, for Sentiment): ").strip()

    env_content = f"""# Exchange Keys
UPBIT_ACCESS_KEY={upbit_access}
UPBIT_SECRET_KEY={upbit_secret}

# Notifications
TELEGRAM_BOT_TOKEN={telegram_token}
TELEGRAM_CHAT_ID={telegram_chat_id}

# Market Intelligence
RAPIDAPI_KEY={rapidapi_key}
"""

    with open(".env", "w", encoding="utf-8") as f:
        f.write(env_content)
    
    print("\n✅ .env file created successfully.")

def main():
    print("=======================================")
    print("   🤖 Trading Bot Setup Assistant")
    print("=======================================")
    
    if not os.path.exists("requirements.txt"):
        print("❌ Error: requirements.txt not found!")
        return

    install_dependencies()
    
    if os.path.exists(".env"):
        overwrite = input("\n⚠️  .env file already exists. Overwrite? (y/N): ").lower()
        if overwrite == 'y':
            create_env_file()
        else:
            print("Skipping configuration.")
    else:
        create_env_file()

    print("\n🎉 Setup Complete!")
    print("Run 'python main.py' to start the bot.")

if __name__ == "__main__":
    main()
