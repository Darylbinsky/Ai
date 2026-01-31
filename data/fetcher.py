"""Stock data fetching utilities using yfinance."""

import yfinance as yf
import pandas as pd
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta


class DataFetcher:
    """Fetches stock data from Yahoo Finance."""

    def __init__(self, cache_enabled: bool = True):
        self.cache_enabled = cache_enabled
        self._cache: Dict[str, pd.DataFrame] = {}

    def get_stock_data(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "1y"
    ) -> pd.DataFrame:
        """
        Fetch historical stock data.

        Args:
            symbol: Stock ticker symbol
            start_date: Start date (YYYY-MM-DD format)
            end_date: End date (YYYY-MM-DD format)
            period: Period to fetch if dates not specified (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)

        Returns:
            DataFrame with OHLCV data
        """
        cache_key = f"{symbol}_{start_date}_{end_date}_{period}"

        if self.cache_enabled and cache_key in self._cache:
            return self._cache[cache_key].copy()

        ticker = yf.Ticker(symbol)

        if start_date and end_date:
            data = ticker.history(start=start_date, end=end_date)
        else:
            data = ticker.history(period=period)

        if data.empty:
            raise ValueError(f"No data found for symbol: {symbol}")

        # Clean column names
        data.columns = [col.lower().replace(' ', '_') for col in data.columns]

        if self.cache_enabled:
            self._cache[cache_key] = data.copy()

        return data

    def get_multiple_stocks(
        self,
        symbols: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "1y"
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch data for multiple stocks.

        Args:
            symbols: List of stock ticker symbols
            start_date: Start date (YYYY-MM-DD format)
            end_date: End date (YYYY-MM-DD format)
            period: Period to fetch if dates not specified

        Returns:
            Dictionary mapping symbols to DataFrames
        """
        result = {}
        for symbol in symbols:
            try:
                result[symbol] = self.get_stock_data(symbol, start_date, end_date, period)
            except Exception as e:
                print(f"Warning: Could not fetch data for {symbol}: {e}")
        return result

    def get_stock_info(self, symbol: str) -> Dict[str, Any]:
        """
        Get stock information (fundamentals, etc.).

        Args:
            symbol: Stock ticker symbol

        Returns:
            Dictionary with stock information
        """
        ticker = yf.Ticker(symbol)
        return ticker.info

    def get_financials(self, symbol: str) -> Dict[str, pd.DataFrame]:
        """
        Get financial statements.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Dictionary with income statement, balance sheet, and cash flow
        """
        ticker = yf.Ticker(symbol)
        return {
            'income_statement': ticker.financials,
            'balance_sheet': ticker.balance_sheet,
            'cash_flow': ticker.cashflow
        }

    def clear_cache(self):
        """Clear the data cache."""
        self._cache.clear()
