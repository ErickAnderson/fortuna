"""Fortuna — Transactions page."""

import streamlit as st
import pandas as pd
from datetime import date
import database as db


def render():
    st.markdown("# Transactions")

    positions = db.get_positions()
    if not positions:
        st.warning("Add positions in the Portfolio page first.")
        return

    brokers = db.get_brokers()
    ticker_map = {p["ticker"]: p["id"] for p in positions}
    broker_map = {b["name"]: b for b in brokers}

    # Transaction form
    tab_buy, tab_sell = st.tabs(["Buy", "Sell"])

    with tab_buy:
        _render_transaction_form("buy", positions, brokers, ticker_map, broker_map)

    with tab_sell:
        _render_transaction_form("sell", positions, brokers, ticker_map, broker_map)

    st.markdown("---")

    # Transaction history
    st.markdown("### History")

    # Filter by ticker
    filter_ticker = st.selectbox(
        "Filter by ticker",
        options=["All"] + [p["ticker"] for p in positions],
        key="filter_ticker",
    )

    position_id = None
    if filter_ticker != "All":
        position_id = ticker_map.get(filter_ticker)

    transactions = db.get_transactions(position_id)

    if not transactions:
        st.info("No transactions yet.")
        return

    df = pd.DataFrame(transactions)
    display_df = df[[
        "date", "type", "ticker", "qty", "price", "fee", "broker_name",
    ]].copy()
    display_df["total"] = df.apply(
        lambda r: r["qty"] * r["price"] + r["fee"] if r["type"] == "buy"
        else r["qty"] * r["price"] - r["fee"],
        axis=1,
    )
    display_df.columns = ["Date", "Type", "Ticker", "Qty", "Price", "Fee", "Broker", "Total"]

    def style_type(val):
        if val == "buy":
            return "color: #00C853"
        elif val == "sell":
            return "color: #FF5252"
        return ""

    styled = display_df.style.map(
        style_type, subset=["Type"]
    ).format({
        "Qty": "{:.0f}",
        "Price": "${:.2f}",
        "Fee": "${:.2f}",
        "Total": "${:,.2f}",
    })

    st.dataframe(styled, use_container_width=True, hide_index=True)

    # Delete transaction
    st.markdown("### Delete Transaction")
    if transactions:
        txn_options = {
            f"#{t['id']} | {t['date']} | {t['type'].upper()} | {t['ticker']} | {t['qty']}x ${t['price']:.2f}": t["id"]
            for t in transactions
        }
        selected_txn = st.selectbox("Select transaction to delete", options=[""] + list(txn_options.keys()))
        if selected_txn and st.button("Delete Transaction", type="secondary"):
            db.delete_transaction(txn_options[selected_txn])
            st.success("Transaction deleted")
            st.rerun()


def _render_transaction_form(txn_type: str, positions, brokers, ticker_map, broker_map):
    prefix = txn_type

    col1, col2 = st.columns(2)

    with col1:
        ticker = st.selectbox(
            "Ticker",
            options=[p["ticker"] for p in positions],
            key=f"{prefix}_ticker",
        )
        qty = st.number_input(
            "Quantity",
            min_value=1,
            value=1,
            step=1,
            key=f"{prefix}_qty",
        )
        txn_date = st.date_input(
            "Date",
            value=date.today(),
            key=f"{prefix}_date",
        )

    with col2:
        price = st.number_input(
            "Price per share ($)",
            min_value=0.01,
            value=1.00,
            step=0.01,
            format="%.2f",
            key=f"{prefix}_price",
        )

        broker_names = [b["name"] for b in brokers]
        selected_broker = st.selectbox(
            "Broker",
            options=["None"] + broker_names,
            key=f"{prefix}_broker",
        )

        # Pre-populate fee from broker default
        default_fee = 0.0
        if selected_broker != "None" and selected_broker in broker_map:
            default_fee = broker_map[selected_broker]["default_fee"]

        fee = st.number_input(
            "Fee ($)",
            min_value=0.0,
            value=default_fee,
            step=0.01,
            format="%.2f",
            key=f"{prefix}_fee",
        )

    # Summary
    if txn_type == "buy":
        total = qty * price + fee
    else:
        total = qty * price - fee
    st.markdown(f"**Total: ${total:,.2f}**")

    if st.button(f"Submit {txn_type.title()}", key=f"{prefix}_submit", type="primary"):
        position_id = ticker_map[ticker]
        broker_id = broker_map[selected_broker]["id"] if selected_broker != "None" else None

        db.add_transaction(
            position_id=position_id,
            txn_type=txn_type,
            txn_date=str(txn_date),
            qty=qty,
            price=price,
            fee=fee,
            broker_id=broker_id,
        )
        st.success(f"{txn_type.title()} recorded: {qty}x {ticker} @ ${price:.2f}")
        st.rerun()
