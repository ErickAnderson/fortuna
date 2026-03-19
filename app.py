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

    /* Gold accent headers */
    h1, h2, h3 { color: #D4AF37 !important; }

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
</style>
""", unsafe_allow_html=True)

# Sidebar navigation
st.sidebar.markdown("# ⚜ Fortuna")
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
