"""Fortuna — Dividends Report page."""

import streamlit as st
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
    div_full_histories = {}   # Full history for chart display
    div_owned_histories = {}  # Only since first transaction for calculations
    total_dividends_received = 0.0

    with st.spinner("Fetching dividend data..."):
        for pos in positions_with_qty:
            ticker = pos["ticker"]
            divs_df = md.get_dividends(ticker)
            divs = divs_df["Dividend"] if not divs_df.empty else pd.Series(dtype=float)
            div_yield = md.get_dividend_yield(ticker)

            # Full history for chart
            div_full_histories[ticker] = divs

            # Filter to only dividends since first transaction (for portfolio value)
            first_txn_date = _get_first_transaction_date(ticker)
            if first_txn_date is not None and not divs.empty:
                cutoff = first_txn_date
                if divs.index.tz is not None:
                    cutoff = cutoff.tz_localize(divs.index.tz)
                owned_divs = divs[divs.index >= cutoff]
            else:
                owned_divs = divs

            div_owned_histories[ticker] = owned_divs

            # Total dividends received (only since ownership)
            total_divs = owned_divs.sum() * pos["qty"] if not owned_divs.empty else 0.0
            total_dividends_received += total_divs

            # Latest dividend (from owned period)
            latest_div = float(owned_divs.iloc[-1]) if not owned_divs.empty else 0.0
            latest_date = str(owned_divs.index[-1].date()) if not owned_divs.empty else "N/A"

            # Trailing 12-month dividends
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

    # Per-ticker dividend history (full history shown, owned period highlighted)
    st.markdown("### Dividend History")
    selected = st.selectbox(
        "Select ticker",
        options=[d["Ticker"] for d in dividend_data],
        key="div_ticker",
    )

    if selected:
        full_divs = div_full_histories.get(selected, pd.Series(dtype=float))
        qty = next(d["Qty"] for d in dividend_data if d["Ticker"] == selected)
        first_txn = next(d["_first_txn"] for d in dividend_data if d["Ticker"] == selected)

        if full_divs.empty:
            st.info(f"No dividend history for {selected}")
        else:
            # Chart — full history
            chart_data = pd.DataFrame({
                "Date": full_divs.index,
                "Dividend": full_divs.values,
            }).set_index("Date")
            st.bar_chart(chart_data)

            # Table — full history with "Owned" indicator
            owned_cutoff = first_txn
            if owned_cutoff is not None and full_divs.index.tz is not None:
                owned_cutoff = owned_cutoff.tz_localize(full_divs.index.tz)

            hist_rows = []
            for d_date, d_val in zip(full_divs.index, full_divs.values):
                is_owned = owned_cutoff is not None and d_date >= owned_cutoff
                hist_rows.append({
                    "Date": d_date.date(),
                    "Dividend/Share": f"${d_val:.4f}",
                    "Income": f"${d_val * qty:,.2f}" if is_owned else "—",
                    "Status": "Received" if is_owned else "Pre-ownership",
                })

            hist_df = pd.DataFrame(hist_rows)
            st.dataframe(
                hist_df.style.map(
                    lambda val: "color: #555555" if val == "Pre-ownership" else "",
                    subset=["Status"],
                ).map(
                    lambda val: "color: #555555" if val == "—" else "",
                    subset=["Income"],
                ),
                use_container_width=True,
                hide_index=True,
            )
