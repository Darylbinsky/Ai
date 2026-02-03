#!/usr/bin/env python3
"""
Stock Analyzer - Data-Driven Stock Screening

Two modes:
1. ANALYZE: Compare winners vs losers to find what metrics matter
2. SCREEN: Apply data-driven criteria to find stocks today

Criteria based on winners vs losers analysis:
- Profit Margin > 6%
- ROE > 9%
- Revenue Growth > 7%
- Debt/Equity < 65
- Current Ratio > 1.8
- Sectors: Energy, Tech, Industrials, Consumer Cyclical
"""

from backtester import TopPerformersAnalysis
from backtester.strategy_backtest import run_backtest
from backtester.true_historical_backtest import run_true_backtest
from backtester.optimizer import run_optimizer
from screener.data_driven_screener import run_screener
from data import get_russell3000, get_sp500


# ============================================================
# CONFIGURATION
# ============================================================

# SimFin API Key (get free key at simfin.com)
SIMFIN_API_KEY = "cda023f3-0157-44f6-a30c-28b4a9c2b36f"

# Set to True for S&P 1500 (broad market), False for S&P 500 only
USE_BROAD_MARKET = True

# Analysis settings
ANALYSIS_YEARS = [2020, 2021, 2022, 2023, 2024]
TOP_N = 50


# ============================================================
# MAIN
# ============================================================

def get_stock_universe():
    """Get the stock universe to analyze."""
    if USE_BROAD_MARKET:
        print("\nFetching S&P 1500 stock list...")
        return get_russell3000()
    else:
        print("\nUsing S&P 500...")
        return get_sp500()


def run_analysis():
    """Analyze top AND bottom performers to find what truly differentiates winners."""
    print("\n" + "=" * 70)
    print("WINNERS vs LOSERS ANALYSIS - 50+ METRICS")
    print("=" * 70)
    print()
    print("This will analyze BOTH top AND bottom performing stocks")
    print("to find what metrics truly differentiate winners from losers.")
    print()
    print(f"  Years to analyze: {ANALYSIS_YEARS}")
    print(f"  Top performers per year: {TOP_N}")
    print(f"  Bottom performers per year: {TOP_N}")
    print(f"  Total stocks to analyze: {TOP_N * len(ANALYSIS_YEARS) * 2}")
    print()

    input("Press Enter to start analysis...")

    universe = get_stock_universe()
    analyzer = TopPerformersAnalysis(api_key=SIMFIN_API_KEY)

    # Analyze TOP performers
    print("\n" + "#" * 70)
    print("PHASE 1: Analyzing TOP performers...")
    print("#" * 70)
    winners = analyzer.analyze_multiple_years(
        tickers=universe,
        years=ANALYSIS_YEARS,
        top_n=TOP_N,
        find_bottom=False
    )

    # Analyze BOTTOM performers
    print("\n" + "#" * 70)
    print("PHASE 2: Analyzing BOTTOM performers...")
    print("#" * 70)
    losers = analyzer.analyze_multiple_years(
        tickers=universe,
        years=ANALYSIS_YEARS,
        top_n=TOP_N,
        find_bottom=True
    )

    # Show comparison
    print("\n" + "#" * 70)
    print("PHASE 3: Comparing Winners vs Losers...")
    print("#" * 70)
    analyzer.compare_winners_vs_losers(winners, losers)

    # Offer to export
    print()
    export = input("Export data to CSV? (y/n) [default=n]: ").strip().lower()
    if export == 'y':
        analyzer.export_to_csv(winners, 'winners_analysis.csv')
        analyzer.export_to_csv(losers, 'losers_analysis.csv')
        print("Data exported to winners_analysis.csv and losers_analysis.csv")


def run_stock_screener():
    """Run the data-driven stock screener."""
    universe = get_stock_universe()
    run_screener(universe)


def run_strategy_backtest():
    """Run the strategy backtest (uses current fundamentals)."""
    universe = get_stock_universe()
    run_backtest(universe)


def run_true_historical_backtest():
    """Run TRUE historical backtest using yfinance data."""
    universe = get_stock_universe()
    run_true_backtest(universe, api_key=SIMFIN_API_KEY)


def run_strategy_optimizer():
    """Run the strategy optimizer to find best criteria."""
    universe = get_stock_universe()
    run_optimizer(universe)


def main():
    """Main menu."""
    print("\n" + "=" * 70)
    print("STOCK ANALYZER - DATA-DRIVEN SCREENING")
    print("=" * 70)
    print()
    print("Options:")
    print()
    print("  1. SCREEN STOCKS NOW")
    print("     Apply data-driven criteria to find stocks today")
    print()
    print("  2. BACKTEST (True Historical)")
    print("     Test current criteria across multiple years")
    print()
    print("  3. OPTIMIZE CRITERIA (Recommended)")
    print("     Auto-test 1000+ criteria combinations to find consistent alpha")
    print("     Loads data once, then tests fast")
    print()
    print("  4. RUN ANALYSIS")
    print("     Compare winners vs losers to understand what works")
    print()

    choice = input("Enter choice (1, 2, 3, or 4) [default=1]: ").strip()

    if choice == '2':
        run_true_historical_backtest()
    elif choice == '3':
        run_strategy_optimizer()
    elif choice == '4':
        run_analysis()
    else:
        run_stock_screener()

    print("\n" + "=" * 70)
    print("DONE!")
    print("=" * 70)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
