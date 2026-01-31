#!/usr/bin/env python3
"""
Stock Screener - Fundamental Analysis with Historical Backtesting

Features:
1. Screen stocks TODAY based on fundamental criteria
2. Backtest with historical P/E and income growth
3. HYBRID backtest: Current insider ownership + historical fundamentals
4. Test MULTIPLE entry years and holding periods

Criteria:
- Insider ownership > 20%
- P/E ratio < 35
- Net income growth > 10%
"""

import os
from screener import FundamentalScreener
from backtester import FundamentalBacktester, HybridBacktester
from data import get_russell3000, get_sp500


# ============================================================
# CONFIGURATION
# ============================================================

# SimFin API Key (get free key at simfin.com)
SIMFIN_API_KEY = "cda023f3-0157-44f6-a30c-28b4a9c2b36f"

# Set to True for broad market, False for S&P 500 only
USE_BROAD_MARKET = True  # Use S&P 1500 for broader coverage

# Screening criteria
MAX_PE = 35
MIN_INCOME_GROWTH = 10  # percent
MIN_INSIDER_OWNERSHIP = 10  # percent (lowered from 20 - very few stocks have >20%)

# Hybrid backtest settings - test multiple combinations
ENTRY_YEARS = [2016, 2017, 2018, 2019, 2020, 2021]
HOLDING_PERIODS = [1, 2, 3, 4, 5]  # years


# ============================================================
# FUNCTIONS
# ============================================================

def get_stock_universe():
    """Get the stock universe to screen."""
    if USE_BROAD_MARKET:
        print("\n" + "=" * 60)
        print("FETCHING STOCK UNIVERSE")
        print("=" * 60)
        print("(S&P 1500 - covers large, mid, small cap)")
        print()
        return get_russell3000()
    else:
        print("\nUsing S&P 500 for faster processing...")
        return get_sp500()


def run_current_screen():
    """Screen stocks based on current fundamental data."""
    print("\n" + "=" * 60)
    print("CURRENT FUNDAMENTAL SCREEN (Today's Data)")
    print("=" * 60)
    print()
    print("Criteria:")
    print(f"  - Insider Ownership > {MIN_INSIDER_OWNERSHIP}%")
    print(f"  - P/E Ratio < {MAX_PE}")
    print(f"  - Net Income Growth > {MIN_INCOME_GROWTH}%")
    print("  - Price > $5")
    print()

    universe = get_stock_universe()
    print(f"\nTotal stocks to screen: {len(universe)}")

    screener = FundamentalScreener()
    results = screener.screen(
        universe=universe,
        min_insider_ownership=MIN_INSIDER_OWNERSHIP,
        max_pe=MAX_PE,
        min_income_growth=MIN_INCOME_GROWTH,
        min_price=5,
        delay=0.3
    )

    print("\n" + "=" * 60)
    print("CURRENT SCREENING RESULTS")
    print("=" * 60)
    screener.print_results(results, sort_by='insider_ownership')

    return results


def run_hybrid_matrix_backtest():
    """
    Run hybrid backtest across multiple entry years and holding periods.

    Uses:
    - Current insider ownership (from yfinance)
    - Historical P/E and income growth (from SimFin)
    """
    print("\n" + "=" * 70)
    print("HYBRID MATRIX BACKTEST")
    print("=" * 70)
    print()
    print("This tests the strategy across multiple entry years and holding periods.")
    print()
    print("Filters:")
    print(f"  - Insider Ownership > {MIN_INSIDER_OWNERSHIP}% (CURRENT - from today)")
    print(f"  - P/E Ratio < {MAX_PE} (HISTORICAL - at entry date)")
    print(f"  - Income Growth > {MIN_INCOME_GROWTH}% (HISTORICAL - at entry date)")
    print()
    print(f"Entry Years to test: {ENTRY_YEARS}")
    print(f"Holding Periods to test: {HOLDING_PERIODS} years")
    print()

    universe = get_stock_universe()

    backtester = HybridBacktester(api_key=SIMFIN_API_KEY)

    results_df = backtester.run_full_analysis(
        tickers=universe,
        entry_years=ENTRY_YEARS,
        holding_periods=HOLDING_PERIODS,
        min_insider_ownership=MIN_INSIDER_OWNERSHIP,
        max_pe=MAX_PE,
        min_income_growth=MIN_INCOME_GROWTH
    )

    return results_df


def run_single_hybrid_backtest():
    """Run a single hybrid backtest for a specific year."""
    print("\n" + "=" * 60)
    print("SINGLE YEAR HYBRID BACKTEST")
    print("=" * 60)

    year = input("Enter entry year (e.g., 2020): ").strip()
    try:
        year = int(year)
    except ValueError:
        print("Invalid year, using 2020")
        year = 2020

    holding = input("Enter holding period in years (e.g., 3): ").strip()
    try:
        holding = int(holding)
    except ValueError:
        print("Invalid period, using 3 years")
        holding = 3

    universe = get_stock_universe()

    backtester = HybridBacktester(api_key=SIMFIN_API_KEY)

    # Screen stocks
    stocks = backtester.screen_hybrid(
        tickers=universe,
        historical_date=f"{year}-01-01",
        min_insider_ownership=MIN_INSIDER_OWNERSHIP,
        max_pe=MAX_PE,
        min_income_growth=MIN_INCOME_GROWTH
    )

    if stocks:
        print(f"\n{len(stocks)} stocks passed the screen:")
        from tabulate import tabulate
        display = [{
            'Ticker': s['ticker'],
            'Insider %': f"{s['insider_ownership']:.1f}%",
            'P/E': s['pe_ratio'],
            'Growth %': f"{s['income_growth']:.1f}%",
            'Entry Price': f"${s['entry_price']:.2f}" if s['entry_price'] else 'N/A'
        } for s in stocks[:20]]
        print(tabulate(display, headers='keys', tablefmt='grid'))

        # Calculate returns
        returns = backtester.calculate_returns(stocks, holding)
        if returns['avg_return'] is not None:
            print(f"\nResults after {holding} years:")
            print(f"  Average Return: {returns['avg_return']:.1f}%")
            print(f"  Median Return: {returns['median_return']:.1f}%")
            print(f"  Best: {returns['max_return']:.1f}%")
            print(f"  Worst: {returns['min_return']:.1f}%")
            print(f"  Stocks tracked: {returns['num_stocks']}")
    else:
        print("No stocks passed the screening criteria.")

    return stocks


def main():
    """Main entry point."""
    print("\n" + "=" * 70)
    print("FUNDAMENTAL STOCK SCREENER & BACKTESTER")
    print("=" * 70)
    print()
    print("Options:")
    print("  1. Current Screen - Find stocks passing criteria TODAY")
    print("  2. Hybrid Matrix Backtest - Test multiple years & holding periods")
    print("  3. Single Year Hybrid - Test one specific year")
    print("  4. All (Current Screen + Matrix Backtest)")
    print()

    choice = input("Enter choice (1/2/3/4) [default=2]: ").strip() or "2"

    try:
        if choice in ["1", "4"]:
            run_current_screen()

        if choice == "2" or choice == "4":
            run_hybrid_matrix_backtest()

        if choice == "3":
            run_single_hybrid_backtest()

    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70)
    print("Complete!")
    print("=" * 70)


if __name__ == '__main__':
    main()
