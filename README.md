# Stock Screener & Backtester

A Python-based stock screening and backtesting system for evaluating trading strategies.

## Features

- **Stock Screener**: Filter stocks based on technical and fundamental criteria
- **Backtester**: Test trading strategies on historical data
- **Built-in Indicators**: SMA, EMA, RSI, MACD, Bollinger Bands, and more
- **Custom Strategies**: Easy-to-implement strategy interface

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

```python
from screener import StockScreener
from backtester import Backtester
from strategies import MACrossoverStrategy

# Screen for stocks
screener = StockScreener()
stocks = screener.screen(
    universe=['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'META'],
    filters={
        'rsi_below': 70,
        'above_sma_200': True,
        'min_volume': 1000000
    }
)

# Backtest a strategy
strategy = MACrossoverStrategy(short_window=20, long_window=50)
backtester = Backtester(initial_capital=10000)
results = backtester.run('AAPL', strategy, start_date='2023-01-01')
backtester.print_results(results)
```

## Project Structure

```
├── data/
│   └── fetcher.py       # Stock data fetching utilities
├── screener/
│   ├── screener.py      # Stock screening logic
│   └── filters.py       # Filter definitions
├── backtester/
│   ├── backtester.py    # Backtesting engine
│   └── metrics.py       # Performance metrics
├── strategies/
│   ├── base.py          # Base strategy class
│   └── examples.py      # Example strategies
└── main.py              # Example usage
```

## Creating Custom Strategies

```python
from strategies.base import Strategy

class MyStrategy(Strategy):
    def generate_signals(self, data):
        # Your logic here
        # Return 1 for buy, -1 for sell, 0 for hold
        signals = pd.Series(0, index=data.index)
        # ... your signal logic
        return signals
```

## License

MIT
