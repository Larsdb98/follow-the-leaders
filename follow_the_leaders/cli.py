import argparse

# TODO: booleans should be simple flags instead


def app_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument("--log-level", type=str, default="INFO", help="INFO, DEBUG")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Re-analyses recent filings even if they have already been previously analysed.",
    )
    parser.add_argument(
        "--process-144",
        action="store_true",
        help="Toggle Form 144 processing and notifications. By default, forms 144 are not processed.",
    )
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="If True, the daily check will be run immediately. This parameter is set to False by default",
    )

    arg = parser.parse_args()
    return arg
