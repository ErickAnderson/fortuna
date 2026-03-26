"""Fortuna — shared metric card UI components."""

import streamlit as st
from components.formatting import DARK_CARD, BORDER, WHITE, GREEN, RED


def render_portfolio_summary(
    total_cost: float,
    total_value: float,
    total_pnl: float,
    total_pnl_pct: float,
    total_fees: float,
) -> None:
    """Render the 4-column portfolio summary metric card row."""
    color = GREEN if total_pnl >= 0 else RED
    bg = "rgba(0,200,83,0.15)" if total_pnl >= 0 else "rgba(255,82,82,0.15)"
    arrow = "▲" if total_pnl >= 0 else "▼"

    st.markdown(
        f"""
        <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:12px;">
            <div style="background:{DARK_CARD}; border:1px solid {BORDER}; border-radius:8px; padding:14px 16px;">
                <p style="font-size:0.85rem; color:#AAAAAA; margin:0 0 6px 0;">Total Invested</p>
                <p style="font-size:1.75rem; font-weight:700; margin:0; color:{WHITE};">${total_cost:,.2f}</p>
            </div>
            <div style="background:{DARK_CARD}; border:1px solid {BORDER}; border-radius:8px; padding:14px 16px;">
                <p style="font-size:0.85rem; color:#AAAAAA; margin:0 0 6px 0;">Current Value</p>
                <p style="font-size:1.75rem; font-weight:700; margin:0; color:{WHITE};">${total_value:,.2f}</p>
            </div>
            <div style="background:{DARK_CARD}; border:1px solid {BORDER}; border-radius:8px; padding:14px 16px;">
                <p style="font-size:0.85rem; color:#AAAAAA; margin:0 0 6px 0;">Total P&L</p>
                <p style="font-size:1.75rem; font-weight:700; margin:0; color:{WHITE};">
                    ${total_pnl:,.2f}
                    <span style="font-size:0.8rem; padding:2px 8px; border-radius:12px;
                        color:{color}; background:{bg}; margin-left:6px; vertical-align:middle;">
                        {arrow} {total_pnl_pct:+.2f}%
                    </span>
                </p>
            </div>
            <div style="background:{DARK_CARD}; border:1px solid {BORDER}; border-radius:8px; padding:14px 16px;">
                <p style="font-size:0.85rem; color:#AAAAAA; margin:0 0 6px 0;">Total Fees</p>
                <p style="font-size:1.75rem; font-weight:700; margin:0; color:{WHITE};">${total_fees:,.2f}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
