"""Fortuna — Candlestick charts with technical indicators using Plotly."""

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots
from components.formatting import GOLD, GREEN, RED, WHITE, BORDER

_FORTUNA_TEMPLATE = go.layout.Template(
    layout=go.Layout(
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        font=dict(color=WHITE, family="sans-serif", size=12),
        colorway=[GOLD, GREEN, RED, "#FFA726", "#42A5F5"],
        xaxis=dict(gridcolor=BORDER, linecolor=BORDER, tickcolor=WHITE, showgrid=True),
        yaxis=dict(gridcolor=BORDER, linecolor=BORDER, tickcolor=WHITE, showgrid=True),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=BORDER, font=dict(color=WHITE)),
        title=dict(font=dict(color=GOLD)),
    )
)
pio.templates["fortuna_theme"] = _FORTUNA_TEMPLATE


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Compute technical indicators on OHLCV data."""
    if df.empty:
        return df

    df = df.copy()

    # Moving Averages
    df["MA50"] = df["Close"].rolling(window=50).mean()
    df["MA200"] = df["Close"].rolling(window=200).mean()
    df["MA20"] = df["Close"].rolling(window=20).mean()

    # RSI (14-period, Wilder's smoothing)
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0.0).ewm(com=13, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0.0)).ewm(com=13, adjust=False).mean()
    rs = gain / loss.replace(0, float('nan'))
    df["RSI"] = (100 - (100 / (1 + rs))).fillna(100)

    # MACD
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]

    # Bollinger Bands
    df["BB_Upper"] = df["MA20"] + 2 * df["Close"].rolling(window=20).std()
    df["BB_Lower"] = df["MA20"] - 2 * df["Close"].rolling(window=20).std()

    return df


def get_indicator_summary(df: pd.DataFrame) -> dict:
    """Extract current indicator values for AI analysis."""
    if df.empty:
        return {}

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest

    summary = {
        "current_price": round(float(latest["Close"]), 2),
        "MA20": round(float(latest["MA20"]), 2) if pd.notna(latest.get("MA20")) else None,
        "MA50": round(float(latest["MA50"]), 2) if pd.notna(latest.get("MA50")) else None,
        "MA200": round(float(latest["MA200"]), 2) if pd.notna(latest.get("MA200")) else None,
        "RSI": round(float(latest["RSI"]), 2) if pd.notna(latest.get("RSI")) else None,
        "MACD": round(float(latest["MACD"]), 4) if pd.notna(latest.get("MACD")) else None,
        "MACD_Signal": round(float(latest["MACD_Signal"]), 4) if pd.notna(latest.get("MACD_Signal")) else None,
        "MACD_Histogram": round(float(latest["MACD_Hist"]), 4) if pd.notna(latest.get("MACD_Hist")) else None,
        "BB_Upper": round(float(latest["BB_Upper"]), 2) if pd.notna(latest.get("BB_Upper")) else None,
        "BB_Lower": round(float(latest["BB_Lower"]), 2) if pd.notna(latest.get("BB_Lower")) else None,
    }

    # Price vs MAs
    price = latest["Close"]
    if pd.notna(latest.get("MA50")):
        summary["price_vs_MA50"] = "above" if price > latest["MA50"] else "below"
    if pd.notna(latest.get("MA200")):
        summary["price_vs_MA200"] = "above" if price > latest["MA200"] else "below"

    # RSI interpretation
    rsi = latest.get("RSI")
    if pd.notna(rsi):
        if rsi > 70:
            summary["RSI_signal"] = "overbought"
        elif rsi < 30:
            summary["RSI_signal"] = "oversold"
        else:
            summary["RSI_signal"] = "neutral"

    # MACD crossover
    if pd.notna(latest.get("MACD")) and pd.notna(latest.get("MACD_Signal")):
        if pd.notna(prev.get("MACD")) and pd.notna(prev.get("MACD_Signal")):
            if latest["MACD"] > latest["MACD_Signal"] and prev["MACD"] <= prev["MACD_Signal"]:
                summary["MACD_signal"] = "bullish crossover"
            elif latest["MACD"] < latest["MACD_Signal"] and prev["MACD"] >= prev["MACD_Signal"]:
                summary["MACD_signal"] = "bearish crossover"
            elif latest["MACD"] > latest["MACD_Signal"]:
                summary["MACD_signal"] = "bullish"
            else:
                summary["MACD_signal"] = "bearish"

    # 52-week range position
    high_52w = df["High"].tail(252).max() if len(df) >= 252 else df["High"].max()
    low_52w = df["Low"].tail(252).min() if len(df) >= 252 else df["Low"].min()
    summary["52w_high"] = round(float(high_52w), 2)
    summary["52w_low"] = round(float(low_52w), 2)
    range_pct = (price - low_52w) / (high_52w - low_52w) * 100 if high_52w != low_52w else 50
    summary["52w_range_position"] = f"{range_pct:.1f}%"

    # Volume trend
    if "Volume" in df.columns:
        avg_vol_20 = df["Volume"].tail(20).mean()
        latest_vol = latest["Volume"]
        if avg_vol_20 > 0:
            summary["volume_vs_avg"] = f"{(latest_vol / avg_vol_20 * 100):.0f}% of 20-day avg"

    return summary


def get_price_summary(df: pd.DataFrame) -> dict:
    """Get price action summary for AI prompt."""
    if df.empty:
        return {}

    latest = df.iloc[-1]

    def safe_pct_change(current, past):
        if pd.notna(past) and past != 0:
            return f"{((current / past - 1) * 100):.2f}%"
        return "N/A"

    close = df["Close"]
    return {
        "open": round(float(latest["Open"]), 2),
        "high": round(float(latest["High"]), 2),
        "low": round(float(latest["Low"]), 2),
        "close": round(float(latest["Close"]), 2),
        "volume": int(latest.get("Volume", 0)),
        "5d_change": safe_pct_change(close.iloc[-1], close.iloc[-5]) if len(df) >= 5 else "N/A",
        "20d_change": safe_pct_change(close.iloc[-1], close.iloc[-20]) if len(df) >= 20 else "N/A",
        "60d_change": safe_pct_change(close.iloc[-1], close.iloc[-60]) if len(df) >= 60 else "N/A",
    }


def create_candlestick_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    """Create a candlestick chart with MA, RSI, MACD, and volume."""
    if df.empty:
        return go.Figure()

    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.5, 0.15, 0.15, 0.2],
        subplot_titles=[f"{ticker} Price", "Volume", "RSI (14)", "MACD"],
    )

    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Price",
            increasing_line_color="#00C853",
            decreasing_line_color="#FF5252",
        ),
        row=1, col=1,
    )

    # Moving Averages
    colors = {"MA20": "#FFA726", "MA50": "#42A5F5", "MA200": "#AB47BC"}
    for ma, color in colors.items():
        if ma in df.columns and df[ma].notna().any():
            fig.add_trace(
                go.Scatter(x=df.index, y=df[ma], name=ma, line=dict(color=color, width=1)),
                row=1, col=1,
            )

    # Bollinger Bands
    if "BB_Upper" in df.columns:
        fig.add_trace(
            go.Scatter(x=df.index, y=df["BB_Upper"], name="BB Upper",
                       line=dict(color="rgba(255,255,255,0.2)", dash="dot", width=1)),
            row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(x=df.index, y=df["BB_Lower"], name="BB Lower",
                       line=dict(color="rgba(255,255,255,0.2)", dash="dot", width=1),
                       fill="tonexty", fillcolor="rgba(255,255,255,0.05)"),
            row=1, col=1,
        )

    # Volume
    if "Volume" in df.columns:
        colors_vol = ["#00C853" if c >= o else "#FF5252" for c, o in zip(df["Close"], df["Open"])]
        fig.add_trace(
            go.Bar(x=df.index, y=df["Volume"], name="Volume", marker_color=colors_vol, opacity=0.7),
            row=2, col=1,
        )

    # RSI
    if "RSI" in df.columns:
        fig.add_trace(
            go.Scatter(x=df.index, y=df["RSI"], name="RSI", line=dict(color="#FFA726", width=1.5)),
            row=3, col=1,
        )
        fig.add_hline(y=70, line_dash="dash", line_color="rgba(255,82,82,0.5)", row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="rgba(0,200,83,0.5)", row=3, col=1)

    # MACD
    if "MACD" in df.columns:
        fig.add_trace(
            go.Scatter(x=df.index, y=df["MACD"], name="MACD", line=dict(color="#42A5F5", width=1.5)),
            row=4, col=1,
        )
        fig.add_trace(
            go.Scatter(x=df.index, y=df["MACD_Signal"], name="Signal", line=dict(color="#FF5252", width=1.5)),
            row=4, col=1,
        )
        hist_colors = ["#00C853" if v >= 0 else "#FF5252" for v in df["MACD_Hist"]]
        fig.add_trace(
            go.Bar(x=df.index, y=df["MACD_Hist"], name="Histogram", marker_color=hist_colors, opacity=0.6),
            row=4, col=1,
        )

    fig.update_layout(
        template="fortuna_theme",
        height=800,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_rangeslider_visible=False,
    )
    fig.update_annotations(font_size=11, font_color="#AAAAAA")

    return fig
