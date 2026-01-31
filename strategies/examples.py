"""Example trading strategies."""

import pandas as pd
import numpy as np
from typing import Optional
from .base import Strategy


class MACrossoverStrategy(Strategy):
    """
    Moving Average Crossover Strategy.

    Buy when short MA crosses above long MA (golden cross).
    Sell when short MA crosses below long MA (death cross).
    """

    def __init__(
        self,
        short_window: int = 20,
        long_window: int = 50,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ):
        super().__init__(
            name=f"MA Crossover ({short_window}/{long_window})",
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        self.short_window = short_window
        self.long_window = long_window

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        signals = pd.Series(0, index=data.index)

        short_ma = data['close'].rolling(window=self.short_window).mean()
        long_ma = data['close'].rolling(window=self.long_window).mean()

        # Generate signals
        for i in range(1, len(data)):
            if short_ma.iloc[i] > long_ma.iloc[i] and short_ma.iloc[i-1] <= long_ma.iloc[i-1]:
                signals.iloc[i] = 1  # Buy signal
            elif short_ma.iloc[i] < long_ma.iloc[i] and short_ma.iloc[i-1] >= long_ma.iloc[i-1]:
                signals.iloc[i] = -1  # Sell signal

        return signals


class RSIStrategy(Strategy):
    """
    RSI Mean Reversion Strategy.

    Buy when RSI drops below oversold threshold.
    Sell when RSI rises above overbought threshold.
    """

    def __init__(
        self,
        rsi_period: int = 14,
        oversold: float = 30,
        overbought: float = 70,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ):
        super().__init__(
            name=f"RSI ({rsi_period}, {oversold}/{overbought})",
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        signals = pd.Series(0, index=data.index)

        rsi = data['rsi'] if 'rsi' in data.columns else self._calculate_rsi(data)

        in_position = False
        for i in range(1, len(data)):
            if not in_position and rsi.iloc[i] < self.oversold and rsi.iloc[i-1] >= self.oversold:
                signals.iloc[i] = 1  # Buy when RSI crosses below oversold
                in_position = True
            elif in_position and rsi.iloc[i] > self.overbought and rsi.iloc[i-1] <= self.overbought:
                signals.iloc[i] = -1  # Sell when RSI crosses above overbought
                in_position = False

        return signals

    def _calculate_rsi(self, data: pd.DataFrame) -> pd.Series:
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))


class MACDStrategy(Strategy):
    """
    MACD Strategy.

    Buy when MACD crosses above signal line.
    Sell when MACD crosses below signal line.
    """

    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ):
        super().__init__(
            name=f"MACD ({fast_period}/{slow_period}/{signal_period})",
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        signals = pd.Series(0, index=data.index)

        if 'macd' in data.columns and 'macd_signal' in data.columns:
            macd = data['macd']
            macd_signal = data['macd_signal']
        else:
            macd, macd_signal = self._calculate_macd(data)

        for i in range(1, len(data)):
            if macd.iloc[i] > macd_signal.iloc[i] and macd.iloc[i-1] <= macd_signal.iloc[i-1]:
                signals.iloc[i] = 1  # Buy signal
            elif macd.iloc[i] < macd_signal.iloc[i] and macd.iloc[i-1] >= macd_signal.iloc[i-1]:
                signals.iloc[i] = -1  # Sell signal

        return signals

    def _calculate_macd(self, data: pd.DataFrame):
        ema_fast = data['close'].ewm(span=self.fast_period, adjust=False).mean()
        ema_slow = data['close'].ewm(span=self.slow_period, adjust=False).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=self.signal_period, adjust=False).mean()
        return macd, macd_signal


