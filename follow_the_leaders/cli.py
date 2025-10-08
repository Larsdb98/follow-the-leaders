import argparse


def app_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument("--log-level", type=str, default="INFO", help="INFO, DEBUG")
    parser.add_argument("--debug", type=bool, default=False)

    arg = parser.parse_args()
    return arg
