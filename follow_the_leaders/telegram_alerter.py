import requests
from typing import Optional
import threading
import time

from follow_the_leaders.secret_vars import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from follow_the_leaders._logger import log_info, log_error, log_debug


class TelegramAlerter:
    def __init__(self, bot_token: str, chat_id: str, auto_listen: bool = True):
        """Simple Telegram alert sender with HTML formatting support."""
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        self.update_url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        self.last_update_id = None  # track latest message to avoid duplicates

        if auto_listen:
            listener_thread = threading.Thread(
                target=self.poll_for_commands, daemon=True
            )
            listener_thread.start()
            log_info("TelegramAlerter :: Started background listener thread")

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
            log_debug(f"TelegramAlerter :: Posting message: {payload}")
            response = requests.post(self.api_url, data=payload, timeout=10)
            if response.status_code == 200:
                return True
            else:
                log_error(
                    f"TelegramAlerter :: Telegram API ERROR: {response.status_code} {response.text}"
                )
                return False
        except requests.RequestException as e:
            log_error(f"TelegramAlerter :: Telegram request failed: {e}")
            return False

    def poll_for_commands(self, interval: int = 30):
        """
        Poll Telegram every `interval` seconds for new messages.
        Responds automatically to 'alive' or '/alive'.
        """
        log_info("TelegramAlerter :: Listening for commands...")

        while True:
            try:
                params = {"timeout": 10}
                if self.last_update_id:
                    params["offset"] = self.last_update_id + 1

                response = requests.get(self.update_url, params=params, timeout=20)
                response.raise_for_status()
                data = response.json()

                if not data.get("ok"):
                    log_error(f"TelegramAlerter :: getUpdates returned error: {data}")
                    time.sleep(interval)
                    continue

                for update in data.get("result", []):
                    self.last_update_id = update["update_id"]

                    message = update.get("message", {})
                    chat_id = message.get("chat", {}).get("id")
                    text = (message.get("text") or "").strip().lower()

                    if not chat_id or not text:
                        continue

                    log_info(f"TelegramAlerter :: Received message: '{text}'")

                    # Simple health check response
                    if text.lower() in (
                        "alive",
                        "/alive",
                        "status",
                        "/status",
                    ):
                        self.send_message("✅ <b>Yes, still monitoring...</b>")
                        log_info("TelegramAlerter :: Responded to alive check")

                time.sleep(interval)

            except Exception as e:
                log_error(f"TelegramAlerter :: Polling error: {e}")
                time.sleep(interval)


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

    # Start listening for 'alive' messages
    alerter.poll_for_commands(interval=30)
    return 0


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
