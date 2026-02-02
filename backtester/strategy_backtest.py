#!/usr/bin/env python3
"""
Strategy Backtester

Backtests the data-driven screening strategy:
- Profit Margin > 6%
- ROE > 9%
- Revenue Growth > 7%
- Debt/Equity < 65
- Current Ratio > 1.8
- Sectors: Energy, Tech, Industrials, Consumer Cyclical

Tests how stocks passing these criteria performed historically.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any
import time
import sys
from tabulate import tabulate


# Strategy criteria
CRITERIA = {
    'profit_margin_min': 0.06,
    'roe_min': 0.09,
    'revenue_growth_min': 0.07,
    'debt_equity_max': 65,
    'current_ratio_min': 1.8,
}

ALLOWED_SECTORS = ['Energy', 'Technology', 'Industrials', 'Consumer Cyclical']


class StrategyBacktester:
    """Backtest the data-driven screening strategy."""

    def __init__(self):
        self.results = []

    def get_historical_price(self, ticker: str, date: str) -> float:
        """Get stock price at a specific date."""
        try:
            stock = yf.Ticker(ticker)
            # Get price around the target date
            start = pd.to_datetime(date) - timedelta(days=5)
            end = pd.to_datetime(date) + timedelta(days=5)
            hist = stock.history(start=start, end=end)
            if not hist.empty:
                return hist['Close'].iloc[-1]
        except:
            pass
        return None

    def calculate_return(self, ticker: str, start_date: str, end_date: str) -> float:
        """Calculate return between two dates."""
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date, end=end_date)
            if len(hist) >= 2:
                start_price = hist['Close'].iloc[0]
                end_price = hist['Close'].iloc[-1]
                return ((end_price - start_price) / start_price) * 100
        except:
            pass
        return None

    def screen_at_date(self, tickers: List[str], screen_date: str, show_progress: bool = True) -> List[Dict]:
        """
        Screen stocks based on criteria.

        Note: Uses current fundamental data as proxy (yfinance limitation).
        For true historical backtesting, would need historical fundamental database.
        """
        passed = []
        total = len(tickers)

        for i, ticker in enumerate(tickers):
            if show_progress and (i + 1) % 50 == 0:
                sys.stdout.write(f"\r  Screening: {i+1}/{total}")
                sys.stdout.flush()

            try:
                stock = yf.Ticker(ticker)
                info = stock.info

                if not info:
                    continue

                # Check sector
                sector = info.get('sector', '')
                if sector not in ALLOWED_SECTORS:
                    continue

                # Get metrics
                pm = info.get('profitMargins')
                roe = info.get('returnOnEquity')
                rg = info.get('revenueGrowth')
                de = info.get('debtToEquity')
                cr = info.get('currentRatio')

                # Apply criteria
                if pm is None or pm < CRITERIA['profit_margin_min']:
                    continue
                if roe is None or roe < CRITERIA['roe_min']:
                    continue
                if rg is None or rg < CRITERIA['revenue_growth_min']:
                    continue
                if de is None or de > CRITERIA['debt_equity_max']:
                    continue
                if cr is None or cr < CRITERIA['current_ratio_min']:
                    continue

                passed.append({
                    'ticker': ticker,
                    'sector': sector,
                    'profit_margin': pm * 100,
                    'roe': roe * 100,
                    'revenue_growth': rg * 100,
                    'debt_equity': de,
                    'current_ratio': cr,
                })

                time.sleep(0.03)

            except Exception:
                continue

        if show_progress:
            print(f"\r  Screening: {total}/{total} - {len(passed)} passed")

        return passed

    def backtest_strategy(
        self,
        tickers: List[str],
        entry_years: List[int] = None,
        holding_periods: List[int] = None
    ) -> pd.DataFrame:
        """
        Backtest the strategy across multiple years and holding periods.

        Args:
            tickers: List of stock tickers to test
            entry_years: Years to test entry (e.g., [2020, 2021, 2022, 2023])
            holding_periods: Holding periods in months (e.g., [6, 12, 24])
        """
        if entry_years is None:
            entry_years = [2020, 2021, 2022, 2023, 2024]
        if holding_periods is None:
            holding_periods = [6, 12]

        print("\n" + "=" * 70)
        print("STRATEGY BACKTEST")
        print("=" * 70)
        print("\nCriteria:")
        print(f"  Profit Margin > {CRITERIA['profit_margin_min']*100}%")
        print(f"  ROE > {CRITERIA['roe_min']*100}%")
        print(f"  Revenue Growth > {CRITERIA['revenue_growth_min']*100}%")
        print(f"  Debt/Equity < {CRITERIA['debt_equity_max']}")
        print(f"  Current Ratio > {CRITERIA['current_ratio_min']}")
        print(f"  Sectors: {', '.join(ALLOWED_SECTORS)}")
        print(f"\nEntry years: {entry_years}")
        print(f"Holding periods: {holding_periods} months")
        print(f"Universe: {len(tickers)} stocks")

        # First, screen stocks (using current data as proxy)
        print("\n" + "-" * 70)
        print("Step 1: Screening stocks...")
        print("-" * 70)
        passed_stocks = self.screen_at_date(tickers, datetime.now().strftime('%Y-%m-%d'))

        if not passed_stocks:
            print("No stocks passed the criteria.")
            return None

        print(f"\n{len(passed_stocks)} stocks passed criteria")

        # Now calculate historical returns for each entry year and holding period
        print("\n" + "-" * 70)
        print("Step 2: Calculating historical returns...")
        print("-" * 70)

        results = []
        stock_tickers = [s['ticker'] for s in passed_stocks]

        for year in entry_years:
            entry_date = f"{year}-01-02"

            for months in holding_periods:
                exit_date = (pd.to_datetime(entry_date) + pd.DateOffset(months=months)).strftime('%Y-%m-%d')

                # Skip if exit date is in the future
                if pd.to_datetime(exit_date) > datetime.now():
                    continue

                print(f"\n  Testing: Entry {year}, Hold {months} months (exit ~{exit_date[:7]})")

                returns = []
                for ticker in stock_tickers:
                    ret = self.calculate_return(ticker, entry_date, exit_date)
                    if ret is not None:
                        returns.append({'ticker': ticker, 'return': ret})

                if returns:
                    avg_return = np.mean([r['return'] for r in returns])
                    median_return = np.median([r['return'] for r in returns])
                    winners = sum(1 for r in returns if r['return'] > 0)
                    win_rate = (winners / len(returns)) * 100

                    results.append({
                        'Entry Year': year,
                        'Hold (months)': months,
                        'Stocks': len(returns),
                        'Avg Return': avg_return,
                        'Median Return': median_return,
                        'Win Rate': win_rate,
                        'Best': max(r['return'] for r in returns),
                        'Worst': min(r['return'] for r in returns),
                    })

                    print(f"    Stocks: {len(returns)}, Avg: {avg_return:.1f}%, Win Rate: {win_rate:.0f}%")

        # Display results
        if results:
            self._display_results(results)

        return pd.DataFrame(results) if results else None

    def _display_results(self, results: List[Dict]):
        """Display backtest results."""
        print("\n" + "=" * 70)
        print("BACKTEST RESULTS")
        print("=" * 70)

        # Summary table
        table_data = []
        for r in results:
            table_data.append({
                'Entry': r['Entry Year'],
                'Hold': f"{r['Hold (months)']}mo",
                'Stocks': r['Stocks'],
                'Avg%': f"{r['Avg Return']:+.1f}%",
                'Median%': f"{r['Median Return']:+.1f}%",
                'Win%': f"{r['Win Rate']:.0f}%",
                'Best%': f"{r['Best']:+.1f}%",
                'Worst%': f"{r['Worst']:+.1f}%",
            })

        print("\n" + tabulate(table_data, headers='keys', tablefmt='grid'))

        # Overall summary
        all_avg = np.mean([r['Avg Return'] for r in results])
        all_median = np.median([r['Median Return'] for r in results])
        all_win = np.mean([r['Win Rate'] for r in results])

        print("\n" + "-" * 70)
        print("OVERALL SUMMARY")
        print("-" * 70)
        print(f"\n  Average Return (all periods): {all_avg:+.1f}%")
        print(f"  Median Return (all periods):  {all_median:+.1f}%")
        print(f"  Average Win Rate:             {all_win:.0f}%")

        # Compare to market (SPY)
        print("\n" + "-" * 70)
        print("vs MARKET (SPY)")
        print("-" * 70)

        for r in results:
            year = r['Entry Year']
            months = r['Hold (months)']
            entry_date = f"{year}-01-02"
            exit_date = (pd.to_datetime(entry_date) + pd.DateOffset(months=months)).strftime('%Y-%m-%d')

            spy_return = self.calculate_return('SPY', entry_date, exit_date)
            if spy_return is not None:
                alpha = r['Avg Return'] - spy_return
                print(f"  {year} ({months}mo): Strategy {r['Avg Return']:+.1f}% vs SPY {spy_return:+.1f}% = Alpha {alpha:+.1f}%")


def run_backtest(tickers: List[str]):
    """Run the strategy backtest."""
    backtester = StrategyBacktester()

    print("\nBacktest Configuration:")
    print("-" * 40)

    # Entry years
    years_input = input("Entry years (comma-separated) [default: 2020,2021,2022,2023,2024]: ").strip()
    if years_input:
        entry_years = [int(y.strip()) for y in years_input.split(',')]
    else:
        entry_years = [2020, 2021, 2022, 2023, 2024]

    # Holding periods
    hold_input = input("Holding periods in months (comma-separated) [default: 6,12]: ").strip()
    if hold_input:
        holding_periods = [int(h.strip()) for h in hold_input.split(',')]
    else:
        holding_periods = [6, 12]

    results = backtester.backtest_strategy(
        tickers=tickers,
        entry_years=entry_years,
        holding_periods=holding_periods
    )

    return results
