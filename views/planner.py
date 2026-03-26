"""Fortuna — Cash Deployment Planner page."""

import streamlit as st
import pandas as pd
import database as db
import market_data as md
import services.planner as svc
from components.formatting import DARK_CARD, BORDER, WHITE


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

    for pos in portfolio:
        pos["current_price"] = prices.get(pos["ticker"])
        pos["value"] = (pos["current_price"] * pos["qty"]) if pos["current_price"] and pos["qty"] > 0 else 0.0

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

    suggestions, total_value = svc.calculate_deployment_plan(portfolio, lump_sum)

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
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        row_height=32,
        column_config={
            "Suggested $": st.column_config.NumberColumn("Suggested $", format="$%,.2f"),
            "Shares":       st.column_config.NumberColumn("Shares",      format="%d"),
        },
    )

    total_deployed = sum(s["actual_cost"] for s in suggestions)
    remaining = lump_sum - total_deployed

    st.markdown(
        f"""
        <div style="display:grid; grid-template-columns:repeat(2,1fr); gap:12px; margin-bottom:16px;">
            <div style="background:{DARK_CARD}; border:1px solid {BORDER}; border-radius:8px; padding:14px 16px;">
                <p class="fortuna-label">Total Deployed</p>
                <p class="fortuna-value-primary">${total_deployed:,.2f}</p>
            </div>
            <div style="background:{DARK_CARD}; border:1px solid {BORDER}; border-radius:8px; padding:14px 16px;">
                <p class="fortuna-label">Remaining Cash</p>
                <p class="fortuna-value-primary">${remaining:,.2f}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
    st.dataframe(preview_df, use_container_width=True, hide_index=True, row_height=32)
