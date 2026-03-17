"""Fortuna — AI Analysis Engine (provider-agnostic + manual prompt mode)."""

import os
import json
from dotenv import load_dotenv

load_dotenv()

AI_PROVIDER = os.getenv("AI_PROVIDER", "").strip().lower()
AI_API_KEY = os.getenv("AI_API_KEY", "").strip()
AI_MODEL = os.getenv("AI_MODEL", "").strip()


def is_api_configured() -> bool:
    return bool(AI_PROVIDER and AI_API_KEY)


def build_analysis_prompt(
    ticker: str,
    portfolio_summary: list[dict],
    stock_info: dict,
    price_history_summary: dict,
    technical_indicators: dict,
    news: list[dict] | None = None,
    recommendations: list[dict] | None = None,
    previous_analyses: list[dict] | None = None,
) -> str:
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
    if not is_api_configured():
        return None

    try:
        if AI_PROVIDER == "claude":
            return _call_claude(system_prompt, user_prompt)
        elif AI_PROVIDER == "openai":
            return _call_openai(system_prompt, user_prompt)
        else:
            return None
    except Exception as e:
        return {"error": str(e)}


def _call_claude(system_prompt: str, user_prompt: str) -> dict:
    from anthropic import Anthropic

    client = Anthropic(api_key=AI_API_KEY)
    model = AI_MODEL or "claude-sonnet-4-6"

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text = response.content[0].text
    return _parse_json_response(text)


def _call_openai(system_prompt: str, user_prompt: str) -> dict:
    from openai import OpenAI

    client = OpenAI(api_key=AI_API_KEY)
    model = AI_MODEL or "gpt-4o"

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=4096,
    )

    text = response.choices[0].message.content
    return _parse_json_response(text)


def _parse_json_response(text: str) -> dict:
    """Extract JSON from AI response, handling markdown code blocks."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines (```json and ```)
        json_lines = []
        in_block = False
        for line in lines:
            if line.strip().startswith("```") and not in_block:
                in_block = True
                continue
            elif line.strip() == "```" and in_block:
                break
            elif in_block:
                json_lines.append(line)
        text = "\n".join(json_lines)

    return json.loads(text)
