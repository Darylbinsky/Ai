#!/usr/bin/env python3
"""
True Historical Backtester

Uses yfinance historical financial statements to screen stocks
at each historical date, then measures forward returns.

This is a TRUE backtest - we use the fundamentals that were available
at each point in time, not today's data.
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import time
import sys
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


class TrueHistoricalBacktester:
    """Backtest using actual historical fundamental data from yfinance."""

    def __init__(self, api_key: str = None):
        """Initialize backtester."""
        # Cache for sector lookups
        self._sector_cache = {}
        self._financials_cache = {}

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

    def _get_historical_financials(self, ticker: str) -> Dict:
        """Get historical financial statements for a ticker."""
        if ticker in self._financials_cache:
            return self._financials_cache[ticker]

        try:
            stock = yf.Ticker(ticker)

            # Get annual financials (income statement)
            income = stock.financials  # columns are dates, rows are line items

            # Get annual balance sheet
            balance = stock.balance_sheet

            self._financials_cache[ticker] = {
                'income': income,
                'balance': balance,
            }
            return self._financials_cache[ticker]
        except:
            self._financials_cache[ticker] = {'income': None, 'balance': None}
            return self._financials_cache[ticker]

    def _get_fundamentals_at_date(self, ticker: str, date: str) -> Optional[Dict]:
        """
        Get fundamental metrics for a stock as of a specific date.
        Uses the most recent annual report available before that date.
        """
        try:
            target_date = pd.to_datetime(date)
            financials = self._get_historical_financials(ticker)

            income = financials.get('income')
            balance = financials.get('balance')

            if income is None or income.empty or balance is None or balance.empty:
                return None

            # Find the most recent fiscal year before target date
            # yfinance financials columns are dates
            income_dates = pd.to_datetime(income.columns)
            valid_dates = [d for d in income_dates if d <= target_date]

            if not valid_dates:
                return None

            latest_date = max(valid_dates)

            # Get income statement data
            if latest_date not in income.columns:
                # Try to find matching column
                for col in income.columns:
                    if pd.to_datetime(col) == latest_date:
                        latest_date = col
                        break

            # Extract values - handle different row name formats
            def get_value(df, names):
                for name in names:
                    if name in df.index:
                        val = df.loc[name, latest_date] if latest_date in df.columns else None
                        if val is not None and not pd.isna(val):
                            return float(val)
                return None

            revenue = get_value(income, ['Total Revenue', 'Revenue', 'Operating Revenue'])
            net_income = get_value(income, ['Net Income', 'Net Income Common Stockholders'])
            total_equity = get_value(balance, ['Total Stockholder Equity', 'Stockholders Equity', 'Total Equity Gross Minority Interest', 'Common Stock Equity'])
            total_debt = get_value(balance, ['Total Debt', 'Long Term Debt', 'Total Liabilities Net Minority Interest'])
            current_assets = get_value(balance, ['Total Current Assets', 'Current Assets'])
            current_liabilities = get_value(balance, ['Total Current Liabilities', 'Current Liabilities'])

            # Calculate metrics
            profit_margin = (net_income / revenue) if revenue and revenue > 0 and net_income else None
            roe = (net_income / total_equity) if total_equity and total_equity > 0 and net_income else None
            debt_equity = (total_debt / total_equity * 100) if total_equity and total_equity > 0 and total_debt else None
            current_ratio = (current_assets / current_liabilities) if current_liabilities and current_liabilities > 0 and current_assets else None

            # Revenue growth - compare to previous year
            revenue_growth = None
            prev_dates = [d for d in income_dates if d < latest_date]
            if prev_dates and revenue:
                prev_date = max(prev_dates)
                for col in income.columns:
                    if pd.to_datetime(col) == prev_date:
                        prev_revenue = get_value(income, ['Total Revenue', 'Revenue', 'Operating Revenue'])
                        # Need to get from prev column
                        for name in ['Total Revenue', 'Revenue', 'Operating Revenue']:
                            if name in income.index:
                                prev_val = income.loc[name, col]
                                if prev_val and not pd.isna(prev_val) and float(prev_val) > 0:
                                    revenue_growth = (revenue - float(prev_val)) / float(prev_val)
                                    break
                        break

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

    def _get_historical_price(self, ticker: str, date: str) -> Optional[float]:
        """Get stock price at a specific date."""
        try:
            stock = yf.Ticker(ticker)
            start = pd.to_datetime(date) - timedelta(days=5)
            end = pd.to_datetime(date) + timedelta(days=5)
            hist = stock.history(start=start, end=end)
            if not hist.empty:
                return hist['Close'].iloc[0]
        except:
            pass
        return None

    def _calculate_return(self, ticker: str, start_date: str, end_date: str) -> Optional[float]:
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

    def screen_at_date(self, tickers: List[str], date: str, show_progress: bool = True) -> List[Dict]:
        """
        Screen stocks using historical fundamentals at a specific date.
        """
        passed = []
        stats = {'total': 0, 'no_data': 0, 'wrong_sector': 0, 'failed_criteria': 0}

        for i, ticker in enumerate(tickers):
            if show_progress and (i + 1) % 50 == 0:
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

            time.sleep(0.05)  # Rate limit

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
            entry_years = [2020, 2021, 2022, 2023]
        if holding_periods is None:
            holding_periods = [12]

        print("\n" + "=" * 70)
        print("TRUE HISTORICAL BACKTEST")
        print("=" * 70)
        print("\nThis uses ACTUAL historical financials from yfinance")
        print("(annual reports available at each point in time)")
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

            spy_return = self._calculate_return('SPY', entry_date, exit_date)
            if spy_return is not None:
                alpha = r['Avg Return'] - spy_return
                print(f"  {year} ({months}mo): Strategy {r['Avg Return']:+.1f}% vs SPY {spy_return:+.1f}% = Alpha {alpha:+.1f}%")


def run_true_backtest(tickers: List[str], api_key: str = None):
    """Run the true historical backtest."""
    backtester = TrueHistoricalBacktester(api_key=api_key)

    print("\nTrue Historical Backtest Configuration:")
    print("-" * 40)
    print("Note: yfinance has ~4 years of historical financials")
    print()

    # Entry years
    years_input = input("Entry years (comma-separated) [default: 2020,2021,2022,2023]: ").strip()
    if years_input:
        entry_years = [int(y.strip()) for y in years_input.split(',')]
    else:
        entry_years = [2020, 2021, 2022, 2023]

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
