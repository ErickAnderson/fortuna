"""Fortuna — Personal ASX Portfolio Tracker."""

import streamlit as st
import database as db

# Initialize database once per session
if "db_initialized" not in st.session_state:
    db.init_db()
    st.session_state.db_initialized = True

st.set_page_config(
    page_title="Fortuna",
    page_icon="⚜",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for clean dark UI
st.markdown("""
<style>
    /* Gold accent headers */
    h1, h2, h3 { color: #D4AF37 !important; }

    /* Metric cards */
    [data-testid="stMetric"] {
        background-color: #1A1D24;
        border: 1px solid #2A2D34;
        border-radius: 8px;
        padding: 12px;
    }

    /* Positive/negative colors */
    .positive { color: #00C853 !important; }
    .negative { color: #FF5252 !important; }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #0E1117;
        border-right: 1px solid #2A2D34;
    }

    /* Table styling */
    .stDataFrame { border-radius: 8px; }

    /* Clean button styling */
    .stButton > button {
        border: 1px solid #D4AF37;
        color: #D4AF37;
        background-color: transparent;
    }
    .stButton > button:hover {
        background-color: #D4AF37;
        color: #0E1117;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar navigation
st.sidebar.markdown("# ⚜ Fortuna")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate",
    ["Portfolio", "Transactions", "Analysis", "Dividends", "Planner"],
    label_visibility="collapsed",
)

if page == "Portfolio":
    from pages import portfolio
    portfolio.render()
elif page == "Transactions":
    from pages import transactions
    transactions.render()
elif page == "Analysis":
    from pages import analysis
    analysis.render()
elif page == "Dividends":
    from pages import dividends
    dividends.render()
elif page == "Planner":
    from pages import planner
    planner.render()
