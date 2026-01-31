"""Stock screener implementation."""

import pandas as pd
import time
import sys
from typing import List, Dict, Any, Optional, Callable
from data.fetcher import DataFetcher
from .filters import Filters


class StockScreener:
    """Screen stocks based on technical and fundamental criteria."""

    def __init__(self, fetcher: Optional[DataFetcher] = None):
        self.fetcher = fetcher or DataFetcher()
        self.filters = Filters()

    def screen(
        self,
        universe: List[str],
        filters: Dict[str, Any],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "1y",
        show_progress: bool = True,
        delay: float = 0.1
    ) -> List[Dict[str, Any]]:
        """
        Screen stocks based on specified filters.

        Args:
            universe: List of stock symbols to screen
            filters: Dictionary of filter criteria
            start_date: Start date for historical data
            end_date: End date for historical data
            period: Period if dates not specified
            show_progress: Show progress indicator
            delay: Delay between requests (seconds) to avoid rate limiting

        Available filters:
            - rsi_below: RSI below threshold
            - rsi_above: RSI above threshold
            - above_sma_20: Price above 20-day SMA
            - above_sma_50: Price above 50-day SMA
            - above_sma_200: Price above 200-day SMA
            - below_sma_20: Price below 20-day SMA
            - below_sma_50: Price below 50-day SMA
            - below_sma_200: Price below 200-day SMA
            - min_volume: Minimum average volume
            - min_price: Minimum stock price
            - max_price: Maximum stock price
            - macd_bullish: MACD above signal line
            - macd_bearish: MACD below signal line
            - golden_cross: Recent golden cross
            - death_cross: Recent death cross
            - volume_spike: Volume spike above threshold
            - adx_above: ADX above threshold (trending)
            - bb_oversold: Price below lower Bollinger Band
            - bb_overbought: Price above upper Bollinger Band

        Returns:
            List of dictionaries with passing stocks and their metrics
        """
        results = []
        total = len(universe)
        errors = 0

        for i, symbol in enumerate(universe):
            # Show progress
            if show_progress:
                pct = (i + 1) / total * 100
                passed = len(results)
                sys.stdout.write(f"\rScreening: {i+1}/{total} ({pct:.1f}%) | Passed: {passed} | Errors: {errors} | Current: {symbol}    ")
                sys.stdout.flush()

            try:
                data = self.fetcher.get_stock_data(symbol, start_date, end_date, period)

                if len(data) < 200:  # Need enough data for indicators
                    continue

                # Add indicators
                data = Filters.add_all_indicators(data)

                # Apply filters
                if self._passes_filters(data, filters):
                    metrics = self._calculate_metrics(symbol, data)
                    results.append(metrics)

            except Exception as e:
                errors += 1
                # Only print errors if not showing progress (to avoid cluttering output)
                if not show_progress:
                    print(f"Error screening {symbol}: {e}")

            # Rate limiting
            if delay > 0:
                time.sleep(delay)

        if show_progress:
            print(f"\n\nScreening complete! {len(results)} stocks passed out of {total} screened.")

        return results

    def _passes_filters(self, data: pd.DataFrame, filters: Dict[str, Any]) -> bool:
        """Check if stock passes all specified filters."""
        latest = data.iloc[-1]

        for filter_name, filter_value in filters.items():
            if not self._check_filter(data, latest, filter_name, filter_value):
                return False
        return True

    def _check_filter(
        self,
        data: pd.DataFrame,
        latest: pd.Series,
        filter_name: str,
        filter_value: Any
    ) -> bool:
        """Check a single filter condition."""

        filter_checks = {
            'rsi_below': lambda: latest['rsi'] < filter_value,
            'rsi_above': lambda: latest['rsi'] > filter_value,
            'above_sma_20': lambda: latest['close'] > latest['sma_20'] if filter_value else True,
            'above_sma_50': lambda: latest['close'] > latest['sma_50'] if filter_value else True,
            'above_sma_200': lambda: latest['close'] > latest['sma_200'] if filter_value else True,
            'below_sma_20': lambda: latest['close'] < latest['sma_20'] if filter_value else True,
            'below_sma_50': lambda: latest['close'] < latest['sma_50'] if filter_value else True,
            'below_sma_200': lambda: latest['close'] < latest['sma_200'] if filter_value else True,
            'min_volume': lambda: latest['volume_sma_20'] >= filter_value,
            'min_price': lambda: latest['close'] >= filter_value,
            'max_price': lambda: latest['close'] <= filter_value,
            'macd_bullish': lambda: latest['macd'] > latest['macd_signal'] if filter_value else True,
            'macd_bearish': lambda: latest['macd'] < latest['macd_signal'] if filter_value else True,
            'golden_cross': lambda: Filters.is_golden_cross(data) if filter_value else True,
            'death_cross': lambda: Filters.is_death_cross(data) if filter_value else True,
            'volume_spike': lambda: Filters.volume_spike(data, filter_value),
            'adx_above': lambda: latest['adx'] > filter_value,
            'bb_oversold': lambda: latest['close'] < latest['bb_lower'] if filter_value else True,
            'bb_overbought': lambda: latest['close'] > latest['bb_upper'] if filter_value else True,
        }

        if filter_name in filter_checks:
            try:
                return filter_checks[filter_name]()
            except Exception:
                return False
        return True

    def _calculate_metrics(self, symbol: str, data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate metrics for a passing stock."""
        latest = data.iloc[-1]

        # Calculate returns
        returns_1d = ((latest['close'] - data.iloc[-2]['close']) / data.iloc[-2]['close'] * 100) if len(data) > 1 else 0
        returns_1w = ((latest['close'] - data.iloc[-5]['close']) / data.iloc[-5]['close'] * 100) if len(data) > 5 else 0
        returns_1m = ((latest['close'] - data.iloc[-21]['close']) / data.iloc[-21]['close'] * 100) if len(data) > 21 else 0

        return {
            'symbol': symbol,
            'price': round(latest['close'], 2),
            'volume': int(latest['volume']),
            'avg_volume': int(latest['volume_sma_20']),
            'rsi': round(latest['rsi'], 2),
            'macd': round(latest['macd'], 4),
            'macd_signal': round(latest['macd_signal'], 4),
            'sma_20': round(latest['sma_20'], 2),
            'sma_50': round(latest['sma_50'], 2),
            'sma_200': round(latest['sma_200'], 2),
            'adx': round(latest['adx'], 2),
            'atr': round(latest['atr'], 2),
            'bb_upper': round(latest['bb_upper'], 2),
            'bb_lower': round(latest['bb_lower'], 2),
            'returns_1d': round(returns_1d, 2),
            'returns_1w': round(returns_1w, 2),
            'returns_1m': round(returns_1m, 2),
        }

    def get_stock_analysis(self, symbol: str, period: str = "1y") -> Dict[str, Any]:
        """
        Get detailed analysis for a single stock.

        Args:
            symbol: Stock ticker symbol
            period: Period for historical data

        Returns:
            Dictionary with detailed stock analysis
        """
        data = self.fetcher.get_stock_data(symbol, period=period)
        data = Filters.add_all_indicators(data)
        latest = data.iloc[-1]

        # Determine trend
        trend = "Neutral"
        if latest['close'] > latest['sma_50'] > latest['sma_200']:
            trend = "Strong Uptrend"
        elif latest['close'] > latest['sma_200']:
            trend = "Uptrend"
        elif latest['close'] < latest['sma_50'] < latest['sma_200']:
            trend = "Strong Downtrend"
        elif latest['close'] < latest['sma_200']:
            trend = "Downtrend"

        # RSI interpretation
        rsi_status = "Neutral"
        if latest['rsi'] < 30:
            rsi_status = "Oversold"
        elif latest['rsi'] > 70:
            rsi_status = "Overbought"

        # MACD interpretation
        macd_status = "Bullish" if latest['macd'] > latest['macd_signal'] else "Bearish"

        return {
            'symbol': symbol,
            'price': round(latest['close'], 2),
            'trend': trend,
            'rsi': round(latest['rsi'], 2),
            'rsi_status': rsi_status,
            'macd_status': macd_status,
            'adx': round(latest['adx'], 2),
            'above_sma_20': latest['close'] > latest['sma_20'],
            'above_sma_50': latest['close'] > latest['sma_50'],
            'above_sma_200': latest['close'] > latest['sma_200'],
            'volume_vs_avg': round(latest['volume'] / latest['volume_sma_20'], 2),
        }

    def print_results(self, results: List[Dict[str, Any]], sort_by: str = 'symbol'):
        """Print screening results in a formatted table."""
        if not results:
            print("No stocks passed the screening criteria.")
            return

        from tabulate import tabulate

        # Sort results
        results = sorted(results, key=lambda x: x.get(sort_by, 0), reverse=(sort_by != 'symbol'))

        # Select columns for display
        display_columns = ['symbol', 'price', 'rsi', 'returns_1d', 'returns_1w', 'returns_1m', 'adx']
        display_data = [{k: v for k, v in r.items() if k in display_columns} for r in results]

        print(tabulate(display_data, headers='keys', tablefmt='grid'))
        print(f"\nTotal: {len(results)} stocks passed screening")
