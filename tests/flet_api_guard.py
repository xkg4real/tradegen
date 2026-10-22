"""Static guards against Flet API drift.

Three separate crashes reached the running application through this gap:

    ft.Dropdown(on_change=...)   # TypeError: it is `on_select` in Flet 0.85
    page.open(dialog)            # AttributeError: it is `show_dialog`
    page.close(dialog)           # AttributeError: it is `pop_dialog`

Each one is accepted at import time and fails inside an event handler, where
an exception takes down the whole application rather than a single control —
so nothing surfaces until someone clicks the button. These checks read the UI
with `ast` and compare every `page.<method>()` call and every Flet control
keyword against what the installed Flet actually defines.

Kept in its own module because it is a lint pass over the UI, not a statement
about the trading engine's behaviour.
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

import flet as ft

UI = Path(__file__).resolve().parents[1] / "ui"

# Controls whose constructor keywords are worth checking. Anything constructed
# as `ft.Name(...)` in the UI and present here gets its kwargs verified.
_CHECKED_CONTROLS = (
    "Dropdown", "TextField", "Button", "IconButton", "Text", "Container",
    "Row", "Column", "ResponsiveRow", "AlertDialog", "SnackBar", "Icon",
    "Divider", "VerticalDivider", "AnimatedSwitcher", "Image", "Checkbox",
    "ExpansionTile", "ProgressRing", "ProgressBar", "FilePicker", "ListTile",
    "Switch", "Slider", "Card", "Stack", "Tabs", "Tab", "Badge", "Tooltip",
)


def _ui_files() -> list[Path]:
    return sorted(UI.glob("*.py"))


def _params(control_name: str) -> set[str] | None:
    control = getattr(ft, control_name, None)
    if control is None:
        return None
    try:
        return set(inspect.signature(control.__init__).parameters)
    except (TypeError, ValueError):
        return None


def test_page_methods_exist():
    """Every `page.<method>()` the UI calls must exist on `ft.Page`."""
    allowed = {name for name in dir(ft.Page) if not name.startswith("_")}
    offenders: list[str] = []
    for path in _ui_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if (isinstance(func, ast.Attribute)
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "page"
                    and func.attr not in allowed):
                offenders.append(f"{path.name}:{node.lineno} page.{func.attr}()")
    assert not offenders, "page methods that do not exist: " + "; ".join(offenders)


def test_control_keywords_exist():
    """Every keyword passed to a checked `ft.<Control>()` must be real."""
    offenders: list[str] = []
    for path in _ui_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Attribute)
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "ft"
                    and func.attr in _CHECKED_CONTROLS):
                continue
            valid = _params(func.attr)
            if valid is None:
                continue
            for keyword in node.keywords:
                if keyword.arg is None:      # **kwargs splat; cannot check
                    continue
                if keyword.arg not in valid:
                    offenders.append(
                        f"{path.name}:{node.lineno} "
                        f"ft.{func.attr}({keyword.arg}=...)")
    assert not offenders, "invalid control keywords: " + "; ".join(offenders)


def test_control_attribute_assignments_exist():
    """`widget.attr = ...` must name a real field of that control.

    The kwarg check above misses this shape entirely, and it is the shape that
    got through: `field.helper_text = "..."` on a Flet 0.85 `TextField`, whose
    sub-label is actually `helper`. Python accepts the assignment, the control
    ignores it, and the text simply never appears — a silent failure rather
    than a crash, which is worse.

    Only names assigned exactly once from an `ft.<Control>(...)` call are
    checked, so a variable reused for two different control types is skipped
    rather than guessed at.
    """
    offenders: list[str] = []
    for path in _ui_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        origins: dict[str, list[str]] = {}
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)):
                continue
            func = node.value.func
            if not (isinstance(func, ast.Attribute)
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "ft"):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    origins.setdefault(target.id, []).append(func.attr)

        single = {name: kinds[0] for name, kinds in origins.items()
                  if len(set(kinds)) == 1}
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if not (isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Name)):
                    continue
                control_name = single.get(target.value.id)
                if control_name is None:
                    continue
                valid = _params(control_name)
                if valid is None or target.attr in valid:
                    continue
                # Properties defined on the class but not in __init__ are fine.
                if hasattr(getattr(ft, control_name, object), target.attr):
                    continue
                offenders.append(f"{path.name}:{node.lineno} "
                                 f"{target.value.id}.{target.attr} "
                                 f"(ft.{control_name} has no such field)")
    assert not offenders, ("control attributes that do not exist: "
                           + "; ".join(offenders))


def test_theme_tokens_referenced_by_ui_exist():
    """`pal.<token>` must be a real palette field.

    A typo here renders as a crash on first paint of that page, which is the
    same late-failure shape as the Flet mismatches above.
    """
    from core.theme import token_names
    tokens = set(token_names())
    offenders: list[str] = []
    for path in _ui_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Attribute)
                    and isinstance(node.value, ast.Name)
                    and node.value.id == "pal"
                    and node.attr not in tokens):
                offenders.append(f"{path.name}:{node.lineno} pal.{node.attr}")
    assert not offenders, "unknown palette tokens: " + "; ".join(offenders)


def tests():
    return sorted((n, v) for n, v in globals().items()
                  if n.startswith("test_") and callable(v))
