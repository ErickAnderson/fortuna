"""Fortuna — AI Analysis page with charts, prompt generation, and timeline."""

import streamlit as st
import pandas as pd
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
        display_items = [
            ("Price", f"${indicators.get('current_price', 'N/A')}"),
            ("RSI (14)", f"{indicators.get('RSI', 'N/A')} ({indicators.get('RSI_signal', '')})"),
            ("MACD", f"{indicators.get('MACD_signal', 'N/A')}"),
            ("52w Range", f"{indicators.get('52w_range_position', 'N/A')}"),
            ("MA20", f"${indicators.get('MA20', 'N/A')}"),
            ("MA50", f"${indicators.get('MA50', 'N/A')}"),
            ("MA200", f"${indicators.get('MA200', 'N/A')}"),
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
        st.success(f"AI API configured ({ai.AI_PROVIDER}). Analysis will run automatically.")
    else:
        st.info("No AI API configured. Using manual prompt mode — copy the prompt to your Claude/ChatGPT session.")

    if st.button(f"Analyze {ticker}", type="primary", key="run_analysis"):
        _run_analysis(ticker, positions, api_configured)


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

        # Previous analyses
        previous = db.get_analyses(
            next((p["id"] for p in positions if p["ticker"] == ticker), None)
        )

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
            _render_manual_prompt(system_prompt, user_prompt, ticker, positions)
        else:
            st.error("Failed to get AI response.")
            _render_manual_prompt(system_prompt, user_prompt, ticker, positions)
    else:
        # Manual prompt mode
        _render_manual_prompt(system_prompt, user_prompt, ticker, positions)


def _render_manual_prompt(system_prompt: str, user_prompt: str, ticker: str, positions: list[dict]):
    """Show copyable prompt and input for pasting AI response."""

    full_prompt = f"SYSTEM:\n{system_prompt}\n\nUSER:\n{user_prompt}"

    st.markdown("### Generated Prompt")
    st.markdown("Copy this prompt to your AI assistant (Claude, ChatGPT, etc.):")

    st.code(full_prompt, language="text")

    if st.button("Copy to Clipboard", key="copy_prompt"):
        st.write(
            f'<script>navigator.clipboard.writeText({json.dumps(full_prompt)})</script>',
            unsafe_allow_html=True,
        )
        st.success("Copied!")

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


def _save_and_display_analysis(ticker: str, positions: list[dict], result: dict):
    """Save analysis to DB and display it."""
    position = next((p for p in positions if p["ticker"] == ticker), None)
    if not position:
        st.error(f"Position {ticker} not found.")
        return

    verdict = result.get("verdict", "HOLD")
    price_target = result.get("price_target")
    summary = result.get("summary", "")
    full_analysis = result.get("full_analysis", "")

    db.add_analysis(
        position_id=position["id"],
        verdict=verdict,
        price_target=float(price_target) if price_target else None,
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

    st.markdown(
        f'<div style="text-align:center; padding:20px; margin:10px 0; '
        f'border:2px solid {color}; border-radius:12px;">'
        f'<h1 style="color:{color} !important; margin:0;">{verdict.upper()}</h1>'
        f'<p style="font-size:1.2em; color:#FAFAFA;">Target: ${price_target:.2f}</p>'
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
        verdict_colors = {"BUY": "#00C853", "SELL": "#FF5252", "HOLD": "#FFA726"}
        color = verdict_colors.get(verdict.upper(), "#FAFAFA") if verdict else "#FAFAFA"

        with st.expander(
            f"**{date_str}** — "
            f":{verdict.upper() if verdict else 'N/A'}: "
            f"(Target: ${analysis.get('price_target', 'N/A')})"
            + (f" — Score: {analysis['accuracy_score']}/10" if analysis.get("accuracy_score") is not None else ""),
        ):
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
                st.rerun()
