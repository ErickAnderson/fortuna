"""Fortuna — Transactions page."""

import streamlit as st
import pandas as pd
from datetime import date, datetime
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

    # Build display dataframe
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

    # Selectable dataframe — click a row to select it
    event = st.dataframe(
        display_df.style.map(
            lambda val: "color: #00C853" if val == "buy" else ("color: #FF5252" if val == "sell" else ""),
            subset=["Type"],
        ).format({
            "Qty": "{:.0f}",
            "Price": "${:.2f}",
            "Fee": "${:.2f}",
            "Total": "${:,.2f}",
        }),
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="txn_table",
    )

    # Show actions for selected row
    selected_rows = event.selection.rows if event.selection else []

    if selected_rows:
        row_idx = selected_rows[0]
        txn = transactions[row_idx]

        st.markdown(
            f"**Selected:** #{txn['id']} — {txn['date']} | "
            f"{txn['type'].upper()} | {txn['ticker']} | "
            f"{txn['qty']:.0f}x ${txn['price']:.2f}"
        )

        col_edit, col_delete, col_spacer = st.columns([1, 1, 4])

        with col_edit:
            if st.button("Edit", key="action_edit", use_container_width=True):
                st.session_state.editing_txn_id = txn["id"]

        with col_delete:
            if st.button("Delete", key="action_delete", type="secondary", use_container_width=True):
                st.session_state.confirm_delete_txn_id = txn["id"]

    # Confirm delete dialog
    if "confirm_delete_txn_id" in st.session_state:
        txn_id = st.session_state.confirm_delete_txn_id
        txn = next((t for t in transactions if t["id"] == txn_id), None)
        if txn:
            st.warning(
                f"Are you sure you want to delete: "
                f"{txn['date']} | {txn['type'].upper()} | {txn['ticker']} | "
                f"{txn['qty']:.0f}x ${txn['price']:.2f}?"
            )
            col_yes, col_no, _ = st.columns([1, 1, 4])
            with col_yes:
                if st.button("Yes, delete", key="confirm_yes", type="primary"):
                    db.delete_transaction(txn_id)
                    del st.session_state.confirm_delete_txn_id
                    st.success("Transaction deleted")
                    st.rerun()
            with col_no:
                if st.button("Cancel", key="confirm_no"):
                    del st.session_state.confirm_delete_txn_id
                    st.rerun()

    # Edit form
    if "editing_txn_id" in st.session_state:
        txn_id = st.session_state.editing_txn_id
        txn = next((t for t in transactions if t["id"] == txn_id), None)
        if txn:
            _render_edit_form(txn, brokers, broker_map)


def _render_edit_form(txn: dict, brokers: list, broker_map: dict):
    """Render inline edit form for a transaction."""
    st.markdown("---")
    st.markdown(f"### Edit Transaction #{txn['id']}")

    col1, col2 = st.columns(2)

    with col1:
        edit_date = st.date_input(
            "Date",
            value=datetime.strptime(txn["date"], "%Y-%m-%d").date(),
            key="edit_date",
        )
        edit_qty = st.number_input(
            "Quantity",
            min_value=1,
            value=int(txn["qty"]),
            step=1,
            key="edit_qty",
        )

    with col2:
        edit_price = st.number_input(
            "Price per share ($)",
            min_value=0.01,
            value=float(txn["price"]),
            step=0.01,
            format="%.2f",
            key="edit_price",
        )

        broker_names = [b["name"] for b in brokers]
        current_broker = txn.get("broker_name") or "None"
        broker_idx = (["None"] + broker_names).index(current_broker) if current_broker in ["None"] + broker_names else 0

        edit_broker = st.selectbox(
            "Broker",
            options=["None"] + broker_names,
            index=broker_idx,
            key="edit_broker",
        )

        default_fee = 0.0
        if edit_broker != "None" and edit_broker in broker_map:
            default_fee = broker_map[edit_broker]["default_fee"]

        edit_fee = st.number_input(
            "Fee ($)",
            min_value=0.0,
            value=float(txn["fee"]),
            step=0.01,
            format="%.2f",
            key="edit_fee",
        )

    col_save, col_cancel, _ = st.columns([1, 1, 4])

    with col_save:
        if st.button("Save", key="edit_save", type="primary", use_container_width=True):
            broker_id = broker_map[edit_broker]["id"] if edit_broker != "None" else None
            db.update_transaction(
                txn_id=txn["id"],
                txn_date=str(edit_date),
                qty=edit_qty,
                price=edit_price,
                fee=edit_fee,
                broker_id=broker_id,
            )
            del st.session_state.editing_txn_id
            st.success("Transaction updated")
            st.rerun()

    with col_cancel:
        if st.button("Cancel", key="edit_cancel", use_container_width=True):
            del st.session_state.editing_txn_id
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
