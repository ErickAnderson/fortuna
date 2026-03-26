"""Fortuna — dividends business logic service."""

import pandas as pd
import database as db
import market_data as md


def _get_first_transaction_date(ticker: str) -> pd.Timestamp | None:
    """Get the earliest transaction date for a ticker."""
    pos = db.get_position_by_ticker(ticker)
    if not pos:
        return None
    txns = db.get_transactions(pos["id"])
    if not txns:
        return None
    dates = [pd.Timestamp(t["date"]) for t in txns]
    return min(dates)


def build_dividend_summary(
    positions_with_qty: list[dict],
) -> tuple[list[dict], dict, dict, float]:
    """
    Fetch and compute dividend data for all positions with qty > 0.

    Returns: (dividend_data, div_full_histories, div_owned_histories, total_dividends_received)

    dividend_data: list of row dicts with display-ready strings and _annual_income, _first_txn
    div_full_histories: dict[ticker -> pd.Series] — full dividend history for charts
    div_owned_histories: dict[ticker -> pd.Series] — owned-period-only history for calculations
    total_dividends_received: float — total dividends since first ownership across all positions
    """
    dividend_data = []
    div_full_histories: dict = {}
    div_owned_histories: dict = {}
    total_dividends_received = 0.0

    for pos in positions_with_qty:
        ticker = pos["ticker"]
        divs_df = md.get_dividends(ticker)
        divs = divs_df["Dividend"] if not divs_df.empty else pd.Series(dtype=float)
        div_yield = md.get_dividend_yield(ticker)

        div_full_histories[ticker] = divs

        first_txn_date = _get_first_transaction_date(ticker)
        if first_txn_date is not None and not divs.empty:
            cutoff = first_txn_date
            if divs.index.tz is not None:
                cutoff = cutoff.tz_localize(divs.index.tz)
            owned_divs = divs[divs.index >= cutoff]
        else:
            owned_divs = divs

        div_owned_histories[ticker] = owned_divs

        total_divs = owned_divs.sum() * pos["qty"] if not owned_divs.empty else 0.0
        total_dividends_received += total_divs

        latest_div = float(owned_divs.iloc[-1]) if not owned_divs.empty else 0.0
        latest_date = str(owned_divs.index[-1].date()) if not owned_divs.empty else "N/A"

        if not divs.empty:
            year_cutoff = pd.Timestamp.now(tz=divs.index.tz) - pd.DateOffset(years=1)
            annual_div = float(divs[divs.index >= year_cutoff].sum())
        else:
            annual_div = 0.0

        dividend_data.append({
            "Ticker": ticker,
            "Qty": pos["qty"],
            "Div Yield %": f"{div_yield:.2f}%" if div_yield is not None else "N/A",
            "Latest Div": f"${latest_div:.4f}",
            "Latest Date": latest_date,
            "Annual Div/Share": f"${annual_div:.4f}",
            "Annual Income": f"${annual_div * pos['qty']:,.2f}",
            "Total Received": f"${total_divs:,.2f}",
            "_annual_income": annual_div * pos["qty"],
            "_first_txn": first_txn_date,
        })

    return dividend_data, div_full_histories, div_owned_histories, total_dividends_received
