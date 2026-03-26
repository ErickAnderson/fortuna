"""Fortuna — shared pandas dataframe style functions for .style.map() calls."""

from components.formatting import GREEN, RED, AMBER


def style_pnl(val) -> str:
    """Color a P&L cell green (positive) or red (negative)."""
    if isinstance(val, (int, float)):
        if val > 0:
            return f"color: {GREEN}"
        elif val < 0:
            return f"color: {RED}"
    return ""


def style_weight_diff(val) -> str:
    """Color a weight diff cell: red if overweight (>2%), amber if underweight (<-2%)."""
    if isinstance(val, (int, float)):
        if val > 2:
            return f"color: {RED}"
        elif val < -2:
            return f"color: {AMBER}"
    return ""


def style_txn_type(val) -> str:
    """Color transaction type: green for buy, red for sell."""
    if val == "buy":
        return f"color: {GREEN}"
    elif val == "sell":
        return f"color: {RED}"
    return ""
