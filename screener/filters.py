"""Stock screening filter definitions and technical indicators."""

import pandas as pd
import numpy as np
from typing import Optional


class Filters:
    """Technical indicators and filters for stock screening."""

    @staticmethod
    def sma(data: pd.DataFrame, period: int, column: str = 'close') -> pd.Series:
        """Calculate Simple Moving Average."""
        return data[column].rolling(window=period).mean()

    @staticmethod
    def ema(data: pd.DataFrame, period: int, column: str = 'close') -> pd.Series:
        """Calculate Exponential Moving Average."""
        return data[column].ewm(span=period, adjust=False).mean()

    @staticmethod
    def rsi(data: pd.DataFrame, period: int = 14, column: str = 'close') -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = data[column].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)

        avg_gain = gain.rolling(window=period, min_periods=period).mean()
        avg_loss = loss.rolling(window=period, min_periods=period).mean()

        # Use EMA for subsequent values (Wilder's smoothing)
        for i in range(period, len(gain)):
            avg_gain.iloc[i] = (avg_gain.iloc[i-1] * (period - 1) + gain.iloc[i]) / period
            avg_loss.iloc[i] = (avg_loss.iloc[i-1] * (period - 1) + loss.iloc[i]) / period

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def macd(data: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9, column: str = 'close'):
        """Calculate MACD indicator."""
        ema_fast = data[column].ewm(span=fast, adjust=False).mean()
        ema_slow = data[column].ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }

    @staticmethod
    def bollinger_bands(data: pd.DataFrame, period: int = 20, std_dev: float = 2.0, column: str = 'close'):
        """Calculate Bollinger Bands."""
        middle = data[column].rolling(window=period).mean()
        std = data[column].rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        width = (upper - lower) / middle
        pband = (data[column] - lower) / (upper - lower)

        return {
            'upper': upper,
            'middle': middle,
            'lower': lower,
            'width': width,
            'pband': pband
        }

    @staticmethod
    def atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        high = data['high']
        low = data['low']
        close = data['close']

        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr

    @staticmethod
    def volume_sma(data: pd.DataFrame, period: int = 20) -> pd.Series:
        """Calculate Volume Simple Moving Average."""
        return data['volume'].rolling(window=period).mean()

    @staticmethod
    def stochastic(data: pd.DataFrame, k_period: int = 14, d_period: int = 3):
        """Calculate Stochastic Oscillator."""
        low_min = data['low'].rolling(window=k_period).min()
        high_max = data['high'].rolling(window=k_period).max()

        stoch_k = 100 * (data['close'] - low_min) / (high_max - low_min)
        stoch_d = stoch_k.rolling(window=d_period).mean()

        return {
            'k': stoch_k,
            'd': stoch_d
        }

    @staticmethod
    def adx(data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average Directional Index."""
        high = data['high']
        low = data['low']
        close = data['close']

        # Calculate +DM and -DM
        up_move = high.diff()
        down_move = -low.diff()

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

        plus_dm = pd.Series(plus_dm, index=data.index)
        minus_dm = pd.Series(minus_dm, index=data.index)

        # Calculate ATR
        atr = Filters.atr(data, period)

        # Calculate smoothed +DI and -DI
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)

        # Calculate DX and ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()

        return adx

    @staticmethod
    def obv(data: pd.DataFrame) -> pd.Series:
        """Calculate On-Balance Volume."""
        close = data['close']
        volume = data['volume']

        obv = pd.Series(0, index=data.index, dtype=float)
        obv.iloc[0] = volume.iloc[0]

        for i in range(1, len(close)):
            if close.iloc[i] > close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
            elif close.iloc[i] < close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]

        return obv

    @staticmethod
    def vwap(data: pd.DataFrame) -> pd.Series:
        """Calculate Volume Weighted Average Price."""
        typical_price = (data['high'] + data['low'] + data['close']) / 3
        vwap = (typical_price * data['volume']).cumsum() / data['volume'].cumsum()
        return vwap

    @staticmethod
    def price_change_percent(data: pd.DataFrame, periods: int = 1, column: str = 'close') -> pd.Series:
        """Calculate percentage price change over periods."""
        return data[column].pct_change(periods=periods) * 100

    @staticmethod
    def is_above_sma(data: pd.DataFrame, period: int, column: str = 'close') -> bool:
        """Check if current price is above SMA."""
        sma = Filters.sma(data, period, column)
        return data[column].iloc[-1] > sma.iloc[-1]

    @staticmethod
    def is_golden_cross(data: pd.DataFrame, short_period: int = 50, long_period: int = 200) -> bool:
        """Check for golden cross (short MA crosses above long MA)."""
        short_ma = Filters.sma(data, short_period)
        long_ma = Filters.sma(data, long_period)

        if len(short_ma) < 2 or len(long_ma) < 2:
            return False

        # Current: short above long, Previous: short below long
        return (short_ma.iloc[-1] > long_ma.iloc[-1] and
                short_ma.iloc[-2] <= long_ma.iloc[-2])

    @staticmethod
    def is_death_cross(data: pd.DataFrame, short_period: int = 50, long_period: int = 200) -> bool:
        """Check for death cross (short MA crosses below long MA)."""
        short_ma = Filters.sma(data, short_period)
        long_ma = Filters.sma(data, long_period)

        if len(short_ma) < 2 or len(long_ma) < 2:
            return False

        # Current: short below long, Previous: short above long
        return (short_ma.iloc[-1] < long_ma.iloc[-1] and
                short_ma.iloc[-2] >= long_ma.iloc[-2])

    @staticmethod
    def volume_spike(data: pd.DataFrame, threshold: float = 2.0, period: int = 20) -> bool:
        """Check if current volume is significantly above average."""
        avg_volume = Filters.volume_sma(data, period).iloc[-1]
        current_volume = data['volume'].iloc[-1]
        return current_volume > avg_volume * threshold

    @staticmethod
    def is_oversold(data: pd.DataFrame, rsi_threshold: float = 30) -> bool:
        """Check if stock is oversold based on RSI."""
        rsi = Filters.rsi(data)
        return rsi.iloc[-1] < rsi_threshold

    @staticmethod
    def is_overbought(data: pd.DataFrame, rsi_threshold: float = 70) -> bool:
        """Check if stock is overbought based on RSI."""
        rsi = Filters.rsi(data)
        return rsi.iloc[-1] > rsi_threshold

    @staticmethod
    def add_all_indicators(data: pd.DataFrame) -> pd.DataFrame:
        """Add all technical indicators to the dataframe."""
        df = data.copy()

        # Moving averages
        df['sma_20'] = Filters.sma(df, 20)
        df['sma_50'] = Filters.sma(df, 50)
        df['sma_200'] = Filters.sma(df, 200)
        df['ema_12'] = Filters.ema(df, 12)
        df['ema_26'] = Filters.ema(df, 26)

        # RSI
        df['rsi'] = Filters.rsi(df)

        # MACD
        macd = Filters.macd(df)
        df['macd'] = macd['macd']
        df['macd_signal'] = macd['signal']
        df['macd_histogram'] = macd['histogram']

        # Bollinger Bands
        bb = Filters.bollinger_bands(df)
        df['bb_upper'] = bb['upper']
        df['bb_middle'] = bb['middle']
        df['bb_lower'] = bb['lower']

        # ATR
        df['atr'] = Filters.atr(df)

        # Volume SMA
        df['volume_sma_20'] = Filters.volume_sma(df, 20)

        # Stochastic
        stoch = Filters.stochastic(df)
        df['stoch_k'] = stoch['k']
        df['stoch_d'] = stoch['d']

        # ADX
        df['adx'] = Filters.adx(df)

        # OBV
        df['obv'] = Filters.obv(df)

        return df
