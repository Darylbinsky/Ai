#!/usr/bin/env python3
"""
Strategy Optimizer

Caches all data upfront then tests many criteria combinations quickly
to find consistent alpha.
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
from typing import List, Dict, Tuple
import time
import sys
from tabulate import tabulate
from itertools import product


ALLOWED_SECTORS = ['Energy', 'Technology', 'Industrials', 'Consumer Cyclical']


class StrategyOptimizer:
    """Optimize screening criteria for consistent alpha."""

    def __init__(self):
        self.data_cache = {}  # ticker -> {sector, financials, prices}
        self.spy_returns = {}  # year -> return

    def load_all_data(self, tickers: List[str], years: List[int]):
        """Load all data upfront for speed."""
        print("\n" + "=" * 70)
        print("LOADING DATA (this is the slow part - only happens once)")
        print("=" * 70)

        # Calculate date range needed
        start_year = min(years) - 1
        end_year = max(years) + 1

        total = len(tickers)
        loaded = 0
        skipped = 0

        for i, ticker in enumerate(tickers):
            if (i + 1) % 50 == 0:
                sys.stdout.write(f"\r  Loading: {i+1}/{total} ({loaded} valid, {skipped} skipped)")
                sys.stdout.flush()

            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                sector = info.get('sector')

                # Skip wrong sectors early
                if sector not in ALLOWED_SECTORS:
                    skipped += 1
                    continue

                # Get financials
                income = stock.financials
                balance = stock.balance_sheet

                if income is None or income.empty or balance is None or balance.empty:
                    skipped += 1
                    continue

                # Get price history
                hist = stock.history(start=f"{start_year}-01-01", end=f"{end_year+1}-01-31")
                if hist.empty:
                    skipped += 1
                    continue

                self.data_cache[ticker] = {
                    'sector': sector,
                    'income': income,
                    'balance': balance,
                    'prices': hist,
                    'info': info,
                }
                loaded += 1

            except Exception as e:
                skipped += 1
                continue

            time.sleep(0.02)

        print(f"\r  Loaded {loaded} stocks, skipped {skipped}                    ")

        # Load SPY returns for each year
        print("  Loading SPY benchmark...")
        for year in years:
            entry = f"{year}-01-02"
            exit_date = f"{year+1}-01-02"
            try:
                spy = yf.Ticker('SPY')
                hist = spy.history(start=entry, end=exit_date)
                if len(hist) >= 2:
                    self.spy_returns[year] = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
            except:
                pass

        print(f"  SPY returns: {self.spy_returns}")
        print(f"\nData loaded! Now testing will be fast.\n")

    def get_fundamentals(self, ticker: str, year: int) -> Dict:
        """Get fundamentals from cache for a specific year."""
        if ticker not in self.data_cache:
            return None

        data = self.data_cache[ticker]
        income = data['income']
        balance = data['balance']
        target = pd.to_datetime(f"{year}-01-02")

        try:
            # Find most recent financial data before target
            income_cols = [c for c in income.columns if pd.to_datetime(c) <= target]
            balance_cols = [c for c in balance.columns if pd.to_datetime(c) <= target]

            if not income_cols or not balance_cols:
                return None

            inc_col = max(income_cols, key=lambda x: pd.to_datetime(x))
            bal_col = max(balance_cols, key=lambda x: pd.to_datetime(x))

            def get_val(df, col, names):
                for name in names:
                    if name in df.index:
                        val = df.loc[name, col]
                        if pd.notna(val):
                            return float(val)
                return None

            revenue = get_val(income, inc_col, ['Total Revenue', 'Revenue'])
            net_income = get_val(income, inc_col, ['Net Income', 'Net Income Common Stockholders'])
            equity = get_val(balance, bal_col, ['Stockholders Equity', 'Common Stock Equity', 'Total Equity Gross Minority Interest'])
            debt = get_val(balance, bal_col, ['Total Debt', 'Long Term Debt', 'Total Liabilities Net Minority Interest'])
            cur_assets = get_val(balance, bal_col, ['Current Assets', 'Total Current Assets'])
            cur_liab = get_val(balance, bal_col, ['Current Liabilities', 'Total Current Liabilities'])

            # Calculate metrics
            pm = (net_income / revenue) if revenue and revenue > 0 and net_income else None
            roe = (net_income / equity) if equity and equity > 0 and net_income else None
            de = (debt / equity * 100) if equity and equity > 0 and debt else None
            cr = (cur_assets / cur_liab) if cur_liab and cur_liab > 0 and cur_assets else None

            # Revenue growth
            rg = None
            prev_cols = [c for c in income.columns if pd.to_datetime(c) < pd.to_datetime(inc_col)]
            if prev_cols and revenue:
                prev_col = max(prev_cols, key=lambda x: pd.to_datetime(x))
                prev_rev = get_val(income, prev_col, ['Total Revenue', 'Revenue'])
                if prev_rev and prev_rev > 0:
                    rg = (revenue - prev_rev) / prev_rev

            return {'pm': pm, 'roe': roe, 'rg': rg, 'de': de, 'cr': cr}

        except:
            return None

    def get_return(self, ticker: str, year: int) -> float:
        """Get 12-month return from cache."""
        if ticker not in self.data_cache:
            return None

        prices = self.data_cache[ticker]['prices']
        start = pd.to_datetime(f"{year}-01-02")
        end = pd.to_datetime(f"{year+1}-01-02")

        try:
            # Find prices near start and end dates
            start_prices = prices[prices.index >= start].head(5)
            end_prices = prices[prices.index >= end].head(5)

            if start_prices.empty or end_prices.empty:
                return None

            start_price = start_prices['Close'].iloc[0]
            end_price = end_prices['Close'].iloc[0]

            return ((end_price - start_price) / start_price) * 100
        except:
            return None

    def test_criteria(self, pm_min: float, roe_min: float, rg_min: float,
                     de_max: float, cr_min: float, years: List[int]) -> Dict:
        """Test a specific set of criteria across years."""
        results = []

        for year in years:
            passed = []

            for ticker, data in self.data_cache.items():
                fund = self.get_fundamentals(ticker, year)
                if not fund:
                    continue

                # Apply criteria
                if fund['pm'] is None or fund['pm'] < pm_min:
                    continue
                if fund['roe'] is None or fund['roe'] < roe_min:
                    continue
                if fund['rg'] is None or fund['rg'] < rg_min:
                    continue
                if fund['de'] is None or fund['de'] > de_max:
                    continue
                if fund['cr'] is None or fund['cr'] < cr_min:
                    continue

                ret = self.get_return(ticker, year)
                if ret is not None:
                    passed.append(ret)

            if passed and year in self.spy_returns:
                avg_ret = np.mean(passed)
                spy_ret = self.spy_returns[year]
                alpha = avg_ret - spy_ret
                results.append({
                    'year': year,
                    'stocks': len(passed),
                    'avg_return': avg_ret,
                    'spy_return': spy_ret,
                    'alpha': alpha,
                })

        if not results:
            return None

        # Calculate consistency score
        alphas = [r['alpha'] for r in results]
        avg_alpha = np.mean(alphas)
        positive_years = sum(1 for a in alphas if a > 0)
        consistency = positive_years / len(alphas)

        return {
            'results': results,
            'avg_alpha': avg_alpha,
            'consistency': consistency,
            'total_stocks': sum(r['stocks'] for r in results),
        }

    def optimize(self, years: List[int], show_top: int = 10):
        """Test many criteria combinations and find the best."""
        print("=" * 70)
        print("OPTIMIZING CRITERIA")
        print("=" * 70)

        # Define parameter ranges to test
        pm_range = [0.03, 0.05, 0.07, 0.10]       # 3%, 5%, 7%, 10%
        roe_range = [0.05, 0.08, 0.12, 0.15]      # 5%, 8%, 12%, 15%
        rg_range = [0.0, 0.05, 0.10, 0.15]        # 0%, 5%, 10%, 15%
        de_range = [50, 80, 120, 200]             # Max debt/equity
        cr_range = [1.0, 1.5, 2.0, 2.5]           # Min current ratio

        combinations = list(product(pm_range, roe_range, rg_range, de_range, cr_range))
        print(f"\nTesting {len(combinations)} criteria combinations...")

        best_results = []

        for i, (pm, roe, rg, de, cr) in enumerate(combinations):
            if (i + 1) % 100 == 0:
                sys.stdout.write(f"\r  Progress: {i+1}/{len(combinations)}")
                sys.stdout.flush()

            result = self.test_criteria(pm, roe, rg, de, cr, years)
            if result and result['total_stocks'] >= len(years) * 5:  # At least 5 stocks per year
                best_results.append({
                    'pm': pm, 'roe': roe, 'rg': rg, 'de': de, 'cr': cr,
                    **result
                })

        print(f"\r  Tested {len(combinations)} combinations, {len(best_results)} valid")

        # Sort by consistency first, then by alpha
        best_results.sort(key=lambda x: (x['consistency'], x['avg_alpha']), reverse=True)

        # Display top results
        print("\n" + "=" * 70)
        print(f"TOP {show_top} CRITERIA COMBINATIONS")
        print("=" * 70)

        for i, r in enumerate(best_results[:show_top]):
            print(f"\n#{i+1}: PM>{r['pm']*100:.0f}%, ROE>{r['roe']*100:.0f}%, RevG>{r['rg']*100:.0f}%, D/E<{r['de']:.0f}, CR>{r['cr']:.1f}")
            print(f"    Avg Alpha: {r['avg_alpha']:+.1f}%, Consistency: {r['consistency']*100:.0f}% of years beat SPY")
            print(f"    Stocks/year: ~{r['total_stocks']//len(years)}")

            # Show year-by-year
            for yr in r['results']:
                symbol = "+" if yr['alpha'] > 0 else "-"
                print(f"      {yr['year']}: {yr['avg_return']:+.1f}% vs SPY {yr['spy_return']:+.1f}% = {yr['alpha']:+.1f}% {symbol}")

        return best_results[:show_top]


def run_optimizer(tickers: List[str]):
    """Run the strategy optimizer."""
    optimizer = StrategyOptimizer()

    print("\nStrategy Optimizer")
    print("-" * 40)

    years_input = input("Years to test (comma-separated) [default: 2023,2024,2025]: ").strip()
    if years_input:
        years = [int(y.strip()) for y in years_input.split(',')]
    else:
        years = [2023, 2024, 2025]

    # Load all data first
    optimizer.load_all_data(tickers, years)

    # Run optimization
    best = optimizer.optimize(years)

    return best
