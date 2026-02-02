#!/usr/bin/env python3
"""
Data-Driven Stock Screener

Screens stocks based on criteria derived from winners vs losers analysis.
These thresholds were determined by comparing top performers to bottom performers.
"""

import yfinance as yf
import pandas as pd
import time
import sys
from typing import List, Dict, Any
from tabulate import tabulate


# Screening criteria based on winners vs losers analysis
SCREENING_CRITERIA = {
    'profitMargins': {'min': 0.06, 'name': 'Profit Margin', 'display': '> 6%'},
    'returnOnEquity': {'min': 0.09, 'name': 'ROE', 'display': '> 9%'},
    'revenueGrowth': {'min': 0.07, 'name': 'Revenue Growth', 'display': '> 7%'},
    'debtToEquity': {'max': 65, 'name': 'Debt/Equity', 'display': '< 65'},
    'currentRatio': {'min': 1.8, 'name': 'Current Ratio', 'display': '> 1.8'},
}

# Sectors that produce more winners than losers
ALLOWED_SECTORS = [
    'Energy',
    'Technology',
    'Industrials',
    'Consumer Cyclical'
]


class DataDrivenScreener:
    """Screen stocks using data-driven criteria from winners vs losers analysis."""

    def __init__(self):
        self.results = []
        self.stats = {
            'total_screened': 0,
            'passed_sector': 0,
            'passed_profit_margin': 0,
            'passed_roe': 0,
            'passed_revenue_growth': 0,
            'passed_debt_equity': 0,
            'passed_current_ratio': 0,
            'passed_all': 0,
        }

    def screen_stock(self, ticker: str) -> Dict[str, Any] | None:
        """Screen a single stock against all criteria."""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            if not info or 'sector' not in info:
                return None

            self.stats['total_screened'] += 1

            # Check sector first (fastest filter)
            sector = info.get('sector', '')
            if sector not in ALLOWED_SECTORS:
                return None
            self.stats['passed_sector'] += 1

            # Get metrics
            profit_margin = info.get('profitMargins')
            roe = info.get('returnOnEquity')
            revenue_growth = info.get('revenueGrowth')
            debt_equity = info.get('debtToEquity')
            current_ratio = info.get('currentRatio')

            # Check Profit Margin > 6%
            if profit_margin is None or profit_margin < 0.06:
                return None
            self.stats['passed_profit_margin'] += 1

            # Check ROE > 9%
            if roe is None or roe < 0.09:
                return None
            self.stats['passed_roe'] += 1

            # Check Revenue Growth > 7%
            if revenue_growth is None or revenue_growth < 0.07:
                return None
            self.stats['passed_revenue_growth'] += 1

            # Check Debt/Equity < 65
            if debt_equity is None or debt_equity > 65:
                return None
            self.stats['passed_debt_equity'] += 1

            # Check Current Ratio > 1.8
            if current_ratio is None or current_ratio < 1.8:
                return None
            self.stats['passed_current_ratio'] += 1

            self.stats['passed_all'] += 1

            # Stock passed all filters - collect data
            return {
                'ticker': ticker,
                'name': info.get('shortName', ticker),
                'sector': sector,
                'industry': info.get('industry', '-'),
                'price': info.get('currentPrice', info.get('regularMarketPrice', 0)),
                'market_cap': info.get('marketCap', 0),
                'profit_margin': profit_margin * 100,
                'roe': roe * 100,
                'revenue_growth': revenue_growth * 100,
                'debt_equity': debt_equity,
                'current_ratio': current_ratio,
                'pe_ratio': info.get('trailingPE'),
                'forward_pe': info.get('forwardPE'),
                'price_to_book': info.get('priceToBook'),
                'dividend_yield': (info.get('dividendYield') or 0) * 100,
                'beta': info.get('beta'),
                '52w_change': info.get('52WeekChange', 0) * 100 if info.get('52WeekChange') else None,
            }

        except Exception as e:
            return None

    def screen_universe(self, tickers: List[str], show_progress: bool = True) -> List[Dict[str, Any]]:
        """Screen all stocks in the universe."""
        print("\n" + "=" * 70)
        print("DATA-DRIVEN STOCK SCREENER")
        print("=" * 70)
        print("\nCriteria (based on winners vs losers analysis):")
        print("-" * 50)
        for key, criteria in SCREENING_CRITERIA.items():
            print(f"  {criteria['name']}: {criteria['display']}")
        print(f"  Sectors: {', '.join(ALLOWED_SECTORS)}")
        print("-" * 50)
        print(f"\nScreening {len(tickers)} stocks...\n")

        self.results = []
        total = len(tickers)

        for i, ticker in enumerate(tickers):
            if show_progress and (i + 1) % 25 == 0:
                pct = (i + 1) / total * 100
                sys.stdout.write(f"\r  Progress: {i+1}/{total} ({pct:.1f}%) - Found {len(self.results)} matches")
                sys.stdout.flush()

            result = self.screen_stock(ticker)
            if result:
                self.results.append(result)

            time.sleep(0.05)  # Rate limiting

        if show_progress:
            print(f"\r  Progress: {total}/{total} (100%) - Found {len(self.results)} matches")

        return self.results

    def show_results(self):
        """Display screening results."""
        print("\n" + "=" * 70)
        print("SCREENING RESULTS")
        print("=" * 70)

        # Show funnel stats
        print("\nFilter Funnel:")
        print("-" * 50)
        print(f"  Total screened:      {self.stats['total_screened']}")
        print(f"  Passed Sector:       {self.stats['passed_sector']}")
        print(f"  Passed Profit Margin:{self.stats['passed_profit_margin']}")
        print(f"  Passed ROE:          {self.stats['passed_roe']}")
        print(f"  Passed Rev Growth:   {self.stats['passed_revenue_growth']}")
        print(f"  Passed Debt/Equity:  {self.stats['passed_debt_equity']}")
        print(f"  Passed Current Ratio:{self.stats['passed_current_ratio']}")
        print(f"  >>> PASSED ALL:      {self.stats['passed_all']} <<<")

        if not self.results:
            print("\nNo stocks passed all criteria.")
            return

        # Sort by ROE (highest first)
        self.results.sort(key=lambda x: x['roe'], reverse=True)

        # Show results table
        print(f"\n{len(self.results)} STOCKS PASSED ALL CRITERIA:")
        print("-" * 70)

        table_data = []
        for stock in self.results:
            cap_str = self._format_market_cap(stock['market_cap'])
            table_data.append({
                'Ticker': stock['ticker'],
                'Name': (stock['name'][:20] + '..') if len(stock['name']) > 22 else stock['name'],
                'Sector': stock['sector'][:12],
                'Price': f"${stock['price']:.2f}" if stock['price'] else '-',
                'Cap': cap_str,
                'PM%': f"{stock['profit_margin']:.1f}",
                'ROE%': f"{stock['roe']:.1f}",
                'RevG%': f"{stock['revenue_growth']:.1f}",
                'D/E': f"{stock['debt_equity']:.1f}",
                'CR': f"{stock['current_ratio']:.2f}",
            })

        print(tabulate(table_data, headers='keys', tablefmt='simple'))

        # Sector breakdown
        print("\nSector Breakdown:")
        print("-" * 30)
        sector_counts = {}
        for stock in self.results:
            sector = stock['sector']
            sector_counts[sector] = sector_counts.get(sector, 0) + 1

        for sector, count in sorted(sector_counts.items(), key=lambda x: x[1], reverse=True):
            pct = count / len(self.results) * 100
            print(f"  {sector}: {count} ({pct:.1f}%)")

    def _format_market_cap(self, cap: float) -> str:
        """Format market cap for display."""
        if not cap:
            return '-'
        if cap >= 1e12:
            return f"${cap/1e12:.1f}T"
        elif cap >= 1e9:
            return f"${cap/1e9:.1f}B"
        elif cap >= 1e6:
            return f"${cap/1e6:.0f}M"
        else:
            return f"${cap:.0f}"

    def export_to_csv(self, filename: str = 'screener_results.csv'):
        """Export results to CSV."""
        if not self.results:
            print("No results to export.")
            return

        df = pd.DataFrame(self.results)
        df.to_csv(filename, index=False)
        print(f"\nExported {len(self.results)} stocks to {filename}")


def run_screener(tickers: List[str]):
    """Run the data-driven screener."""
    screener = DataDrivenScreener()
    screener.screen_universe(tickers)
    screener.show_results()

    # Offer export
    print()
    export = input("Export to CSV? (y/n) [default=n]: ").strip().lower()
    if export == 'y':
        screener.export_to_csv('screener_results.csv')

    return screener.results
