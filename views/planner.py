"""Fortuna — Cash Deployment Planner page."""

import streamlit as st
import pandas as pd
import database as db
import market_data as md


def render():
    st.markdown("# Cash Deployment Planner")

    portfolio = db.get_portfolio_summary()
    if not portfolio:
        st.info("No positions yet. Add tickers in Portfolio first.")
        return

    # Check for target weights
    total_target = sum(p["target_weight"] for p in portfolio)
    if total_target == 0:
        st.warning("Set target weights in the Portfolio page to get allocation suggestions.")
        return

    # Fetch current prices
    tickers = tuple(p["ticker"] for p in portfolio)
    with st.spinner("Fetching prices..."):
        prices = md.get_batch_prices(tickers)

    # Current portfolio value
    for pos in portfolio:
        pos["current_price"] = prices.get(pos["ticker"])
        pos["value"] = (pos["current_price"] * pos["qty"]) if pos["current_price"] and pos["qty"] > 0 else 0.0

    total_value = sum(p["value"] for p in portfolio)

    # Input: lump sum
    st.markdown("### How much do you want to invest?")
    lump_sum = st.number_input(
        "Lump sum ($)",
        min_value=0.0,
        value=1000.0,
        step=100.0,
        format="%.2f",
        key="lump_sum",
    )

    if lump_sum <= 0:
        st.info("Enter an amount above $0.")
        return

    new_total = total_value + lump_sum

    # Calculate suggested allocation to match target weights
    suggestions = []
    for pos in portfolio:
        target_value = new_total * (pos["target_weight"] / 100)
        current_value = pos["value"]
        needed = max(target_value - current_value, 0)

        # How many shares can that buy?
        price = pos["current_price"]
        shares = int(needed / price) if price and price > 0 else 0
        actual_cost = shares * price if price else 0

        suggestions.append({
            "ticker": pos["ticker"],
            "target_weight": pos["target_weight"],
            "current_value": current_value,
            "target_value": target_value,
            "suggested_amount": round(needed, 2),
            "suggested_shares": shares,
            "actual_cost": round(actual_cost, 2),
            "price": price,
        })

    # Normalize if total suggestions exceed lump sum
    total_suggested = sum(s["suggested_amount"] for s in suggestions)
    if total_suggested > 0:
        scale = min(lump_sum / total_suggested, 1.0)
        for s in suggestions:
            s["suggested_amount"] = round(s["suggested_amount"] * scale, 2)
            s["suggested_shares"] = int(s["suggested_amount"] / s["price"]) if s["price"] and s["price"] > 0 else 0
            s["actual_cost"] = round(s["suggested_shares"] * s["price"], 2) if s["price"] else 0

    st.markdown("---")
    st.markdown("### Suggested Allocation")
    st.markdown(f"Deploying **${lump_sum:,.2f}** to match target weights:")

    # Display table
    rows = []
    for s in suggestions:
        rows.append({
            "Ticker": s["ticker"],
            "Target %": f"{s['target_weight']:.1f}%",
            "Current Value": f"${s['current_value']:,.2f}",
            "Price": f"${s['price']:.2f}" if s["price"] is not None else "N/A",
            "Suggested $": s["suggested_amount"],
            "Shares": s["suggested_shares"],
            "Cost": f"${s['actual_cost']:,.2f}",
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    total_deployed = sum(s["actual_cost"] for s in suggestions)
    remaining = lump_sum - total_deployed

    col1, col2 = st.columns(2)
    col1.metric("Total Deployed", f"${total_deployed:,.2f}")
    col2.metric("Remaining Cash", f"${remaining:,.2f}")

    if remaining > 0:
        st.info(f"${remaining:,.2f} remaining due to whole-share rounding. "
                f"Consider adding to your largest underweight position.")

    # Post-deployment weight preview
    st.markdown("---")
    st.markdown("### Portfolio After Deployment")

    # Build lookup by ticker for safety
    sug_by_ticker = {s["ticker"]: s for s in suggestions}

    preview_rows = []
    new_total_after = total_value + total_deployed
    for pos in portfolio:
        sug = sug_by_ticker[pos["ticker"]]
        new_value = pos["value"] + sug["actual_cost"]
        new_weight = (new_value / new_total_after * 100) if new_total_after > 0 else 0
        preview_rows.append({
            "Ticker": pos["ticker"],
            "Target %": f"{pos['target_weight']:.1f}%",
            "Before %": f"{(pos['value'] / total_value * 100):.1f}%" if total_value > 0 else "0.0%",
            "After %": f"{new_weight:.1f}%",
            "Diff": f"{new_weight - pos['target_weight']:+.1f}%",
        })

    if remaining > 0:
        cash_pct = remaining / (new_total_after + remaining) * 100
        preview_rows.append({
            "Ticker": "CASH",
            "Target %": "—",
            "Before %": "—",
            "After %": f"{cash_pct:.1f}%",
            "Diff": "—",
        })

    preview_df = pd.DataFrame(preview_rows)
    st.dataframe(preview_df, use_container_width=True, hide_index=True)
