from follow_the_leaders import (
    configure_logger,
    log_info,
    ROOT_PATH,
    app_parser,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)
from follow_the_leaders.controller import Controller

import schedule
import time


def main():
    args = app_parser()
    log_level = args.log_level
    strategy_debug = args.debug
    process_form_144 = args.process_144
    run_once = args.run_once

    log_dir = ROOT_PATH / "logs"

    configure_logger(log_level=log_level, log_dir=log_dir)
    log_info("_______________ Follow The Leaders _______________")

    controller = Controller(
        funds_csv_path="follow_the_leaders/watchlist.csv",
        telegram_bot_token=TELEGRAM_BOT_TOKEN,
        telegram_chat_id=TELEGRAM_CHAT_ID,
        start_date=None,
        end_date=None,
        log_path="data/processed_filings.csv",
        debug=strategy_debug,
    )

    if run_once:
        controller.run_daily_check(process_form_144=process_form_144)

    else:
        # The SEC EDGAR system typically posts filings between ~6 PM–10 PM ET.
        # Running the check around 7:00 AM UTC (≈2 AM ET) ensures all filings from the previous day are available.
        optimal_time = "07:00"
        schedule.every().day.at(optimal_time).do(
            controller.run_daily_check, process_form_144=process_form_144
        )

        log_info(f"Daily filing check scheduled at {optimal_time} UTC each day.")
        log_info("Controller instance initialized — waiting for first run.\n")

        # ─────────────────────────────────────────────
        # 🔁 Keep process alive
        # ─────────────────────────────────────────────
        try:
            while True:
                schedule.run_pending()
                time.sleep(30)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
