"""Fortuna — Dividends Report page."""

import streamlit as st
import pandas as pd
import database as db
import market_data as md


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
    total_dividends_received = 0.0

    with st.spinner("Fetching dividend data..."):
        for pos in positions_with_qty:
            ticker = pos["ticker"]
            divs = md.get_dividends(ticker)
            div_yield = md.get_dividend_yield(ticker)

            # Calculate total dividends received (based on holding qty)
            total_divs = divs.sum() * pos["qty"] if not divs.empty else 0.0
            total_dividends_received += total_divs

            # Latest dividend
            latest_div = float(divs.iloc[-1]) if not divs.empty else 0.0
            latest_date = str(divs.index[-1].date()) if not divs.empty else "N/A"
            annual_div = float(divs.tail(4).sum()) if len(divs) >= 4 else float(divs.sum())

            dividend_data.append({
                "Ticker": ticker,
                "Qty": pos["qty"],
                "Div Yield %": f"{div_yield:.2f}%" if div_yield else "N/A",
                "Latest Div": f"${latest_div:.4f}",
                "Latest Date": latest_date,
                "Annual Div/Share": f"${annual_div:.4f}",
                "Annual Income": f"${annual_div * pos['qty']:,.2f}",
                "Total Received": f"${total_divs:,.2f}",
                "_annual_income": annual_div * pos["qty"],
                "_div_history": divs,
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
        div_entry = next(d for d in dividend_data if d["Ticker"] == selected)
        divs = div_entry["_div_history"]

        if divs.empty:
            st.info(f"No dividend history for {selected}")
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
                "Income": [f"${v * div_entry['Qty']:,.2f}" for v in divs.values],
            })
            st.dataframe(hist_df, use_container_width=True, hide_index=True)
