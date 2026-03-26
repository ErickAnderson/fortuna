"""Fortuna — AI Analysis page with charts, prompt generation, and timeline."""

import html as html_mod
import streamlit as st
import streamlit.components.v1 as components
import base64
import json
from datetime import datetime
import database as db
import market_data as md
import ai_engine as ai
import charts
import services.analysis as svc
from components.formatting import VERDICT_COLORS, BORDER, format_au_date


def render():
    st.markdown("# Analysis")

    positions = db.get_positions()
    if not positions:
        st.warning("Add positions in the Portfolio page first.")
        return

    # Ticker selector
    ticker_options = [p["ticker"] for p in positions]
    selected_ticker = st.selectbox("Select position to analyze", options=ticker_options)

    if not selected_ticker:
        return

    # Tabs — AI Analysis is the hero, then Chart, then Timeline
    tab_analyze, tab_chart, tab_timeline = st.tabs(["AI Analysis", "Chart", "Timeline"])

    with tab_analyze:
        _render_analysis(selected_ticker, positions)

    with tab_chart:
        _render_chart(selected_ticker)

    with tab_timeline:
        _render_timeline(selected_ticker)


def _render_chart(ticker: str):
    """Render candlestick chart with technical indicators."""
    period = st.selectbox(
        "Period",
        options=["1mo", "3mo", "6mo", "1y", "2y"],
        index=2,
        key="chart_period",
    )

    with st.spinner(f"Loading {ticker} chart..."):
        price_data = md.get_price_history(ticker, period=period)

    if price_data.empty:
        st.error(f"No price data available for {ticker}.AX")
        return

    # Compute indicators and render chart
    df = charts.compute_indicators(price_data)
    fig = charts.create_candlestick_chart(df, f"{ticker}.AX")
    st.plotly_chart(fig, use_container_width=True)

    # Show current indicator values
    indicators = charts.get_indicator_summary(df)
    if indicators:
        st.markdown("### Current Indicators")
        cols = st.columns(4)
        col_idx = 0
        def fmt_price(val):
            return f"${val}" if val is not None else "N/A"

        display_items = [
            ("Price", fmt_price(indicators.get("current_price"))),
            ("RSI (14)", f"{indicators.get('RSI', 'N/A')} ({indicators.get('RSI_signal', '')})"),
            ("MACD", f"{indicators.get('MACD_signal', 'N/A')}"),
            ("52w Range", f"{indicators.get('52w_range_position', 'N/A')}"),
            ("MA20", fmt_price(indicators.get("MA20"))),
            ("MA50", fmt_price(indicators.get("MA50"))),
            ("MA200", fmt_price(indicators.get("MA200"))),
            ("Volume", indicators.get("volume_vs_avg", "N/A")),
        ]
        for label, value in display_items:
            with cols[col_idx % 4]:
                st.metric(label, value)
            col_idx += 1


def _render_analysis(ticker: str, positions: list[dict]):
    """Render AI analysis section — AI-powered analysis + manual prompt fallback."""

    provider_options = ai.get_provider_model_options()
    run_ai = False
    selected_provider = None
    selected_model = None

    # Row 1: Generate AI Prompt (manual mode)
    if st.button(f"Generate AI Prompt {ticker}", key="gen_prompt", use_container_width=True):
        st.session_state.pop("manual_prompt", None)
        st.session_state.pop("manual_prompt_ticker", None)
        with st.spinner("Gathering market data..."):
            system_prompt, user_prompt = svc.gather_analysis_data(ticker, positions)
        _store_manual_prompt(system_prompt, user_prompt, ticker)

    # "or" divider
    st.markdown(
        '<div style="text-align:center; color:#888; margin: 0.25rem 0;">or</div>',
        unsafe_allow_html=True,
    )

    # Row 2: [Provider] [Model] [Run AI Analysis]
    if provider_options:
        provider_names = list(provider_options.keys())
        col_prov, col_model, col_run = st.columns([1, 2, 1])

        with col_prov:
            selected_prov_label = st.selectbox(
                "Provider",
                options=provider_names,
                key="ai_provider_select",
                label_visibility="collapsed",
            )
        with col_model:
            models = provider_options[selected_prov_label]
            selected_mdl = st.selectbox(
                "Model",
                options=models,
                key="ai_model_select",
                label_visibility="collapsed",
            )
        with col_run:
            if st.button("Run AI Analysis", type="primary", key="run_ai_analysis", use_container_width=True):
                selected_provider = selected_prov_label.replace(" (env)", "").lower()
                selected_model = selected_mdl
                run_ai = True
    else:
        st.info("Configure an AI provider in Settings to enable automated analysis.")

    # Run AI analysis at full width (outside columns)
    if run_ai and selected_provider:
        _run_ai_analysis(ticker, positions, selected_provider, selected_model)

    # Render manual prompt UI from session state (persists across reruns)
    if (
        st.session_state.get("manual_prompt_ticker") == ticker
        and "manual_prompt" in st.session_state
    ):
        st.markdown("---")
        state = st.session_state["manual_prompt"]
        _render_manual_prompt(
            state["system_prompt"],
            state["user_prompt"],
            ticker,
            positions,
        )


