import argparse

# TODO: booleans should be simple flags instead


def app_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument("--log-level", type=str, default="INFO", help="INFO, DEBUG")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Since processed filings will no longer show up. This flag re-processes the recent filings.",
    )
    parser.add_argument(
        "--process-144",
        action="store_true",
        help="By default, form 144 analysis is turned off. But can be activated with this flag.",
    )
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Useful for debugging purposes, it allows to run the daily check right away instead of waiting for the scheduler to call this.",
    )

    arg = parser.parse_args()
    return arg
