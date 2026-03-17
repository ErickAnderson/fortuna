"""Fortuna — Market data layer using yfinance for ASX."""

import yfinance as yf
import pandas as pd
import streamlit as st


ASX_SUFFIX = ".AX"


def _asx_ticker(ticker: str) -> str:
    """Ensure ticker has .AX suffix for ASX."""
    if not ticker.upper().endswith(ASX_SUFFIX):
        return f"{ticker.upper()}{ASX_SUFFIX}"
    return ticker.upper()


def get_stock(ticker: str) -> yf.Ticker:
    return yf.Ticker(_asx_ticker(ticker))


def get_current_price(ticker: str) -> float | None:
    stock = get_stock(ticker)
    try:
        hist = stock.history(period="5d")
        if hist.empty:
            return None
        return round(float(hist["Close"].iloc[-1]), 2)
    except Exception:
        return None


@st.cache_data(ttl=300)
def get_batch_prices(tickers: tuple[str, ...]) -> dict[str, float | None]:
    """Fetch current prices for multiple tickers. Accepts tuple for caching."""
    prices = {}
    if not tickers:
        return prices

    asx_tickers = [_asx_ticker(t) for t in tickers]
    try:
        data = yf.download(asx_tickers, period="5d", group_by="ticker", progress=False)
        for orig, asx in zip(tickers, asx_tickers):
            try:
                if len(asx_tickers) == 1:
                    close = data["Close"].iloc[-1]
                else:
                    close = data[asx]["Close"].iloc[-1]
                prices[orig] = round(float(close), 2) if pd.notna(close) else None
            except (KeyError, IndexError):
                prices[orig] = None
    except Exception:
        for t in tickers:
            prices[t] = get_current_price(t)

    return prices


@st.cache_data(ttl=300)
def get_stock_info(ticker: str) -> dict:
    """Get fundamental data for a ticker."""
    stock = get_stock(ticker)
    try:
        info = stock.info
        return {
            "name": info.get("shortName", ticker),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "pb_ratio": info.get("priceToBook"),
            "dividend_yield": info.get("dividendYield"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "50d_avg": info.get("fiftyDayAverage"),
            "200d_avg": info.get("twoHundredDayAverage"),
            "beta": info.get("beta"),
        }
    except Exception:
        return {"name": ticker}


@st.cache_data(ttl=300)
def get_price_history(ticker: str, period: str = "6mo") -> pd.DataFrame:
    """Get OHLCV history for charting."""
    stock = get_stock(ticker)
    try:
        hist = stock.history(period=period)
        return hist
    except Exception:
        return pd.DataFrame()


def get_dividends(ticker: str) -> pd.Series:
    """Get dividend history."""
    stock = get_stock(ticker)
    try:
        return stock.dividends
    except Exception:
        return pd.Series(dtype=float)


@st.cache_data(ttl=300)
def get_dividend_yield(ticker: str) -> float | None:
    """Get current dividend yield as percentage."""
    info = get_stock_info(ticker)
    yield_val = info.get("dividend_yield")
    if yield_val is not None:
        return round(yield_val * 100, 2)
    return None
