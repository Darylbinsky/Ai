"""SimFin data fetcher for historical fundamental data."""

import simfin as sf
from simfin.names import *
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import os


class SimFinData:
    """Fetch historical fundamental data from SimFin."""

    def __init__(self, api_key: str = None):
        """
        Initialize SimFin data fetcher.

        Args:
            api_key: SimFin API key. If not provided, looks for SIMFIN_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get('SIMFIN_API_KEY')
        if not self.api_key:
            raise ValueError("SimFin API key required. Pass api_key or set SIMFIN_API_KEY env var.")

        # Configure SimFin
        sf.set_api_key(self.api_key)
        sf.set_data_dir('~/simfin_data/')  # Cache data locally

        # Load datasets (will download on first use)
        self._income_df = None
        self._prices_df = None
        self._companies_df = None

    def _load_income_data(self):
        """Load income statement data."""
        if self._income_df is None:
            print("Loading SimFin income statement data (first time may take a minute)...")
            self._income_df = sf.load_income(variant='annual', market='us')
        return self._income_df

    def _load_price_data(self):
        """Load share price data."""
        if self._prices_df is None:
            print("Loading SimFin share price data...")
            self._prices_df = sf.load_shareprices(market='us', variant='daily')
        return self._prices_df

    def _load_companies(self):
        """Load company info."""
        if self._companies_df is None:
            self._companies_df = sf.load_companies(market='us')
        return self._companies_df

    def get_historical_net_income(self, ticker: str) -> pd.DataFrame:
        """
        Get historical net income for a stock.

        Args:
            ticker: Stock ticker symbol

        Returns:
            DataFrame with fiscal year and net income
        """
        income_df = self._load_income_data()

        if ticker not in income_df.index.get_level_values('Ticker'):
            return pd.DataFrame()

        ticker_data = income_df.loc[ticker]
        if NET_INCOME in ticker_data.columns:
            result = ticker_data[[NET_INCOME]].copy()
            result = result.dropna()
            return result

        return pd.DataFrame()

    def get_historical_pe(self, ticker: str, date: str = None) -> Optional[float]:
        """
        Get P/E ratio at a specific date.

        Args:
            ticker: Stock ticker symbol
            date: Date string 'YYYY-MM-DD'. If None, uses latest.

        Returns:
            P/E ratio or None if not available
        """
        try:
            income_df = self._load_income_data()
            prices_df = self._load_price_data()

            if ticker not in income_df.index.get_level_values('Ticker'):
                return None
            if ticker not in prices_df.index.get_level_values('Ticker'):
                return None

            # Get price at date
            ticker_prices = prices_df.loc[ticker]
            if date:
                target_date = pd.to_datetime(date)
                # Find closest date
                available_dates = ticker_prices.index
                closest_idx = available_dates.get_indexer([target_date], method='ffill')[0]
                if closest_idx < 0:
                    return None
                price = ticker_prices.iloc[closest_idx][CLOSE]
            else:
                price = ticker_prices.iloc[-1][CLOSE]

            # Get most recent EPS before the date
            ticker_income = income_df.loc[ticker]
            if date:
                target_date = pd.to_datetime(date)
                valid_income = ticker_income[ticker_income.index <= target_date]
                if valid_income.empty:
                    return None
                latest_income = valid_income.iloc[-1]
            else:
                latest_income = ticker_income.iloc[-1]

            # Get shares outstanding and net income
            net_income = latest_income.get(NET_INCOME)
            shares = latest_income.get(SHARES_DILUTED) or latest_income.get(SHARES_BASIC)

            if net_income and shares and shares > 0 and net_income > 0:
                eps = net_income / shares
                pe = price / eps
                return pe

            return None

        except Exception as e:
            return None

    def get_income_growth(self, ticker: str, years: int = 3, as_of_date: str = None) -> Optional[float]:
        """
        Calculate net income CAGR over specified years.

        Args:
            ticker: Stock ticker symbol
            years: Number of years for growth calculation
            as_of_date: Calculate growth as of this date

        Returns:
            Compound annual growth rate as percentage, or None
        """
        try:
            income_df = self._load_income_data()

            if ticker not in income_df.index.get_level_values('Ticker'):
                return None

            ticker_data = income_df.loc[ticker]

            if as_of_date:
                target_date = pd.to_datetime(as_of_date)
                ticker_data = ticker_data[ticker_data.index <= target_date]

            if len(ticker_data) < years + 1:
                return None

            net_incomes = ticker_data[NET_INCOME].dropna()
            if len(net_incomes) < years + 1:
                return None

            recent = net_incomes.iloc[-1]
            old = net_incomes.iloc[-(years + 1)]

            if old <= 0 or recent <= 0:
                return None

            cagr = ((recent / old) ** (1 / years) - 1) * 100
            return cagr

        except Exception as e:
            return None

    def get_price_at_date(self, ticker: str, date: str) -> Optional[float]:
        """
        Get stock price at a specific date.

        Args:
            ticker: Stock ticker symbol
            date: Date string 'YYYY-MM-DD'

        Returns:
            Closing price or None
        """
        try:
            prices_df = self._load_price_data()

            if ticker not in prices_df.index.get_level_values('Ticker'):
                return None

            ticker_prices = prices_df.loc[ticker]
            target_date = pd.to_datetime(date)

            # Find closest available date
            available_dates = ticker_prices.index
            closest_idx = available_dates.get_indexer([target_date], method='ffill')[0]

            if closest_idx < 0:
                return None

            return ticker_prices.iloc[closest_idx][CLOSE]

        except Exception as e:
            return None

    def screen_at_date(
        self,
        tickers: List[str],
        date: str,
        max_pe: float = None,
        min_income_growth: float = None,
        growth_years: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Screen stocks based on fundamentals at a historical date.

        Args:
            tickers: List of stock tickers to screen
            date: Historical date 'YYYY-MM-DD'
            max_pe: Maximum P/E ratio
            min_income_growth: Minimum income growth %
            growth_years: Years for growth calculation

        Returns:
            List of stocks passing the screen with their metrics
        """
        results = []

        print(f"\nScreening {len(tickers)} stocks as of {date}...")

        for i, ticker in enumerate(tickers):
            if (i + 1) % 50 == 0:
                print(f"  Progress: {i + 1}/{len(tickers)}")

            try:
                # Get P/E at date
                pe = self.get_historical_pe(ticker, date)

                # Get income growth
                growth = self.get_income_growth(ticker, growth_years, date)

                # Get price at date
                price = self.get_price_at_date(ticker, date)

                # Apply filters
                if max_pe is not None and (pe is None or pe > max_pe or pe <= 0):
                    continue

                if min_income_growth is not None and (growth is None or growth < min_income_growth):
                    continue

                results.append({
                    'ticker': ticker,
                    'date': date,
                    'price': price,
                    'pe_ratio': round(pe, 2) if pe else None,
                    'income_growth': round(growth, 2) if growth else None,
                })

            except Exception as e:
                continue

        print(f"  Found {len(results)} stocks passing criteria")
        return results
