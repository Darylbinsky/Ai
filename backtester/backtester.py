"""Backtesting engine for trading strategies."""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from datetime import datetime
from data.fetcher import DataFetcher
from screener.filters import Filters
from .metrics import PerformanceMetrics

if TYPE_CHECKING:
    from strategies.base import Strategy


class Backtester:
    """
    Backtesting engine for trading strategies.

    Supports:
    - Long and short positions
    - Transaction costs
    - Position sizing
    - Stop loss and take profit
    """

    def __init__(
        self,
        initial_capital: float = 10000,
        commission: float = 0.001,
        slippage: float = 0.0005,
        fetcher: Optional[DataFetcher] = None
    ):
        """
        Initialize backtester.

        Args:
            initial_capital: Starting capital
            commission: Commission per trade (as decimal, e.g., 0.001 = 0.1%)
            slippage: Slippage per trade (as decimal)
            fetcher: Data fetcher instance
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.fetcher = fetcher or DataFetcher()

    def run(
        self,
        symbol: str,
        strategy: 'Strategy',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "2y"
    ) -> Dict[str, Any]:
        """
        Run backtest for a strategy on a single symbol.

        Args:
            symbol: Stock ticker symbol
            strategy: Strategy instance to test
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            period: Period if dates not specified

        Returns:
            Dictionary with backtest results
        """
        # Fetch data
        data = self.fetcher.get_stock_data(symbol, start_date, end_date, period)

        # Add indicators
        data = Filters.add_all_indicators(data)

        # Generate signals
        signals = strategy.generate_signals(data)

        # Simulate trades
        results = self._simulate_trades(data, signals, strategy)

        # Calculate metrics
        metrics = PerformanceMetrics.calculate_all(
            results['equity_curve'],
            results['trades'],
            self.initial_capital
        )

        return {
            'symbol': symbol,
            'strategy': strategy.name,
            'start_date': data.index[0],
            'end_date': data.index[-1],
            'data': data,
            'signals': signals,
            'equity_curve': results['equity_curve'],
            'trades': results['trades'],
            'positions': results['positions'],
            'metrics': metrics
        }

    def _simulate_trades(
        self,
        data: pd.DataFrame,
        signals: pd.Series,
        strategy: 'Strategy'
    ) -> Dict[str, Any]:
        """
        Simulate trades based on signals.

        Args:
            data: OHLCV data with indicators
            signals: Series with 1 (buy), -1 (sell), 0 (hold)
            strategy: Strategy instance

        Returns:
            Dictionary with equity curve, trades, and positions
        """
        cash = self.initial_capital
        position = 0  # Number of shares
        entry_price = 0
        trades = []
        equity_curve = []
        positions = []

        for i, (date, row) in enumerate(data.iterrows()):
            signal = signals.iloc[i] if i < len(signals) else 0
            price = row['close']

            # Calculate current equity
            current_equity = cash + position * price
            equity_curve.append({'date': date, 'equity': current_equity})
            positions.append({'date': date, 'position': position, 'cash': cash})

            # Check stop loss / take profit if in position
            if position != 0 and strategy.stop_loss is not None:
                if position > 0:  # Long position
                    if price <= entry_price * (1 - strategy.stop_loss):
                        signal = -1  # Trigger sell
                    elif strategy.take_profit and price >= entry_price * (1 + strategy.take_profit):
                        signal = -1  # Take profit

            # Execute trades
            if signal == 1 and position == 0:  # Buy signal
                # Calculate position size
                shares = strategy.position_size(cash, price, data.iloc[:i+1])
                if shares > 0:
                    cost = shares * price * (1 + self.commission + self.slippage)
                    if cost <= cash:
                        cash -= cost
                        position = shares
                        entry_price = price
                        trades.append({
                            'date': date,
                            'type': 'BUY',
                            'price': price,
                            'shares': shares,
                            'cost': cost
                        })

            elif signal == -1 and position > 0:  # Sell signal
                proceeds = position * price * (1 - self.commission - self.slippage)
                pnl = proceeds - (position * entry_price)
                pnl_pct = (price / entry_price - 1) * 100
                cash += proceeds

                trades.append({
                    'date': date,
                    'type': 'SELL',
                    'price': price,
                    'shares': position,
                    'proceeds': proceeds,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct
                })

                position = 0
                entry_price = 0

        # Convert equity curve to series
        equity_df = pd.DataFrame(equity_curve)
        equity_series = pd.Series(equity_df['equity'].values, index=equity_df['date'])

        return {
            'equity_curve': equity_series,
            'trades': trades,
            'positions': pd.DataFrame(positions)
        }

    def run_multiple(
        self,
        symbols: List[str],
        strategy: 'Strategy',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "2y"
    ) -> Dict[str, Dict[str, Any]]:
        """
        Run backtest on multiple symbols.

        Args:
            symbols: List of stock ticker symbols
            strategy: Strategy instance to test
            start_date: Start date
            end_date: End date
            period: Period if dates not specified

        Returns:
            Dictionary mapping symbols to their results
        """
        results = {}
        for symbol in symbols:
            try:
                results[symbol] = self.run(symbol, strategy, start_date, end_date, period)
            except Exception as e:
                print(f"Error backtesting {symbol}: {e}")
        return results

    def compare_strategies(
        self,
        symbol: str,
        strategies: List['Strategy'],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "2y"
    ) -> List[Dict[str, Any]]:
        """
        Compare multiple strategies on the same symbol.

        Args:
            symbol: Stock ticker symbol
            strategies: List of strategy instances
            start_date: Start date
            end_date: End date
            period: Period if dates not specified

        Returns:
            List of results for each strategy
        """
        results = []
        for strategy in strategies:
            try:
                result = self.run(symbol, strategy, start_date, end_date, period)
                results.append(result)
            except Exception as e:
                print(f"Error with strategy {strategy.name}: {e}")
        return results

    def print_results(self, results: Dict[str, Any]):
        """Print backtest results in a formatted way."""
        from tabulate import tabulate

        print("\n" + "=" * 60)
        print(f"BACKTEST RESULTS: {results['symbol']}")
        print(f"Strategy: {results['strategy']}")
        print(f"Period: {results['start_date'].strftime('%Y-%m-%d')} to {results['end_date'].strftime('%Y-%m-%d')}")
        print("=" * 60)

        metrics = results['metrics']

        # Performance metrics
        print("\n📈 PERFORMANCE METRICS")
        perf_data = [
            ['Initial Capital', f"${metrics['initial_capital']:,.2f}"],
            ['Final Value', f"${metrics['final_value']:,.2f}"],
            ['Total Return', f"{metrics['total_return_pct']:.2f}%"],
            ['Annualized Return', f"{metrics['annualized_return_pct']:.2f}%"],
            ['Volatility', f"{metrics['volatility_pct']:.2f}%"],
        ]
        print(tabulate(perf_data, tablefmt='simple'))

        # Risk metrics
        print("\n⚠️ RISK METRICS")
        risk_data = [
            ['Sharpe Ratio', f"{metrics['sharpe_ratio']:.2f}"],
            ['Sortino Ratio', f"{metrics['sortino_ratio']:.2f}"],
            ['Max Drawdown', f"{metrics['max_drawdown_pct']:.2f}%"],
            ['Calmar Ratio', f"{metrics['calmar_ratio']:.2f}"],
        ]
        print(tabulate(risk_data, tablefmt='simple'))

        # Trade statistics
        print("\n📊 TRADE STATISTICS")
        trade_data = [
            ['Total Trades', metrics['total_trades']],
            ['Win Rate', f"{metrics['win_rate_pct']:.2f}%"],
            ['Profit Factor', f"{metrics['profit_factor']:.2f}"],
            ['Avg Trade P&L', f"${metrics['avg_trade_pnl']:.2f}"],
            ['Avg Winning Trade', f"${metrics['avg_winning_trade']:.2f}"],
            ['Avg Losing Trade', f"${metrics['avg_losing_trade']:.2f}"],
            ['Expectancy', f"${metrics['expectancy']:.2f}"],
        ]
        print(tabulate(trade_data, tablefmt='simple'))

        # Trade log
        if results['trades']:
            print("\n📝 TRADE LOG (Last 10 trades)")
            trade_log = []
            for trade in results['trades'][-10:]:
                trade_info = {
                    'Date': trade['date'].strftime('%Y-%m-%d'),
                    'Type': trade['type'],
                    'Price': f"${trade['price']:.2f}",
                    'Shares': trade['shares']
                }
                if 'pnl' in trade:
                    trade_info['P&L'] = f"${trade['pnl']:.2f}"
                    trade_info['P&L %'] = f"{trade['pnl_pct']:.2f}%"
                trade_log.append(trade_info)
            print(tabulate(trade_log, headers='keys', tablefmt='simple'))

        print("\n" + "=" * 60)

    def plot_results(self, results: Dict[str, Any], save_path: Optional[str] = None):
        """
        Plot backtest results.

        Args:
            results: Backtest results dictionary
            save_path: Optional path to save the plot
        """
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)

        # Plot 1: Price with buy/sell signals
        ax1 = axes[0]
        data = results['data']
        ax1.plot(data.index, data['close'], label='Price', alpha=0.7)
        ax1.plot(data.index, data['sma_20'], label='SMA 20', alpha=0.5)
        ax1.plot(data.index, data['sma_50'], label='SMA 50', alpha=0.5)

        # Mark trades
        for trade in results['trades']:
            if trade['type'] == 'BUY':
                ax1.scatter(trade['date'], trade['price'], color='green', marker='^', s=100, zorder=5)
            else:
                ax1.scatter(trade['date'], trade['price'], color='red', marker='v', s=100, zorder=5)

        ax1.set_title(f"{results['symbol']} - {results['strategy']}")
        ax1.set_ylabel('Price')
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)

        # Plot 2: Equity curve
        ax2 = axes[1]
        equity = results['equity_curve']
        ax2.plot(equity.index, equity.values, label='Portfolio Value', color='blue')
        ax2.axhline(y=self.initial_capital, color='gray', linestyle='--', label='Initial Capital')
        ax2.set_ylabel('Portfolio Value ($)')
        ax2.legend(loc='upper left')
        ax2.grid(True, alpha=0.3)

        # Plot 3: Drawdown
        ax3 = axes[2]
        rolling_max = equity.expanding().max()
        drawdown = (equity - rolling_max) / rolling_max * 100
        ax3.fill_between(drawdown.index, drawdown.values, 0, color='red', alpha=0.3)
        ax3.plot(drawdown.index, drawdown.values, color='red', linewidth=0.5)
        ax3.set_ylabel('Drawdown (%)')
        ax3.set_xlabel('Date')
        ax3.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"Plot saved to {save_path}")
        else:
            plt.show()
