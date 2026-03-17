"""Fortuna — Portfolio Dashboard page."""

import streamlit as st
import pandas as pd
import database as db
import market_data as md


def render():
    st.markdown("# Portfolio")

    portfolio = db.get_portfolio_summary()

    if not portfolio:
        st.info("No positions yet. Add tickers below to get started.")
        _render_add_position()
        return

    # Warn on negative quantities
    for pos in portfolio:
        if pos["qty"] < 0:
            st.warning(f"{pos['ticker']} has negative qty ({pos['qty']}). Check transactions.")

    # Fetch live prices (tuple for caching)
    tickers = tuple(p["ticker"] for p in portfolio)
    with st.spinner("Fetching live prices..."):
        prices = md.get_batch_prices(tickers)

    # Build portfolio table data
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

        rows.append({
            **pos,
            "current_price": current_price,
            "value": round(value, 2),
        })

    # Calculate weights and P&L
    for row in rows:
        row["current_weight"] = round((row["value"] / total_value * 100), 2) if total_value > 0 else 0.0
        row["pnl_dollar"] = round(row["value"] - row["total_cost"], 2)
        row["pnl_pct"] = round((row["pnl_dollar"] / row["total_cost"] * 100), 2) if row["total_cost"] > 0 else 0.0
        row["weight_diff"] = round(row["current_weight"] - row["target_weight"], 2)
        row["div_yield"] = md.get_dividend_yield(row["ticker"])

    # Top-level metrics
    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0.0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Invested", f"${total_cost:,.2f}")
    col2.metric("Current Value", f"${total_value:,.2f}")
    pnl_color = "#00C853" if total_pnl >= 0 else "#FF5252"
    pnl_bg = "rgba(0,200,83,0.15)" if total_pnl >= 0 else "rgba(255,82,82,0.15)"
    pnl_arrow = "▲" if total_pnl >= 0 else "▼"
    col3.markdown(
        f'<div style="background-color:#1A1D24; border:1px solid #2A2D34; border-radius:8px; padding:14px 16px;">'
        f'<p style="font-size:0.875rem; color:#AAAAAA; margin:0 0 4px 0; font-weight:400;">Total P&L</p>'
        f'<p style="font-size:2rem; font-weight:700; margin:0; line-height:1.2; color:#FAFAFA;">${total_pnl:,.2f}</p>'
        f'<span style="display:inline-block; margin-top:4px; padding:2px 8px; border-radius:12px; '
        f'font-size:0.8rem; color:{pnl_color}; background:{pnl_bg};">'
        f'{pnl_arrow} {total_pnl_pct:+.2f}%</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    col4.metric("Total Fees", f"${total_fees:,.2f}")

    st.markdown("---")

    # Portfolio table
    df = pd.DataFrame(rows)
    display_df = df[[
        "ticker", "target_weight", "current_weight", "weight_diff",
        "qty", "avg_price", "current_price", "total_cost",
        "value", "pnl_pct", "pnl_dollar", "total_fees", "div_yield",
    ]].copy()

    display_df.columns = [
        "Ticker", "Target %", "Current %", "Diff %",
        "Qty", "Avg Price", "Price", "Cost",
        "Value", "P&L %", "P&L $", "Fees", "Div Yield %",
    ]

    # Style the dataframe
    def style_pnl(val):
        if isinstance(val, (int, float)):
            if val > 0:
                return "color: #00C853"
            elif val < 0:
                return "color: #FF5252"
        return ""

    def style_weight_diff(val):
        if isinstance(val, (int, float)):
            if val > 2:
                return "color: #FF5252"  # Overweight
            elif val < -2:
                return "color: #FFA726"  # Underweight
        return ""

    styled = display_df.style.map(
        style_pnl, subset=["P&L %", "P&L $"]
    ).map(
        style_weight_diff, subset=["Diff %"]
    ).format({
        "Target %": "{:.1f}%",
        "Current %": "{:.1f}%",
        "Diff %": "{:+.1f}%",
        "Qty": "{:.0f}",
        "Avg Price": "${:,.2f}",
        "Price": lambda x: f"${x:,.2f}" if x is not None else "N/A",
        "Cost": "${:,.2f}",
        "Value": "${:,.2f}",
        "P&L %": "{:+.2f}%",
        "P&L $": "${:+,.2f}",
        "Fees": "${:,.2f}",
        "Div Yield %": lambda x: f"{x:.2f}%" if x is not None else "N/A",
    })

    st.dataframe(styled, use_container_width=True, hide_index=True)

    # Allocation chart
    st.markdown("### Allocation")
    col_target, col_actual = st.columns(2)

    with col_target:
        st.markdown("**Target**")
        target_data = pd.DataFrame({
            "Ticker": [r["ticker"] for r in rows],
            "Weight": [r["target_weight"] for r in rows],
        })
        st.bar_chart(target_data.set_index("Ticker"), horizontal=True)

    with col_actual:
        st.markdown("**Actual**")
        actual_data = pd.DataFrame({
            "Ticker": [r["ticker"] for r in rows],
            "Weight": [r["current_weight"] for r in rows],
        })
        st.bar_chart(actual_data.set_index("Ticker"), horizontal=True)

    st.markdown("---")

    # Manage positions
    st.markdown("### Manage Positions")

    # Edit target weights with confirm button
    st.markdown("**Edit Target Weights**")
    weight_cols = st.columns(len(rows))
    weight_changed = False
    for i, row in enumerate(rows):
        with weight_cols[i]:
            new_weight = st.number_input(
                f"{row['ticker']}",
                min_value=0.0,
                max_value=100.0,
                value=row["target_weight"],
                step=1.0,
                key=f"weight_{row['ticker']}",
            )
            if new_weight != row["target_weight"]:
                weight_changed = True

    if weight_changed and st.button("Save Weights", type="primary"):
        for i, row in enumerate(rows):
            new_weight = st.session_state.get(f"weight_{row['ticker']}", row["target_weight"])
            if new_weight != row["target_weight"]:
                db.update_target_weight(row["id"], new_weight)
        st.rerun()

    _render_add_position()

    # Delete position
    st.markdown("**Remove Position**")
    ticker_to_delete = st.selectbox(
        "Select ticker to remove",
        options=[""] + [r["ticker"] for r in rows],
        key="delete_ticker",
    )
    if ticker_to_delete and st.button("Remove Position", type="secondary"):
        pos = db.get_position_by_ticker(ticker_to_delete)
        if pos:
            db.delete_position(pos["id"])
            st.success(f"Removed {ticker_to_delete}")
            st.rerun()


def _render_add_position():
    st.markdown("**Add Position**")
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        new_ticker = st.text_input("Ticker (e.g. CBA, VAS)", key="new_ticker").strip().upper()
    with col2:
        new_weight = st.number_input("Target Weight %", min_value=0.0, max_value=100.0, value=0.0, key="new_weight")
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Add", key="add_position") and new_ticker:
            db.upsert_position(new_ticker, new_weight)
            st.success(f"Added {new_ticker}")
            st.rerun()
