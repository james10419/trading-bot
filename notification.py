import os
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

class NotificationManager:
    """Class to manage Telegram notifications."""
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if self.token and self.chat_id:
            logging.info("Telegram notifications enabled.")
        else:
            logging.warning("Telegram token or Chat ID not set. Notifications disabled.")

    def send_message(self, message):
        """Sends a message via Telegram."""
        if not self.token or not self.chat_id:
            return

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        params = {'chat_id': self.chat_id, 'text': message}
        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            logging.info("Telegram message sent successfully.")
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to send Telegram message: {e}")
