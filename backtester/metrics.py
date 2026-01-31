"""Performance metrics for backtesting."""

import pandas as pd
import numpy as np
from typing import Dict, Any, List


class PerformanceMetrics:
    """Calculate performance metrics for backtest results."""

    @staticmethod
    def calculate_returns(equity_curve: pd.Series) -> pd.Series:
        """Calculate daily returns from equity curve."""
        return equity_curve.pct_change().dropna()

    @staticmethod
    def total_return(equity_curve: pd.Series) -> float:
        """Calculate total return percentage."""
        return (equity_curve.iloc[-1] / equity_curve.iloc[0] - 1) * 100

    @staticmethod
    def annualized_return(equity_curve: pd.Series, trading_days: int = 252) -> float:
        """Calculate annualized return."""
        total_days = len(equity_curve)
        total_return = equity_curve.iloc[-1] / equity_curve.iloc[0]
        years = total_days / trading_days
        return (total_return ** (1 / years) - 1) * 100 if years > 0 else 0

    @staticmethod
    def volatility(returns: pd.Series, trading_days: int = 252) -> float:
        """Calculate annualized volatility."""
        return returns.std() * np.sqrt(trading_days) * 100

    @staticmethod
    def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.02, trading_days: int = 252) -> float:
        """
        Calculate Sharpe Ratio.

        Args:
            returns: Daily returns series
            risk_free_rate: Annual risk-free rate (default 2%)
            trading_days: Number of trading days per year
        """
        if returns.std() == 0:
            return 0

        daily_rf = risk_free_rate / trading_days
        excess_returns = returns - daily_rf
        return np.sqrt(trading_days) * excess_returns.mean() / returns.std()

    @staticmethod
    def sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.02, trading_days: int = 252) -> float:
        """
        Calculate Sortino Ratio (uses downside deviation).

        Args:
            returns: Daily returns series
            risk_free_rate: Annual risk-free rate (default 2%)
            trading_days: Number of trading days per year
        """
        daily_rf = risk_free_rate / trading_days
        excess_returns = returns - daily_rf

        downside_returns = returns[returns < 0]
        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return 0

        downside_std = downside_returns.std() * np.sqrt(trading_days)
        annualized_excess = excess_returns.mean() * trading_days

        return annualized_excess / downside_std if downside_std != 0 else 0

    @staticmethod
    def max_drawdown(equity_curve: pd.Series) -> Dict[str, Any]:
        """
        Calculate maximum drawdown.

        Returns:
            Dictionary with max drawdown percentage, start date, end date, and recovery date
        """
        rolling_max = equity_curve.expanding().max()
        drawdowns = (equity_curve - rolling_max) / rolling_max

        max_dd = drawdowns.min() * 100
        end_idx = drawdowns.idxmin()

        # Find start of drawdown
        equity_to_end = equity_curve[:end_idx]
        start_idx = equity_to_end.idxmax()

        # Find recovery (if any)
        equity_after = equity_curve[end_idx:]
        recovery_mask = equity_after >= rolling_max[end_idx]
        recovery_idx = recovery_mask.idxmax() if recovery_mask.any() else None

        return {
            'max_drawdown': round(max_dd, 2),
            'start_date': start_idx,
            'end_date': end_idx,
            'recovery_date': recovery_idx
        }

    @staticmethod
    def calmar_ratio(equity_curve: pd.Series, trading_days: int = 252) -> float:
        """Calculate Calmar Ratio (annualized return / max drawdown)."""
        ann_return = PerformanceMetrics.annualized_return(equity_curve, trading_days)
        max_dd = abs(PerformanceMetrics.max_drawdown(equity_curve)['max_drawdown'])
        return ann_return / max_dd if max_dd != 0 else 0

    @staticmethod
    def win_rate(trades: List[Dict[str, Any]]) -> float:
        """Calculate win rate percentage."""
        if not trades:
            return 0
        winning_trades = sum(1 for t in trades if t.get('pnl', 0) > 0)
        return (winning_trades / len(trades)) * 100

    @staticmethod
    def profit_factor(trades: List[Dict[str, Any]]) -> float:
        """Calculate profit factor (gross profit / gross loss)."""
        gross_profit = sum(t['pnl'] for t in trades if t.get('pnl', 0) > 0)
        gross_loss = abs(sum(t['pnl'] for t in trades if t.get('pnl', 0) < 0))
        return gross_profit / gross_loss if gross_loss != 0 else float('inf')

    @staticmethod
    def average_trade(trades: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate average trade statistics."""
        if not trades:
            return {'avg_pnl': 0, 'avg_win': 0, 'avg_loss': 0}

        pnls = [t.get('pnl', 0) for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        return {
            'avg_pnl': np.mean(pnls) if pnls else 0,
            'avg_win': np.mean(wins) if wins else 0,
            'avg_loss': np.mean(losses) if losses else 0
        }

    @staticmethod
    def expectancy(trades: List[Dict[str, Any]]) -> float:
        """Calculate trade expectancy (expected value per trade)."""
        if not trades:
            return 0

        win_rate = PerformanceMetrics.win_rate(trades) / 100
        avg = PerformanceMetrics.average_trade(trades)

        return (win_rate * avg['avg_win']) + ((1 - win_rate) * avg['avg_loss'])

    @staticmethod
    def calculate_all(equity_curve: pd.Series, trades: List[Dict[str, Any]], initial_capital: float) -> Dict[str, Any]:
        """
        Calculate all performance metrics.

        Args:
            equity_curve: Series of portfolio values over time
            trades: List of trade dictionaries
            initial_capital: Starting capital

        Returns:
            Dictionary with all performance metrics
        """
        returns = PerformanceMetrics.calculate_returns(equity_curve)
        max_dd_info = PerformanceMetrics.max_drawdown(equity_curve)
        avg_trade = PerformanceMetrics.average_trade(trades)

        return {
            'initial_capital': initial_capital,
            'final_value': round(equity_curve.iloc[-1], 2),
            'total_return_pct': round(PerformanceMetrics.total_return(equity_curve), 2),
            'annualized_return_pct': round(PerformanceMetrics.annualized_return(equity_curve), 2),
            'volatility_pct': round(PerformanceMetrics.volatility(returns), 2),
            'sharpe_ratio': round(PerformanceMetrics.sharpe_ratio(returns), 2),
            'sortino_ratio': round(PerformanceMetrics.sortino_ratio(returns), 2),
            'max_drawdown_pct': max_dd_info['max_drawdown'],
            'max_drawdown_start': max_dd_info['start_date'],
            'max_drawdown_end': max_dd_info['end_date'],
            'calmar_ratio': round(PerformanceMetrics.calmar_ratio(equity_curve), 2),
            'total_trades': len(trades),
            'win_rate_pct': round(PerformanceMetrics.win_rate(trades), 2),
            'profit_factor': round(PerformanceMetrics.profit_factor(trades), 2),
            'avg_trade_pnl': round(avg_trade['avg_pnl'], 2),
            'avg_winning_trade': round(avg_trade['avg_win'], 2),
            'avg_losing_trade': round(avg_trade['avg_loss'], 2),
            'expectancy': round(PerformanceMetrics.expectancy(trades), 2),
        }
