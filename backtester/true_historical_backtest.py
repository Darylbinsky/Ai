#!/usr/bin/env python3
"""
True Historical Backtester

Uses SimFin for actual historical fundamental data to screen stocks
at each historical date, then measures forward returns.

This is a TRUE backtest - we use the fundamentals that were available
at each point in time, not today's data.
"""

import simfin as sf
from simfin.names import *
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import time
import sys
import os
from tabulate import tabulate


# Strategy criteria
CRITERIA = {
    'profit_margin_min': 0.06,      # > 6%
    'roe_min': 0.09,                # > 9%
    'revenue_growth_min': 0.07,     # > 7%
    'debt_equity_max': 65,          # < 65
    'current_ratio_min': 1.8,       # > 1.8
}

ALLOWED_SECTORS = ['Energy', 'Technology', 'Industrials', 'Consumer Cyclical']

# Map yfinance sectors to SimFin industries
SECTOR_MAPPING = {
    'Technology': ['Software', 'Hardware', 'Semiconductors', 'Technology Services'],
    'Energy': ['Oil & Gas', 'Energy', 'Utilities'],
    'Industrials': ['Industrial', 'Aerospace & Defense', 'Transportation', 'Machinery'],
    'Consumer Cyclical': ['Retail', 'Consumer Discretionary', 'Automobiles', 'Consumer Services'],
}


