"""Fortuna — AI analysis data gathering service."""

import database as db
import market_data as md
import ai_engine as ai
import charts


def gather_analysis_data(ticker: str, positions: list[dict]) -> tuple[str, str]:
    """
    Gather market data for ticker and build AI analysis prompts.

    Returns: (system_prompt, user_prompt) ready to pass to ai.call_ai_api()
    """
    portfolio = db.get_portfolio_summary()
    prices = md.get_batch_prices(tuple(p["ticker"] for p in portfolio))  # tuple required for Streamlit cache hashability
    total_value = sum(
        (prices.get(p["ticker"], 0) or 0) * p["qty"]
        for p in portfolio
    )
    for p in portfolio:
        price = prices.get(p["ticker"])
        value = (price * p["qty"]) if price and p["qty"] > 0 else 0
        p["current_weight"] = round(value / total_value * 100, 2) if total_value > 0 else 0
        p["current_price"] = price

    stock_info = md.get_stock_info(ticker)

    price_data = md.get_price_history(ticker, period="1y")
    df = charts.compute_indicators(price_data)
    price_summary = charts.get_price_summary(df)
    technical_indicators = charts.get_indicator_summary(df)

    news = None
    try:
        stock = md.get_stock(ticker)
        news = stock.news
    except Exception:
        pass

    recommendations = None
    try:
        stock = md.get_stock(ticker)
        recs = stock.recommendations
        if recs is not None and not recs.empty:
            recommendations = recs.tail(5).to_dict("records")
    except Exception:
        pass

    pos_id = next((p["id"] for p in positions if p["ticker"] == ticker), None)
    previous = db.get_analyses(pos_id) if pos_id is not None else []

    return ai.build_analysis_prompt(
        ticker=ticker,
        portfolio_summary=portfolio,
        stock_info=stock_info,
        price_history_summary=price_summary,
        technical_indicators=technical_indicators,
        news=news,
        recommendations=recommendations,
        previous_analyses=previous[:3] if previous else None,
    )
