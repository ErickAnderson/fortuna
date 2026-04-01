"""Fortuna — Personal ASX Portfolio Tracker."""

import os
import sys

import streamlit as st
import database as db

__version__ = "0.1.0"

# Initialize database once per session
if "db_initialized" not in st.session_state:
    db.init_db()
    st.session_state.db_initialized = True

st.set_page_config(
    page_title="Fortuna",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Navigation state
if "current_page" not in st.session_state:
    st.session_state.current_page = "Portfolio"

# Custom CSS
st.markdown("""
<style>
    /* Dropdowns — pointer cursor */
    [data-baseweb="select"],
    [data-baseweb="select"] * {
        cursor: pointer !important;
    }

    /* Gold accent headers — consistent hierarchy */
    [data-testid="stMarkdownContainer"] h1 { color: #D4AF37 !important; font-size: 1.6rem !important; }
    [data-testid="stMarkdownContainer"] h2 { color: #D4AF37 !important; font-size: 1.25rem !important; }
    [data-testid="stMarkdownContainer"] h3 { color: #D4AF37 !important; font-size: 1.05rem !important; }

    /* Metric cards */
    [data-testid="stMetric"] {
        background-color: #1A1D24;
        border: 1px solid #2A2D34;
        border-radius: 8px;
        padding: 12px;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #0E1117;
        border-right: 1px solid #2A2D34;
    }

    /* Table styling */
    .stDataFrame { border-radius: 8px; }

    /* Prevent text overflow in markdown/analysis content */
    [data-testid="stMarkdownContainer"],
    [data-testid="stExpander"] {
        overflow-wrap: break-word;
        word-break: break-word;
    }

    /* Main content buttons — gold outline, balanced sizing */
    [data-testid="stMainBlockContainer"] .stButton {
        display: flex;
        justify-content: center;
    }
    [data-testid="stMainBlockContainer"] .stButton > button {
        border: 1px solid #D4AF37;
        color: #D4AF37;
        background-color: transparent;
        width: auto !important;
        min-width: 7rem;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        white-space: nowrap;
    }
    [data-testid="stMainBlockContainer"] .stButton > button:hover {
        background-color: #D4AF37;
        color: #0E1117;
    }

    /* Sidebar nav buttons — styled as links */
    [data-testid="stSidebar"] .stButton > button {
        background: transparent !important;
        border: none !important;
        border-left: 3px solid transparent !important;
        border-radius: 8px !important;
        color: #888888 !important;
        text-align: left !important;
        padding: 10px 16px !important;
        font-size: 0.95rem !important;
        font-weight: 400 !important;
        justify-content: flex-start !important;
    }
    [data-testid="stSidebar"] .stButton > button > div,
    [data-testid="stSidebar"] .stButton > button > div > p,
    [data-testid="stSidebar"] .stButton > button p {
        text-align: left !important;
        width: 100% !important;
    }
    [data-testid="stSidebar"] .stButton > button > div {
        display: flex !important;
        justify-content: flex-start !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: #1A1D24 !important;
        color: #D4AF37 !important;
    }
    [data-testid="stSidebar"] .stButton > button:focus {
        box-shadow: none !important;
    }
    /* Active nav — disabled buttons styled as highlighted */
    [data-testid="stSidebar"] .stButton > button:disabled {
        background-color: #1A1D24 !important;
        color: #D4AF37 !important;
        border-left: 3px solid #D4AF37 !important;
        font-weight: 600 !important;
        opacity: 1 !important;
        cursor: default !important;
    }

    /* Monospace font for financial numbers in dataframe cells */
    [data-testid="stDataFrame"] td {
        font-family: "SF Mono", "Fira Code", "Courier New", monospace !important;
        font-size: 0.82rem !important;
    }

    /* Metric card typography — label (muted) and value (prominent) */
    .fortuna-label {
        font-size: 0.8rem !important;
        color: #888888 !important;
        margin: 0 0 4px 0;
        line-height: 1.2;
    }
    .fortuna-value-primary {
        font-size: 1.75rem !important;
        font-weight: 700 !important;
        color: #FAFAFA !important;
        margin: 0;
        line-height: 1.2;
    }
    .fortuna-value-secondary {
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        color: #FAFAFA !important;
        margin: 0;
        line-height: 1.2;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar navigation
import base64 as _b64
_base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(_base_dir, "assets", "logo-cropped.png"), "rb") as _f:
    _logo_b64 = _b64.b64encode(_f.read()).decode()
st.sidebar.markdown(
    f'<div style="text-align:center;padding:0.5rem 0;"><img src="data:image/png;base64,{_logo_b64}" width="150" /></div>',
    unsafe_allow_html=True,
)
st.sidebar.markdown("---")

NAV_ITEMS = ["Portfolio", "Transactions", "Analysis", "Dividends", "Planner", "Settings", "Logs"]

for item in NAV_ITEMS:
    is_active = st.session_state.current_page == item
    clicked = st.sidebar.button(
        item,
        key=f"nav_{item}",
        use_container_width=True,
        disabled=is_active,
    )
    if clicked:
        st.session_state.current_page = item
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown(
    f'<div style="color:#555555; font-size:0.75rem; padding:4px 0;">Fortuna &nbsp;·&nbsp; v{__version__}</div>',
    unsafe_allow_html=True,
)

page = st.session_state.current_page

if page == "Portfolio":
    from views import portfolio
    portfolio.render()
elif page == "Transactions":
    from views import transactions
    transactions.render()
elif page == "Analysis":
    from views import analysis
    analysis.render()
elif page == "Dividends":
    from views import dividends
    dividends.render()
elif page == "Planner":
    from views import planner
    planner.render()
elif page == "Settings":
    from views import settings
    settings.render()
elif page == "Logs":
    from views import logs
    logs.render()
