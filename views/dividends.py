"""Fortuna — Dividends Report page."""

import streamlit as st
import pandas as pd
import database as db
import market_data as md


def _get_first_transaction_date(ticker: str) -> pd.Timestamp | None:
    """Get the earliest transaction date for a ticker."""
    txns = db.get_transactions(
        db.get_position_by_ticker(ticker)["id"]
    ) if db.get_position_by_ticker(ticker) else []
    if not txns:
        return None
    dates = [pd.Timestamp(t["date"]) for t in txns]
    return min(dates)


def render():
    st.markdown("# Dividends")

    portfolio = db.get_portfolio_summary()
    if not portfolio:
        st.info("No positions yet.")
        return

    positions_with_qty = [p for p in portfolio if p["qty"] > 0]
    if not positions_with_qty:
        st.info("No holdings to show dividends for.")
        return

    # Fetch dividend data for all positions
    dividend_data = []
    div_histories = {}
    total_dividends_received = 0.0

    with st.spinner("Fetching dividend data..."):
        for pos in positions_with_qty:
            ticker = pos["ticker"]
            divs_df = md.get_dividends(ticker)
            divs = divs_df["Dividend"] if not divs_df.empty else pd.Series(dtype=float)
            div_yield = md.get_dividend_yield(ticker)

            # Filter dividends to only those after first transaction
            first_txn_date = _get_first_transaction_date(ticker)
            if first_txn_date is not None and not divs.empty:
                if divs.index.tz is not None:
                    first_txn_date = first_txn_date.tz_localize(divs.index.tz)
                divs = divs[divs.index >= first_txn_date]

            div_histories[ticker] = divs

            # Total dividends received (only since we held the stock)
            total_divs = divs.sum() * pos["qty"] if not divs.empty else 0.0
            total_dividends_received += total_divs

            # Latest dividend
            latest_div = float(divs.iloc[-1]) if not divs.empty else 0.0
            latest_date = str(divs.index[-1].date()) if not divs.empty else "N/A"

            # Trailing 12-month dividends
            if not divs.empty:
                cutoff = pd.Timestamp.now(tz=divs.index.tz) - pd.DateOffset(years=1)
                annual_div = float(divs[divs.index >= cutoff].sum())
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
            })

    # Top metrics
    total_annual = sum(d["_annual_income"] for d in dividend_data)
    total_invested = sum(p["total_cost"] for p in positions_with_qty)
    portfolio_yield = (total_annual / total_invested * 100) if total_invested > 0 else 0.0

    col1, col2, col3 = st.columns(3)
    col1.metric("Annual Dividend Income", f"${total_annual:,.2f}")
    col2.metric("Portfolio Yield", f"{portfolio_yield:.2f}%")
    col3.metric("Total Dividends Received", f"${total_dividends_received:,.2f}")

    st.markdown("---")

    # Summary table
    st.markdown("### Dividend Summary")
    display_cols = ["Ticker", "Qty", "Div Yield %", "Latest Div", "Latest Date",
                    "Annual Div/Share", "Annual Income", "Total Received"]
    df = pd.DataFrame(dividend_data)[display_cols]
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Per-ticker dividend history
    st.markdown("### Dividend History")
    selected = st.selectbox(
        "Select ticker",
        options=[d["Ticker"] for d in dividend_data],
        key="div_ticker",
    )

    if selected:
        divs = div_histories.get(selected, pd.Series(dtype=float))
        qty = next(d["Qty"] for d in dividend_data if d["Ticker"] == selected)

        if divs.empty:
            st.info(f"No dividends received since first purchase of {selected}")
        else:
            # Chart
            chart_data = pd.DataFrame({
                "Date": divs.index,
                "Dividend": divs.values,
            }).set_index("Date")
            st.bar_chart(chart_data)

            # Table
            hist_df = pd.DataFrame({
                "Date": [d.date() for d in divs.index],
                "Dividend/Share": [f"${v:.4f}" for v in divs.values],
                "Income": [f"${v * qty:,.2f}" for v in divs.values],
            })
            st.dataframe(hist_df, use_container_width=True, hide_index=True)
