"""Fundamental stock screener using yfinance data."""

import yfinance as yf
import time
import sys
from typing import List, Dict, Any, Optional


class FundamentalScreener:
    """Screen stocks based on fundamental criteria."""

    def __init__(self):
        self._cache = {}

    def get_fundamentals(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get fundamental data for a stock.

        Returns dict with: pe_ratio, insider_ownership, net_income_growth, etc.
        """
        if symbol in self._cache:
            return self._cache[symbol]

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            # Get P/E ratio
            pe_ratio = info.get('trailingPE') or info.get('forwardPE')

            # Get insider ownership percentage
            insider_pct = info.get('heldPercentInsiders', 0)
            if insider_pct:
                insider_pct = insider_pct * 100  # Convert to percentage

            # Get net income growth (compare recent years)
            net_income_growth = None
            try:
                financials = ticker.financials
                if financials is not None and not financials.empty:
                    if 'Net Income' in financials.index:
                        net_incomes = financials.loc['Net Income'].dropna()
                        if len(net_incomes) >= 2:
                            recent = net_incomes.iloc[0]
                            oldest = net_incomes.iloc[-1]
                            if oldest != 0 and oldest > 0:
                                years = len(net_incomes) - 1
                                # Calculate CAGR
                                if recent > 0:
                                    net_income_growth = ((recent / oldest) ** (1/years) - 1) * 100
            except Exception:
                pass

            # Get other useful metrics
            result = {
                'symbol': symbol,
                'price': info.get('currentPrice') or info.get('regularMarketPrice'),
                'pe_ratio': round(pe_ratio, 2) if pe_ratio else None,
                'insider_ownership': round(insider_pct, 2) if insider_pct else None,
                'net_income_growth': round(net_income_growth, 2) if net_income_growth else None,
                'market_cap': info.get('marketCap'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'profit_margin': round(info.get('profitMargins', 0) * 100, 2) if info.get('profitMargins') else None,
                'revenue_growth': round(info.get('revenueGrowth', 0) * 100, 2) if info.get('revenueGrowth') else None,
                'roe': round(info.get('returnOnEquity', 0) * 100, 2) if info.get('returnOnEquity') else None,
            }

            self._cache[symbol] = result
            return result

        except Exception as e:
            return None

    def screen(
        self,
        universe: List[str],
        min_insider_ownership: float = 0,
        max_pe: float = None,
        min_income_growth: float = None,
        min_price: float = 0,
        max_price: float = None,
        show_progress: bool = True,
        delay: float = 0.2
    ) -> List[Dict[str, Any]]:
        """
        Screen stocks based on fundamental criteria.

        Args:
            universe: List of stock symbols to screen
            min_insider_ownership: Minimum insider ownership percentage (e.g., 20 for 20%)
            max_pe: Maximum P/E ratio (e.g., 35)
            min_income_growth: Minimum net income growth % (e.g., 10 for 10%)
            min_price: Minimum stock price
            max_price: Maximum stock price
            show_progress: Show progress indicator
            delay: Delay between requests (seconds)

        Returns:
            List of stocks that pass all criteria
        """
        results = []
        total = len(universe)
        errors = 0
        skipped = 0

        for i, symbol in enumerate(universe):
            if show_progress:
                pct = (i + 1) / total * 100
                passed = len(results)
                sys.stdout.write(
                    f"\rScreening: {i+1}/{total} ({pct:.1f}%) | "
                    f"Passed: {passed} | Skipped: {skipped} | Errors: {errors} | "
                    f"Current: {symbol}    "
                )
                sys.stdout.flush()

            try:
                data = self.get_fundamentals(symbol)

                if data is None:
                    errors += 1
                    continue

                # Check price filter
                if data['price']:
                    if data['price'] < min_price:
                        skipped += 1
                        continue
                    if max_price and data['price'] > max_price:
                        skipped += 1
                        continue

                # Check insider ownership
                if min_insider_ownership > 0:
                    if data['insider_ownership'] is None:
                        skipped += 1
                        continue
                    if data['insider_ownership'] < min_insider_ownership:
                        skipped += 1
                        continue

                # Check P/E ratio
                if max_pe is not None:
                    if data['pe_ratio'] is None:
                        skipped += 1
                        continue
                    if data['pe_ratio'] <= 0:  # Skip negative P/E
                        skipped += 1
                        continue
                    if data['pe_ratio'] > max_pe:
                        skipped += 1
                        continue

                # Check net income growth
                if min_income_growth is not None:
                    if data['net_income_growth'] is None:
                        skipped += 1
                        continue
                    if data['net_income_growth'] < min_income_growth:
                        skipped += 1
                        continue

                # Passed all filters!
                results.append(data)

            except Exception as e:
                errors += 1

            if delay > 0:
                time.sleep(delay)

        if show_progress:
            print(f"\n\nScreening complete! {len(results)} stocks passed out of {total} screened.")
            print(f"(Skipped: {skipped}, Errors: {errors})")

        return results

    def print_results(self, results: List[Dict[str, Any]], sort_by: str = 'insider_ownership'):
        """Print screening results in a formatted table."""
        if not results:
            print("No stocks passed the screening criteria.")
            return

        from tabulate import tabulate

        # Sort results
        results = sorted(
            results,
            key=lambda x: x.get(sort_by) if x.get(sort_by) is not None else -999,
            reverse=True
        )

        # Format for display
        display_data = []
        for r in results:
            display_data.append({
                'Symbol': r['symbol'],
                'Price': f"${r['price']:.2f}" if r['price'] else 'N/A',
                'P/E': r['pe_ratio'] if r['pe_ratio'] else 'N/A',
                'Insider %': f"{r['insider_ownership']:.1f}%" if r['insider_ownership'] else 'N/A',
                'Income Growth': f"{r['net_income_growth']:.1f}%" if r['net_income_growth'] else 'N/A',
                'Sector': r['sector'][:20] if r['sector'] else 'N/A',
            })

        print(tabulate(display_data, headers='keys', tablefmt='grid'))
        print(f"\nTotal: {len(results)} stocks passed screening")
