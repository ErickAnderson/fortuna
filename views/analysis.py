"""Fortuna — AI Analysis page with charts, prompt generation, and timeline."""

import streamlit as st
import streamlit.components.v1 as components
import base64
import json
from datetime import datetime
import database as db
import market_data as md
import ai_engine as ai
import charts


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

    # Tabs for chart, analysis, and timeline
    tab_chart, tab_analyze, tab_timeline = st.tabs(["Chart", "Analyze", "Timeline"])

    with tab_chart:
        _render_chart(selected_ticker)

    with tab_analyze:
        _render_analysis(selected_ticker, positions)

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
    """Render AI analysis section — API or manual prompt mode."""

    api_configured = ai.is_api_configured()

    if api_configured:
        provider, _, _ = ai._get_config()
        st.success(f"AI API configured ({provider}). Analysis will run automatically.")
    else:
        st.info("No AI API configured. Using manual prompt mode — copy the prompt to your Claude/ChatGPT session.")

    if st.button(f"Analyze {ticker}", type="primary", key="run_analysis"):
        # Clear previous prompt state when re-analyzing
        st.session_state.pop("manual_prompt", None)
        st.session_state.pop("manual_prompt_ticker", None)
        _run_analysis(ticker, positions, api_configured)

    # Render manual prompt UI from session state (persists across reruns)
    if (
        st.session_state.get("manual_prompt_ticker") == ticker
        and "manual_prompt" in st.session_state
    ):
        state = st.session_state["manual_prompt"]
        _render_manual_prompt(
            state["system_prompt"],
            state["user_prompt"],
            ticker,
            positions,
        )


