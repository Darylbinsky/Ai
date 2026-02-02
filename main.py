#!/usr/bin/env python3
"""
Stock Analyzer - Find Winning Patterns by Comparing Winners vs Losers

Analyzes BOTH top and bottom performing stocks to discover
what metrics differentiate winners from losers.

This is REVERSE ENGINEERING - we look at actual winners AND losers
to find patterns that truly matter.
"""

from backtester import TopPerformersAnalysis
from data import get_russell3000, get_sp500


# ============================================================
# CONFIGURATION
# ============================================================

# SimFin API Key (get free key at simfin.com)
SIMFIN_API_KEY = "cda023f3-0157-44f6-a30c-28b4a9c2b36f"

# Set to True for S&P 1500 (broad market), False for S&P 500 only
USE_BROAD_MARKET = True

# Analysis settings
ANALYSIS_YEARS = [2020, 2021, 2022, 2023, 2024]  # Years to analyze
TOP_N = 50  # Number of top/bottom performers per year


# ============================================================
# MAIN
# ============================================================

def get_stock_universe():
    """Get the stock universe to analyze."""
    if USE_BROAD_MARKET:
        print("\n" + "=" * 60)
        print("FETCHING STOCK UNIVERSE")
        print("=" * 60)
        print("(S&P 1500 - covers large, mid, small cap)")
        print()
        return get_russell3000()
    else:
        print("\nUsing S&P 500...")
        return get_sp500()


def main():
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
    print("By comparing winners AND losers, we can find:")
    print("  - Metrics where winners clearly differ from losers")
    print("  - What to LOOK FOR (winner characteristics)")
    print("  - What to AVOID (loser characteristics)")
    print("  - Actionable screening criteria with clear thresholds")
    print()

    input("Press Enter to start analysis...")

    # Get universe
    universe = get_stock_universe()

    # Create analyzer
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

    # Show comparison - the key insight!
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
        print("Open in Excel to do your own analysis!")

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE!")
    print("=" * 70)
    print()
    print("Key takeaways:")
    print("  1. Look at the METRIC COMPARISON table above")
    print("  2. Metrics with large Diff% are most predictive")
    print("  3. Use the ACTIONABLE SCREENING CRITERIA section")
    print("  4. Sectors with positive diff = more winners than losers")
    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
