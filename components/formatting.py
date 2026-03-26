"""Fortuna — shared color constants, formatters, and verdict mappings."""

# --- Color Constants ---

GOLD = "#D4AF37"
GREEN = "#00C853"
RED = "#FF5252"
AMBER = "#FFA726"
WHITE = "#FAFAFA"
DARK_CARD = "#1A1D24"
BORDER = "#2A2D34"

# --- Verdict Mapping ---

VERDICT_COLORS: dict[str, str] = {
    "BUY": GREEN,
    "SELL": RED,
    "HOLD": AMBER,
}


# --- Color Helpers ---

def pnl_color(val: float) -> str:
    """Return GREEN or RED hex based on whether val is positive or negative."""
    return GREEN if val > 0 else (RED if val < 0 else "")


def pnl_bg(val: float) -> str:
    """Return a semi-transparent green or red background for P&L badges."""
    return "rgba(0,200,83,0.15)" if val >= 0 else "rgba(255,82,82,0.15)"


# --- Formatters ---

def format_currency(val: float | None) -> str:
    """Format a dollar value as $1,234.56 or N/A if None."""
    return f"${val:,.2f}" if val is not None else "N/A"


def format_pct(val: float | None) -> str:
    """Format a percentage as 1.23% or N/A if None."""
    return f"{val:.2f}%" if val is not None else "N/A"


def format_au_date(iso_date: str) -> str:
    """Convert ISO date (2026-03-19) to Australian format (19/03/2026)."""
    try:
        parts = iso_date[:10].split("-")
        return f"{parts[2]}/{parts[1]}/{parts[0]}"
    except (IndexError, ValueError):
        return iso_date[:10]
