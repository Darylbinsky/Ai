"""
Hybrid Backtester - Combines current insider ownership with historical fundamentals.

Tests multiple entry years and holding periods to find optimal strategy parameters.
"""

import pandas as pd
import numpy as np
import yfinance as yf
from typing import List, Dict, Any, Optional
from datetime import datetime
from tabulate import tabulate
import sys
import time

from data.simfin_data import SimFinData


class HybridBacktester:
    """
    Backtest using:
    - Current insider ownership (yfinance)
    - Historical P/E and income growth (SimFin)

    Tests multiple entry years and holding periods.
    """

    def __init__(self, api_key: str):
        """
        Initialize the hybrid backtester.

        Args:
            api_key: SimFin API key
        """
        self.simfin = SimFinData(api_key)
        self._insider_cache = {}

    def get_current_insider_ownership(self, ticker: str) -> Optional[float]:
        """Get current insider ownership percentage from yfinance."""
        if ticker in self._insider_cache:
            return self._insider_cache[ticker]

        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            insider_pct = info.get('heldPercentInsiders', 0)
            if insider_pct:
                insider_pct = insider_pct * 100
            self._insider_cache[ticker] = insider_pct
            return insider_pct
        except Exception:
            self._insider_cache[ticker] = None
            return None

    def screen_hybrid(
        self,
        tickers: List[str],
        historical_date: str,
        min_insider_ownership: float = 20,
        max_pe: float = 35,
        min_income_growth: float = 10,
        show_progress: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Screen stocks using current insider ownership + historical fundamentals.

        Args:
            tickers: List of stock tickers
            historical_date: Date for P/E and income growth 'YYYY-MM-DD'
            min_insider_ownership: Min insider ownership % (current)
            max_pe: Max P/E ratio (historical)
            min_income_growth: Min income growth % (historical)

        Returns:
            List of stocks passing all criteria
        """
        results = []
        total = len(tickers)

        for i, ticker in enumerate(tickers):
            if show_progress and (i + 1) % 20 == 0:
                sys.stdout.write(f"\rScreening: {i+1}/{total} | Passed: {len(results)}")
                sys.stdout.flush()

            try:
                # Get CURRENT insider ownership
                insider = self.get_current_insider_ownership(ticker)
                if insider is None or insider < min_insider_ownership:
                    continue

                # Get HISTORICAL P/E
                pe = self.simfin.get_historical_pe(ticker, historical_date)
                if pe is None or pe <= 0 or pe > max_pe:
                    continue

                # Get HISTORICAL income growth
                growth = self.simfin.get_income_growth(ticker, years=3, as_of_date=historical_date)
                if growth is None or growth < min_income_growth:
                    continue

                # Get price at historical date
                price = self.simfin.get_price_at_date(ticker, historical_date)

                results.append({
                    'ticker': ticker,
                    'entry_date': historical_date,
                    'entry_price': price,
                    'insider_ownership': round(insider, 2),
                    'pe_ratio': round(pe, 2),
                    'income_growth': round(growth, 2),
                })

            except Exception:
                continue

            time.sleep(0.05)  # Rate limiting

        if show_progress:
            print(f"\rScreening complete: {len(results)} stocks passed")

        return results

    def calculate_returns(
        self,
        stocks: List[Dict[str, Any]],
        holding_years: int
    ) -> Dict[str, Any]:
        """
        Calculate returns for a list of stocks over a holding period.

        Args:
            stocks: List of stocks with entry_date and entry_price
            holding_years: Number of years to hold

        Returns:
            Dictionary with return metrics
        """
        if not stocks:
            return {'avg_return': None, 'median_return': None, 'num_stocks': 0}

        returns = []

        for stock in stocks:
            try:
                entry_date = datetime.strptime(stock['entry_date'], '%Y-%m-%d')
                exit_date = entry_date.replace(year=entry_date.year + holding_years)
                exit_date_str = exit_date.strftime('%Y-%m-%d')

                # Don't calculate if exit date is in the future
                if exit_date > datetime.now():
                    continue

                entry_price = stock['entry_price']
                exit_price = self.simfin.get_price_at_date(stock['ticker'], exit_date_str)

                if entry_price and exit_price and entry_price > 0:
                    ret = (exit_price - entry_price) / entry_price * 100
                    returns.append(ret)

            except Exception:
                continue

        if not returns:
            return {'avg_return': None, 'median_return': None, 'num_stocks': 0}

        return {
            'avg_return': np.mean(returns),
            'median_return': np.median(returns),
            'min_return': np.min(returns),
            'max_return': np.max(returns),
            'num_stocks': len(returns),
            'returns': returns
        }

    def run_matrix_backtest(
        self,
        tickers: List[str],
        entry_years: List[int],
        holding_periods: List[int],
        min_insider_ownership: float = 20,
        max_pe: float = 35,
        min_income_growth: float = 10
    ) -> pd.DataFrame:
        """
        Run backtest across multiple entry years and holding periods.

        Args:
            tickers: Universe of stocks
            entry_years: List of years to test entry (e.g., [2015, 2016, 2017, 2018, 2019, 2020])
            holding_periods: List of holding periods in years (e.g., [1, 2, 3, 4, 5])
            min_insider_ownership: Min insider % (current)
            max_pe: Max P/E (historical)
            min_income_growth: Min income growth % (historical)

        Returns:
            DataFrame with results matrix
        """
        print("\n" + "=" * 70)
        print("HYBRID BACKTEST - Multiple Entry Years & Holding Periods")
        print("=" * 70)
        print()
        print("Strategy:")
        print(f"  - Insider Ownership > {min_insider_ownership}% (current)")
        print(f"  - P/E < {max_pe} (at entry)")
        print(f"  - Income Growth > {min_income_growth}% (at entry)")
        print()
        print(f"Entry Years: {entry_years}")
        print(f"Holding Periods: {holding_periods} years")
        print()

        # Results matrix
        results_matrix = {}

        for year in entry_years:
            entry_date = f"{year}-01-01"
            print(f"\n--- Entry Year: {year} ---")

            # Screen stocks at this entry date
            stocks = self.screen_hybrid(
                tickers=tickers,
                historical_date=entry_date,
                min_insider_ownership=min_insider_ownership,
                max_pe=max_pe,
                min_income_growth=min_income_growth,
                show_progress=True
            )

            if not stocks:
                print(f"  No stocks passed screening for {year}")
                results_matrix[year] = {hp: None for hp in holding_periods}
                continue

            print(f"  Stocks selected: {[s['ticker'] for s in stocks[:10]]}")
            if len(stocks) > 10:
                print(f"  ... and {len(stocks) - 10} more")

            # Calculate returns for each holding period
            results_matrix[year] = {}
            for hp in holding_periods:
                # Check if this combination is valid (not in future)
                exit_year = year + hp
                if exit_year > datetime.now().year:
                    results_matrix[year][hp] = None
                    continue

                returns = self.calculate_returns(stocks, hp)
                results_matrix[year][hp] = returns['avg_return']

                if returns['avg_return'] is not None:
                    print(f"  {hp}yr hold: {returns['avg_return']:.1f}% avg ({returns['num_stocks']} stocks)")

        # Convert to DataFrame
        df = pd.DataFrame(results_matrix).T
        df.columns = [f"{hp}yr" for hp in holding_periods]
        df.index.name = "Entry Year"

        return df

    def print_results_matrix(self, df: pd.DataFrame):
        """Print the results matrix in a nice format."""
        print("\n" + "=" * 70)
        print("RESULTS MATRIX - Average Returns by Entry Year & Holding Period")
        print("=" * 70)
        print()

        # Format for display
        display_df = df.copy()
        for col in display_df.columns:
            display_df[col] = display_df[col].apply(
                lambda x: f"{x:.1f}%" if pd.notna(x) else "-"
            )

        print(tabulate(display_df, headers='keys', tablefmt='grid'))

        # Summary statistics
        print("\n" + "-" * 70)
        print("SUMMARY")
        print("-" * 70)

        valid_returns = df.values.flatten()
        valid_returns = valid_returns[~pd.isna(valid_returns)]

        if len(valid_returns) > 0:
            print(f"  Overall Average Return: {np.mean(valid_returns):.1f}%")
            print(f"  Best Combination: {df.max().max():.1f}%")
            print(f"  Worst Combination: {df.min().min():.1f}%")

            # Find best entry year
            best_year_avg = df.mean(axis=1).idxmax()
            print(f"  Best Entry Year (avg): {best_year_avg}")

            # Find best holding period
            best_hp_avg = df.mean(axis=0).idxmax()
            print(f"  Best Holding Period (avg): {best_hp_avg}")

    def run_full_analysis(
        self,
        tickers: List[str],
        entry_years: List[int] = None,
        holding_periods: List[int] = None,
        min_insider_ownership: float = 20,
        max_pe: float = 35,
        min_income_growth: float = 10
    ):
        """
        Run full analysis with default parameters.
        """
        if entry_years is None:
            entry_years = [2015, 2016, 2017, 2018, 2019, 2020, 2021]

        if holding_periods is None:
            holding_periods = [1, 2, 3, 4, 5]

        df = self.run_matrix_backtest(
            tickers=tickers,
            entry_years=entry_years,
            holding_periods=holding_periods,
            min_insider_ownership=min_insider_ownership,
            max_pe=max_pe,
            min_income_growth=min_income_growth
        )

        self.print_results_matrix(df)

        return df
