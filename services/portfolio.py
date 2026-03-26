"""Fortuna — portfolio business logic service."""

import database as db
import market_data as md


def build_portfolio_rows() -> tuple[list[dict], float, float, float]:
    """
    Load portfolio positions, fetch live prices, compute per-row P&L and weights.

    Returns: (rows, total_cost, total_value, total_fees)

    Each row dict contains: ticker, id, qty, avg_price, total_cost, total_fees,
    target_weight, current_price, value, current_weight, pnl_dollar, pnl_pct,
    weight_diff, div_yield
    """
    portfolio = db.get_portfolio_summary()
    if not portfolio:
        return [], 0.0, 0.0, 0.0

    tickers = tuple(p["ticker"] for p in portfolio)  # tuple required for Streamlit cache hashability
    prices = md.get_batch_prices(tickers)

    rows = []
    total_cost = 0.0
    total_value = 0.0
    total_fees = 0.0

    for pos in portfolio:
        current_price = prices.get(pos["ticker"])
        value = (current_price * pos["qty"]) if current_price and pos["qty"] > 0 else 0.0
        total_cost += pos["total_cost"]
        total_value += value
        total_fees += pos["total_fees"]
        rows.append({**pos, "current_price": current_price, "value": round(value, 2)})

    for row in rows:
        row["current_weight"] = round((row["value"] / total_value * 100), 2) if total_value > 0 else 0.0
        row["pnl_dollar"] = round(row["value"] - row["total_cost"], 2)
        row["pnl_pct"] = round((row["pnl_dollar"] / row["total_cost"] * 100), 2) if row["total_cost"] > 0 else 0.0
        row["weight_diff"] = round(row["current_weight"] - row["target_weight"], 2)
        row["div_yield"] = md.get_dividend_yield(row["ticker"])

    return rows, total_cost, total_value, total_fees
