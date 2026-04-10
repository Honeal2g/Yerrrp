"""Yerrrp — visual design tokens."""

# --- Backgrounds ---
BG_ROOT        = "#0d0d1a"
BG_CARD        = "#1a1a2e"
BG_SURFACE     = "#16213e"
BG_INPUT       = "#0f1627"

# --- Accents ---
ACCENT_1       = "#6e40c9"   # purple deep
ACCENT_2       = "#bf5af2"   # purple bright
ACCENT_BORDER  = "#3a2060"   # subtle border

# --- Semantic ---
DANGER         = "#ff3b30"
SUCCESS        = "#28c840"
WARNING        = "#febc2e"

# --- Text ---
TEXT_PRIMARY   = "#ffffff"
TEXT_SECONDARY = "#9999bb"
TEXT_MUTED     = "#44445a"

# --- Pill ---
TRANSPARENT_KEY = "#010203"  # used for Windows transparentcolor trick
PILL_HEIGHT     = 46

# --- Fonts ---
FONT_FAMILY  = "Segoe UI"
FONT_SMALL   = (FONT_FAMILY, 9)
FONT_NORMAL  = (FONT_FAMILY, 10)
FONT_BOLD    = (FONT_FAMILY, 10, "bold")
FONT_TITLE   = (FONT_FAMILY, 13, "bold")
FONT_LABEL   = (FONT_FAMILY, 8)
FONT_MONO    = ("Consolas", 10)


def round_rect(canvas, x1, y1, x2, y2, radius, **kwargs):
    """Draw a rounded rectangle on a tkinter Canvas using smooth polygon."""
    r = radius
    points = [
        x1 + r, y1,
        x2 - r, y1,
        x2,     y1,
        x2,     y1 + r,
        x2,     y2 - r,
        x2,     y2,
        x2 - r, y2,
        x1 + r, y2,
        x1,     y2,
        x1,     y2 - r,
        x1,     y1 + r,
        x1,     y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)
