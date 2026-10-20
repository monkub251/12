"""Design tokens + global stylesheet. Monochrome, instrument-panel register."""

# ---- surfaces -------------------------------------------------------------
BG = "#08090A"
PANEL = "#0C0D0F"
PANEL_HI = "#111216"
RAIL = "#0A0B0D"

# ---- strokes --------------------------------------------------------------
LINE = "#1B1C20"
LINE_HI = "#2C2E35"

# ---- ink ------------------------------------------------------------------
TEXT = "#F2F2F3"
DIM = "#8C8E95"
FAINT = "#4A4C53"
GHOST = "#2E3036"

# ---- signal ---------------------------------------------------------------
ACCENT = "#FFFFFF"
OK = "#79D18D"
WARN = "#D9B65C"
BAD = "#E06A6A"

# ---- type -----------------------------------------------------------------
FONT_UI = "Rajdhani, Bahnschrift, Segoe UI Variable, Segoe UI, Arial"
FONT_TH = "Noto Sans Thai, Leelawadee UI, Segoe UI, Tahoma"
FONT_MONO = "JetBrains Mono, Cascadia Mono, Consolas, monospace"

QSS = f"""
* {{
    font-family: "{FONT_UI}";
    color: {TEXT};
}}

QWidget#root {{ background: {BG}; }}
QWidget#rail {{ background: {RAIL}; border-right: 1px solid {LINE}; }}

/* ---- rail nav ---- */
QPushButton[role="rail"] {{
    background: transparent;
    border: none;
    border-left: 2px solid transparent;
    color: {FAINT};
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 2px;
    padding: 14px 0;
}}
QPushButton[role="rail"]:hover {{ color: {DIM}; background: rgba(255,255,255,0.03); }}
QPushButton[role="rail"][active="true"] {{
    color: {TEXT};
    border-left: 2px solid {ACCENT};
    background: rgba(255,255,255,0.05);
}}

/* ---- window buttons ---- */
QPushButton[role="win"], QPushButton[role="close"] {{
    background: transparent; border: none; outline: none;
    color: {FAINT}; font-size: 14px; padding: 0;
}}
QPushButton[role="win"]:hover {{ background: rgba(255,255,255,0.07); color: {TEXT}; }}
QPushButton[role="close"]:hover {{ background: rgba(224,106,106,0.18); color: {BAD}; }}

/* ---- type roles ---- */
QLabel[role="wordmark"] {{
    font-size: 19px; font-weight: 700; letter-spacing: 6px; color: {TEXT};
}}
QLabel[role="tagline"] {{
    font-size: 8px; letter-spacing: 3px; color: {FAINT};
}}
QLabel[role="eyebrow"] {{
    font-size: 9px; letter-spacing: 3px; color: {FAINT};
}}
QLabel[role="pagetitle"] {{
    font-size: 24px; font-weight: 700; letter-spacing: 5px; color: {TEXT};
}}
QLabel[role="body"] {{
    font-family: "{FONT_TH}"; font-size: 13px; color: {DIM};
}}
QLabel[role="note"] {{
    font-family: "{FONT_TH}"; font-size: 11px; color: {FAINT};
}}
QLabel[role="mono"] {{
    font-family: "{FONT_MONO}"; font-size: 10px; color: {FAINT};
}}

/* ---- console ---- */
QPlainTextEdit {{
    background: {PANEL};
    border: 1px solid {LINE};
    font-family: "{FONT_MONO}";
    font-size: 11px;
    color: {DIM};
    padding: 10px 12px;
    selection-background-color: #2B2D34;
}}

QScrollBar:vertical {{ background: transparent; width: 7px; margin: 0; }}
QScrollBar::handle:vertical {{
    background: {LINE_HI}; border-radius: 3px; min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{ background: {FAINT}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QDialog {{ background: {PANEL}; }}
"""
