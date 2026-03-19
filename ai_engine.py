"""Fortuna — AI Analysis Engine (provider-agnostic + manual prompt mode)."""

import os
import re
import json
import traceback
from datetime import date
from dotenv import load_dotenv
import database as db


def _friendly_error(error: Exception, provider: str) -> str:
    """Convert raw API exceptions into short user-friendly messages.
    Logs the full traceback to the DB for the Logs page."""
    raw = str(error)
    detail = traceback.format_exc()

    # Detect common patterns
    msg = raw.lower()
    if "401" in msg or ("invalid" in msg and "key" in msg) or "authentication" in msg:
        friendly = f"{provider.title()}: Invalid API key. Check your key in Settings."
    elif "403" in msg or "permission" in msg:
        friendly = f"{provider.title()}: Access denied. Your API key may lack permissions."
    elif "429" in msg or "rate" in msg or "quota" in msg or "resource_exhausted" in msg:
        friendly = f"{provider.title()}: Rate limit or quota exceeded. Wait a moment and try again, or check your plan."
    elif "404" in msg or ("not found" in msg and "model" in msg):
        friendly = f"{provider.title()}: Model not found. Try fetching models again."
    elif "timeout" in msg or "timed out" in msg:
        friendly = f"{provider.title()}: Request timed out. Try again."
    elif "connection" in msg or "network" in msg or "unreachable" in msg:
        friendly = f"{provider.title()}: Connection failed. Check your internet."
    else:
        # Truncate to first sentence or 120 chars
        short = raw.split("\n")[0][:120]
        friendly = f"{provider.title()}: {short}"

    db.add_log("error", f"ai_engine/{provider}", friendly, detail)
    return friendly


def _get_config(provider_name: str | None = None, model_override: str | None = None) -> tuple[str, str, str]:
    """Get AI config. Priority: DB provider → first enabled DB provider → .env fallback.
    model_override takes precedence over the stored model."""
    if provider_name:
        row = db.get_ai_provider(provider_name)
        if row and row["is_enabled"]:
            model = model_override or row["model"]
            return row["provider"], row["api_key"], model

    # First enabled provider from DB
    enabled = db.get_enabled_ai_providers()
    if enabled:
        row = enabled[0]
        model = model_override or row["model"]
        return row["provider"], row["api_key"], model

    # Fallback to .env
    load_dotenv(override=True)
    provider = os.getenv("AI_PROVIDER", "").strip().lower()
    api_key = os.getenv("AI_API_KEY", "").strip()
    model = model_override or os.getenv("AI_MODEL", "").strip()
    return provider, api_key, model


def is_api_configured() -> bool:
    provider, api_key, _ = _get_config()
    return bool(provider and api_key)


def _get_ordered_models(row: dict) -> list[str]:
    """Get ordered model list for a provider row (saved model first, then cached)."""
    cached = []
    if row.get("models_cache"):
        try:
            cached = json.loads(row["models_cache"])
        except (json.JSONDecodeError, TypeError):
            pass

    if not cached:
        return [row["model"] or "default"]

    saved_model = row["model"]
    ordered = []
    if saved_model in cached:
        ordered.append(saved_model)
    for m in cached:
        if m != saved_model:
            ordered.append(m)
    return ordered


def get_configured_providers() -> list[dict]:
    """Return list of provider+model options for UI dropdowns."""
    providers = []
    for row in db.get_enabled_ai_providers():
        for m in _get_ordered_models(row):
            label = f"{row['provider'].title()} — {m}"
            providers.append({"provider": row["provider"], "label": label, "model": m})

    if not providers:
        load_dotenv(override=True)
        env_provider = os.getenv("AI_PROVIDER", "").strip().lower()
        env_key = os.getenv("AI_API_KEY", "").strip()
        env_model = os.getenv("AI_MODEL", "").strip()
        if env_provider and env_key:
            label = f"{env_provider.title()} — {env_model or 'default'} (env)"
            providers.append({"provider": env_provider, "label": label, "model": env_model})

    return providers


