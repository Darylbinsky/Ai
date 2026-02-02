"""
Top Performers Analysis - Find common characteristics of winning stocks.

Analyzes 50+ metrics to find which are most predictive of top performance.
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


# All metrics to collect from yfinance
METRICS_TO_COLLECT = {
    # Valuation
    'trailingPE': 'P/E (Trailing)',
    'forwardPE': 'P/E (Forward)',
    'priceToBook': 'Price/Book',
    'priceToSalesTrailing12Months': 'Price/Sales',
    'pegRatio': 'PEG Ratio',
    'enterpriseToRevenue': 'EV/Revenue',
    'enterpriseToEbitda': 'EV/EBITDA',

    # Profitability
    'profitMargins': 'Profit Margin',
    'operatingMargins': 'Operating Margin',
    'grossMargins': 'Gross Margin',
    'returnOnAssets': 'ROA',
    'returnOnEquity': 'ROE',
    'revenuePerShare': 'Revenue/Share',
    'trailingEps': 'EPS (Trailing)',
    'forwardEps': 'EPS (Forward)',

    # Growth
    'revenueGrowth': 'Revenue Growth',
    'earningsGrowth': 'Earnings Growth',
    'earningsQuarterlyGrowth': 'Earnings Growth (Q)',

    # Financial Health
    'debtToEquity': 'Debt/Equity',
    'currentRatio': 'Current Ratio',
    'quickRatio': 'Quick Ratio',
    'totalDebt': 'Total Debt',
    'totalCash': 'Total Cash',
    'totalCashPerShare': 'Cash/Share',
    'freeCashflow': 'Free Cash Flow',
    'operatingCashflow': 'Operating Cash Flow',

    # Size
    'marketCap': 'Market Cap',
    'enterpriseValue': 'Enterprise Value',
    'fullTimeEmployees': 'Employees',
    'floatShares': 'Float Shares',
    'sharesOutstanding': 'Shares Outstanding',

    # Dividends
    'dividendYield': 'Dividend Yield',
    'dividendRate': 'Dividend Rate',
    'payoutRatio': 'Payout Ratio',
    'fiveYearAvgDividendYield': '5Y Avg Dividend Yield',

    # Momentum/Technical
    'beta': 'Beta',
    'fiftyTwoWeekHigh': '52W High',
    'fiftyTwoWeekLow': '52W Low',
    'fiftyDayAverage': '50 Day Avg',
    'twoHundredDayAverage': '200 Day Avg',
    '52WeekChange': '52 Week Change',

    # Ownership
    'heldPercentInsiders': 'Insider Ownership',
    'heldPercentInstitutions': 'Institutional Ownership',
    'shortRatio': 'Short Ratio',
    'shortPercentOfFloat': 'Short % of Float',

    # Other
    'bookValue': 'Book Value',
    'averageVolume': 'Avg Volume',
    'averageVolume10days': 'Avg Volume 10D',
    'averageDailyVolume10Day': 'Avg Daily Volume 10D',
}


class TopPerformersAnalysis:
    """
    Analyze top performing stocks to find common characteristics.
    Collects 50+ metrics and identifies which are most predictive.
    """

    def __init__(self, api_key: str = None):
        self.simfin = SimFinData(api_key) if api_key else None
        self._price_cache = {}
        self._info_cache = {}

    def get_yearly_returns(self, ticker: str, year: int) -> Optional[float]:
        """Calculate stock return for a specific year."""
        cache_key = f"{ticker}_{year}"
        if cache_key in self._price_cache:
            return self._price_cache[cache_key]

        try:
            stock = yf.Ticker(ticker)
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"
            hist = stock.history(start=start_date, end=end_date)

            if hist.empty or len(hist) < 50:
                return None

            start_price = hist['Close'].iloc[0]
            end_price = hist['Close'].iloc[-1]

            if start_price <= 0:
                return None

            ret = ((end_price - start_price) / start_price) * 100
            self._price_cache[cache_key] = ret
            return ret

        except Exception:
            return None

    def get_all_metrics(self, ticker: str) -> Dict[str, Any]:
        """
        Get ALL available metrics for a stock (50+ metrics).
        """
        metrics = {'ticker': ticker}

        try:
            if ticker not in self._info_cache:
                stock = yf.Ticker(ticker)
                self._info_cache[ticker] = stock.info

            info = self._info_cache[ticker]

            # Collect all defined metrics
            for key, name in METRICS_TO_COLLECT.items():
                value = info.get(key)
                if value is not None:
                    # Convert percentages to actual percentages
                    if any(x in name.lower() for x in ['margin', 'growth', 'yield', 'ownership', 'roa', 'roe', 'change']):
                        if isinstance(value, (int, float)) and abs(value) < 10:
                            value = value * 100  # Convert decimal to percentage
                    metrics[key] = value

            # Add sector and industry
            metrics['sector'] = info.get('sector', 'Unknown')
            metrics['industry'] = info.get('industry', 'Unknown')

            # Calculate derived metrics
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            fifty_two_high = info.get('fiftyTwoWeekHigh')
            fifty_two_low = info.get('fiftyTwoWeekLow')
            fifty_day = info.get('fiftyDayAverage')
            two_hundred_day = info.get('twoHundredDayAverage')

            if current_price and fifty_two_high and fifty_two_high > 0:
                metrics['pct_from_52w_high'] = ((current_price - fifty_two_high) / fifty_two_high) * 100

            if current_price and fifty_two_low and fifty_two_low > 0:
                metrics['pct_from_52w_low'] = ((current_price - fifty_two_low) / fifty_two_low) * 100

            if current_price and fifty_day and fifty_day > 0:
                metrics['pct_above_50d'] = ((current_price - fifty_day) / fifty_day) * 100

            if current_price and two_hundred_day and two_hundred_day > 0:
                metrics['pct_above_200d'] = ((current_price - two_hundred_day) / two_hundred_day) * 100

            # Market cap category
            market_cap = info.get('marketCap', 0)
            if market_cap:
                if market_cap >= 200e9:
                    metrics['cap_category'] = 'Mega'
                elif market_cap >= 10e9:
                    metrics['cap_category'] = 'Large'
                elif market_cap >= 2e9:
                    metrics['cap_category'] = 'Mid'
                elif market_cap >= 300e6:
                    metrics['cap_category'] = 'Small'
                else:
                    metrics['cap_category'] = 'Micro'

        except Exception as e:
            pass

        return metrics

    def find_top_performers(
        self,
        tickers: List[str],
        year: int,
        top_n: int = 100,
        show_progress: bool = True,
        find_bottom: bool = False
    ) -> List[Dict[str, Any]]:
        """Find top or bottom performing stocks for a specific year with all metrics."""
        label = "bottom" if find_bottom else "top"
        print(f"\nAnalyzing {year} ({label} performers)...")

        results = []
        total = len(tickers)

        for i, ticker in enumerate(tickers):
            if show_progress and (i + 1) % 50 == 0:
                sys.stdout.write(f"\r  Processing: {i+1}/{total} | Found: {len(results)}")
                sys.stdout.flush()

            try:
                ret = self.get_yearly_returns(ticker, year)
                if ret is not None:
                    results.append({
                        'ticker': ticker,
                        'return': ret,
                        'year': year
                    })
            except Exception:
                continue

            time.sleep(0.02)

        if show_progress:
            print(f"\r  Processed {total} stocks, {len(results)} had valid returns")

        # Sort by return and get top/bottom N
        results.sort(key=lambda x: x['return'], reverse=not find_bottom)
        selected_performers = results[:top_n]

        # Get ALL metrics for selected performers
        label = "bottom" if find_bottom else "top"
        print(f"  Getting 50+ metrics for {label} {len(selected_performers)} performers...")
        for i, stock in enumerate(selected_performers):
            if (i + 1) % 20 == 0:
                sys.stdout.write(f"\r  Fetching metrics: {i+1}/{len(selected_performers)}")
                sys.stdout.flush()

            metrics = self.get_all_metrics(stock['ticker'])
            stock.update(metrics)
            time.sleep(0.05)

        print(f"\r  Done!                                        ")

        return selected_performers

    def analyze_multiple_years(
        self,
        tickers: List[str],
        years: List[int] = None,
        top_n: int = 100,
        find_bottom: bool = False
    ) -> Dict[int, List[Dict[str, Any]]]:
        """Analyze top or bottom performers across multiple years."""
        if years is None:
            current_year = datetime.now().year
            years = list(range(current_year - 5, current_year))

        label = "BOTTOM" if find_bottom else "TOP"
        print("\n" + "=" * 70)
        print(f"{label} PERFORMERS ANALYSIS - 50+ METRICS")
        print("=" * 70)
        print(f"\nAnalyzing {label.lower()} {top_n} performers for years: {years}")
        print(f"Universe: {len(tickers)} stocks")
        print(f"Metrics collected: {len(METRICS_TO_COLLECT)}+")

        all_results = {}
        for year in years:
            performers = self.find_top_performers(tickers, year, top_n, find_bottom=find_bottom)
            all_results[year] = performers

        return all_results

    def analyze_metric_importance(self, results: Dict[int, List[Dict[str, Any]]]) -> pd.DataFrame:
        """
        Analyze which metrics are most common/distinctive among top performers.
        Returns a DataFrame ranking metrics by their predictive value.
        """
        # Collect all metric values
        all_data = []
        for year, performers in results.items():
            for stock in performers:
                all_data.append(stock)

        if not all_data:
            return pd.DataFrame()

        df = pd.DataFrame(all_data)

        # Analyze each numeric metric
        metric_stats = []

        for col in df.columns:
            if col in ['ticker', 'year', 'return', 'sector', 'industry', 'cap_category']:
                continue

            try:
                values = pd.to_numeric(df[col], errors='coerce').dropna()
                if len(values) < 10:
                    continue

                # Get display name
                display_name = METRICS_TO_COLLECT.get(col, col)

                metric_stats.append({
                    'Metric': display_name,
                    'Key': col,
                    'Data Points': len(values),
                    'Mean': values.mean(),
                    'Median': values.median(),
                    'Std Dev': values.std(),
                    '25th %ile': values.quantile(0.25),
                    '75th %ile': values.quantile(0.75),
                    'Min': values.min(),
                    'Max': values.max(),
                })
            except Exception:
                continue

        return pd.DataFrame(metric_stats).sort_values('Data Points', ascending=False)

    def summarize_patterns(self, results: Dict[int, List[Dict[str, Any]]]):
        """Comprehensive pattern analysis across all metrics."""
        print("\n" + "=" * 70)
        print("COMPREHENSIVE PATTERN ANALYSIS")
        print("=" * 70)

        # Returns by year
        print("\n" + "-" * 70)
        print("RETURNS BY YEAR")
        print("-" * 70)

        year_summary = []
        for year in sorted(results.keys()):
            performers = results[year]
            returns = [p['return'] for p in performers if p.get('return')]
            if returns:
                year_summary.append({
                    'Year': year,
                    'Top 100 Avg': f"{np.mean(returns):.1f}%",
                    'Median': f"{np.median(returns):.1f}%",
                    'Best': f"{max(returns):.1f}%",
                    '#100': f"{min(returns):.1f}%"
                })

        print(tabulate(year_summary, headers='keys', tablefmt='grid'))

        # Metric importance analysis
        print("\n" + "-" * 70)
        print("ALL METRICS ANALYSIS (sorted by data availability)")
        print("-" * 70)

        metric_df = self.analyze_metric_importance(results)

        if not metric_df.empty:
            # Show top metrics with most data
            display_df = metric_df.head(30).copy()

            # Format numbers
            for col in ['Mean', 'Median', 'Std Dev', '25th %ile', '75th %ile']:
                display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}" if pd.notna(x) else '-')

            print(tabulate(display_df[['Metric', 'Data Points', 'Mean', 'Median', '25th %ile', '75th %ile']],
                          headers='keys', tablefmt='grid', showindex=False))

        # Sector analysis
        print("\n" + "-" * 70)
        print("SECTOR BREAKDOWN")
        print("-" * 70)

        sector_counts = {}
        for year, performers in results.items():
            for stock in performers:
                sector = stock.get('sector', 'Unknown')
                sector_counts[sector] = sector_counts.get(sector, 0) + 1

        sorted_sectors = sorted(sector_counts.items(), key=lambda x: x[1], reverse=True)
        total = sum(sector_counts.values())

        sector_table = [[s, c, f"{(c/total)*100:.1f}%"] for s, c in sorted_sectors[:10]]
        print(tabulate(sector_table, headers=['Sector', 'Count', '%'], tablefmt='grid'))

        # Market cap analysis
        print("\n" + "-" * 70)
        print("MARKET CAP BREAKDOWN")
        print("-" * 70)

        cap_counts = {}
        for year, performers in results.items():
            for stock in performers:
                cap = stock.get('cap_category', 'Unknown')
                cap_counts[cap] = cap_counts.get(cap, 0) + 1

        cap_order = ['Mega', 'Large', 'Mid', 'Small', 'Micro', 'Unknown']
        cap_table = [[c, cap_counts.get(c, 0), f"{(cap_counts.get(c, 0)/total)*100:.1f}%"]
                     for c in cap_order if c in cap_counts]
        print(tabulate(cap_table, headers=['Cap Category', 'Count', '%'], tablefmt='grid'))

        # Key insights
        print("\n" + "-" * 70)
        print("KEY INSIGHTS FOR SCREENING")
        print("-" * 70)

        if not metric_df.empty:
            # Show recommended ranges for top metrics
            key_metrics = ['trailingPE', 'priceToBook', 'profitMargins', 'returnOnEquity',
                          'revenueGrowth', 'debtToEquity', 'heldPercentInsiders', 'beta']

            print("\nRecommended ranges (25th-75th percentile of top performers):\n")

            for key in key_metrics:
                row = metric_df[metric_df['Key'] == key]
                if not row.empty:
                    row = row.iloc[0]
                    name = row['Metric']
                    low = row['25th %ile']
                    high = row['75th %ile']
                    median = row['Median']
                    print(f"  {name}: {low:.1f} - {high:.1f} (median: {median:.1f})")

    def show_top_stocks(self, results: Dict[int, List[Dict[str, Any]]], n: int = 10):
        """Show top N stocks for each year with key metrics."""
        print("\n" + "=" * 70)
        print(f"TOP {n} STOCKS BY YEAR (with key metrics)")
        print("=" * 70)

        for year in sorted(results.keys()):
            performers = results[year][:n]

            print(f"\n{year}:")
            table = []
            for p in performers:
                table.append({
                    'Ticker': p['ticker'],
                    'Return': f"{p['return']:.0f}%",
                    'P/E': f"{p.get('trailingPE', 0):.1f}" if p.get('trailingPE') else '-',
                    'P/B': f"{p.get('priceToBook', 0):.1f}" if p.get('priceToBook') else '-',
                    'ROE%': f"{p.get('returnOnEquity', 0):.1f}" if p.get('returnOnEquity') else '-',
                    'Insider%': f"{p.get('heldPercentInsiders', 0):.1f}" if p.get('heldPercentInsiders') else '-',
                    'Cap': p.get('cap_category', '-'),
                    'Sector': (p.get('sector', '-')[:12]) if p.get('sector') else '-'
                })

            print(tabulate(table, headers='keys', tablefmt='simple'))

    def export_to_csv(self, results: Dict[int, List[Dict[str, Any]]], filename: str = 'top_performers.csv'):
        """Export all data to CSV for further analysis."""
        all_data = []
        for year, performers in results.items():
            for stock in performers:
                all_data.append(stock)

        df = pd.DataFrame(all_data)
        df.to_csv(filename, index=False)
        print(f"\nExported {len(all_data)} records to {filename}")
        return df

    def compare_winners_vs_losers(
        self,
        winners: Dict[int, List[Dict[str, Any]]],
        losers: Dict[int, List[Dict[str, Any]]]
    ):
        """
        Compare metrics between top performers and bottom performers.
        Shows which metrics best differentiate winners from losers.
        """
        print("\n" + "=" * 70)
        print("WINNERS vs LOSERS COMPARISON")
        print("=" * 70)

        # Collect all data
        winner_data = []
        loser_data = []

        for year, performers in winners.items():
            for stock in performers:
                winner_data.append(stock)

        for year, performers in losers.items():
            for stock in performers:
                loser_data.append(stock)

        if not winner_data or not loser_data:
            print("Not enough data to compare.")
            return

        winner_df = pd.DataFrame(winner_data)
        loser_df = pd.DataFrame(loser_data)

        # Returns comparison
        print("\n" + "-" * 70)
        print("RETURNS COMPARISON")
        print("-" * 70)

        winner_returns = [p['return'] for p in winner_data if p.get('return')]
        loser_returns = [p['return'] for p in loser_data if p.get('return')]

        print(f"\n  WINNERS: {len(winner_returns)} stocks")
        print(f"    Average Return: {np.mean(winner_returns):.1f}%")
        print(f"    Median Return:  {np.median(winner_returns):.1f}%")
        print(f"    Range: {min(winner_returns):.1f}% to {max(winner_returns):.1f}%")

        print(f"\n  LOSERS: {len(loser_returns)} stocks")
        print(f"    Average Return: {np.mean(loser_returns):.1f}%")
        print(f"    Median Return:  {np.median(loser_returns):.1f}%")
        print(f"    Range: {min(loser_returns):.1f}% to {max(loser_returns):.1f}%")

        # Metric comparison
        print("\n" + "-" * 70)
        print("METRIC COMPARISON (Winners vs Losers)")
        print("-" * 70)
        print("\nMetrics sorted by how well they differentiate winners from losers:\n")

        comparison_results = []

        for col in winner_df.columns:
            if col in ['ticker', 'year', 'return', 'sector', 'industry', 'cap_category']:
                continue

            try:
                winner_vals = pd.to_numeric(winner_df[col], errors='coerce').dropna()
                loser_vals = pd.to_numeric(loser_df[col], errors='coerce').dropna()

                if len(winner_vals) < 10 or len(loser_vals) < 10:
                    continue

                winner_median = winner_vals.median()
                loser_median = loser_vals.median()

                # Calculate difference
                if loser_median != 0:
                    pct_diff = ((winner_median - loser_median) / abs(loser_median)) * 100
                else:
                    pct_diff = 0 if winner_median == 0 else 100

                display_name = METRICS_TO_COLLECT.get(col, col)

                comparison_results.append({
                    'Metric': display_name,
                    'Key': col,
                    'Winner Median': winner_median,
                    'Loser Median': loser_median,
                    'Difference': winner_median - loser_median,
                    'Pct Diff': pct_diff,
                    'Data Points': min(len(winner_vals), len(loser_vals))
                })

            except Exception:
                continue

        # Sort by absolute percentage difference
        comparison_results.sort(key=lambda x: abs(x['Pct Diff']), reverse=True)

        # Display top 20 most differentiating metrics
        table_data = []
        for row in comparison_results[:25]:
            table_data.append({
                'Metric': row['Metric'],
                'Winner': f"{row['Winner Median']:.2f}",
                'Loser': f"{row['Loser Median']:.2f}",
                'Diff': f"{row['Difference']:+.2f}",
                'Diff%': f"{row['Pct Diff']:+.1f}%",
            })

        print(tabulate(table_data, headers='keys', tablefmt='grid'))

        # Sector comparison
        print("\n" + "-" * 70)
        print("SECTOR COMPARISON")
        print("-" * 70)

        winner_sectors = {}
        loser_sectors = {}

        for stock in winner_data:
            sector = stock.get('sector', 'Unknown')
            winner_sectors[sector] = winner_sectors.get(sector, 0) + 1

        for stock in loser_data:
            sector = stock.get('sector', 'Unknown')
            loser_sectors[sector] = loser_sectors.get(sector, 0) + 1

        all_sectors = set(list(winner_sectors.keys()) + list(loser_sectors.keys()))
        total_winners = len(winner_data)
        total_losers = len(loser_data)

        sector_table = []
        for sector in all_sectors:
            w_count = winner_sectors.get(sector, 0)
            l_count = loser_sectors.get(sector, 0)
            w_pct = (w_count / total_winners) * 100 if total_winners > 0 else 0
            l_pct = (l_count / total_losers) * 100 if total_losers > 0 else 0
            diff = w_pct - l_pct
            sector_table.append({
                'Sector': sector,
                'Winners': f"{w_pct:.1f}%",
                'Losers': f"{l_pct:.1f}%",
                'Diff': f"{diff:+.1f}%"
            })

        sector_table.sort(key=lambda x: float(x['Diff'].replace('%', '').replace('+', '')), reverse=True)
        print("\n" + tabulate(sector_table[:10], headers='keys', tablefmt='grid'))

        # Actionable insights
        print("\n" + "-" * 70)
        print("ACTIONABLE SCREENING CRITERIA")
        print("-" * 70)
        print("\nBased on winner vs loser comparison, consider these filters:\n")

        # Show key metrics with clear thresholds
        key_metrics = ['trailingPE', 'priceToBook', 'profitMargins', 'returnOnEquity',
                      'revenueGrowth', 'debtToEquity', 'heldPercentInsiders', 'beta',
                      'earningsGrowth', 'currentRatio']

        for key in key_metrics:
            winner_row = None
            loser_row = None
            for row in comparison_results:
                if row['Key'] == key:
                    winner_row = row
                    break

            if winner_row:
                w_med = winner_row['Winner Median']
                l_med = winner_row['Loser Median']
                name = winner_row['Metric']

                # Determine if higher or lower is better
                if w_med > l_med:
                    direction = "HIGHER is better"
                    suggestion = f"Look for: > {l_med:.1f}"
                else:
                    direction = "LOWER is better"
                    suggestion = f"Look for: < {l_med:.1f}"

                print(f"  {name}:")
                print(f"    Winners: {w_med:.2f} | Losers: {l_med:.2f} ({direction})")
                print(f"    {suggestion}")
                print()
