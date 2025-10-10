from follow_the_leaders import (
    TelegramAlerter,
    Form13FComparator,
    FilingsFetcher,
    FilingTracker,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    ROOT_PATH,
    configure_logger,
    log_info,
    log_debug,
    log_error,
    log_fatal,
)

import pandas as pd
from datetime import datetime
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
        log_path: str = "data/processed_filings.csv",
        debug: bool = False,
    ):
        """Controller to orchestrate daily filings fetching and alerts."""
        self.funds_csv_path = funds_csv_path
        self.start_date = start_date
        self.end_date = end_date
        self.tracker = FilingTracker(log_path)
        self.debug = debug

        # Load active entities
        self.funds_df = pd.read_csv(self.funds_csv_path, dtype=str)
        self.funds_df = self.funds_df[self.funds_df["active"].str.lower() == "true"]

        # Initialize Telegram alerter
        self.alerter = TelegramAlerter(
            bot_token=telegram_bot_token, chat_id=telegram_chat_id
        )

        if self.debug:
            log_info(
                "Controller :: DEBUG MODE ENABLED — No skipping of old or processed filings.\n"
            )

        log_info("Controller :: Initiated successfully")

    # ─────────────────────────────────────────────
    # Process Form 13F — institutional holdings
    # ─────────────────────────────────────────────
    def process_fund(self, cik: str, fund_name: str):
        """Handle Form 13F filings (fund holdings updates)."""
        try:
            comparator = Form13FComparator(
                cik, start_date=self.start_date, end_date=self.end_date
            )
            results = comparator.compare_filings()

            latest_date_str = results["latest_date"]
            latest_date = datetime.strptime(latest_date_str, "%Y-%m-%d")
            accession_number = getattr(comparator, "latest_accession", "unknown")

            # Skip if already processed (unless debug mode)
            if not self.debug and not self.tracker.is_new_filing(
                cik, "13F-HR", accession_number
            ):
                log_info(
                    f"Skipping {fund_name} ({cik}) — already processed this filing."
                )
                return

            # Skip old filings (>1 day)
            if not self.debug and (datetime.now().date() - latest_date.date()).days > 1:
                log_info(f"Skipping {fund_name} — filing too old ({latest_date_str}).")
                return

            msg = (
                f"<b>📊 13F Update for {fund_name}</b>\n"
                f"<b>Comparing:</b> {results['previous_date']} → {results['latest_date']}\n\n"
            )
            log_msg = (
                f"13F Update for {fund_name}\n"
                f"Comparing: {results['previous_date']} -> {results['latest_date']}\n\n"
            )

            new_buys = results["new_buys"].copy()
            exits = results["exits"].copy()

            # Convert reported value (in thousands) to actual dollars
            if "value_usd" in new_buys.columns:
                new_buys["value_usd"] = new_buys["value_usd"].astype(float) / 1000
            if "value_usd" in exits.columns:
                exits["value_usd"] = exits["value_usd"].astype(float) / 1000

            # 🟢 New buys
            if not new_buys.empty:
                msg += f"<b>🟢 New Buys ({len(new_buys)})</b>\n"
                log_msg += f"New Buys ({len(new_buys)})\n"

                for _, row in new_buys.iterrows():
                    issuer = row.get("issuer", "Unknown")
                    value_usd = row.get("value_usd", 0.0)
                    shares = row.get("shares", 0)

                    msg += f"• {issuer} — {shares:,} shares (${value_usd:,.0f})\n"
                    log_msg += f"+ {issuer} — {shares:,} shares (${value_usd:,.0f})\n"

            # ❌ Exits
            if not exits.empty:
                msg += f"\n<b>❌ Exits ({len(exits)})</b>\n"
                log_msg += f"\nExits ({len(exits)})\n"

                for _, row in exits.iterrows():
                    issuer = row.get("issuer", "Unknown")
                    value_usd = row.get("value_usd", 0.0)
                    shares = row.get("shares", 0)

                    msg += f"• {issuer} — {shares:,} shares (${value_usd:,.0f})\n"
                    log_msg += f"+ {issuer} — {shares:,} shares (${value_usd:,.0f})\n"

            # No changes
            if new_buys.empty and exits.empty:
                msg += "<i>No new buys or exits detected.</i>\n"
                log_msg += "No new buys or exits detected.\n"

            msg += "\n<i>🕒 Automated scan completed.</i>"
            log_msg += "\nAutomated scan completed."

            log_debug(f"Controller :: Sending the following message: {msg}")
            log_info(f"Controller :: process_fund: {log_msg}")

            self.alerter.send_message(msg)
            self.tracker.log_filing(cik, "13F-HR", accession_number, latest_date_str)

        except Exception as e:
            err_msg = f"Error processing {fund_name} (CIK {cik}): {e}"
            log_error(f"Controller :: {err_msg}")
            self.alerter.send_message(f"<b>{err_msg}</b>")

    # ─────────────────────────────────────────────
    # Process Forms 4 and 144 — insider trades
    # ─────────────────────────────────────────────
    def process_company(
        self, cik: str, company_name: str, process_form_144: bool = True
    ):
        try:
            fetcher = FilingsFetcher(cik)

            for form_type in ["4", "144"]:
                filings = fetcher.get_recent_filings(form_type, count=5)

                for filing in filings:
                    accession = filing["accession"]
                    filing_date = filing["filing_date"]

                    # Skip already processed
                    if not self.debug and not self.tracker.is_new_filing(
                        cik, form_type, accession
                    ):
                        continue

                    # Skip old filings (>1 day)
                    date_obj = datetime.strptime(filing_date, "%Y-%m-%d")
                    if (
                        not self.debug
                        and (datetime.now().date() - date_obj.date()).days > 1
                    ):
                        continue

                    # Handle Form 4 filings — aggregate trades
                    if form_type == "4":
                        df = fetcher.parse_form4(filing)
                        if not df.empty:
                            # Normalize column names — different XMLs sometimes vary
                            df.columns = [c.lower().strip() for c in df.columns]

                            # Try to locate security title column
                            possible_cols = [
                                "securitytitle",
                                "security_title",
                                "issuer",
                                "name",
                            ]
                            sec_col = next(
                                (c for c in possible_cols if c in df.columns), None
                            )
                            if sec_col is None:
                                raise KeyError(
                                    "No column describing the traded security found."
                                )

                            df["shares"] = pd.to_numeric(
                                df.get("shares"), errors="coerce"
                            )
                            df["price"] = pd.to_numeric(
                                df.get("price"), errors="coerce"
                            )

                            # Aggregate total shares and weighted avg price per security
                            grouped = (
                                df.dropna(subset=["shares", "price"])
                                .groupby(sec_col)
                                .apply(
                                    lambda g: pd.Series(
                                        {
                                            "total_shares": g["shares"].sum(),
                                            "avg_price": (
                                                g["shares"] * g["price"]
                                            ).sum()
                                            / g["shares"].sum(),
                                        }
                                    ),
                                    include_groups=False,  # needed for newer versions of pandas
                                )
                                .reset_index()
                                .rename(columns={sec_col: "security"})
                            )

                            # Filter to show only external securities (different from company)
                            grouped = grouped[
                                grouped["security"]
                                .str.lower()
                                .str.contains(company_name.lower())
                                == False
                            ]

                            # If all trades are internal (own stock), still display a summary
                            msg = (
                                f"<b>🧾 Form 4 — Insider Trades</b>\n"
                                f"<b>🏢 {company_name}</b>\n"
                                f"<b>📅 {filing_date}</b>\n\n"
                            )
                            log_msg = (
                                f"Form 4 — Insider Trades\n"
                                f"{company_name}\n"
                                f"{filing_date}\n\n"
                            )

                            if grouped.empty:
                                total_shares = int(df["shares"].sum())
                                avg_price = (df["shares"] * df["price"]).sum() / df[
                                    "shares"
                                ].sum()
                                msg += (
                                    f"• <b>Own stock:</b> {total_shares:,} shares @ ${avg_price:.2f}\n"
                                    f"<i>(All trades were for {company_name}'s own stock.)</i>"
                                )
                                log_msg += (
                                    f"+ Own stock: {total_shares:,} shares @ ${avg_price:.2f}\n"
                                    f"(All trades were for {company_name}'s own stock.)"
                                )

                            else:
                                for _, row in grouped.iterrows():
                                    msg += (
                                        f"• <b>{row['security']}</b>: "
                                        f"{int(row['total_shares']):,} shares "
                                        f"@ ${row['avg_price']:.2f}\n"
                                    )
                                    log_msg += (
                                        f"+ {row['security']}: "
                                        f"{int(row['total_shares']):,} shares "
                                        f"@ ${row['avg_price']:.2f}\n"
                                    )

                            log_debug(f"Controller :: Sending the following message: ")
                            log_info(f"Controller :: process_company: {log_msg}")
                            self.alerter.send_message(msg)

                    # Handle Form 144 filings — simpler link alert
                    elif form_type == "144" and process_form_144:
                        df = fetcher.parse_form144(filing)
                        msg = (
                            f"<b>📜 Form 144 — Insider Sale Notice</b>\n"
                            f"<b>🏢 {company_name}</b>\n"
                            f"<b>📅 {filing_date}</b>\n"
                            f"🔗 <a href='{df['filing_url'].iloc[0]}'>View filing</a>"
                        )
                        log_msg = (
                            f"Form 144 — Insider Sale Notice\n"
                            f"{company_name}\n"
                            f"{filing_date}\n"
                            f"'{df['filing_url'].iloc[0]}'"
                        )

                        log_debug(f"Controller :: Sending the following message:")
                        log_info(f"Controller :: process_company: {log_msg}")
                        self.alerter.send_message(msg)

                    # Log after successful alert
                    self.tracker.log_filing(cik, form_type, accession, filing_date)

        except Exception as e:
            err_msg = f"⚠️ Error processing {company_name} (CIK {cik}): {e}"
            log_error(f"Controller :: {err_msg}")
            self.alerter.send_message(f"<b>{err_msg}</b>")

    # ─────────────────────────────────────────────
    # Main runner
    # ─────────────────────────────────────────────
    def run_daily_check(self, process_form_144: bool = False):
        log_info(
            f"Controller :: Starting daily filings check — {datetime.now():%Y-%m-%d %H:%M:%S}"
        )
        for _, row in self.funds_df.iterrows():
            cik = row["cik"]
            name = row["fund_name"]
            entity_type = row.get("entity_type", "fund").lower()

            log_info(f"Controller :: Checking {name} ({cik}) as {entity_type}...")
            if entity_type == "fund":
                self.process_fund(cik, name)
            elif entity_type == "company":
                self.process_company(cik, name, process_form_144=process_form_144)

            # Avoid hammering SEC API
            time.sleep(15)
        log_info("Controller :: Daily check completed.")


# ─────────────────────────────────────────────
# Test entry point
# ─────────────────────────────────────────────
def main():
    log_level = "DEBUG"
    log_dir = ROOT_PATH / "logs"

    configure_logger(log_level=log_level, log_dir=log_dir)
    controller = Controller(
        funds_csv_path="watchlist.csv",
        telegram_bot_token=TELEGRAM_BOT_TOKEN,
        telegram_chat_id=TELEGRAM_CHAT_ID,
        start_date=None,
        end_date=None,
        log_path="data/processed_filings.csv",
        debug=True,
        process_form_144=False,
    )

    controller.run_daily_check()


if __name__ == "__main__":
    main()