class TrueHistoricalBacktester:
    """Backtest using actual historical fundamental data from SimFin."""

    def __init__(self, api_key: str):
        """Initialize with SimFin API key."""
        self.api_key = api_key
        sf.set_api_key(api_key)
        sf.set_data_dir('~/simfin_data/')

        self._income_df = None
        self._balance_df = None
        self._prices_df = None
        self._companies_df = None

        # Cache for sector lookups (use yfinance since SimFin doesn't have good sector data)
        self._sector_cache = {}

    def _load_data(self):
        """Load all required SimFin datasets."""
        if self._income_df is None:
            print("Loading SimFin datasets (first time may download data)...")
            print("  Loading income statements...")
            self._income_df = sf.load_income(variant='annual', market='us')
            print("  Loading balance sheets...")
            self._balance_df = sf.load_balance(variant='annual', market='us')
            print("  Loading share prices...")
            self._prices_df = sf.load_shareprices(market='us', variant='daily')
            print("  Done loading data.")

    def _get_sector(self, ticker: str) -> Optional[str]:
        """Get sector for a ticker (cached)."""
        if ticker in self._sector_cache:
            return self._sector_cache[ticker]

        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            sector = info.get('sector')
            self._sector_cache[ticker] = sector
            return sector
        except:
            self._sector_cache[ticker] = None
            return None

    def _get_fundamentals_at_date(self, ticker: str, date: str) -> Optional[Dict]:
        """
        Get fundamental metrics for a stock as of a specific date.
        Uses the most recent annual report available before that date.
        """
        try:
            target_date = pd.to_datetime(date)

            # Get income statement data
            if ticker not in self._income_df.index.get_level_values('Ticker'):
                return None

            income_data = self._income_df.loc[ticker]
            income_before_date = income_data[income_data.index <= target_date]

            if income_before_date.empty:
                return None

            latest_income = income_before_date.iloc[-1]

            # Get balance sheet data
            if ticker not in self._balance_df.index.get_level_values('Ticker'):
                return None

            balance_data = self._balance_df.loc[ticker]
            balance_before_date = balance_data[balance_data.index <= target_date]

            if balance_before_date.empty:
                return None

            latest_balance = balance_before_date.iloc[-1]

            # Calculate metrics
            revenue = latest_income.get(REVENUE, 0)
            net_income = latest_income.get(NET_INCOME, 0)
            total_equity = latest_balance.get(TOTAL_EQUITY, 0)
            total_debt = latest_balance.get(TOTAL_DEBT, 0) or latest_balance.get(TOTAL_LIABILITIES, 0)
            current_assets = latest_balance.get(TOTAL_CUR_ASSETS, 0)
            current_liabilities = latest_balance.get(TOTAL_CUR_LIAB, 0)

            # Profit margin
            profit_margin = (net_income / revenue) if revenue and revenue > 0 else None

            # ROE
            roe = (net_income / total_equity) if total_equity and total_equity > 0 else None

            # Debt/Equity
            debt_equity = (total_debt / total_equity * 100) if total_equity and total_equity > 0 else None

            # Current ratio
            current_ratio = (current_assets / current_liabilities) if current_liabilities and current_liabilities > 0 else None

            # Revenue growth (compare to previous year)
            if len(income_before_date) >= 2:
                prev_revenue = income_before_date.iloc[-2].get(REVENUE, 0)
                if prev_revenue and prev_revenue > 0:
                    revenue_growth = (revenue - prev_revenue) / prev_revenue
                else:
                    revenue_growth = None
            else:
                revenue_growth = None

            return {
                'profit_margin': profit_margin,
                'roe': roe,
                'revenue_growth': revenue_growth,
                'debt_equity': debt_equity,
                'current_ratio': current_ratio,
                'revenue': revenue,
                'net_income': net_income,
            }

        except Exception as e:
            return None

    def _get_price_at_date(self, ticker: str, date: str) -> Optional[float]:
        """Get stock price at a specific date."""
        try:
            if ticker not in self._prices_df.index.get_level_values('Ticker'):
                return None

            ticker_prices = self._prices_df.loc[ticker]
            target_date = pd.to_datetime(date)

            # Find closest available date
            available_dates = ticker_prices.index
            closest_idx = available_dates.get_indexer([target_date], method='ffill')[0]

            if closest_idx < 0:
                return None

            return ticker_prices.iloc[closest_idx][CLOSE]
        except:
            return None

    def _calculate_return(self, ticker: str, start_date: str, end_date: str) -> Optional[float]:
        """Calculate return between two dates using SimFin price data."""
        start_price = self._get_price_at_date(ticker, start_date)
        end_price = self._get_price_at_date(ticker, end_date)

        if start_price and end_price and start_price > 0:
            return ((end_price - start_price) / start_price) * 100
        return None

    def screen_at_date(self, tickers: List[str], date: str, show_progress: bool = True) -> List[Dict]:
        """
        Screen stocks using historical fundamentals at a specific date.

        This is a TRUE historical screen - uses only data available at that time.
        """
        passed = []
        stats = {'total': 0, 'no_data': 0, 'wrong_sector': 0, 'failed_criteria': 0}

        for i, ticker in enumerate(tickers):
            if show_progress and (i + 1) % 100 == 0:
                sys.stdout.write(f"\r  Screening: {i+1}/{len(tickers)} ({len(passed)} passed)")
                sys.stdout.flush()

            stats['total'] += 1

            # Check sector first
            sector = self._get_sector(ticker)
            if sector not in ALLOWED_SECTORS:
                stats['wrong_sector'] += 1
                continue

            # Get historical fundamentals
            fundamentals = self._get_fundamentals_at_date(ticker, date)
            if not fundamentals:
                stats['no_data'] += 1
                continue

            # Apply criteria
            pm = fundamentals.get('profit_margin')
            roe = fundamentals.get('roe')
            rg = fundamentals.get('revenue_growth')
            de = fundamentals.get('debt_equity')
            cr = fundamentals.get('current_ratio')

            # Check each criterion
            if pm is None or pm < CRITERIA['profit_margin_min']:
                stats['failed_criteria'] += 1
                continue
            if roe is None or roe < CRITERIA['roe_min']:
                stats['failed_criteria'] += 1
                continue
            if rg is None or rg < CRITERIA['revenue_growth_min']:
                stats['failed_criteria'] += 1
                continue
            if de is None or de > CRITERIA['debt_equity_max']:
                stats['failed_criteria'] += 1
                continue
            if cr is None or cr < CRITERIA['current_ratio_min']:
                stats['failed_criteria'] += 1
                continue

            # Passed all criteria
            passed.append({
                'ticker': ticker,
                'sector': sector,
                'profit_margin': pm * 100,
                'roe': roe * 100,
                'revenue_growth': rg * 100,
                'debt_equity': de,
                'current_ratio': cr,
            })

            time.sleep(0.02)  # Rate limit yfinance sector lookups

        if show_progress:
            print(f"\r  Screening: {len(tickers)}/{len(tickers)} - {len(passed)} passed")
            print(f"    (No data: {stats['no_data']}, Wrong sector: {stats['wrong_sector']}, Failed criteria: {stats['failed_criteria']})")

        return passed

    def backtest(
        self,
        tickers: List[str],
        entry_years: List[int] = None,
        holding_periods: List[int] = None
    ) -> pd.DataFrame:
        """
        Run true historical backtest.

        For each entry year:
        1. Screen stocks using fundamentals available at that time
        2. Buy stocks that pass the screen
        3. Measure returns over the holding period
        """
        if entry_years is None:
            entry_years = [2018, 2019, 2020, 2021, 2022, 2023]
        if holding_periods is None:
            holding_periods = [12]

        print("\n" + "=" * 70)
        print("TRUE HISTORICAL BACKTEST")
        print("=" * 70)
        print("\nThis uses ACTUAL historical fundamentals from SimFin")
        print("(not today's data projected backwards)")
        print("\nCriteria:")
        print(f"  Profit Margin > {CRITERIA['profit_margin_min']*100}%")
        print(f"  ROE > {CRITERIA['roe_min']*100}%")
        print(f"  Revenue Growth > {CRITERIA['revenue_growth_min']*100}%")
        print(f"  Debt/Equity < {CRITERIA['debt_equity_max']}")
        print(f"  Current Ratio > {CRITERIA['current_ratio_min']}")
        print(f"  Sectors: {', '.join(ALLOWED_SECTORS)}")
        print(f"\nEntry years: {entry_years}")
        print(f"Holding periods: {holding_periods} months")

        # Load SimFin data
        self._load_data()

        results = []

        for year in entry_years:
            entry_date = f"{year}-01-02"

            print(f"\n" + "-" * 70)
            print(f"SCREENING AT {entry_date}")
            print("-" * 70)

            # Screen stocks using historical fundamentals
            passed_stocks = self.screen_at_date(tickers, entry_date)

            if not passed_stocks:
                print(f"  No stocks passed criteria for {year}")
                continue

            # Calculate returns for each holding period
            for months in holding_periods:
                exit_date = (pd.to_datetime(entry_date) + pd.DateOffset(months=months)).strftime('%Y-%m-%d')

                # Skip if exit is in the future
                if pd.to_datetime(exit_date) > datetime.now():
                    continue

                print(f"\n  Calculating {months}-month returns (exit: {exit_date[:7]})...")

                returns = []
                for stock in passed_stocks:
                    ret = self._calculate_return(stock['ticker'], entry_date, exit_date)
                    if ret is not None:
                        returns.append({
                            'ticker': stock['ticker'],
                            'return': ret,
                            **stock
                        })

                if returns:
                    avg_return = np.mean([r['return'] for r in returns])
                    median_return = np.median([r['return'] for r in returns])
                    winners = sum(1 for r in returns if r['return'] > 0)
                    win_rate = (winners / len(returns)) * 100

                    results.append({
                        'Entry Year': year,
                        'Hold (months)': months,
                        'Stocks Screened': len(passed_stocks),
                        'Stocks w/ Returns': len(returns),
                        'Avg Return': avg_return,
                        'Median Return': median_return,
                        'Win Rate': win_rate,
                        'Best': max(r['return'] for r in returns),
                        'Worst': min(r['return'] for r in returns),
                    })

                    print(f"    Results: {len(returns)} stocks, Avg: {avg_return:+.1f}%, Win Rate: {win_rate:.0f}%")

        # Display results
        if results:
            self._display_results(results, holding_periods)

        return pd.DataFrame(results) if results else None

    def _display_results(self, results: List[Dict], holding_periods: List[int]):
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
                'Screened': r['Stocks Screened'],
                'Traded': r['Stocks w/ Returns'],
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

        # Compare to market
        print("\n" + "-" * 70)
        print("vs MARKET (SPY)")
        print("-" * 70)

        for r in results:
            year = r['Entry Year']
            months = r['Hold (months)']
            entry_date = f"{year}-01-02"
            exit_date = (pd.to_datetime(entry_date) + pd.DateOffset(months=months)).strftime('%Y-%m-%d')

            # Get SPY return using yfinance (more reliable for SPY)
            try:
                spy = yf.Ticker('SPY')
                hist = spy.history(start=entry_date, end=exit_date)
                if len(hist) >= 2:
                    spy_return = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
                    alpha = r['Avg Return'] - spy_return
                    print(f"  {year} ({months}mo): Strategy {r['Avg Return']:+.1f}% vs SPY {spy_return:+.1f}% = Alpha {alpha:+.1f}%")
            except:
                pass


def run_true_backtest(tickers: List[str], api_key: str):
    """Run the true historical backtest."""
    backtester = TrueHistoricalBacktester(api_key=api_key)

    print("\nTrue Historical Backtest Configuration:")
    print("-" * 40)
    print("Note: SimFin free tier has data from ~2010 onwards")
    print()

    # Entry years
    years_input = input("Entry years (comma-separated) [default: 2018,2019,2020,2021,2022,2023]: ").strip()
    if years_input:
        entry_years = [int(y.strip()) for y in years_input.split(',')]
    else:
        entry_years = [2018, 2019, 2020, 2021, 2022, 2023]

    # Holding periods
    hold_input = input("Holding periods in months (comma-separated) [default: 12]: ").strip()
    if hold_input:
        holding_periods = [int(h.strip()) for h in hold_input.split(',')]
    else:
        holding_periods = [12]

    results = backtester.backtest(
        tickers=tickers,
        entry_years=entry_years,
        holding_periods=holding_periods
    )

    return results
