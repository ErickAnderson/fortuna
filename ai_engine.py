"""Fortuna — AI Analysis Engine (provider-agnostic + manual prompt mode)."""

import os
import re
import json
from dotenv import load_dotenv


def _get_config() -> tuple[str, str, str]:
    """Read AI config from env each time (supports hot-reload of .env)."""
    load_dotenv(override=True)
    provider = os.getenv("AI_PROVIDER", "").strip().lower()
    api_key = os.getenv("AI_API_KEY", "").strip()
    model = os.getenv("AI_MODEL", "").strip()
    return provider, api_key, model


def is_api_configured() -> bool:
    provider, api_key, _ = _get_config()
    return bool(provider and api_key)


def build_analysis_prompt(
    ticker: str,
    portfolio_summary: list[dict],
    stock_info: dict,
    price_history_summary: dict,
    technical_indicators: dict,
    news: list[dict] | None = None,
    recommendations: list[dict] | None = None,
    previous_analyses: list[dict] | None = None,
) -> tuple[str, str]:
    """Build the analysis prompt with all available data."""

    # Portfolio context
    portfolio_text = "Current Portfolio:\n"
    for pos in portfolio_summary:
        portfolio_text += (
            f"  {pos['ticker']}: {pos['qty']} shares @ ${pos['avg_price']:.4f} avg, "
            f"target weight {pos['target_weight']}%, current weight {pos.get('current_weight', 'N/A')}%\n"
        )

    # Stock fundamentals
    fundamentals_text = f"\nFundamentals for {ticker}:\n"
    for key, val in stock_info.items():
        if val is not None and val != "N/A":
            fundamentals_text += f"  {key}: {val}\n"

    # Price summary
    price_text = f"\nPrice History Summary ({ticker}):\n"
    for key, val in price_history_summary.items():
        price_text += f"  {key}: {val}\n"

    # Technical indicators
    tech_text = f"\nTechnical Indicators ({ticker}):\n"
    for key, val in technical_indicators.items():
        if val is not None:
            tech_text += f"  {key}: {val}\n"

    # News
    news_text = ""
    if news:
        news_text = f"\nRecent News ({ticker}):\n"
        for item in news[:10]:
            news_text += f"  - {item.get('title', 'N/A')} ({item.get('publisher', 'N/A')})\n"

    # Analyst recommendations
    rec_text = ""
    if recommendations:
        rec_text = f"\nAnalyst Recommendations ({ticker}):\n"
        for rec in recommendations[:5]:
            rec_text += f"  - {rec}\n"

    # Previous analysis context
    prev_text = ""
    if previous_analyses:
        prev_text = f"\nPrevious Analyses ({ticker}):\n"
        for analysis in previous_analyses[:3]:
            prev_text += (
                f"  [{analysis['date']}] Verdict: {analysis['verdict']}, "
                f"Target: ${analysis.get('price_target', 'N/A')}\n"
                f"  Summary: {analysis['summary']}\n"
            )
            if analysis.get('accuracy_score') is not None:
                prev_text += f"  Accuracy Score: {analysis['accuracy_score']}/10 — {analysis.get('accuracy_notes', '')}\n"

    system_prompt = """You are Fortuna, an expert ASX (Australian Securities Exchange) portfolio analyst.
You provide detailed, actionable investment analysis using technical and fundamental analysis.
Use proper financial terminology — the user is familiar with trading concepts.

Your analysis MUST include:
1. **VERDICT**: Exactly one of: BUY, SELL, or HOLD
2. **PRICE TARGET**: A specific price to buy at, sell at, or hold until
3. **SUMMARY**: 2-3 sentence executive summary
4. **DETAILED ANALYSIS** covering:
   - Fundamental Analysis: P/E, P/B, dividend yield, earnings, debt, ROE, sector outlook
   - Technical Analysis: Support/resistance levels, RSI interpretation, MACD signal, moving average crossovers, volume trends, candlestick patterns
   - Portfolio Context: How this position fits the overall portfolio, correlation with other holdings, weight vs target
   - Risk Assessment: Key risks, volatility, downside scenarios
   - Catalyst Watch: Upcoming events (earnings, ex-dividend dates, macro events) that could move the price
5. **ACTION PLAN**: Specific steps — e.g. "Buy at $X if RSI drops below 30" or "Wait for price to test $X support before adding"

Consider the FULL portfolio context including potential overlaps between ETFs/stocks.
If previous analyses exist, reference them and note if conditions have changed.

Format your response as JSON:
{
    "verdict": "BUY|SELL|HOLD",
    "price_target": 0.00,
    "summary": "...",
    "full_analysis": "... (use markdown formatting for readability)"
}"""

    user_prompt = f"""Analyze {ticker} for a buy/sell/hold decision today.

{portfolio_text}
{fundamentals_text}
{price_text}
{tech_text}
{news_text}
{rec_text}
{prev_text}

Provide your complete analysis as JSON."""

    return system_prompt, user_prompt


def call_ai_api(system_prompt: str, user_prompt: str) -> dict | None:
    """Call the configured AI API. Returns parsed JSON or None on failure."""
    provider, api_key, _ = _get_config()
    if not (provider and api_key):
        return None

    try:
        if provider == "claude":
            return _call_claude(system_prompt, user_prompt)
        elif provider == "openai":
            return _call_openai(system_prompt, user_prompt)
        else:
            return {"error": f"Unknown AI provider: {provider}"}
    except Exception as e:
        return {"error": str(e)}


def _call_claude(system_prompt: str, user_prompt: str) -> dict:
    from anthropic import Anthropic

    _, api_key, model = _get_config()
    client = Anthropic(api_key=api_key)
    model = model or "claude-sonnet-4-6"

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    if not response.content:
        return {"error": "Empty response from Claude API"}

    text = response.content[0].text
    return _parse_json_response(text)


def _call_openai(system_prompt: str, user_prompt: str) -> dict:
    from openai import OpenAI

    _, api_key, model = _get_config()
    client = OpenAI(api_key=api_key)
    model = model or "gpt-4o"

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=4096,
    )

    text = response.choices[0].message.content
    if not text:
        return {"error": "Empty response from OpenAI API"}

    return _parse_json_response(text)


def _parse_json_response(text: str) -> dict:
    """Extract JSON from AI response, handling markdown code blocks."""
    text = text.strip()

    # Try to extract JSON from code blocks anywhere in the text
    match = re.search(r'```(?:json)?\s*\n(.*?)\n```', text, re.DOTALL)
    if match:
        text = match.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"error": f"Failed to parse AI response as JSON. Raw response: {text[:500]}"}
