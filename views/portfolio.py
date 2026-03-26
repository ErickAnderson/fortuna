"""Fortuna — Portfolio Dashboard page."""

import streamlit as st
import pandas as pd
import database as db
import services.portfolio as svc
import components.metrics as metrics
from components.dataframes import style_pnl, style_weight_diff


def render():
    st.markdown("# Portfolio")

    rows, total_cost, total_value, total_fees = svc.build_portfolio_rows()

    if not rows:
        st.info("No positions yet. Add tickers below to get started.")
        _render_add_position()
        return

    # Warn on negative quantities
    for row in rows:
        if row["qty"] < 0:
            st.warning(f"{row['ticker']} has negative qty ({row['qty']}). Check transactions.")

    # Top-level metrics
    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0.0
    metrics.render_portfolio_summary(total_cost, total_value, total_pnl, total_pnl_pct, total_fees)

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
