"""Fortuna — Transactions page."""

import streamlit as st
import pandas as pd
from datetime import date, datetime
import database as db
import market_data as md
from components.dataframes import style_txn_type


def render():
    st.markdown("# Transactions")

    positions = db.get_positions()
    if not positions:
        st.warning("Add positions in the Portfolio page first.")
        return

    brokers = db.get_brokers()
    ticker_map = {p["ticker"]: p["id"] for p in positions}
    broker_map = {b["name"]: b for b in brokers}

    # Get portfolio summary for sell validation
    portfolio = db.get_portfolio_summary()
    holdings = {p["ticker"]: p["qty"] for p in portfolio}

    # Transaction form
    tab_buy, tab_sell = st.tabs(["Buy", "Sell"])

    with tab_buy:
        _render_buy_form(positions, brokers, ticker_map, broker_map)

    with tab_sell:
        _render_sell_form(positions, brokers, ticker_map, broker_map, holdings)

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

    # Selectable dataframe
    event = st.dataframe(
        display_df.style.map(
            style_txn_type,
            subset=["Type"],
        ).format({
            "Qty": "{:,.0f}",
            "Price": "${:,.2f}",
            "Fee": "${:,.2f}",
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
            f"{txn['qty']:,.0f}x ${txn['price']:,.2f}"
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
                f"{txn['qty']:,.0f}x ${txn['price']:,.2f}?"
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


def _render_buy_form(positions, brokers, ticker_map, broker_map):
    """Buy form — all tickers available, defaults to market price."""
    col1, col2 = st.columns(2)

    with col1:
        ticker = st.selectbox(
            "Ticker",
            options=[p["ticker"] for p in positions],
            key="buy_ticker",
        )
        qty = st.number_input(
            "Quantity",
            min_value=1,
            value=1,
            step=1,
            key="buy_qty",
        )
        txn_date = st.date_input(
            "Date",
            value=date.today(),
            key="buy_date",
        )

    # Update price when ticker changes
    if ticker != st.session_state.get("_buy_last_ticker"):
        market_price = md.get_current_price(ticker) if ticker else None
        if market_price is not None:
            st.session_state.buy_price = market_price
        st.session_state._buy_last_ticker = ticker

    with col2:
        price = st.number_input(
            "Price per share ($)",
            min_value=0.01,
            value=st.session_state.get("buy_price", 1.00),
            step=0.01,
            format="%.2f",
            key="buy_price",
        )

        broker_names = [b["name"] for b in brokers]
        selected_broker = st.selectbox(
            "Broker",
            options=["None"] + broker_names,
            index=1 if broker_names else 0,
            key="buy_broker",
        )

        default_fee = 0.0
        if selected_broker != "None" and selected_broker in broker_map:
            default_fee = broker_map[selected_broker]["default_fee"]

        fee = st.number_input(
            "Fee ($)",
            min_value=0.0,
            value=default_fee,
            step=0.01,
            format="%.2f",
            key="buy_fee",
        )

    total = qty * price + fee
    st.markdown(f"**Total: ${total:,.2f}**")

    if st.button("Submit Buy", key="buy_submit", type="primary"):
        position_id = ticker_map[ticker]
        broker_id = broker_map[selected_broker]["id"] if selected_broker != "None" else None

        db.add_transaction(
            position_id=position_id,
            txn_type="buy",
            txn_date=str(txn_date),
            qty=qty,
            price=price,
            fee=fee,
            broker_id=broker_id,
        )
        st.success(f"Buy recorded: {qty:,}x {ticker} @ ${price:,.2f}")
        st.rerun()


def _render_sell_form(positions, brokers, ticker_map, broker_map, holdings):
    """Sell form — only tickers with holdings, max qty enforced."""
    # Filter to only tickers with qty > 0
    sellable = [p for p in positions if holdings.get(p["ticker"], 0) > 0]

    if not sellable:
        st.info("No holdings to sell. Buy some shares first.")
        return

    col1, col2 = st.columns(2)

    with col1:
        ticker = st.selectbox(
            "Ticker",
            options=[p["ticker"] for p in sellable],
            key="sell_ticker",
        )

        max_qty = int(holdings.get(ticker, 0))

        qty = st.number_input(
            f"Quantity (max {max_qty:,})",
            min_value=1,
            max_value=max_qty,
            value=min(1, max_qty),
            step=1,
            key="sell_qty",
        )
        txn_date = st.date_input(
            "Date",
            value=date.today(),
            key="sell_date",
        )

    # Update price when ticker changes
    if ticker != st.session_state.get("_sell_last_ticker"):
        market_price = md.get_current_price(ticker) if ticker else None
        if market_price is not None:
            st.session_state.sell_price = market_price
        st.session_state._sell_last_ticker = ticker

    with col2:
        price = st.number_input(
            "Price per share ($)",
            min_value=0.01,
            value=st.session_state.get("sell_price", 1.00),
            step=0.01,
            format="%.2f",
            key="sell_price",
        )

        broker_names = [b["name"] for b in brokers]
        selected_broker = st.selectbox(
            "Broker",
            options=["None"] + broker_names,
            index=1 if broker_names else 0,
            key="sell_broker",
        )

        default_fee = 0.0
        if selected_broker != "None" and selected_broker in broker_map:
            default_fee = broker_map[selected_broker]["default_fee"]

        fee = st.number_input(
            "Fee ($)",
            min_value=0.0,
            value=default_fee,
            step=0.01,
            format="%.2f",
            key="sell_fee",
        )

    total = qty * price - fee
    st.markdown(f"**Total: ${total:,.2f}**")

    if st.button("Submit Sell", key="sell_submit", type="primary"):
        position_id = ticker_map[ticker]
        broker_id = broker_map[selected_broker]["id"] if selected_broker != "None" else None

        db.add_transaction(
            position_id=position_id,
            txn_type="sell",
            txn_date=str(txn_date),
            qty=qty,
            price=price,
            fee=fee,
            broker_id=broker_id,
        )
        st.success(f"Sell recorded: {qty:,}x {ticker} @ ${price:,.2f}")
        st.rerun()
