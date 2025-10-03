import pandas as pd
from datetime import datetime, timedelta
from typing import Optional

from follow_the_leaders.yfinance_fetcher import YFinanceFetcher


class Backtester:
    def __init__(
        self,
        holdings: pd.DataFrame,
        start_date: datetime,
        time_delta: timedelta,
        lookup_file: str = "CUSIP.csv",
        initial_capital: float = 100000.0,
    ):
        """
        holdings: DataFrame with at least ['issuer', 'cusip']
        start_date: start date of backtest (when 'filing is released')
        time_delta: how long to hold the positions
        lookup_file: path to CUSIP -> ticker lookup CSV
        initial_capital: starting portfolio value

        If multiple holdings are given. This backtester will allocate the initial
        capital equally amongst all instruments.
        """
        self.holdings = holdings
        self.start_date = start_date
        self.end_date = start_date + time_delta
        self.initial_capital = initial_capital

        # Load lookup file
        self.lookup_df = pd.read_csv(lookup_file, dtype=str)
        self.lookup_map = dict(zip(self.lookup_df["cusip"], self.lookup_df["symbol"]))

    def map_holdings(self) -> pd.DataFrame:
        """
        Merge holdings with CUSIP -> ticker lookup.
        Skip holdings without a ticker.
        """
        mapped = self.holdings.copy()
        mapped["ticker"] = mapped["cusip"].map(self.lookup_map)

        # Drop missing mappings
        unmapped = mapped[mapped["ticker"].isnull()]
        if not unmapped.empty:
            print("WARNING: Some holdings had no ticker mapping and were skipped:")
            print(unmapped[["issuer", "cusip"]])

        mapped = mapped.dropna(subset=["ticker"])
        return mapped

    def run(self) -> pd.DataFrame:
        """
        Run a simple buy-and-hold backtest.
        Equal-weight allocation across mapped tickers.
        """
        mapped = self.map_holdings()
        tickers = mapped["ticker"].unique().tolist()

        if not tickers:
            raise ValueError("No tickers could be mapped from the given CUSIPs.")

        fetcher = YFinanceFetcher(
            start=self.start_date,
            end=self.end_date,
            tickers=tickers,
            interval="1d",
        )
        price_data = fetcher.get_price_data("Adj Close")

        # Equal-weight allocation
        n_assets = len(tickers)
        allocation = self.initial_capital / n_assets

        portfolio = pd.DataFrame(index=price_data.index)
        portfolio_value = pd.Series(0.0, index=price_data.index)

        # TODO: reimplement core backtester using quantitative_trading methods previously deved
        for ticker in tickers:
            series = price_data[ticker]
            if series.isnull().all():
                continue
            first_price = series.iloc[0]
            shares = allocation / first_price
            position_value = shares * series
            portfolio_value += position_value

        portfolio["Portfolio"] = portfolio_value
        return portfolio


def main() -> int:
    holdings = pd.DataFrame(
        {
            "issuer": ["ARM HOLDINGS PLC", "RECURSION PHARMACEUTICALS"],
            "cusip": ["042068205", "75629V104"],
        }
    )

    backtester = Backtester(
        holdings=holdings,
        start_date=datetime(2024, 11, 15),
        time_delta=timedelta(days=90),
        lookup_file="CUSIP.csv",
        initial_capital=10000.0,
    )

    result = backtester.run()
    print(result.head())
    print(result.tail())

    return 0


if __name__ == "__main__":
    main()
