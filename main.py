#!/usr/bin/env python3
"""
Stock Screener - Fundamental Analysis with Historical Backtesting

Features:
1. Screen stocks TODAY based on fundamental criteria (yfinance)
2. Backtest the strategy on HISTORICAL data (SimFin)

Criteria:
- Insider ownership > 20% (current screen only - SimFin doesn't have this)
- P/E ratio < 35
- Net income growth > 10%
"""

import os
from screener import FundamentalScreener
from backtester import FundamentalBacktester
from data import get_russell3000, get_sp500


# ============================================================
# CONFIGURATION
# ============================================================

# SimFin API Key (get free key at simfin.com)
SIMFIN_API_KEY = "cda023f3-0157-44f6-a30c-28b4a9c2b36f"

# Set to True for broad market, False for S&P 500 only
USE_BROAD_MARKET = False  # Start with S&P 500 for faster testing

# Screening criteria
MAX_PE = 35
MIN_INCOME_GROWTH = 10  # percent
MIN_INSIDER_OWNERSHIP = 20  # percent (current screen only)

# Backtest settings
BACKTEST_START = "2019-01-01"
BACKTEST_END = "2024-01-01"
REBALANCE_MONTHS = 12  # Rebalance annually


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


def run_historical_backtest():
    """Backtest the fundamental strategy on historical data."""
    print("\n" + "=" * 60)
    print("HISTORICAL BACKTEST (SimFin Data)")
    print("=" * 60)
    print()
    print("Strategy:")
    print(f"  - P/E Ratio < {MAX_PE}")
    print(f"  - Net Income Growth > {MIN_INCOME_GROWTH}%")
    print(f"  - Rebalance every {REBALANCE_MONTHS} months")
    print()
    print("Note: Insider ownership not available in historical data.")
    print()

    universe = get_stock_universe()

    backtester = FundamentalBacktester(api_key=SIMFIN_API_KEY)

    results = backtester.backtest(
        tickers=universe,
        start_date=BACKTEST_START,
        end_date=BACKTEST_END,
        rebalance_months=REBALANCE_MONTHS,
        max_pe=MAX_PE,
        min_income_growth=MIN_INCOME_GROWTH,
        growth_years=3,
        max_holdings=20
    )

    backtester.print_results(results)
    backtester.compare_to_benchmark(results, benchmark_ticker='SPY')

    return results


def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("FUNDAMENTAL STOCK SCREENER & BACKTESTER")
    print("=" * 60)
    print()
    print("Options:")
    print("  1. Current Screen - Find stocks passing criteria TODAY")
    print("  2. Historical Backtest - Test strategy on past data")
    print("  3. Both")
    print()

    choice = input("Enter choice (1/2/3) [default=3]: ").strip() or "3"

    try:
        if choice in ["1", "3"]:
            run_current_screen()

        if choice in ["2", "3"]:
            run_historical_backtest()

    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("Complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()
