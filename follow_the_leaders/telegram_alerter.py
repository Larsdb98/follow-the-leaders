import requests
import re
from typing import Optional

from follow_the_leaders.secret_vars import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


class TelegramAlerter:
    def __init__(self, bot_token: str, chat_id: str):
        """
        Parameters
        ----------
        bot_token : str
            Your Telegram bot token (from @BotFather)
        chat_id : str
            Your Telegram chat ID (from getUpdates)
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def _escape_markdown(self, text: str) -> str:
        """Escape Telegram Markdown special characters."""
        escape_chars = r"_*[]()~`>#+-=|{}.!"
        return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)

    def send_message(self, text: str, parse_mode: Optional[str] = "Markdown") -> bool:
        """
        Send a message to your Telegram chat.
        Returns True if successful, False otherwise.
        """
        safe_markdown_text = self._escape_markdown(text=text)
        payload = {
            "chat_id": self.chat_id,
            "text": safe_markdown_text,
            "parse_mode": parse_mode,
        }

        try:
            response = requests.post(self.api_url, data=payload, timeout=10)
            if response.status_code == 200:
                return True
            else:
                print(f"Telegram API ERROR: {response.status_code} {response.text}")
                return False
        except requests.RequestException as e:
            print(f"Telegram request failed: {e}")
            return False


def main() -> int:
    alerter = TelegramAlerter(bot_token=TELEGRAM_BOT_TOKEN, chat_id=TELEGRAM_CHAT_ID)

    msg = (
        "*New Trade Signal Detected!*\n"
        "Instrument: NVDA\n"
        "Signal: 13F new buy\n"
        "Confidence: High\n"
        "Backtest Return: +12.3%\n"
        "_Generated automatically by FollowTheLeaders \n"
        "This is ONLY a test !"
    )

    alerter.send_message(msg)


if __name__ == "__main__":
    main()
