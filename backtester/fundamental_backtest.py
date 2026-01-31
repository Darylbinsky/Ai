"""Fundamental strategy backtester using historical data."""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from tabulate import tabulate

from data.simfin_data import SimFinData


class FundamentalBacktester:
    """
    Backtest fundamental screening strategies on historical data.

    Simulates:
    1. Screen stocks at a historical date based on fundamental criteria
    2. Buy equal-weighted portfolio of stocks passing the screen
    3. Hold for specified period
    4. Measure returns
    """

    def __init__(self, api_key: str):
        """
        Initialize the backtester.

        Args:
            api_key: SimFin API key
        """
        self.simfin = SimFinData(api_key)

    def backtest(
        self,
        tickers: List[str],
        start_date: str,
        end_date: str,
        rebalance_months: int = 12,
        max_pe: float = 35,
        min_income_growth: float = 10,
        growth_years: int = 3,
        max_holdings: int = 20
    ) -> Dict[str, Any]:
        """
        Run a backtest of the fundamental screening strategy.

        Args:
            tickers: Universe of stocks to screen
            start_date: Backtest start date 'YYYY-MM-DD'
            end_date: Backtest end date 'YYYY-MM-DD'
            rebalance_months: Months between rebalancing
            max_pe: Maximum P/E ratio filter
            min_income_growth: Minimum income growth % filter
            growth_years: Years for growth calculation
            max_holdings: Maximum stocks to hold

        Returns:
            Dictionary with backtest results
        """
        print("\n" + "=" * 60)
        print("FUNDAMENTAL BACKTEST")
        print("=" * 60)
        print(f"\nStrategy: P/E < {max_pe}, Income Growth > {min_income_growth}%")
        print(f"Period: {start_date} to {end_date}")
        print(f"Rebalance: Every {rebalance_months} months")
        print(f"Universe: {len(tickers)} stocks")
        print()

        # Generate rebalance dates
        current = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')

        rebalance_dates = []
        while current < end:
            rebalance_dates.append(current.strftime('%Y-%m-%d'))
            current += relativedelta(months=rebalance_months)

        # Track portfolio
        portfolio_values = [10000]  # Start with $10,000
        portfolio_dates = [start_date]
        holdings_history = []

        for i, screen_date in enumerate(rebalance_dates):
            print(f"\n--- Rebalance {i + 1}: {screen_date} ---")

            # Screen stocks at this date
            passed = self.simfin.screen_at_date(
                tickers=tickers,
                date=screen_date,
                max_pe=max_pe,
                min_income_growth=min_income_growth,
                growth_years=growth_years
            )

            if not passed:
                print("  No stocks passed screening, holding cash")
                holdings_history.append({'date': screen_date, 'holdings': [], 'returns': 0})
                continue

            # Limit holdings
            holdings = passed[:max_holdings]
            print(f"  Selected {len(holdings)} stocks:")
            for h in holdings[:5]:
                print(f"    {h['ticker']}: P/E={h['pe_ratio']}, Growth={h['income_growth']}%")
            if len(holdings) > 5:
                print(f"    ... and {len(holdings) - 5} more")

            # Calculate returns until next rebalance or end
            if i + 1 < len(rebalance_dates):
                next_date = rebalance_dates[i + 1]
            else:
                next_date = end_date

            period_returns = []
            for stock in holdings:
                buy_price = stock['price']
                sell_price = self.simfin.get_price_at_date(stock['ticker'], next_date)

                if buy_price and sell_price and buy_price > 0:
                    ret = (sell_price - buy_price) / buy_price
                    period_returns.append(ret)

            if period_returns:
                avg_return = np.mean(period_returns)
                portfolio_values.append(portfolio_values[-1] * (1 + avg_return))
                portfolio_dates.append(next_date)
                print(f"  Period return: {avg_return * 100:.2f}%")

                holdings_history.append({
                    'date': screen_date,
                    'holdings': [h['ticker'] for h in holdings],
                    'returns': avg_return * 100
                })

        # Calculate final metrics
        total_return = (portfolio_values[-1] / portfolio_values[0] - 1) * 100
        years = (datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days / 365.25
        cagr = ((portfolio_values[-1] / portfolio_values[0]) ** (1 / years) - 1) * 100 if years > 0 else 0

        results = {
            'start_date': start_date,
            'end_date': end_date,
            'initial_value': 10000,
            'final_value': portfolio_values[-1],
            'total_return_pct': total_return,
            'cagr_pct': cagr,
            'num_rebalances': len(rebalance_dates),
            'portfolio_values': portfolio_values,
            'portfolio_dates': portfolio_dates,
            'holdings_history': holdings_history,
        }

        return results

    def print_results(self, results: Dict[str, Any]):
        """Print backtest results in a formatted way."""
        print("\n" + "=" * 60)
        print("BACKTEST RESULTS")
        print("=" * 60)

        summary = [
            ['Start Date', results['start_date']],
            ['End Date', results['end_date']],
            ['Initial Value', f"${results['initial_value']:,.2f}"],
            ['Final Value', f"${results['final_value']:,.2f}"],
            ['Total Return', f"{results['total_return_pct']:.2f}%"],
            ['CAGR', f"{results['cagr_pct']:.2f}%"],
            ['Rebalances', results['num_rebalances']],
        ]

        print(tabulate(summary, tablefmt='grid'))

        # Show holdings over time
        if results['holdings_history']:
            print("\n" + "-" * 60)
            print("HOLDINGS HISTORY")
            print("-" * 60)

            for period in results['holdings_history']:
                print(f"\n{period['date']}: {len(period['holdings'])} stocks, Return: {period['returns']:.2f}%")
                if period['holdings']:
                    print(f"  Holdings: {', '.join(period['holdings'][:10])}")
                    if len(period['holdings']) > 10:
                        print(f"  ... and {len(period['holdings']) - 10} more")

    def compare_to_benchmark(
        self,
        results: Dict[str, Any],
        benchmark_ticker: str = 'SPY'
    ) -> Dict[str, Any]:
        """
        Compare strategy results to a benchmark.

        Args:
            results: Backtest results
            benchmark_ticker: Benchmark ticker (default SPY)

        Returns:
            Comparison metrics
        """
        start_price = self.simfin.get_price_at_date(benchmark_ticker, results['start_date'])
        end_price = self.simfin.get_price_at_date(benchmark_ticker, results['end_date'])

        if start_price and end_price:
            benchmark_return = (end_price / start_price - 1) * 100
            years = (datetime.strptime(results['end_date'], '%Y-%m-%d') -
                     datetime.strptime(results['start_date'], '%Y-%m-%d')).days / 365.25
            benchmark_cagr = ((end_price / start_price) ** (1 / years) - 1) * 100

            alpha = results['cagr_pct'] - benchmark_cagr

            print("\n" + "-" * 60)
            print(f"COMPARISON TO {benchmark_ticker}")
            print("-" * 60)

            comparison = [
                ['Metric', 'Strategy', benchmark_ticker],
                ['Total Return', f"{results['total_return_pct']:.2f}%", f"{benchmark_return:.2f}%"],
                ['CAGR', f"{results['cagr_pct']:.2f}%", f"{benchmark_cagr:.2f}%"],
                ['Alpha', f"{alpha:.2f}%", '-'],
            ]

            print(tabulate(comparison, headers='firstrow', tablefmt='grid'))

            return {
                'benchmark': benchmark_ticker,
                'benchmark_return': benchmark_return,
                'benchmark_cagr': benchmark_cagr,
                'alpha': alpha
            }

        return {}
