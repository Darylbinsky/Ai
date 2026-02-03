#!/usr/bin/env python3
"""
True Historical Backtester

Uses yfinance historical financial statements to screen stocks
at each historical date, then measures forward returns.
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

    def _get_fundamentals_at_date(self, ticker: str, target_date: str) -> Optional[Dict]:
        """
        Get fundamental metrics using yfinance historical financials.
        """
        try:
            stock = yf.Ticker(ticker)
            target = pd.to_datetime(target_date)

            # Get income statement and balance sheet
            income = stock.financials
            balance = stock.balance_sheet

            if income is None or income.empty:
                return None
            if balance is None or balance.empty:
                return None

            # Columns are dates - find most recent before target date
            income_cols = [c for c in income.columns if pd.to_datetime(c) <= target]
            balance_cols = [c for c in balance.columns if pd.to_datetime(c) <= target]

            if not income_cols or not balance_cols:
                return None

            # Get the most recent column
            latest_income_col = max(income_cols, key=lambda x: pd.to_datetime(x))
            latest_balance_col = max(balance_cols, key=lambda x: pd.to_datetime(x))

            # Helper to get value from dataframe
            def get_val(df, col, possible_names):
                for name in possible_names:
                    try:
                        if name in df.index:
                            val = df.loc[name, col]
                            if pd.notna(val):
                                return float(val)
                    except:
                        pass
                return None

            # Get values
            revenue = get_val(income, latest_income_col, [
                'Total Revenue', 'Revenue', 'Operating Revenue', 'Net Sales'
            ])
            net_income = get_val(income, latest_income_col, [
                'Net Income', 'Net Income Common Stockholders',
                'Net Income From Continuing Operations'
            ])
            total_equity = get_val(balance, latest_balance_col, [
                'Stockholders Equity', 'Total Stockholder Equity',
                'Common Stock Equity', 'Total Equity Gross Minority Interest',
                'Ordinary Shares Number'
            ])
            total_debt = get_val(balance, latest_balance_col, [
                'Total Debt', 'Long Term Debt', 'Total Liabilities Net Minority Interest',
                'Total Non Current Liabilities Net Minority Interest'
            ])
            current_assets = get_val(balance, latest_balance_col, [
                'Current Assets', 'Total Current Assets'
            ])
            current_liab = get_val(balance, latest_balance_col, [
                'Current Liabilities', 'Total Current Liabilities'
            ])

            # Calculate metrics
            profit_margin = None
            if revenue and revenue > 0 and net_income is not None:
                profit_margin = net_income / revenue

            roe = None
            if total_equity and total_equity > 0 and net_income is not None:
                roe = net_income / total_equity

            debt_equity = None
            if total_equity and total_equity > 0 and total_debt is not None:
                debt_equity = (total_debt / total_equity) * 100

            current_ratio = None
            if current_liab and current_liab > 0 and current_assets:
                current_ratio = current_assets / current_liab

            # Revenue growth
            revenue_growth = None
            prev_cols = [c for c in income.columns if pd.to_datetime(c) < pd.to_datetime(latest_income_col)]
            if prev_cols and revenue:
                prev_col = max(prev_cols, key=lambda x: pd.to_datetime(x))
                prev_revenue = get_val(income, prev_col, [
                    'Total Revenue', 'Revenue', 'Operating Revenue', 'Net Sales'
                ])
                if prev_revenue and prev_revenue > 0:
                    revenue_growth = (revenue - prev_revenue) / prev_revenue

            return {
                'profit_margin': profit_margin,
                'roe': roe,
                'revenue_growth': revenue_growth,
                'debt_equity': debt_equity,
                'current_ratio': current_ratio,
            }

        except Exception as e:
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
        """Screen stocks using historical fundamentals at a specific date."""
        passed = []
        stats = {'total': 0, 'no_data': 0, 'wrong_sector': 0, 'failed_criteria': 0}
        fail_reasons = {'pm': 0, 'roe': 0, 'rg': 0, 'de': 0, 'cr': 0}

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

            pm = fundamentals.get('profit_margin')
            roe = fundamentals.get('roe')
            rg = fundamentals.get('revenue_growth')
            de = fundamentals.get('debt_equity')
            cr = fundamentals.get('current_ratio')

            # Check criteria (track which ones fail)
            failed = False
            if pm is None or pm < CRITERIA['profit_margin_min']:
                fail_reasons['pm'] += 1
                failed = True
            if roe is None or roe < CRITERIA['roe_min']:
                fail_reasons['roe'] += 1
                failed = True
            if rg is None or rg < CRITERIA['revenue_growth_min']:
                fail_reasons['rg'] += 1
                failed = True
            if de is None or de > CRITERIA['debt_equity_max']:
                fail_reasons['de'] += 1
                failed = True
            if cr is None or cr < CRITERIA['current_ratio_min']:
                fail_reasons['cr'] += 1
                failed = True

            if failed:
                stats['failed_criteria'] += 1
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

        if show_progress:
            print(f"\r  Screening: {len(tickers)}/{len(tickers)} - {len(passed)} passed")
            print(f"    Wrong sector: {stats['wrong_sector']}, No data: {stats['no_data']}, Failed criteria: {stats['failed_criteria']}")
            print(f"    Fail breakdown - PM: {fail_reasons['pm']}, ROE: {fail_reasons['roe']}, RevG: {fail_reasons['rg']}, D/E: {fail_reasons['de']}, CR: {fail_reasons['cr']}")

        return passed

    def backtest(
        self,
        tickers: List[str],
        entry_years: List[int] = None,
        holding_periods: List[int] = None
    ) -> pd.DataFrame:
        """Run true historical backtest."""
        if entry_years is None:
            entry_years = [2021, 2022, 2023]
        if holding_periods is None:
            holding_periods = [12]

        print("\n" + "=" * 70)
        print("TRUE HISTORICAL BACKTEST")
        print("=" * 70)
        print("\nThis uses ACTUAL historical financials from yfinance")
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

            passed_stocks = self.screen_at_date(tickers, entry_date)

            if not passed_stocks:
                print(f"  No stocks passed criteria for {year}")
                continue

            for months in holding_periods:
                exit_date = (pd.to_datetime(entry_date) + pd.DateOffset(months=months)).strftime('%Y-%m-%d')

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

        if results:
            self._display_results(results)

        return pd.DataFrame(results) if results else None

    def _display_results(self, results: List[Dict]):
        """Display backtest results."""
        print("\n" + "=" * 70)
        print("BACKTEST RESULTS")
        print("=" * 70)

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

        all_avg = np.mean([r['Avg Return'] for r in results])
        all_win = np.mean([r['Win Rate'] for r in results])

        print("\n" + "-" * 70)
        print("OVERALL SUMMARY")
        print("-" * 70)
        print(f"\n  Average Return: {all_avg:+.1f}%")
        print(f"  Average Win Rate: {all_win:.0f}%")

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

    years_input = input("Entry years (comma-separated) [default: 2021,2022,2023]: ").strip()
    if years_input:
        entry_years = [int(y.strip()) for y in years_input.split(',')]
    else:
        entry_years = [2021, 2022, 2023]

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
