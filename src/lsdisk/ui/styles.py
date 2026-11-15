"""Application-defined Rich styles shared by every terminal view."""

PALETTE = {
    "heading": "bold bright_cyan",
    "device": "bold bright_cyan",
    "filesystem": "bright_white",
    "category": "bright_blue",
    "warning": "bright_yellow",
    "error": "bright_red",
    "unknown": "grey70",
    "usage_low": "green",
    "usage_medium": "yellow",
    "usage_high": "red",
    "muted": "grey58",
}


def usage_style(percentage: float) -> str:
    """Return the semantic utilization style for a percentage."""
    if percentage >= 90:
        return PALETTE["usage_high"]
    if percentage >= 70:
        return PALETTE["usage_medium"]
    return PALETTE["usage_low"]
