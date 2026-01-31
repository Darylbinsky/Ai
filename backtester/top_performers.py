"""
Top Performers Analysis - Find common characteristics of winning stocks.

Analyzes the top performing stocks from each year to identify
patterns and common metrics.
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


class TopPerformersAnalysis:
    """
    Analyze top performing stocks to find common characteristics.

    Instead of guessing criteria, this looks at what actually worked
    and reverse engineers the patterns.
    """

    def __init__(self, api_key: str = None):
        """
        Initialize the analyzer.

        Args:
            api_key: SimFin API key (optional, for fundamental data)
        """
        self.simfin = SimFinData(api_key) if api_key else None
        self._price_cache = {}
        self._info_cache = {}

    def get_yearly_returns(self, ticker: str, year: int) -> Optional[float]:
        """
        Calculate stock return for a specific year.

        Args:
            ticker: Stock ticker
            year: Year to calculate return for

        Returns:
            Percentage return or None
        """
        cache_key = f"{ticker}_{year}"
        if cache_key in self._price_cache:
            return self._price_cache[cache_key]

        try:
            stock = yf.Ticker(ticker)

            # Get data for the year
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"

            hist = stock.history(start=start_date, end=end_date)

            if hist.empty or len(hist) < 50:  # Need at least ~50 trading days
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

    def get_stock_metrics(self, ticker: str, year: int) -> Dict[str, Any]:
        """
        Get stock metrics at the start of a year.

        Args:
            ticker: Stock ticker
            year: Year (metrics are from start of this year)

        Returns:
            Dictionary of metrics
        """
        metrics = {
            'ticker': ticker,
            'year': year,
            'pe_ratio': None,
            'insider_ownership': None,
            'market_cap': None,
            'income_growth': None,
            'sector': None,
        }

        try:
            # Get current info from yfinance (for sector, market cap, insider)
            if ticker not in self._info_cache:
                stock = yf.Ticker(ticker)
                self._info_cache[ticker] = stock.info

            info = self._info_cache[ticker]

            metrics['sector'] = info.get('sector', 'Unknown')
            metrics['market_cap'] = info.get('marketCap')

            insider = info.get('heldPercentInsiders')
            if insider:
                metrics['insider_ownership'] = insider * 100

            # Get historical P/E and growth from SimFin if available
            if self.simfin:
                date_str = f"{year}-01-01"

                pe = self.simfin.get_historical_pe(ticker, date_str)
                if pe and pe > 0:
                    metrics['pe_ratio'] = pe

                growth = self.simfin.get_income_growth(ticker, years=3, as_of_date=date_str)
                if growth:
                    metrics['income_growth'] = growth

        except Exception:
            pass

        return metrics

    def find_top_performers(
        self,
        tickers: List[str],
        year: int,
        top_n: int = 100,
        show_progress: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Find top performing stocks for a specific year.

        Args:
            tickers: List of stock tickers to analyze
            year: Year to analyze
            top_n: Number of top performers to return
            show_progress: Show progress indicator

        Returns:
            List of top performers with their returns and metrics
        """
        print(f"\nAnalyzing {year}...")

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

            time.sleep(0.02)  # Rate limiting

        if show_progress:
            print(f"\r  Processed {total} stocks, {len(results)} had valid returns")

        # Sort by return and get top N
        results.sort(key=lambda x: x['return'], reverse=True)
        top_performers = results[:top_n]

        # Get metrics for top performers
        print(f"  Getting metrics for top {len(top_performers)} performers...")
        for i, stock in enumerate(top_performers):
            if (i + 1) % 20 == 0:
                sys.stdout.write(f"\r  Fetching metrics: {i+1}/{len(top_performers)}")
                sys.stdout.flush()

            metrics = self.get_stock_metrics(stock['ticker'], year)
            stock.update(metrics)
            time.sleep(0.05)

        print(f"\r  Done!                                        ")

        return top_performers

    def analyze_multiple_years(
        self,
        tickers: List[str],
        years: List[int] = None,
        top_n: int = 100
    ) -> Dict[int, List[Dict[str, Any]]]:
        """
        Analyze top performers across multiple years.

        Args:
            tickers: List of stock tickers
            years: List of years to analyze (default: last 5 years)
            top_n: Number of top performers per year

        Returns:
            Dictionary mapping year to list of top performers
        """
        if years is None:
            current_year = datetime.now().year
            years = list(range(current_year - 5, current_year))

        print("\n" + "=" * 70)
        print("TOP PERFORMERS ANALYSIS")
        print("=" * 70)
        print(f"\nAnalyzing top {top_n} performers for years: {years}")
        print(f"Universe: {len(tickers)} stocks")

        all_results = {}

        for year in years:
            top = self.find_top_performers(tickers, year, top_n)
            all_results[year] = top

        return all_results

    def summarize_patterns(self, results: Dict[int, List[Dict[str, Any]]]):
        """
        Summarize common patterns across all top performers.

        Args:
            results: Dictionary from analyze_multiple_years()
        """
        print("\n" + "=" * 70)
        print("PATTERN ANALYSIS - What do top performers have in common?")
        print("=" * 70)

        # Collect all metrics
        all_pe = []
        all_insider = []
        all_growth = []
        all_returns = []
        sector_counts = {}

        for year, performers in results.items():
            for stock in performers:
                all_returns.append(stock.get('return'))

                if stock.get('pe_ratio') and 0 < stock['pe_ratio'] < 500:
                    all_pe.append(stock['pe_ratio'])

                if stock.get('insider_ownership'):
                    all_insider.append(stock['insider_ownership'])

                if stock.get('income_growth'):
                    all_growth.append(stock['income_growth'])

                sector = stock.get('sector', 'Unknown')
                sector_counts[sector] = sector_counts.get(sector, 0) + 1

        # Print summary by year
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
                    'Top 100 Avg Return': f"{np.mean(returns):.1f}%",
                    'Top 100 Median Return': f"{np.median(returns):.1f}%",
                    'Best Stock Return': f"{max(returns):.1f}%",
                    '#100 Return': f"{min(returns):.1f}%"
                })

        print(tabulate(year_summary, headers='keys', tablefmt='grid'))

        # Print metric patterns
        print("\n" + "-" * 70)
        print("COMMON METRICS OF TOP PERFORMERS (at start of year)")
        print("-" * 70)

        metrics_summary = []

        if all_pe:
            metrics_summary.append(['P/E Ratio', f"{np.mean(all_pe):.1f}", f"{np.median(all_pe):.1f}", f"{np.percentile(all_pe, 25):.1f} - {np.percentile(all_pe, 75):.1f}", len(all_pe)])

        if all_insider:
            metrics_summary.append(['Insider %', f"{np.mean(all_insider):.1f}%", f"{np.median(all_insider):.1f}%", f"{np.percentile(all_insider, 25):.1f}% - {np.percentile(all_insider, 75):.1f}%", len(all_insider)])

        if all_growth:
            metrics_summary.append(['Income Growth', f"{np.mean(all_growth):.1f}%", f"{np.median(all_growth):.1f}%", f"{np.percentile(all_growth, 25):.1f}% - {np.percentile(all_growth, 75):.1f}%", len(all_growth)])

        if metrics_summary:
            print(tabulate(metrics_summary,
                          headers=['Metric', 'Mean', 'Median', '25th-75th %ile', 'Data Points'],
                          tablefmt='grid'))
        else:
            print("  Limited metric data available")

        # Print sector breakdown
        print("\n" + "-" * 70)
        print("SECTOR BREAKDOWN OF TOP PERFORMERS")
        print("-" * 70)

        sorted_sectors = sorted(sector_counts.items(), key=lambda x: x[1], reverse=True)
        total_stocks = sum(sector_counts.values())

        sector_table = []
        for sector, count in sorted_sectors[:10]:
            pct = (count / total_stocks) * 100
            sector_table.append([sector, count, f"{pct:.1f}%"])

        print(tabulate(sector_table, headers=['Sector', 'Count', '% of Top Performers'], tablefmt='grid'))

        # Print suggested criteria
        print("\n" + "-" * 70)
        print("SUGGESTED SCREENING CRITERIA (based on analysis)")
        print("-" * 70)

        if all_pe:
            pe_25 = np.percentile(all_pe, 25)
            pe_75 = np.percentile(all_pe, 75)
            print(f"  P/E Ratio: {pe_25:.0f} - {pe_75:.0f} (middle 50% of top performers)")

        if all_insider:
            insider_25 = np.percentile(all_insider, 25)
            print(f"  Insider Ownership: > {insider_25:.1f}% (above 25th percentile)")

        if all_growth:
            growth_25 = np.percentile(all_growth, 25)
            print(f"  Income Growth: > {growth_25:.0f}% (above 25th percentile)")

        top_sectors = [s[0] for s in sorted_sectors[:3] if s[0] != 'Unknown']
        if top_sectors:
            print(f"  Focus Sectors: {', '.join(top_sectors)}")

    def show_top_stocks(self, results: Dict[int, List[Dict[str, Any]]], n: int = 10):
        """Show top N stocks for each year."""
        print("\n" + "=" * 70)
        print(f"TOP {n} STOCKS BY YEAR")
        print("=" * 70)

        for year in sorted(results.keys()):
            performers = results[year][:n]

            print(f"\n{year}:")
            table = []
            for p in performers:
                table.append({
                    'Ticker': p['ticker'],
                    'Return': f"{p['return']:.1f}%",
                    'P/E': f"{p['pe_ratio']:.1f}" if p.get('pe_ratio') else '-',
                    'Insider%': f"{p['insider_ownership']:.1f}" if p.get('insider_ownership') else '-',
                    'Growth%': f"{p['income_growth']:.1f}" if p.get('income_growth') else '-',
                    'Sector': (p.get('sector', '-')[:15]) if p.get('sector') else '-'
                })

            print(tabulate(table, headers='keys', tablefmt='simple'))
