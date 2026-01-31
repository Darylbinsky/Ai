#!/usr/bin/env python3
"""
Stock Screener & Backtester - Example Usage

This script demonstrates how to use the stock screener and backtester.
"""

from screener import StockScreener
from backtester import Backtester
from strategies import (
    MACrossoverStrategy,
    RSIStrategy,
    MACDStrategy,
    BollingerBandsStrategy,
    MomentumStrategy,
    MeanReversionStrategy
)


def demo_screener():
    """Demonstrate the stock screener."""
    print("\n" + "=" * 60)
    print("STOCK SCREENER DEMO")
    print("=" * 60)

    # Define universe of stocks to screen
    universe = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META',
        'NVDA', 'TSLA', 'JPM', 'V', 'JNJ',
        'WMT', 'PG', 'MA', 'HD', 'DIS'
    ]

    screener = StockScreener()

    # Example 1: Find stocks with RSI below 40 (potentially oversold)
    print("\n📊 Screening for stocks with RSI < 40...")
    results = screener.screen(
        universe=universe,
        filters={
            'rsi_below': 40,
            'min_volume': 500000
        }
    )
    screener.print_results(results)

    # Example 2: Find stocks in uptrend
    print("\n📊 Screening for stocks in uptrend (above SMA 50 and 200)...")
    results = screener.screen(
        universe=universe,
        filters={
            'above_sma_50': True,
            'above_sma_200': True,
            'min_volume': 1000000
        }
    )
    screener.print_results(results)

    # Example 3: Find stocks with MACD bullish crossover
    print("\n📊 Screening for stocks with MACD bullish...")
    results = screener.screen(
        universe=universe,
        filters={
            'macd_bullish': True,
            'rsi_below': 70  # Not overbought
        }
    )
    screener.print_results(results)

    # Get detailed analysis for a single stock
    print("\n📊 Detailed analysis for AAPL:")
    analysis = screener.get_stock_analysis('AAPL')
    for key, value in analysis.items():
        print(f"  {key}: {value}")


def demo_backtest():
    """Demonstrate the backtester."""
    print("\n" + "=" * 60)
    print("BACKTEST DEMO")
    print("=" * 60)

    backtester = Backtester(
        initial_capital=10000,
        commission=0.001,  # 0.1% commission
        slippage=0.0005   # 0.05% slippage
    )

    # Test MA Crossover Strategy
    print("\n📈 Testing MA Crossover Strategy on AAPL...")
    strategy = MACrossoverStrategy(
        short_window=20,
        long_window=50,
        stop_loss=0.05  # 5% stop loss
    )
    results = backtester.run('AAPL', strategy, period='2y')
    backtester.print_results(results)

    # Test RSI Strategy
    print("\n📈 Testing RSI Strategy on MSFT...")
    strategy = RSIStrategy(
        oversold=30,
        overbought=70,
        stop_loss=0.05
    )
    results = backtester.run('MSFT', strategy, period='2y')
    backtester.print_results(results)


def demo_strategy_comparison():
    """Compare multiple strategies."""
    print("\n" + "=" * 60)
    print("STRATEGY COMPARISON DEMO")
    print("=" * 60)

    backtester = Backtester(initial_capital=10000)

    strategies = [
        MACrossoverStrategy(short_window=20, long_window=50),
        MACrossoverStrategy(short_window=10, long_window=30),
        RSIStrategy(oversold=30, overbought=70),
        MACDStrategy(),
        MomentumStrategy(lookback=20, momentum_threshold=0.03),
    ]

    symbol = 'AAPL'
    print(f"\n📊 Comparing strategies on {symbol}...\n")

    results = backtester.compare_strategies(symbol, strategies, period='2y')

    # Print comparison table
    from tabulate import tabulate

    comparison_data = []
    for result in results:
        comparison_data.append({
            'Strategy': result['strategy'],
            'Total Return': f"{result['metrics']['total_return_pct']:.2f}%",
            'Sharpe Ratio': f"{result['metrics']['sharpe_ratio']:.2f}",
            'Max Drawdown': f"{result['metrics']['max_drawdown_pct']:.2f}%",
            'Win Rate': f"{result['metrics']['win_rate_pct']:.2f}%",
            'Trades': result['metrics']['total_trades']
        })

    print(tabulate(comparison_data, headers='keys', tablefmt='grid'))


def demo_multi_stock_backtest():
    """Backtest on multiple stocks."""
    print("\n" + "=" * 60)
    print("MULTI-STOCK BACKTEST DEMO")
    print("=" * 60)

    backtester = Backtester(initial_capital=10000)
    strategy = MACrossoverStrategy(short_window=20, long_window=50)

    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']

    print(f"\n📊 Backtesting {strategy.name} on multiple stocks...\n")

    results = backtester.run_multiple(symbols, strategy, period='2y')

    # Print summary
    from tabulate import tabulate

    summary_data = []
    for symbol, result in results.items():
        summary_data.append({
            'Symbol': symbol,
            'Total Return': f"{result['metrics']['total_return_pct']:.2f}%",
            'Sharpe Ratio': f"{result['metrics']['sharpe_ratio']:.2f}",
            'Max Drawdown': f"{result['metrics']['max_drawdown_pct']:.2f}%",
            'Win Rate': f"{result['metrics']['win_rate_pct']:.2f}%",
            'Trades': result['metrics']['total_trades']
        })

    print(tabulate(summary_data, headers='keys', tablefmt='grid'))


def main():
    """Run all demos."""
    print("\n🚀 STOCK SCREENER & BACKTESTER")
    print("=" * 60)

    try:
        demo_screener()
    except Exception as e:
        print(f"Screener demo failed: {e}")

    try:
        demo_backtest()
    except Exception as e:
        print(f"Backtest demo failed: {e}")

    try:
        demo_strategy_comparison()
    except Exception as e:
        print(f"Strategy comparison demo failed: {e}")

    try:
        demo_multi_stock_backtest()
    except Exception as e:
        print(f"Multi-stock backtest demo failed: {e}")

    print("\n✅ Demo complete!")


if __name__ == '__main__':
    main()