class BollingerBandsStrategy(Strategy):
    """
    Bollinger Bands Mean Reversion Strategy.

    Buy when price touches lower band.
    Sell when price touches upper band or middle band.
    """

    def __init__(
        self,
        period: int = 20,
        std_dev: float = 2.0,
        exit_at_middle: bool = False,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ):
        super().__init__(
            name=f"Bollinger Bands ({period}, {std_dev})",
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        self.period = period
        self.std_dev = std_dev
        self.exit_at_middle = exit_at_middle

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        signals = pd.Series(0, index=data.index)

        if 'bb_upper' in data.columns and 'bb_lower' in data.columns:
            upper = data['bb_upper']
            lower = data['bb_lower']
            middle = data['bb_middle']
        else:
            middle = data['close'].rolling(window=self.period).mean()
            std = data['close'].rolling(window=self.period).std()
            upper = middle + (std * self.std_dev)
            lower = middle - (std * self.std_dev)

        in_position = False
        for i in range(1, len(data)):
            price = data['close'].iloc[i]

            if not in_position and price <= lower.iloc[i]:
                signals.iloc[i] = 1  # Buy at lower band
                in_position = True
            elif in_position:
                if self.exit_at_middle and price >= middle.iloc[i]:
                    signals.iloc[i] = -1  # Sell at middle band
                    in_position = False
                elif price >= upper.iloc[i]:
                    signals.iloc[i] = -1  # Sell at upper band
                    in_position = False

        return signals


class MomentumStrategy(Strategy):
    """
    Momentum Strategy.

    Buy when price shows strong upward momentum.
    Sell when momentum weakens or reverses.
    """

    def __init__(
        self,
        lookback: int = 20,
        momentum_threshold: float = 0.05,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ):
        super().__init__(
            name=f"Momentum ({lookback} days, {momentum_threshold*100}%)",
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        self.lookback = lookback
        self.momentum_threshold = momentum_threshold

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        signals = pd.Series(0, index=data.index)

        # Calculate momentum as rate of change
        momentum = data['close'].pct_change(periods=self.lookback)

        in_position = False
        for i in range(self.lookback, len(data)):
            if not in_position and momentum.iloc[i] > self.momentum_threshold:
                signals.iloc[i] = 1  # Buy on strong upward momentum
                in_position = True
            elif in_position and momentum.iloc[i] < 0:
                signals.iloc[i] = -1  # Sell when momentum turns negative
                in_position = False

        return signals


class MeanReversionStrategy(Strategy):
    """
    Mean Reversion Strategy using Z-Score.

    Buy when price is significantly below the mean.
    Sell when price returns to or exceeds the mean.
    """

    def __init__(
        self,
        lookback: int = 20,
        entry_zscore: float = -2.0,
        exit_zscore: float = 0.0,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ):
        super().__init__(
            name=f"Mean Reversion (Z-Score {entry_zscore}/{exit_zscore})",
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        self.lookback = lookback
        self.entry_zscore = entry_zscore
        self.exit_zscore = exit_zscore

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        signals = pd.Series(0, index=data.index)

        # Calculate rolling z-score
        rolling_mean = data['close'].rolling(window=self.lookback).mean()
        rolling_std = data['close'].rolling(window=self.lookback).std()
        zscore = (data['close'] - rolling_mean) / rolling_std

        in_position = False
        for i in range(self.lookback, len(data)):
            if not in_position and zscore.iloc[i] <= self.entry_zscore:
                signals.iloc[i] = 1  # Buy when price is significantly below mean
                in_position = True
            elif in_position and zscore.iloc[i] >= self.exit_zscore:
                signals.iloc[i] = -1  # Sell when price returns to mean
                in_position = False

        return signals

    def position_size(self, cash: float, price: float, data: pd.DataFrame) -> int:
        """Size position based on z-score magnitude."""
        if len(data) < self.lookback:
            return int(cash / price)

        rolling_mean = data['close'].rolling(window=self.lookback).mean()
        rolling_std = data['close'].rolling(window=self.lookback).std()
        zscore = (data['close'].iloc[-1] - rolling_mean.iloc[-1]) / rolling_std.iloc[-1]

        # Larger position for more extreme z-scores (max 100% of cash)
        size_multiplier = min(1.0, abs(zscore) / 3)
        return int((cash * size_multiplier) / price)
