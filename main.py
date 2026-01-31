#!/usr/bin/env python3
"""
Stock Screener - Fundamental Analysis with Historical Backtesting

Features:
1. Screen stocks TODAY based on fundamental criteria
2. Analyze TOP PERFORMERS to find winning patterns
3. HYBRID backtest: Current insider ownership + historical fundamentals
4. Test MULTIPLE entry years and holding periods

Criteria:
- Insider ownership
- P/E ratio
- Net income growth
"""

import os
from screener import FundamentalScreener
from backtester import FundamentalBacktester, HybridBacktester, TopPerformersAnalysis
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
MIN_INSIDER_OWNERSHIP = 10  # percent

# Analysis settings
ANALYSIS_YEARS = [2020, 2021, 2022, 2023, 2024]  # Years to analyze
TOP_N = 100  # Number of top performers to analyze per year


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


def run_top_performers_analysis():
    """
    Analyze top performing stocks to find common patterns.

    This is REVERSE ENGINEERING - instead of guessing criteria,
    we look at what actually worked.
    """
    print("\n" + "=" * 70)
    print("TOP PERFORMERS ANALYSIS")
    print("=" * 70)
    print()
    print("This analyzes the top 100 performing stocks from each year")
    print("to find common characteristics (P/E, insider %, growth, sectors).")
    print()
    print(f"Years to analyze: {ANALYSIS_YEARS}")
    print(f"Top performers per year: {TOP_N}")
    print()

    universe = get_stock_universe()

    analyzer = TopPerformersAnalysis(api_key=SIMFIN_API_KEY)

    # Find top performers for each year
    results = analyzer.analyze_multiple_years(
        tickers=universe,
        years=ANALYSIS_YEARS,
        top_n=TOP_N
    )

    # Show top stocks
    analyzer.show_top_stocks(results, n=10)

    # Analyze patterns
    analyzer.summarize_patterns(results)

    return results


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
    """Run hybrid backtest across multiple entry years and holding periods."""
    print("\n" + "=" * 70)
    print("HYBRID MATRIX BACKTEST")
    print("=" * 70)
    print()
    print("Filters:")
    print(f"  - Insider Ownership > {MIN_INSIDER_OWNERSHIP}% (CURRENT)")
    print(f"  - P/E Ratio < {MAX_PE} (HISTORICAL)")
    print(f"  - Income Growth > {MIN_INCOME_GROWTH}% (HISTORICAL)")
    print()

    universe = get_stock_universe()

    backtester = HybridBacktester(api_key=SIMFIN_API_KEY)

    entry_years = [2016, 2017, 2018, 2019, 2020, 2021]
    holding_periods = [1, 2, 3, 4, 5]

    results_df = backtester.run_full_analysis(
        tickers=universe,
        entry_years=entry_years,
        holding_periods=holding_periods,
        min_insider_ownership=MIN_INSIDER_OWNERSHIP,
        max_pe=MAX_PE,
        min_income_growth=MIN_INCOME_GROWTH
    )

    return results_df


def main():
    """Main entry point."""
    print("\n" + "=" * 70)
    print("STOCK ANALYZER & SCREENER")
    print("=" * 70)
    print()
    print("Options:")
    print("  1. TOP PERFORMERS ANALYSIS - Find what winning stocks have in common")
    print("  2. Current Screen - Find stocks passing criteria today")
    print("  3. Hybrid Backtest - Test strategy on historical data")
    print()

    choice = input("Enter choice (1/2/3) [default=1]: ").strip() or "1"

    try:
        if choice == "1":
            run_top_performers_analysis()

        elif choice == "2":
            run_current_screen()

        elif choice == "3":
            run_hybrid_matrix_backtest()

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