def _run_ai_analysis(ticker: str, positions: list[dict], provider_name: str, model: str | None = None):
    """Gather data and run AI analysis with selected provider."""
    with st.spinner("Gathering market data..."):
        system_prompt, user_prompt = svc.gather_analysis_data(ticker, positions)

    with st.spinner(f"Running AI analysis via {provider_name}..."):
        result = ai.call_ai_api(system_prompt, user_prompt, provider_name, model)

    if result and "error" not in result:
        _save_and_display_analysis(ticker, positions, result, provider=provider_name)
    elif result and "error" in result:
        st.error(f"AI API error: {result['error']}")
        _store_manual_prompt(system_prompt, user_prompt, ticker)
    else:
        st.error("Failed to get AI response.")
        _store_manual_prompt(system_prompt, user_prompt, ticker)


def _store_manual_prompt(system_prompt: str, user_prompt: str, ticker: str):
    """Store prompt data in session state for persistent rendering."""
    st.session_state["manual_prompt"] = {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
    }
    st.session_state["manual_prompt_ticker"] = ticker


def _render_manual_prompt(system_prompt: str, user_prompt: str, ticker: str, positions: list[dict]):
    """Show copyable prompt and input for pasting AI response."""

    full_prompt = f"SYSTEM:\n{system_prompt}\n\nUSER:\n{user_prompt}"

    st.markdown("#### Generated Prompt")

    st.code(full_prompt, language="text")

    # Clipboard copy via embedded JS button (avoids Streamlit rerun issues)
    b64_prompt = base64.b64encode(full_prompt.encode()).decode()
    components.html(
        f"""
        <script>
        function copyPrompt() {{
            var text = atob("{b64_prompt}");
            navigator.clipboard.writeText(text).then(
                function() {{ document.getElementById('copyMsg').style.display='inline'; }},
                function() {{ document.getElementById('copyMsg').textContent='Copy failed'; document.getElementById('copyMsg').style.display='inline'; }}
            );
        }}
        </script>
        <button id="copyBtn" onclick="copyPrompt()" style="
            background-color: #262730; color: #FAFAFA; border: 1px solid #4A4A5A;
            padding: 8px 16px; border-radius: 8px; cursor: pointer;
            font-size: 14px; font-family: sans-serif;
        ">Copy to Clipboard</button>
        <span id="copyMsg" style="font-family: sans-serif; margin-left: 10px; display: none;">
            Copied!
        </span>
        """,
        height=50,
    )

    st.markdown("#### Paste AI Response")

    response_text = st.text_area(
        "AI Response (JSON)",
        height=300,
        key="ai_response",
        label_visibility="collapsed",
        placeholder='{\n    "verdict": "BUY|SELL|HOLD",\n    "price_target": 0.00,\n    "summary": "...",\n    "full_analysis": "...",\n    "action_plan": "..."\n}',
    )

    if st.button("Save Analysis", key="save_manual") and response_text:
        try:
            result = json.loads(response_text)
            _save_and_display_analysis(ticker, positions, result, provider="manual")
        except json.JSONDecodeError:
            st.error("Invalid JSON. Make sure to paste the complete JSON response.")


def _normalize_verdict(verdict: str) -> str:
    """Normalize verdict to BUY, SELL, or HOLD."""
    v = verdict.upper().strip()
    if "BUY" in v:
        return "BUY"
    elif "SELL" in v:
        return "SELL"
    return "HOLD"


def _save_and_display_analysis(ticker: str, positions: list[dict], result: dict, provider: str = "manual"):
    """Save analysis to DB and display it."""
    position = next((p for p in positions if p["ticker"] == ticker), None)
    if not position:
        st.error(f"Position {ticker} not found.")
        return

    verdict = _normalize_verdict(result.get("verdict", "HOLD"))

    raw_target = result.get("price_target")
    try:
        price_target = float(raw_target) if raw_target is not None else None
    except (ValueError, TypeError):
        price_target = None

    summary = result.get("summary", "")
    full_analysis = result.get("full_analysis", "")

    action_plan = result.get("action_plan", "")
    if action_plan and "action plan" not in full_analysis.lower():
        full_analysis += f"\n\n## Action Plan\n{action_plan}"

    db.add_analysis(
        position_id=position["id"],
        verdict=verdict,
        price_target=price_target,
        summary=summary,
        full_analysis=full_analysis,
        provider=provider,
    )

    _display_analysis_result(verdict, price_target, summary, full_analysis)
    st.success("Analysis saved to timeline.")


