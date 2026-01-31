"""Stock universe utilities - Get lists of stocks for screening."""

import pandas as pd
from typing import List, Optional
import os
import time


def get_sp500() -> List[str]:
    """
    Fetch S&P 500 tickers from Wikipedia.

    Returns:
        List of S&P 500 ticker symbols
    """
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url)
        sp500_table = tables[0]
        tickers = sp500_table['Symbol'].tolist()
        # Clean tickers (some have dots that need to be dashes for yfinance)
        tickers = [t.replace('.', '-') for t in tickers]
        return tickers
    except Exception as e:
        print(f"Error fetching S&P 500: {e}")
        return []


def get_sp400() -> List[str]:
    """
    Fetch S&P 400 MidCap tickers from Wikipedia.

    Returns:
        List of S&P 400 ticker symbols
    """
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies"
        tables = pd.read_html(url)
        sp400_table = tables[0]
        # Column name might vary
        if 'Symbol' in sp400_table.columns:
            tickers = sp400_table['Symbol'].tolist()
        elif 'Ticker symbol' in sp400_table.columns:
            tickers = sp400_table['Ticker symbol'].tolist()
        else:
            tickers = sp400_table.iloc[:, 0].tolist()
        tickers = [str(t).replace('.', '-') for t in tickers]
        return tickers
    except Exception as e:
        print(f"Error fetching S&P 400: {e}")
        return []


def get_sp600() -> List[str]:
    """
    Fetch S&P 600 SmallCap tickers from Wikipedia.

    Returns:
        List of S&P 600 ticker symbols
    """
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies"
        tables = pd.read_html(url)
        sp600_table = tables[0]
        if 'Symbol' in sp600_table.columns:
            tickers = sp600_table['Symbol'].tolist()
        elif 'Ticker symbol' in sp600_table.columns:
            tickers = sp600_table['Ticker symbol'].tolist()
        else:
            tickers = sp600_table.iloc[:, 0].tolist()
        tickers = [str(t).replace('.', '-') for t in tickers]
        return tickers
    except Exception as e:
        print(f"Error fetching S&P 600: {e}")
        return []


def get_sp1500() -> List[str]:
    """
    Get S&P 1500 (combination of S&P 500 + S&P 400 + S&P 600).

    Returns:
        List of ~1500 ticker symbols
    """
    print("Fetching S&P 500...")
    sp500 = get_sp500()
    time.sleep(1)  # Rate limiting

    print("Fetching S&P 400 MidCap...")
    sp400 = get_sp400()
    time.sleep(1)

    print("Fetching S&P 600 SmallCap...")
    sp600 = get_sp600()

    # Combine and remove duplicates
    all_tickers = list(set(sp500 + sp400 + sp600))
    print(f"Total unique tickers: {len(all_tickers)}")
    return sorted(all_tickers)


def get_russell3000() -> List[str]:
    """
    Get Russell 3000 stocks.

    First tries to load from a local file (data/russell3000.txt).
    If not found, falls back to S&P 1500 as an approximation.

    Returns:
        List of ticker symbols
    """
    # Try to load from file first
    file_paths = [
        os.path.join(os.path.dirname(__file__), 'russell3000.txt'),
        'data/russell3000.txt',
        'russell3000.txt'
    ]

    for file_path in file_paths:
        if os.path.exists(file_path):
            print(f"Loading Russell 3000 from {file_path}...")
            with open(file_path, 'r') as f:
                tickers = [line.strip().upper() for line in f if line.strip()]
            print(f"Loaded {len(tickers)} tickers")
            return tickers

    # Fall back to S&P 1500 (good approximation of large/mid/small cap)
    print("Russell 3000 file not found. Using S&P 1500 as approximation...")
    print("(For full Russell 3000, create data/russell3000.txt with one ticker per line)")
    return get_sp1500()


def load_from_file(file_path: str) -> List[str]:
    """
    Load ticker symbols from a text file (one per line).

    Args:
        file_path: Path to text file with tickers

    Returns:
        List of ticker symbols
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, 'r') as f:
        tickers = [line.strip().upper() for line in f if line.strip() and not line.startswith('#')]

    return tickers


def get_universe(name: str) -> List[str]:
    """
    Get a stock universe by name.

    Args:
        name: Universe name ('sp500', 'sp400', 'sp600', 'sp1500', 'russell3000')

    Returns:
        List of ticker symbols
    """
    universes = {
        'sp500': get_sp500,
        'sp400': get_sp400,
        'sp600': get_sp600,
        'sp1500': get_sp1500,
        'russell3000': get_russell3000,
    }

    name = name.lower().replace(' ', '').replace('&', '')

    if name not in universes:
        raise ValueError(f"Unknown universe: {name}. Available: {list(universes.keys())}")

    return universes[name]()
