"""Central visual tokens for the NEXTGEN desktop interface."""
from __future__ import annotations
from dataclasses import dataclass

RADII = {"sm": 8, "md": 12, "lg": 16, "pill": 999}
BREAKPOINTS = {"compact": 700, "medium": 1200}
TRANSITION_MS = 180
MODES = ("dark", "light", "system")
DEFAULT_MODE = "system"

@dataclass(frozen=True)
class Palette:
    bg: str
    surface: str
    surface_2: str
    border: str
    text: str
    muted: str
    accent: str
    accent_soft: str
    success: str
    error: str
    on_accent: str
    warning: str = "#d9a441"      # last, with a default: positional constructors keep working (02_ui_design 3)

DARK = Palette("#101417", "#171d21", "#1d252a", "#324047", "#e7ecef", "#9eabb2", "#4f98a3", "#233b40", "#6daa45", "#d1637f", "#071012", "#d9a441")
LIGHT = Palette("#f5f7f6", "#ffffff", "#edf2f0", "#d2dcda", "#192326", "#647277", "#01696f", "#d8e8e5", "#437a22", "#a12c53", "#ffffff", "#8a5a00")
_state = {"mode": DEFAULT_MODE, "palette": DARK}

def palette_for(mode: str, *, system_is_dark: bool = True) -> Palette:
    mode = (mode or DEFAULT_MODE).lower()
    if mode == "light": return LIGHT
    if mode == "dark": return DARK
    return DARK if system_is_dark else LIGHT

def set_mode(mode: str, *, system_is_dark: bool = True) -> Palette:
    p = palette_for(mode, system_is_dark=system_is_dark)
    _state.update(mode=mode if mode in MODES else DEFAULT_MODE, palette=p)
    return p

def active() -> Palette: return _state["palette"]
def active_mode() -> str: return _state["mode"]
def token_names() -> tuple[str, ...]: return tuple(Palette.__dataclass_fields__)
