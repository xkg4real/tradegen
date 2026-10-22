"""Macro -> Research register view (02_ui_design section 1; code_ui D.1-D.2; council_pages C).

The tech-fund weight table (market filter; the R3:703 caption verbatim; w/3 only as a display column), the go/no-go
register (group filter, table, detail pane), the DO-NOT-BUILD list (macro items 1-37 and DNB-TF-01..17 with their
labels), the backlog status board and council queue, the twelve council resolutions and the module-status table, the
proposals pending owner confirmation (XS with status, OQ), and two buttons that open the offline council pages.

A research record, display only: nothing here is an input to exposure, a rule or a book. `research_blocks` is a
pure dict -> controls renderer; `load_inputs` reads the shipped files (manifest-checked by `core.techfund`; a mismatch
raises and the view fails closed).
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import flet as ft

from core.theme import active
from ui.components import chip, data_table, notice, open_path
from ui.macro_cards_view import view_shell

ROOT = Path(__file__).resolve().parents[1]
COUNCIL = ROOT / "docs" / "council"
PAGES = {"Open Quant Council page": COUNCIL / "QUANTGEN_Quant_Council.html",
         "Open Macro Neural Link page": COUNCIL / "QUANTGEN_Macro_Neural_Link.html"}
SPEC = ROOT / "QUANTGEN_Quant_Council_2026-10-03" / "claude_code" / "QUANTGEN_MACRO_INTEGRATION.md"

DISCLAIMERS = (   # docs/council/README.md lines 3-4 and the tech-fund bundle README, verbatim
    "All panel members in these documents are simulated, fictional composites; nothing speaks for any real firm or person.",
    "Not investment advice: QUANTGEN is a read-only research desk with no order path.",
    "All lab numbers are in-sample computations on price returns without dividends, not runs of QUANTGEN's gate.",
)
WEIGHT_CAPTION = ("Weights are 0-3 design priors, not gate results; any weight of 2 or more still needs a PASS card "
                  "before it can feed the displayed book. Proposed normalisation base_weight = w / 3 (never above "
                  "1.0x). Rules W1-W5 in section 3; * = one panel only; n.r. = no panel reviewed.")   # R3:703
W3_HEADER = "w/3 (display; XS-21 proposal, not sizing)"
MARKETS = ("All markets", "Korea", "US", "Crypto", "Futures/FX", "Other markets")
REGISTER_GROUPS = ("All groups", "BUILD", "INVARIANT", "GOVERNANCE", "FORWARD-SIM", "BACKLOG", "OWNER DECISION",
                   "CONTEXT", "DROP")
# a 3 is not a PASS: success is reserved for a QUANTGEN gate PASS
GROUP_TOKEN = {"BUILD": "accent", "INVARIANT": "accent", "GOVERNANCE": "accent", "DROP": "error"}
STATUS_TOKEN = {"OPEN": "accent", "OWNER-DECISION": "warning", "CONFLICT": "warning", "RETIRED": "error",
                "DEMOTED": "error", "NEW": "accent"}


def _repaint(control: ft.Control) -> None:
    try:
        control.update()
    except RuntimeError:                     # not on a page yet (headless render)
        pass


def _h(text: str, caption: str = "") -> ft.Control:
    pal = active()
    rows = [ft.Text(text, size=15, weight=ft.FontWeight.W_600, color=pal.text)]
    if caption:
        rows.append(ft.Text(caption, size=12, color=pal.muted, selectable=True))
    return ft.Column(rows, spacing=2)


def _scroll(table: ft.Control) -> ft.Control:
    return ft.Row([table], scroll=ft.ScrollMode.AUTO)


def _cut(text, n: int) -> str:
    s = str(text or "")
    return s if len(s) <= n else s[: n - 1] + "…"


def _tile(title: str, controls: list[ft.Control]) -> ft.Control:
    return ft.ExpansionTile(title=ft.Text(title, size=13, weight=ft.FontWeight.W_600, color=active().text),
                            controls=controls, expanded=False)


def _dropdown(label: str, options, width: int) -> ft.Dropdown:
    return ft.Dropdown(label=label, width=width, value=options[0],
                       options=[ft.dropdown.Option(o, o) for o in options])


# --------------------------------------------------------------------------- #
# weights
# --------------------------------------------------------------------------- #
def _weight_table(rows: list[dict], other: list[dict], market: str) -> ft.Control:
    if market == "Other markets":
        cols = list(other[0].keys()) if other else ["market"]
        return _scroll(data_table(cols, [[r.get(c) for c in cols] for r in other]))
    pick = rows if market == "All markets" else [r for r in rows if r.get("market") == market]
    body = []
    for r in pick:
        tip = " · ".join(f"{k}: {r.get(k)}" for k in ("prior", "professors", "executives", "reason"))
        w = r.get("w")
        body.append([r.get("market"), ft.Text(str(r.get("family")), size=12, color=active().text, tooltip=tip),
                     r.get("column"), r.get("final"), "—" if w is None else f"{w / 3:.2f}", r.get("rule"),
                     r.get("nodes")])
    return _scroll(data_table(["Market", "Family", "Column", "Final", W3_HEADER, "Rule", "Nodes"], body))


def _weights_section(tf: dict) -> list[ft.Control]:
    rows, other = tf.get("weights") or [], tf.get("other_markets") or []
    host = ft.Column([_weight_table(rows, other, MARKETS[0])])
    market = _dropdown("Market", MARKETS, 220)

    def on_market(e=None) -> None:
        host.controls = [_weight_table(rows, other, market.value or MARKETS[0])]
        _repaint(host)

    market.on_select = on_market
    return [_h("Tech-fund weight table (R3 design priors)", WEIGHT_CAPTION), ft.Row([market], spacing=10), host]


# --------------------------------------------------------------------------- #
# go/no-go register
# --------------------------------------------------------------------------- #
def _register_detail(r: dict | None) -> list[ft.Control]:
    pal = active()
    if r is None:
        return [ft.Text("Pick an item to see its ruling and evidence.", size=12, color=pal.muted)]
    out = [ft.Row([chip(str(r.get("id"))), chip(str(r.get("decision")), GROUP_TOKEN.get(r.get("class"), "muted")),
                   chip(f"section {r.get('section')}")] + [chip(n.strip()) for n in str(r.get("ruling") or "").split(";")
                                                          if n.strip()], spacing=6, wrap=True),
           ft.Text(str(r.get("item")), size=12, color=pal.text, selectable=True)]
    for k, label in (("indicative_gate", "Indicative (lab, in sample)"), ("evidence_for", "Evidence for"),
                     ("evidence_against", "Evidence against"), ("what_would_change_it", "What would change it"),
                     ("nodes", "Nodes"), ("target", "Target")):
        out.append(ft.Text(f"{label}: {r.get(k) or '—'}", size=12, color=pal.text, selectable=True))
    return out


def _register_section(tf: dict) -> list[ft.Control]:
    rows = tf.get("register") or []
    table_host, detail = ft.Column(), ft.Column(spacing=6)
    group = _dropdown("Group", REGISTER_GROUPS, 220)
    item = ft.Dropdown(label="Register item", width=420)

    def picked() -> list[dict]:
        g = group.value or REGISTER_GROUPS[0]
        return rows if g == REGISTER_GROUPS[0] else [r for r in rows if r.get("class") == g]

    def on_item(e=None) -> None:
        detail.controls = _register_detail(next((r for r in rows if r.get("id") == item.value), None))
        _repaint(detail)

    def on_group(e=None) -> None:
        pick = picked()
        table_host.controls = [chip(f"{len(pick)} items"), _scroll(data_table(
            ["ID", "Item", "Market", "Decision", "Indicative gate", "Target"],
            [[r.get("id"), _cut(r.get("item"), 90), r.get("market"),
              chip(str(r.get("decision")), GROUP_TOKEN.get(r.get("class"), "muted")),
              _cut("indicative (lab, in sample): " + str(r.get("indicative_gate")), 90), r.get("target")]
             for r in pick]))]
        item.options = [ft.dropdown.Option(r.get("id"), f"{r.get('id')} — {_cut(r.get('item'), 60)}") for r in pick]
        item.value = pick[0].get("id") if pick else None
        on_item()
        _repaint(table_host)
        _repaint(item)

    group.on_select, item.on_select = on_group, on_item
    on_group()
    return [_h("Go/no-go register (R3, G-01..G-77)",
               "Indicative gates are lab, in-sample results, never QUANTGEN gate results; BUILD means build the card "
               "and run the gate, nothing acts until its own card passes."),
            ft.Row([group, item], spacing=10, wrap=True), table_host, ft.Container(detail, padding=12)]


# --------------------------------------------------------------------------- #
# DO-NOT-BUILD, backlog, council, proposals
# --------------------------------------------------------------------------- #
def _label_text(v) -> str:
    return "; ".join(f"{k}: {x}" for k, x in v.items()) if isinstance(v, dict) else str(v)


def _dnb_section(tf: dict) -> list[ft.Control]:
    dnb = tf.get("dnb") or {}
    items, titles, tfi = dnb.get("items") or {}, dnb.get("titles") or {}, dnb.get("tf_items") or []
    macro = [[k, _label_text(v), titles.get(str(k), "—")] for k, v in sorted(items.items(), key=lambda kv: int(kv[0]))]
    tech = [[r.get("id"), r.get("label_proposed"), r.get("text")] for r in tfi]
    return [_h("DO-NOT-BUILD", f"{len(macro)} macro items (spec section 10, labels from the rules store) and "
                               f"{len(tech)} tech-fund items (DNB-TF); rules-store validation refuses every listed shape."),
            _tile(f"Macro items 1-{len(macro)}", [_scroll(data_table(["Item", "Label", "Refused"], macro, wide_last=True))]),
            _tile(f"Tech-fund items DNB-TF ({len(tech)})",
                  [_scroll(data_table(["ID", "Label", "Refused"], tech, wide_last=True))])]


def _counts(rows: list[dict], key: str) -> ft.Control:
    n: dict[str, int] = {}
    for r in rows:
        n[str(r.get(key))] = n.get(str(r.get(key)), 0) + 1
    return ft.Row([chip(f"{k}: {v}", STATUS_TOKEN.get(k, "muted")) for k, v in sorted(n.items())], spacing=6, wrap=True)


def _backlog_section(backlog: dict) -> list[ft.Control]:
    board, queue = backlog.get("status_board") or [], backlog.get("council_queue") or []
    return [_h("Backlog", "Status board and council queue (data/backlog_registry.json); nothing here acts."),
            _tile(f"Status board ({len(board)})", [_counts(board, "status"), _scroll(data_table(
                ["ID", "Class", "Status", "Priority", "Title"],
                [[r.get("item_id"), r.get("class"), chip(str(r.get("status")), STATUS_TOKEN.get(r.get("status"), "muted")),
                  r.get("priority"), r.get("title")] for r in board], wide_last=True))]),
            _tile(f"Council queue ({len(queue)})", [_scroll(data_table(
                ["ID", "Class", "Priority", "Settling test", "Title"],
                [[r.get("item_id"), r.get("class"), r.get("priority"), r.get("settling_test"), r.get("title")]
                 for r in queue], wide_last=True))])]


def _council_section(council: dict) -> list[ft.Control]:
    res, mods = council.get("resolutions") or [], council.get("modules") or []
    mods = sorted(list(mods) + ([{"id": "R-05", "change": "UNCHANGED", "cls": "—", "pri": "—", "ms": "—",
                                  "name": "Reversal and quality stay 1.0x (not in the page's module list)"}]
                                if mods and not any(m.get("id") == "R-05" for m in mods) else []),
                  key=lambda m: str(m.get("id")))
    return [_h("Quant Council", f"The {len(res)} resolutions and the module-status table, as recorded by the council "
                                "pages (simulated panel)."),
            _tile(f"Resolutions ({len(res)})", [_scroll(data_table(
                ["#", "Topic", "Vote", "Outcome", "Resolution"],
                [[r[0], r[1], r[3], r[5], r[2]] for r in res], wide_last=True))]),
            _tile(f"Module status ({len(mods)})", [_counts(mods, "change"), _scroll(data_table(
                ["ID", "Change", "Class", "Priority", "Milestone", "Name"],
                [[m.get("id"), chip(str(m.get("change")), STATUS_TOKEN.get(m.get("change"), "muted")), m.get("cls"),
                  m.get("pri"), m.get("ms"), m.get("name")] for m in mods], wide_last=True))])]


def _proposals_section(tf: dict) -> list[ft.Control]:
    xs, oq = tf.get("xs") or [], tf.get("open_questions") or []
    return [_h("Proposals pending owner confirmation",
               "Tech-fund cross-spec amendments (XS) and open questions (OQ); Council v2.0 governs every conflict."),
            _tile(f"Cross-spec amendments XS ({len(xs)})", [_counts(xs, "status"), _scroll(data_table(
                ["ID", "Status", "Type", "Macro target", "Amendment"],
                [[r.get("id"), chip(str(r.get("status")), STATUS_TOKEN.get(r.get("status"), "muted")), r.get("type"),
                  _cut(r.get("macro_target"), 60), r.get("amendment")] for r in xs], wide_last=True))]),
            _tile(f"Open questions OQ ({len(oq)})", [_scroll(data_table(
                ["ID", "Owner status", "Conservative default", "Question"],
                [[r.get("id"), r.get("owner_status"), _cut(r.get("conservative_default"), 70), r.get("question")]
                 for r in oq], wide_last=True))])]


def _open_buttons(pages: dict) -> list[ft.Control]:
    msg = ft.Column(spacing=4)

    def opener(path: Path):
        def go(e=None) -> None:
            shown = open_path(path)
            msg.controls = [shown] if shown is not None else []
            _repaint(msg)
        return go

    return [ft.Row([ft.Button(label, icon=ft.Icons.OPEN_IN_NEW, on_click=opener(Path(p)), data=str(p),
                              tooltip=f"{p} · research only, simulated panels; opens in the system browser")
                    for label, p in pages.items()], spacing=10, wrap=True), msg]


def research_blocks(tf: dict, backlog: dict, council: dict) -> list[ft.Control]:
    """tf = {weights, other_markets, register, dnb{items, titles, tf_items}, xs, open_questions}; backlog =
    `backlog_registry.load_registry()`; council = {resolutions, modules, pages{label: path}}. Missing or malformed
    inputs fail closed: one error notice and nothing else."""
    if not all(isinstance(x, dict) for x in (tf, backlog, council)) or not tf.get("weights") or not tf.get("register"):
        return [notice("Research register not shown: the tech-fund record, backlog or council data is missing or "
                       "invalid (fail closed).", "error", icon=ft.Icons.ERROR_OUTLINE)]
    return ([notice("\n".join(DISCLAIMERS), "accent", icon=ft.Icons.LOCK_OUTLINE)]
            + _open_buttons(council.get("pages") or PAGES)
            + _weights_section(tf) + _register_section(tf) + _dnb_section(tf) + _backlog_section(backlog)
            + _council_section(council) + _proposals_section(tf))


# --------------------------------------------------------------------------- #
# loader
# --------------------------------------------------------------------------- #
def dnb_titles(spec: Path = SPEC) -> dict[str, str]:
    """Item number -> bold title of spec section 10.2 (descriptive text; the labels come from the store)."""
    try:
        s = spec.read_text(encoding="utf-8")
    except OSError:
        return {}
    body = s[s.find("### 10.2 The list"):s.find("### 10.3")]
    return {m.group(1): m.group(2) for m in re.finditer(r"^(\d+)\. (?:`[^`]*` )?\*\*(.+?)\*\*", body, re.M)}


def council_resolutions(html: Path = PAGES["Open Quant Council page"]) -> list[list[str]]:
    """The twelve `RES` rows of the Quant Council page script: [#, topic, resolution, vote, stamp class, outcome]."""
    m = re.search(r"const RES = (\[.*?\]);", html.read_text(encoding="utf-8"), re.S)
    rows = ast.literal_eval(m.group(1)) if m else []
    if len(rows) != 12 or any(len(r) != 6 for r in rows):
        raise ValueError(f"{html.name}: expected 12 resolutions of 6 fields, found {len(rows)}")
    return rows


def load_inputs() -> dict:
    from core import techfund as T
    from core.rules import backlog_registry as B
    from core.rules.macro_rules import load_store
    dnb = load_store().get("do_not_build")
    data = json.loads((COUNCIL / "council_pages_data.json").read_text(encoding="utf-8"))
    return {"tf": {"weights": T.weights(), "other_markets": T.weights_other_markets(), "register": T.register(),
                   "xs": T.cross_spec_amendments(), "open_questions": T.open_questions(),
                   "dnb": {"items": dnb["items"], "titles": dnb_titles(), "tf_items": dnb["tf_items"]}},
            "backlog": B.load_registry(),
            "council": {"resolutions": council_resolutions(), "modules": data["quant_council"]["modules"],
                        "pages": dict(PAGES)}}


def build_research_view(page: ft.Page) -> ft.Control:
    return view_shell(page, load_inputs, lambda d: research_blocks(d["tf"], d["backlog"], d["council"]))
