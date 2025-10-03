import yfinance
import pandas as pd
import datetime

from typing import List, Dict


class YFinanceFetcher:
    def __init__(
        self, start: datetime, end: datetime, tickers: List | str, interval: str = "1d"
    ):
        """
        Fetch OHLC market data from Yahoo Finance
        Parameters
        ----------
        start: datetime object as start date
        end: datetime object as end date
        tickers: list or str of ticker(s)
        interval: Data interval, defaults to "1d" but can take: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
        """
        self.unique_ticker = isinstance(tickers, str)
        self.tickers = tickers
        self.interval = interval
        self.start = start
        self.end = end

        self.ticker_obj = None
        try:
            if self.unique_ticker:
                self.ticker_obj = yfinance.Ticker(tickers)
        except Exception as e:
            raise Exception(f"yfinance Ticker exception: {e}")

        self.raw_df = None
        self.swapped_data_indexes = False

        self._fetch_instrument_data()

    def update_fetch_parameters(
        self,
        start: datetime = None,
        end: datetime = None,
        tickers: List | str = None,
        interval: str = None,
    ) -> None:
        if start is not None:
            self.start = start
        if end is not None:
            self.end = end
        if tickers is not None:
            self.tickers = tickers
            self.unique_ticker = isinstance(tickers, str)
        if interval is not None:
            self.interval = interval

    def _fetch_instrument_data(self) -> None:
        if not self.unique_ticker:
            if len(self.tickers) == 1:
                self.tickers = self.tickers[0]
                self.raw_df = raw_yfinance_fetcher(
                    start=self.start,
                    end=self.end,
                    tickers=self.tickers,
                    multi_level_index=False,
                    interval=self.interval,
                )
            else:
                self.raw_df = raw_yfinance_fetcher(
                    start=self.start,
                    end=self.end,
                    tickers=self.tickers,
                    multi_level_index=True,
                    interval=self.interval,
                )
        else:
            self.raw_df = raw_yfinance_fetcher(
                start=self.start,
                end=self.end,
                tickers=self.tickers,
                multi_level_index=False,
                interval=self.interval,
            )
            # self.swap_column_indexes()

    def get_raw_ohlc_data(self) -> pd.DataFrame:
        """Returns the raw and complete data downloaded from YFinance"""
        return self.raw_df

    def get_price_data(self, price_type: str = "Close") -> pd.Series:
        """Get price data from the dataframe

        Parameters
        ----------
        price_type: Can take "Open", "High", "Low", "Close", "Adj Close" and "Volume"
        """
        return self.raw_df[price_type]

    def swap_column_indexes(self) -> None:
        """Swap outer (price type) and inner (ticker) indexes"""
        self.raw_df = self.raw_df.swaplevel(axis="columns").sort_index(axis="columns")
        self.swapped_data_indexes = not self.swapped_data_indexes

    @property
    def get_raw_yf_item(self):
        if self.raw_df is not None:
            return self.raw_df
        else:
            raise ValueError("The instrument information has not been fetched !")

    @property
    def get_ticker_obj(self) -> yfinance.Ticker:
        if self.unique_ticker:
            return self.ticker_obj
        else:
            raise Exception(
                "Multiple tickers were given ! Only parse one ticker when creating an instance of the YFinanceFetcher class."
            )

    @property
    def get_instrument_info(self) -> Dict:
        if self.unique_ticker:
            return self.ticker_obj.get_info()


def raw_yfinance_fetcher(
    start: datetime,
    end: datetime,
    tickers: List | str,
    multi_level_index: bool = True,
    interval: str = "1d",
) -> pd.DataFrame:
    raw_df = yfinance.download(
        tickers=tickers,
        start=start,
        end=end,
        auto_adjust=False,
        multi_level_index=multi_level_index,
        interval=interval,
    )
    return raw_df
