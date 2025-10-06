from follow_the_leaders import (
    TelegramAlerter,
    Form13FComparator,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)

import pandas as pd
from datetime import datetime, timedelta
import time
from typing import Optional


class Controller:
    def __init__(
        self,
        funds_csv_path: str,
        telegram_bot_token: str,
        telegram_chat_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ):
        """
        Controller to orchestrate daily 13F fetching, comparison, and alerts.
        """
        self.funds_csv_path = funds_csv_path
        self.start_date = start_date
        self.end_date = end_date

        # Load active funds
        self.funds_df = pd.read_csv(self.funds_csv_path, dtype=str)
        self.funds_df = self.funds_df[self.funds_df["active"].str.lower() == "true"]

        # Initialize Telegram alerter
        self.alerter = TelegramAlerter(
            bot_token=telegram_bot_token, chat_id=telegram_chat_id
        )

    def process_fund(self, cik: str, fund_name: str):
        """
        Fetch and compare last two filings for one fund.
        Sends an alert only if the latest filing is from today or yesterday.
        """
        try:
            comparator = Form13FComparator(
                cik, start_date=self.start_date, end_date=self.end_date
            )
            results = comparator.compare_filings()

            latest_date_str = results["latest_date"]
            latest_date = datetime.strptime(latest_date_str, "%Y-%m-%d")

            # Only alert if the filing is from today or yesterday
            today = datetime.now()
            delta_days = (today.date() - latest_date.date()).days
            if delta_days > 1:
                print(
                    f"Skipping {fund_name} ({cik}) — latest filing is from {latest_date_str} ({delta_days} days ago)."
                )
                return

            msg = f"📊 *13F Update for {fund_name}*\n"
            msg += (
                f"Comparing {results['previous_date']} ➝ {results['latest_date']}\n\n"
            )

            new_buys = results["new_buys"]
            exits = results["exits"]

            if not new_buys.empty:
                msg += f"🟢 *New Buys ({len(new_buys)})*\n"
                for _, row in new_buys.head(5).iterrows():  # limit to top 5
                    msg += f"• {row['issuer']} (${row['value_usd']:,})\n"
                if len(new_buys) > 5:
                    msg += f"...and {len(new_buys) - 5} more.\n"

            if not exits.empty:
                msg += f"\n❌ *Exits ({len(exits)})*\n"
                for _, row in exits.head(5).iterrows():
                    msg += f"• {row['issuer']}\n"
                if len(exits) > 5:
                    msg += f"...and {len(exits) - 5} more.\n"

            if new_buys.empty and exits.empty:
                msg += "_No new buys or exits detected._"

            msg += "\n\n🕒 Automated scan completed."

            # Hellooo telegram Bot
            self.alerter.send_message(msg)

        except Exception as e:
            err_msg = f"⚠️ Error processing {fund_name} (CIK {cik}): {e}"
            print(err_msg)
            self.alerter.send_message(err_msg, parse_mode=None)

    def run_daily_check(self):
        """
        Loop over all funds and process them.
        Only sends alerts for filings that appeared today or yesterday.
        """
        print(
            f"Starting daily 13F check — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        for _, row in self.funds_df.iterrows():
            cik = row["cik"]
            fund_name = row["fund_name"]
            print(f"→ Checking {fund_name} ({cik})...")
            self.process_fund(cik, fund_name)

            time.sleep(30)
        print("✅ Daily check completed.")


def main():
    controller = Controller(
        funds_csv_path="funds_watchlist.csv",
        telegram_bot_token=TELEGRAM_BOT_TOKEN,
        telegram_chat_id=TELEGRAM_CHAT_ID,
        start_date=None,  # datetime(2024, 1, 1),
        end_date=None,  # datetime(2025, 12, 31),
    )

    controller.run_daily_check()


if __name__ == "__main__":
    main()
