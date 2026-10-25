"""CJK display-width calculation."""
import unicodedata


def display_width(text):
    """Calculate display width: fullwidth=1, halfwidth=0.5, spaces ignored."""
    return sum(
        1.0 if unicodedata.east_asian_width(c) in ("W", "F") else 0.5
        for c in text.replace(" ", "")
    )