def _display_analysis_result(verdict: str, price_target, summary: str, full_analysis: str):
    """Display a single analysis result with formatting."""
    color = VERDICT_COLORS.get(verdict.upper(), "#FAFAFA")

    target_text = f"${price_target:.2f}" if price_target is not None else "N/A"

    st.markdown(
        f'<div style="text-align:center; padding:20px; margin:10px 0; '
        f'border:2px solid {color}; border-radius:12px;">'
        f'<h1 style="color:{color} !important; margin:0;">{html_mod.escape(verdict.upper())}</h1>'
        f'<p style="font-size:1.2em; color:#FAFAFA;">Target: {html_mod.escape(target_text)}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(f"### Summary\n{summary}")

    with st.expander("Full Analysis", expanded=True):
        st.markdown(full_analysis)


@st.dialog("Analysis Details", width="large")
def _show_analysis_dialog(analysis_id: int):
    """Modal dialog showing full analysis details and scoring."""
    analysis = db.get_analysis_by_id(analysis_id)
    if not analysis:
        st.error("Analysis not found.")
        return

    verdict = analysis.get("verdict", "N/A")
    color = VERDICT_COLORS.get(verdict.upper(), "#FAFAFA")
    target = analysis.get("price_target")
    target_str = f"${target:.2f}" if target is not None else "N/A"
    provider = analysis.get("provider", "unknown")
    provider_label = provider.title() if provider and provider != "unknown" else "Unknown"
    date_str = format_au_date(analysis["date"])

    # Header
    st.markdown(
        f'<div style="text-align:center; padding:12px; margin-bottom:12px; '
        f'border:2px solid {color}; border-radius:12px;">'
        f'<h2 style="color:{color} !important; margin:0;">{html_mod.escape(verdict)}</h2>'
        f'<p style="color:#FAFAFA; margin:4px 0 0;">Target: {html_mod.escape(target_str)}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.caption(f"{date_str} — via {provider_label}")

    if analysis.get("summary"):
        st.markdown(f"**Summary:** {analysis['summary']}")

    if analysis.get("full_analysis"):
        st.markdown(analysis["full_analysis"])

    # Accuracy scoring
    st.markdown("---")
    st.markdown("**Rate Accuracy**")
    col_sc, col_notes, col_save = st.columns([1, 3, 1])
    with col_sc:
        score = st.number_input(
            "Score (0-10)",
            min_value=0.0,
            max_value=10.0,
            value=analysis.get("accuracy_score") or 0.0,
            step=0.5,
            key=f"dlg_score_{analysis['id']}",
        )
    with col_notes:
        notes = st.text_input(
            "Accuracy notes",
            value=analysis.get("accuracy_notes") or "",
            key=f"dlg_notes_{analysis['id']}",
        )
    with col_save:
        st.markdown("<div style='height: 1.65rem;'></div>", unsafe_allow_html=True)
        if st.button("Save", key=f"dlg_save_{analysis['id']}", use_container_width=True):
            db.update_analysis_accuracy(analysis["id"], score, notes)
            st.rerun()


def _render_timeline(ticker: str):
    """Render analysis history timeline with table-like layout and modal details."""
    position = db.get_position_by_ticker(ticker)
    if not position:
        st.info("No position found.")
        return

    analyses = db.get_analyses(position["id"])

    if not analyses:
        st.info(f"No previous analyses for {ticker}. Run an analysis first.")
        return

    st.markdown(f"### Analysis History — {ticker}")

    # Table header
    hd, ha, ht, hf, hs, hv = st.columns([2, 1, 1, 2, 1, 1])
    hd.markdown("**Date**")
    ha.markdown("**Action**")
    ht.markdown("**Target**")
    hf.markdown("**From**")
    hs.markdown("**Score**")
    hv.markdown("")
    st.markdown(
        f'<hr style="margin: 0.25rem 0 0.5rem; border-color: {BORDER};">',
        unsafe_allow_html=True,
    )

    for analysis in analyses:
        date_str = format_au_date(analysis["date"])
        verdict = analysis.get("verdict", "N/A")
        target = analysis.get("price_target")
        target_str = f"${target:.2f}" if target is not None else "—"
        provider = analysis.get("provider", "unknown")
        provider_label = provider.title() if provider and provider != "unknown" else "—"
        color = VERDICT_COLORS.get(verdict.upper(), "#FAFAFA")
        score_val = analysis.get("accuracy_score")
        score_str = f"{score_val}/10" if score_val is not None else "—"

        cd, ca, ct, cf, cs, cv = st.columns([2, 1, 1, 2, 1, 1])
        cd.markdown(date_str)
        ca.markdown(
            f'<span style="color:{color}; font-weight:600;">{html_mod.escape(verdict)}</span>',
            unsafe_allow_html=True,
        )
        ct.markdown(target_str)
        cf.markdown(provider_label)
        cs.markdown(score_str)
        if cv.button("View", key=f"view_{analysis['id']}", use_container_width=True):
            _show_analysis_dialog(analysis["id"])
