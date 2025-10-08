from follow_the_leaders import (
    configure_logger,
    log_info,
    ROOT_PATH,
    app_parser,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)
from follow_the_leaders.controller import Controller


def main():
    args = app_parser()
    log_level = args.log_level
    strategy_debug = args.debug

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

    # TODO: Implement logic for daily checks
    controller.run_daily_check()


if __name__ == "__main__":
    main()
