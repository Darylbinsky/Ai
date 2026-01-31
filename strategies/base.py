"""Base strategy class for backtesting."""

import pandas as pd
from abc import ABC, abstractmethod
from typing import Optional


class Strategy(ABC):
    """
    Abstract base class for trading strategies.

    All strategies must implement the generate_signals method.
    """

    def __init__(
        self,
        name: str = "Strategy",
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ):
        """
        Initialize strategy.

        Args:
            name: Strategy name
            stop_loss: Stop loss as decimal (e.g., 0.05 = 5%)
            take_profit: Take profit as decimal (e.g., 0.10 = 10%)
        """
        self.name = name
        self.stop_loss = stop_loss
        self.take_profit = take_profit

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        Generate trading signals based on data.

        Args:
            data: DataFrame with OHLCV data and indicators

        Returns:
            Series with signals: 1 (buy), -1 (sell), 0 (hold)
        """
        pass

    def position_size(
        self,
        cash: float,
        price: float,
        data: pd.DataFrame
    ) -> int:
        """
        Calculate position size (number of shares to buy).

        Default implementation: use all available cash.
        Override this method for custom position sizing.

        Args:
            cash: Available cash
            price: Current price
            data: Historical data up to current point

        Returns:
            Number of shares to buy
        """
        return int(cash / price)

    def __repr__(self):
        return f"{self.__class__.__name__}(name='{self.name}')"