def get_provider_model_options() -> dict[str, list[str]]:
    """Return {provider_label: [models]} for enabled providers. Used for two-dropdown UI."""
    result = {}
    for row in db.get_enabled_ai_providers():
        result[row["provider"].title()] = _get_ordered_models(row)

    if not result:
        load_dotenv(override=True)
        env_provider = os.getenv("AI_PROVIDER", "").strip().lower()
        env_key = os.getenv("AI_API_KEY", "").strip()
        env_model = os.getenv("AI_MODEL", "").strip()
        if env_provider and env_key:
            result[f"{env_provider.title()} (env)"] = [env_model or "default"]

    return result


def list_models(provider: str, api_key: str) -> list[str]:
    """List available models for a provider."""
    try:
        if provider == "claude":
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key)
            models = client.models.list()
            return sorted([m.id for m in models.data if "claude" in m.id.lower()])
        elif provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            models = client.models.list()
            return sorted([m.id for m in models.data if any(p in m.id for p in ("gpt", "o1", "o3", "o4"))])
        elif provider == "gemini":
            from google import genai
            client = genai.Client(api_key=api_key)
            # The list endpoint returns all models, not just ones the key
            # can use. Filter to main gemini text models only.
            skip = ("tts", "image", "robotics", "computer-use", "customtools", "banana")
            return sorted([
                m.name.replace("models/", "")
                for m in client.models.list()
                if "generateContent" in (m.supported_actions or [])
                and m.name.startswith("models/gemini")
                and not any(s in m.name for s in skip)
            ])
    except Exception as e:
        return [f"Error: {_friendly_error(e, provider)}"]
    return []


