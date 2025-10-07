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


class ControllerNew:
    def __init__(
        self,
        funds_csv_path: str,
        telegram_bot_token: str,
        telegram_chat_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        log_path: str = "data/processed_filings.csv",
    ):
        """
        Controller to orchestrate daily filings fetching and alerts.
        """
        self.funds_csv_path = funds_csv_path
        self.start_date = start_date
        self.end_date = end_date
        self.tracker = FilingTracker(log_path)

        # Load active entities
        self.funds_df = pd.read_csv(self.funds_csv_path, dtype=str)
        self.funds_df = self.funds_df[self.funds_df["active"].str.lower() == "true"]

        # Initialize Telegram alerter
        self.alerter = TelegramAlerter(
            bot_token=telegram_bot_token, chat_id=telegram_chat_id
        )

    # ─────────────────────────────────────────────
    # Process Fund (13F filings)
    # ─────────────────────────────────────────────
    def process_fund(self, cik: str, fund_name: str):
        """Handle Form 13F for funds."""
        try:
            comparator = Form13FComparator(
                cik, start_date=self.start_date, end_date=self.end_date
            )
            results = comparator.compare_filings()

            latest_date_str = results["latest_date"]
            latest_date = datetime.strptime(latest_date_str, "%Y-%m-%d")
            accession_number = getattr(comparator, "latest_accession", "unknown")

            # Skip if already processed
            if not self.tracker.is_new_filing(cik, "13F-HR", accession_number):
                print(f"Skipping {fund_name} ({cik}) — already processed this filing.")
                return

            # Skip old filings (>1 day)
            if (datetime.now().date() - latest_date.date()).days > 1:
                print(f"Skipping {fund_name} — filing too old ({latest_date_str}).")
                return

            # Compose message
            msg = f"📊 *13F Update for {fund_name}*\n"
            msg += (
                f"Comparing {results['previous_date']} ➝ {results['latest_date']}\n\n"
            )

            new_buys = results["new_buys"]
            exits = results["exits"]

            if not new_buys.empty:
                msg += f"🟢 *New Buys ({len(new_buys)})*\n"
                for _, row in new_buys.head(5).iterrows():
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
            self.alerter.send_message(msg)
            self.tracker.log_filing(cik, "13F-HR", accession_number, latest_date_str)

        except Exception as e:
            err_msg = f"⚠️ Error processing {fund_name} (CIK {cik}): {e}"
            print(err_msg)
            self.alerter.send_message(err_msg, parse_mode=None)

    # ─────────────────────────────────────────────
    # Process Company (Forms 4 and 144)
    # ─────────────────────────────────────────────
    def process_company(self, cik: str, company_name: str):
        """Handle Forms 4 and 144 for public companies."""
        try:
            fetcher = FilingsFetcher(cik)

            for form_type in ["4", "144"]:
                filings = fetcher.get_recent_filings(form_type, count=5)

                for filing in filings:
                    accession = filing["accession"]
                    filing_date = filing["filing_date"]

                    # Skip already-processed filings
                    if not self.tracker.is_new_filing(cik, form_type, accession):
                        continue

                    # Skip old filings
                    date_obj = datetime.strptime(filing_date, "%Y-%m-%d")
                    if (datetime.now().date() - date_obj.date()).days > 1:
                        continue

                    # Parse Form 4 and Form 144 differently
                    if form_type == "4":
                        df = fetcher.parse_form4(filing)
                        if not df.empty:
                            msg = f"🧾 *Form 4 — Insider Trades*\n🏢 {company_name}\n📅 {filing_date}\n\n"
                            for _, row in df.head(3).iterrows():
                                msg += (
                                    f"• {row['insider']} traded {row['shares']} shares "
                                    f"@ ${row['price']} on {row['transaction_date']}\n"
                                )
                            if len(df) > 3:
                                msg += f"...and {len(df) - 3} more transactions.\n"
                            self.alerter.send_message(msg)
                    elif form_type == "144":
                        df = fetcher.parse_form144(filing)
                        msg = (
                            f"📜 *Form 144 — Insider Sale Notice*\n🏢 {company_name}\n"
                            f"📅 {filing_date}\n🔗 {df['filing_url'].iloc[0]}"
                        )
                        self.alerter.send_message(msg)

                    # Log after alert
                    self.tracker.log_filing(cik, form_type, accession, filing_date)

        except Exception as e:
            err_msg = f"⚠️ Error processing {company_name} (CIK {cik}): {e}"
            print(err_msg)
            self.alerter.send_message(err_msg, parse_mode=None)

    # ─────────────────────────────────────────────
    # Main Daily Runner
    # ─────────────────────────────────────────────
    def run_daily_check(self):
        """Iterate over funds & companies, processing filings."""
        print(f"Starting daily filings check — {datetime.now():%Y-%m-%d %H:%M:%S}")
        for _, row in self.funds_df.iterrows():
            cik = row["cik"]
            name = row["fund_name"]
            entity_type = row.get("entity_type", "fund").lower()

            print(f"→ Checking {name} ({cik}) as {entity_type}...")
            if entity_type == "fund":
                self.process_fund(cik, name)
            elif entity_type == "company":
                self.process_company(cik, name)

            # Avoid hammering SEC API
            time.sleep(15)
        print("✅ Daily check completed.")


def main():
    # controller = Controller(
    #     funds_csv_path="funds_watchlist.csv",
    #     telegram_bot_token=TELEGRAM_BOT_TOKEN,
    #     telegram_chat_id=TELEGRAM_CHAT_ID,
    #     start_date=None,  # datetime(2024, 1, 1),
    #     end_date=None,  # datetime(2025, 12, 31),
    # )

    # controller.run_daily_check()


if __name__ == "__main__":
    main()
