# follow-the-leaders
Stock trading strategy that examines Form 13F (for funds), Form 4 and Form 144 of publicly listed companies to get insights on their investments. It will give live alerts for potential trade opportunities.

## In Development

More information to come later as the project progresse

## Installation & Deployment

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

8. Run the strategy:

    ```zsh
    poetry run strategy
    ```

## Credits

The CUSIP ID to Ticker symbol lookup table used in this script isn't pushed on this repository. However it can be found [here](https://github.com/yoshishima/Stock_Data).
