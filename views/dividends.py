"""Fortuna — Dividends Report page."""

import streamlit as st
import pandas as pd
import database as db
import services.dividends as svc


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

    with st.spinner("Fetching dividend data..."):
        dividend_data, div_full_histories, div_owned_histories, total_dividends_received = \
            svc.build_dividend_summary(positions_with_qty)

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
