#!/usr/bin/env python3
"""
Stock Analyzer - Find Winning Patterns

Analyzes the top performing stocks from each year to discover
what metrics/characteristics they have in common.

This is REVERSE ENGINEERING - instead of guessing what works,
we look at actual winners and find patterns.
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
TOP_N = 50  # Number of top performers per year (50 = 250 total stocks analyzed)


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
    """Analyze top performers to find winning patterns."""
    print("\n" + "=" * 70)
    print("TOP PERFORMERS ANALYSIS - 50+ METRICS")
    print("=" * 70)
    print()
    print("This will analyze the top performing stocks from each year")
    print("and find what 50+ metrics they have in common.")
    print()
    print(f"  Years to analyze: {ANALYSIS_YEARS}")
    print(f"  Top performers per year: {TOP_N}")
    print(f"  Total stocks to analyze: {TOP_N * len(ANALYSIS_YEARS)}")
    print()
    print("Metrics collected include:")
    print("  - Valuation: P/E, P/B, P/S, PEG, EV/EBITDA")
    print("  - Profitability: ROE, ROA, margins")
    print("  - Growth: revenue growth, earnings growth")
    print("  - Financial: debt/equity, current ratio, cash flow")
    print("  - Ownership: insider %, institutional %, short interest")
    print("  - Momentum: beta, 52-week range, moving averages")
    print("  - And 30+ more...")
    print()

    input("Press Enter to start analysis...")

    # Get universe
    universe = get_stock_universe()

    # Create analyzer
    analyzer = TopPerformersAnalysis(api_key=SIMFIN_API_KEY)

    # Run analysis
    results = analyzer.analyze_multiple_years(
        tickers=universe,
        years=ANALYSIS_YEARS,
        top_n=TOP_N
    )

    # Show top stocks by year
    analyzer.show_top_stocks(results, n=10)

    # Show comprehensive pattern analysis
    analyzer.summarize_patterns(results)

    # Offer to export
    print()
    export = input("Export data to CSV? (y/n) [default=n]: ").strip().lower()
    if export == 'y':
        analyzer.export_to_csv(results, 'top_performers_analysis.csv')
        print("Data exported to top_performers_analysis.csv")
        print("Open in Excel to do your own analysis!")

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Review the KEY INSIGHTS section above")
    print("  2. Note which metrics have consistent patterns")
    print("  3. Use those ranges to build a screening strategy")
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
