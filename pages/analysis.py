"""Fortuna — Analysis page (placeholder for Phase 2)."""

import streamlit as st
import database as db


def render():
    st.markdown("# Analysis")
    st.info("AI-powered analysis coming in Phase 2. Stay tuned.")

    positions = db.get_positions()
    if positions:
        st.markdown("### Available positions for analysis")
        for pos in positions:
            st.markdown(f"- **{pos['ticker']}** (target: {pos['target_weight']}%)")
