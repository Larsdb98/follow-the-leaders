import requests
from typing import Optional

from follow_the_leaders.secret_vars import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


class TelegramAlerter:
    def __init__(self, bot_token: str, chat_id: str):
        """Simple Telegram alert sender with HTML formatting support."""
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    @staticmethod
    def escape_html(text: str) -> str:
        """Escape HTML special characters for safe variable interpolation."""
        if text is None:
            return ""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def send_message(
        self,
        text: str,
        parse_mode: Optional[str] = "HTML",
        disable_web_page_preview: bool = True,
        protect_content: bool = False,
    ) -> bool:
        """Send an HTML-formatted message to Telegram."""
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview,
            "protect_content": protect_content,
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


# ─────────────────────────────────────────────
# 🧪 Example Test
# ─────────────────────────────────────────────
def main() -> int:
    alerter = TelegramAlerter(bot_token=TELEGRAM_BOT_TOKEN, chat_id=TELEGRAM_CHAT_ID)

    msg = (
        "<b>🚀 New Trade Signal Detected!</b>\n"
        "<b>Instrument:</b> NVDA\n"
        "<b>Signal:</b> 13F New Buy\n"
        "<b>Confidence:</b> High\n"
        "<b>Backtest Return:</b> +12.3%\n\n"
        "<i>Generated automatically by FollowTheLeaders</i>\n"
        "<u>This is ONLY a test!</u>"
    )

    alerter.send_message(msg)
    return 0


if __name__ == "__main__":
    main()
