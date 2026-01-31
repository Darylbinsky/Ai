#!/usr/bin/env python3
"""
Stock Screener - Fundamental Analysis

Screens stocks based on fundamental criteria:
- Insider ownership
- P/E ratio
- Net income growth
"""

from screener import FundamentalScreener
from data import get_russell3000, get_sp500


# Set to True for full S&P 1500 screening (takes 30+ minutes)
# Set to False for quick demo with S&P 500 (takes ~10 minutes)
USE_BROAD_MARKET = True


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
        print("\nUsing S&P 500 for faster screening...")
        return get_sp500()


def run_fundamental_screen():
    """Run fundamental stock screening."""
    print("\n" + "=" * 60)
    print("FUNDAMENTAL STOCK SCREENER")
    print("=" * 60)
    print()
    print("Criteria:")
    print("  - Insider Ownership > 20%")
    print("  - P/E Ratio < 35")
    print("  - Net Income Growth > 10% (3-year CAGR)")
    print("  - Price > $5 (avoid penny stocks)")
    print()

    # Get stock universe
    universe = get_stock_universe()
    print(f"\nTotal stocks to screen: {len(universe)}")
    print("\nNote: Fundamental data takes longer to fetch than technical data.")
    print("This screen will take approximately 20-40 minutes.\n")

    screener = FundamentalScreener()

    # Run the screen with user's criteria
    results = screener.screen(
        universe=universe,
        min_insider_ownership=20,  # > 20%
        max_pe=35,                  # P/E < 35
        min_income_growth=10,       # > 10% net income growth
        min_price=5,                # Avoid penny stocks
        delay=0.3                   # Slightly slower to avoid rate limits
    )

    # Print results
    print("\n" + "=" * 60)
    print("SCREENING RESULTS")
    print("=" * 60)
    screener.print_results(results, sort_by='insider_ownership')

    return results


def main():
    """Run the fundamental screener."""
    print("\n" + "=" * 60)
    print("STOCK SCREENER - FUNDAMENTAL ANALYSIS")
    print("=" * 60)

    try:
        results = run_fundamental_screen()

        if results:
            print("\n" + "-" * 60)
            print("SUMMARY")
            print("-" * 60)
            print(f"Found {len(results)} stocks matching your criteria:")
            print("  - Insider Ownership > 20%")
            print("  - P/E < 35")
            print("  - Net Income Growth > 10%")

    except KeyboardInterrupt:
        print("\n\nScreening cancelled by user.")
    except Exception as e:
        print(f"\nError during screening: {e}")

    print("\n" + "=" * 60)
    print("Screening complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()
