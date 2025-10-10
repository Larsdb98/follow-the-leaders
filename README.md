# Follow the Leaders
Stock trading strategy that examines Form 13F (for funds), Form 4 and Form 144 of publicly listed companies to get insights on their investments. It will give live alerts for potential trade opportunities.

It communicates findings and potential trade opportunities via Telegram messages through a bot. The form examinations happen every day at 7 AM. This can be adjusted in the strategy's entry point file [main.py](follow_the_leaders/main.py).

## Installation

1. Make sure you have Python 3.11 installed on your machine.

2. Install [poetry](https://python-poetry.org)

3. Clone the project

    ```zsh
    git clone https://github.com/Larsdb98/follow-the-leaders.git
    ```

4. Download the CUSIP.csv found [here](https://github.com/yoshishima/Stock_Data). This is the lookup table to match CUSIP IDs to Ticker Symbols. Place it in the [follow_the_leaders](follow_the_leaders/) directory. 

5. In the [follow_the_leaders](follow_the_leaders/) directory, create a new Python file named `secret_vars.py`. This file will contain your SEC header for fetching, Telegram bot token and chat ID:

    ```python
    SEC_HEADERS = {"User-Agent": "{YOUR NAME} {YOUR EMAIL}"}
    TELEGRAM_BOT_TOKEN = r"{YOUR BOT TOKEN}"
    TELEGRAM_CHAT_ID = r"{YOUR CHAT ID}"
    ```

6. Again in the same directory, create a CSV file named `watchlist.csv`. In this file is where you will add all companies/funds to monitor. An example of the file is provided below:

    ```
    cik,fund_name,notes,entity_type,active
    1045810, NVIDIA Corp,Tech AI leader,company,TRUE
    1697748,ARK Investment Management,Cathie Wood,fund,TRUE
    ```

7. Install the project:

    ```zsh
    poetry install
    ```

## Running The Strategy

To run the strategy:

```zsh
poetry run strategy
```

The following arguments are available:
1. `--process-144`: By default, form 144 analysis is turned off. But can be activated with this flag.
2. `--debug`: Since processed filings will no longer show up. This flag re-processes the recent filings.
3. `--log-level`: Set the logging level of the strategy. It defaults to `INFO` but can also be set to `DEBUG`.
4. `--run-once`: Useful for debugging purposes, it allows to run the daily check right away instead of waiting for the scheduler to call this.

To show this list of arguments:

```zsh
poetry run strategy -h
```

Ideal launch for debugging purposes:
```zsh
poetry run strategy --run-once --log-level DEBUG --debug
```

To check if the strategy is still running. Send a message to the Telegram bot and say either `alive` or `status`.

## Credits

The CUSIP ID to Ticker symbol lookup table used in this script isn't pushed on this repository. However it can be found [here](https://github.com/yoshishima/Stock_Data).
