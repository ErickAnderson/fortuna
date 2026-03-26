"""Fortuna — cash deployment planner business logic service."""

import database as db
import market_data as md


def calculate_deployment_plan(
    portfolio: list[dict],
    lump_sum: float,
) -> tuple[list[dict], float]:
    """
    Calculate suggested share allocation to deploy lump_sum into existing positions.

    portfolio: list of position dicts from db.get_portfolio_summary(), each augmented with
               current_price (float | None) and value (float) before calling this function.
    lump_sum: dollar amount to deploy.

    Returns: (suggestions, total_value)
    suggestions: list of dicts with keys:
        ticker, target_weight, current_value, target_value,
        suggested_amount, suggested_shares, actual_cost, price
    total_value: total current portfolio value before deployment
    """
    for pos in portfolio:
        pos["current_price"] = pos.get("current_price")
        pos["value"] = pos.get("value", 0.0)

    total_value = sum(p["value"] for p in portfolio)
    new_total = total_value + lump_sum

    suggestions = []
    for pos in portfolio:
        target_value = new_total * (pos["target_weight"] / 100)
        current_value = pos["value"]
        needed = max(target_value - current_value, 0)

        price = pos["current_price"]
        shares = int(needed / price) if price and price > 0 else 0
        actual_cost = shares * price if price else 0

        suggestions.append({
            "ticker": pos["ticker"],
            "target_weight": pos["target_weight"],
            "current_value": current_value,
            "target_value": target_value,
            "suggested_amount": round(needed, 2),
            "suggested_shares": shares,
            "actual_cost": round(actual_cost, 2),
            "price": price,
        })

    total_suggested = sum(s["suggested_amount"] for s in suggestions)
    if total_suggested > 0:
        scale = min(lump_sum / total_suggested, 1.0)
        for s in suggestions:
            s["suggested_amount"] = round(s["suggested_amount"] * scale, 2)
            s["suggested_shares"] = int(s["suggested_amount"] / s["price"]) if s["price"] and s["price"] > 0 else 0
            s["actual_cost"] = round(s["suggested_shares"] * s["price"], 2) if s["price"] else 0

    return suggestions, total_value