def test_connection(provider: str, api_key: str, model: str) -> tuple[bool, str]:
    """Test API connection with a minimal request."""
    try:
        if provider == "claude":
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key)
            resp = client.messages.create(
                model=model or "claude-sonnet-4-6",
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return True, f"Connected — {resp.model}"
        elif provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model=model or "gpt-4o",
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return True, f"Connected — {resp.model}"
        elif provider == "gemini":
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=api_key)
            resp = client.models.generate_content(
                model=model or "gemini-2.0-flash",
                contents="Hi",
                config=types.GenerateContentConfig(max_output_tokens=10),
            )
            return True, f"Connected — {model or 'gemini-2.0-flash'}"
        else:
            return False, f"Unknown provider: {provider}"
    except Exception as e:
        return False, _friendly_error(e, provider)


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

    today = date.today().strftime("%Y-%m-%d")

    system_prompt = f"""You are an expert ASX (Australian Securities Exchange) portfolio analyst.
Today's date is {today}.
You provide detailed, actionable investment analysis using technical and fundamental analysis.
Use proper financial terminology — the user is familiar with trading concepts.

IMPORTANT — REAL-TIME RESEARCH:
The market data below is a starting point, NOT the full picture. You MUST supplement it with current information:
- **Search the web** for the latest news, analyst reports, and sector developments for this ticker.
- For ASX-listed ETFs/stocks, check sources like: ASX.com.au, MarketIndex.com.au, Simply Wall St, TradingView.
- For commodities (uranium, gold, etc.), look up the CURRENT spot price (e.g. uranium U3O8 $/lb on TradingEconomics, Kitco, UxC, or CarbonCredits). Always state the current commodity spot price and its recent trend — this is essential context.
- For macro context: check the MOST RECENT RBA decision (not the next one — confirm what actually happened), current oil prices, and any major geopolitical events affecting markets RIGHT NOW.
- For ETFs, identify the top holdings and check for recent production guidance changes, earnings reports, or material news from those companies.
- Cite specific sources or data points when making claims about sector trends or catalysts.

ACCURACY REQUIREMENTS:
- Do NOT guess dates for events — verify them. If you cannot verify a date, say "date TBC" rather than fabricating one.
- Do NOT present past events as upcoming. Verify whether an event has already occurred before listing it as a catalyst.
- Do NOT include internal citation markers, reference tags, or any non-readable artifacts in your output. Your response must be clean, human-readable markdown.
- If you do NOT have web access, clearly state this limitation upfront and note which claims are based on general knowledge vs the provided data.

Your analysis MUST include:
1. **VERDICT**: Exactly one of: BUY, SELL, or HOLD
2. **PRICE TARGET**: A specific price to buy at, sell at, or hold until
3. **SUMMARY**: 2-3 sentence executive summary
4. **DETAILED ANALYSIS** covering:
   - Macro & Geopolitical Context: Current major events affecting this asset class (wars, trade policy, energy crises, central bank decisions). This section should demonstrate awareness of what is happening in the world TODAY, not generic sector commentary.
   - Fundamental Analysis: P/E, P/B, dividend yield, earnings, debt, ROE, sector outlook. For commodity ETFs, include the current commodity spot price, recent price action, and analyst forecasts.
   - Technical Analysis: Support/resistance levels, RSI interpretation, MACD signal, moving average crossovers, volume trends, candlestick patterns
   - Portfolio Context: How this position fits the overall portfolio, correlation with other holdings, weight vs target
   - Risk Assessment: Key risks, volatility, downside scenarios
   - Catalyst Watch: **Specific, dated** upcoming events ONLY — e.g. "Cameco Q1 earnings ~April 30" or "RBA next meeting May 2026". Do NOT list generic categories like "earnings" or "policy changes" without specific dates. Do NOT list events that have already passed.
   - Sources & Recent Events: List 3-5 specific recent news items, reports, or data points you found during research, with approximate dates. This proves your analysis is grounded in current information, not generic knowledge.
5. **ACTION PLAN**: Specific steps — e.g. "Buy at $X if RSI drops below 30" or "Wait for price to test $X support before adding"

Consider the FULL portfolio context including potential overlaps between ETFs/stocks.
If previous analyses exist, reference them and note if conditions have changed.

Format your response as JSON:
{{
    "verdict": "BUY|SELL|HOLD",
    "price_target": 0.00,
    "summary": "...",
    "full_analysis": "... (use markdown formatting for readability)",
    "action_plan": "... (numbered steps with specific price levels and conditions)"
}}"""

    user_prompt = f"""Analyze {ticker} for a buy/sell/hold decision today ({today}).

{portfolio_text}
{fundamentals_text}
{price_text}
{tech_text}
{news_text}
{rec_text}
{prev_text}

Before writing your analysis, research the following:
1. Current spot/commodity price relevant to {ticker} and its recent trajectory
2. The MOST RECENT RBA rate decision and what was decided (do not guess the next one)
3. Any major geopolitical events currently affecting markets (conflicts, trade wars, energy crises)
4. Recent news about {ticker}'s top holdings or underlying companies (production guidance, earnings, contracts)
5. Upcoming dated catalysts (earnings dates, central bank meetings, policy announcements)

Include what you find in your analysis. If you cannot access live data, state this clearly.
Provide your complete analysis as JSON."""

    return system_prompt, user_prompt


def call_ai_api(system_prompt: str, user_prompt: str, provider_name: str | None = None, model_override: str | None = None) -> dict | None:
    """Call the configured AI API. Returns parsed JSON or None on failure."""
    provider, api_key, model = _get_config(provider_name, model_override)
    if not (provider and api_key):
        return None

    try:
        if provider == "claude":
            return _call_claude(system_prompt, user_prompt, api_key, model)
        elif provider == "openai":
            return _call_openai(system_prompt, user_prompt, api_key, model)
        elif provider == "gemini":
            return _call_gemini(system_prompt, user_prompt, api_key, model)
        else:
            return {"error": f"Unknown AI provider: {provider}"}
    except Exception as e:
        return {"error": _friendly_error(e, provider)}


def _call_claude(system_prompt: str, user_prompt: str, api_key: str, model: str) -> dict:
    from anthropic import Anthropic

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


def _call_openai(system_prompt: str, user_prompt: str, api_key: str, model: str) -> dict:
    from openai import OpenAI

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


def _call_gemini(system_prompt: str, user_prompt: str, api_key: str, model: str) -> dict:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    model_name = model or "gemini-2.0-flash"

    response = client.models.generate_content(
        model=model_name,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=4096,
        ),
    )

    text = response.text
    if not text:
        return {"error": "Empty response from Gemini API"}

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