def _run_analysis(ticker: str, positions: list[dict], api_configured: bool):
    """Gather data and run or display analysis."""

    with st.spinner("Gathering market data..."):
        # Portfolio summary with current weights
        portfolio = db.get_portfolio_summary()
        prices = md.get_batch_prices(tuple(p["ticker"] for p in portfolio))
        total_value = sum(
            (prices.get(p["ticker"], 0) or 0) * p["qty"]
            for p in portfolio
        )
        for p in portfolio:
            price = prices.get(p["ticker"])
            value = (price * p["qty"]) if price and p["qty"] > 0 else 0
            p["current_weight"] = round(value / total_value * 100, 2) if total_value > 0 else 0
            p["current_price"] = price

        # Stock info
        stock_info = md.get_stock_info(ticker)

        # Price history with indicators
        price_data = md.get_price_history(ticker, period="1y")
        df = charts.compute_indicators(price_data)
        price_summary = charts.get_price_summary(df)
        technical_indicators = charts.get_indicator_summary(df)

        # News
        news = None
        try:
            stock = md.get_stock(ticker)
            news = stock.news
        except Exception:
            pass

        # Analyst recommendations
        recommendations = None
        try:
            stock = md.get_stock(ticker)
            recs = stock.recommendations
            if recs is not None and not recs.empty:
                recommendations = recs.tail(5).to_dict("records")
        except Exception:
            pass

        # Previous analyses (guard against None position_id)
        pos_id = next((p["id"] for p in positions if p["ticker"] == ticker), None)
        previous = db.get_analyses(pos_id) if pos_id is not None else []

    # Build prompt
    system_prompt, user_prompt = ai.build_analysis_prompt(
        ticker=ticker,
        portfolio_summary=portfolio,
        stock_info=stock_info,
        price_history_summary=price_summary,
        technical_indicators=technical_indicators,
        news=news,
        recommendations=recommendations,
        previous_analyses=previous[:3] if previous else None,
    )

    if api_configured:
        # Auto mode — call API
        with st.spinner("Running AI analysis..."):
            result = ai.call_ai_api(system_prompt, user_prompt)

        if result and "error" not in result:
            _save_and_display_analysis(ticker, positions, result)
        elif result and "error" in result:
            st.error(f"AI API error: {result['error']}")
            st.markdown("Falling back to manual prompt mode below.")
            _store_manual_prompt(system_prompt, user_prompt, ticker)
        else:
            st.error("Failed to get AI response.")
            _store_manual_prompt(system_prompt, user_prompt, ticker)
    else:
        # Manual prompt mode — store in session state, rendered by _render_analysis
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

    st.markdown("### Generated Prompt")
    st.markdown("Copy this prompt to your AI assistant (Claude, ChatGPT, etc.):")

    st.code(full_prompt, language="text")

    # Clipboard copy via embedded JS button (avoids Streamlit rerun issues)
    # Store text as base64 in JS to avoid HTML attribute escaping issues
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
        <span id="copyMsg" style="color: #00C853; font-family: sans-serif; margin-left: 10px; display: none;">
            Copied!
        </span>
        """,
        height=50,
    )

    st.markdown("---")
    st.markdown("### Paste AI Response")
    st.markdown("Paste the JSON response from your AI assistant:")

    response_text = st.text_area(
        "AI Response (JSON)",
        height=300,
        key="ai_response",
        placeholder='{\n    "verdict": "BUY|SELL|HOLD",\n    "price_target": 0.00,\n    "summary": "...",\n    "full_analysis": "..."\n}',
    )

    if st.button("Save Analysis", key="save_manual") and response_text:
        try:
            result = json.loads(response_text)
            _save_and_display_analysis(ticker, positions, result)
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


def _save_and_display_analysis(ticker: str, positions: list[dict], result: dict):
    """Save analysis to DB and display it."""
    position = next((p for p in positions if p["ticker"] == ticker), None)
    if not position:
        st.error(f"Position {ticker} not found.")
        return

    verdict = _normalize_verdict(result.get("verdict", "HOLD"))

    # Safely parse price_target
    raw_target = result.get("price_target")
    try:
        price_target = float(raw_target) if raw_target is not None else None
    except (ValueError, TypeError):
        price_target = None

    summary = result.get("summary", "")
    full_analysis = result.get("full_analysis", "")

    db.add_analysis(
        position_id=position["id"],
        verdict=verdict,
        price_target=price_target,
        summary=summary,
        full_analysis=full_analysis,
    )

    _display_analysis_result(verdict, price_target, summary, full_analysis)
    st.success("Analysis saved to timeline.")


def _display_analysis_result(verdict: str, price_target, summary: str, full_analysis: str):
    """Display a single analysis result with formatting."""
    # Verdict badge
    verdict_colors = {"BUY": "#00C853", "SELL": "#FF5252", "HOLD": "#FFA726"}
    color = verdict_colors.get(verdict.upper(), "#FAFAFA")

    target_text = f"${price_target:.2f}" if price_target is not None else "N/A"

    st.markdown(
        f'<div style="text-align:center; padding:20px; margin:10px 0; '
        f'border:2px solid {color}; border-radius:12px;">'
        f'<h1 style="color:{color} !important; margin:0;">{verdict.upper()}</h1>'
        f'<p style="font-size:1.2em; color:#FAFAFA;">Target: {target_text}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(f"### Summary\n{summary}")

    with st.expander("Full Analysis", expanded=True):
        st.markdown(full_analysis)


def _render_timeline(ticker: str):
    """Render analysis history timeline with accuracy scoring."""
    position = db.get_position_by_ticker(ticker)
    if not position:
        st.info("No position found.")
        return

    analyses = db.get_analyses(position["id"])

    if not analyses:
        st.info(f"No previous analyses for {ticker}. Run an analysis first.")
        return

    st.markdown(f"### Analysis History — {ticker}")

    for analysis in analyses:
        date_str = analysis["date"][:10]
        verdict = analysis.get("verdict", "N/A")
        target = analysis.get("price_target")
        target_str = f"${target:.2f}" if target is not None else "N/A"
        score_str = f" | Score: {analysis['accuracy_score']}/10" if analysis.get("accuracy_score") is not None else ""

        with st.expander(f"{date_str} — [{verdict}] Target: {target_str}{score_str}"):
            if analysis.get("summary"):
                st.markdown(f"**Summary:** {analysis['summary']}")

            if analysis.get("full_analysis"):
                st.markdown(analysis["full_analysis"])

            # Accuracy scoring
            st.markdown("---")
            st.markdown("**Rate this analysis (how accurate was it?)**")

            col1, col2 = st.columns([1, 3])
            with col1:
                score = st.number_input(
                    "Score (0-10)",
                    min_value=0.0,
                    max_value=10.0,
                    value=analysis.get("accuracy_score") or 0.0,
                    step=0.5,
                    key=f"score_{analysis['id']}",
                )
            with col2:
                notes = st.text_input(
                    "Notes (what happened vs predicted)",
                    value=analysis.get("accuracy_notes") or "",
                    key=f"notes_{analysis['id']}",
                )

            if st.button("Save Score", key=f"save_score_{analysis['id']}"):
                db.update_analysis_accuracy(analysis["id"], score, notes)
                st.success("Score saved")
