"""Macro -> Model cards view (02_ui_design section 1; code_ui D.1).

Renders the v2 macro card registry as records: every card's verdict chip, a disposition chip beside it
(BUILD-AS-INSURANCE is a disposition, never a verdict), its reason code, its label verbatim, the instrument book and
the notional status; the gate package status with its refusal reasons; the registered R-06 US REJECT; FORWARD-SIM and
refusal books in their own groups marked "not a recommendation" and never styled success; the tech-fund card drafts
with their NOT_RUN reasons; the CRY-1 control results under their vendor-data label.

`cards_blocks` is a pure dict -> controls renderer (testable without a page). `load_inputs` reads the validated
records once (call it in a worker: a broken verdict chain or a re-hash mismatch raises, and the view fails closed).
Nothing here computes exposure, admits a card or writes a file.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Optional

import flet as ft

from core.theme import active
from ui.components import card, chip, disposition_chip, notice, verdict_chip

ROOT = Path(__file__).resolve().parents[1]
VERDICTS = ("PASS", "REVISE", "REJECT", "INSUFFICIENT_DATA", "NOT_RUN")    # schema $defs.card verdict
TF_DOCS = ROOT / "docs" / "techfund"
STRETCH = ft.CrossAxisAlignment.STRETCH          # cards fill the view width

# (group key, heading, caption); a card's group follows its disposition, the registered REJECT has its own.
GROUPS = (
    ("cards", "Macro model cards",
     "CARD-O / CARD-P registry. Nothing here reaches the recommended book until it PASSes under a frozen gate package."),
    ("registered", "Registered REJECT — a fact about the instrument",
     "Registered card: never re-run, never rebuilt."),
    ("forward_sim", "FORWARD-SIM books — not a recommendation",
     "Display only: a FORWARD-SIM multiplier never reaches the recommended book, and a forward record never validates."),
    ("refusal", "Refusal books — not a recommendation",
     "Retired legs kept as labelled REJECTs (archived council records); display only."),
)


def _group(c: dict) -> str:
    d = c.get("disposition")
    if d == "FORWARD_SIM":
        return "forward_sim"
    if d == "REFUSAL_BOOK":
        return "refusal"
    return "registered" if c.get("rerun") is False else "cards"


def _heading(text: str, caption: str = "") -> ft.Control:
    pal = active()
    rows = [ft.Text(text, size=15, weight=ft.FontWeight.W_600, color=pal.text)]
    if caption:
        rows.append(ft.Text(caption, size=12, color=pal.muted))
    return ft.Column(rows, spacing=2)


def _tagged(control: ft.Control, tag: str) -> ft.Control:
    control.data = tag                       # lets a test tell a verdict chip from a disposition chip
    return control


def _kv(d: dict) -> str:
    """Scalars of a result dict as 'k v' pairs (format only, 3 significant digits)."""
    out = []
    for k, v in d.items():
        if isinstance(v, float):
            out.append(f"{k} {v:.3g}")
        elif isinstance(v, (bool, int, str)) or v is None:
            out.append(f"{k} {v}")
    return ", ".join(out)


def _reason(c: dict, row: Optional[dict], verdict: str, gate: dict) -> tuple[str, str]:
    """(reason code, reason text) for the verdict shown."""
    if row is not None:
        code = row.get("reason_code") or row.get("reason") or c.get("reason_code") or c.get("reason")
        return (str(code), f"verdict row {row.get('card_id')} r{row.get('revision')} in cards/verdicts.jsonl") if code \
            else ("—", "verdict row carries no reason code")
    if c.get("rerun") is False:
        return "registered", "registered card: never re-run, never rebuilt"
    if c.get("source"):
        return "archived_record", f"archived council record ({c['source']})"
    if verdict == "NOT_RUN":
        st = gate.get("status") or "UNKNOWN"
        if st != "FROZEN":
            return st, f"gate package {st}: no card runs before the freeze (P11)"
        return "no_verdict_row", "no verdict row in cards/verdicts.jsonl"
    code = c.get("reason_code") or c.get("reason")
    return (str(code), str(code)) if code else ("—", "no reason code recorded")


def _notional(c: dict) -> ft.Control:
    n = c.get("notional")
    if not n:
        return chip("notional: no sleeve key", "muted")
    if n.get("value") is None:
        return chip("notional: null (owner input)", "warning", tooltip=f"{n.get('ref')} is null in the store")
    return chip(f"notional: {n['value']}", "muted", tooltip=str(n.get("ref")))


def _card_row(c: dict, row: Optional[dict], gate: dict, drafts: list[dict]) -> ft.Control:
    pal = active()
    verdict = str((row or c).get("verdict") or "NOT_RUN")
    disp = str((row or c).get("disposition") or "DESCRIPTIVE")
    code, why = _reason(c, row, verdict, gate)
    if verdict in VERDICTS:
        vchip = verdict_chip(verdict, tooltip=why)
    else:                                    # never let a disposition or a stray word pose as a verdict
        code, why = "invalid_verdict", f"verdict {verdict!r} is not a schema verdict (fail closed)"
        vchip = chip("verdict invalid", "error", tooltip=why)
    head = ft.Row([
        ft.Text(str(c.get("card_id")), size=13, weight=ft.FontWeight.W_600, color=pal.text, selectable=True),
        chip(str(c.get("class") or "class ?")),
        _tagged(vchip, "verdict"),
        _tagged(disposition_chip(disp), "disposition"),
        chip(f"reason: {code}", "muted", tooltip=why),
    ], spacing=6, wrap=True)
    facts = [chip(f"instrument book: {c['instrument_book']}")] if c.get("instrument_book") else []
    if c.get("build_status"):
        facts.append(chip(f"build status: {c['build_status']}"))
    if "notional" in c:
        facts.append(_notional(c))
    nulls = c.get("owner_nulls") or {}
    if nulls:
        facts.append(chip(f"{len(nulls)} owner / reference nulls", "warning",
                          tooltip="\n".join(f"{k}: {v}" for k, v in nulls.items())))
    revs = sorted(d.get("revision") for d in drafts if isinstance(d.get("revision"), int))
    if revs:
        committed = any(d.get("header_md5") for d in drafts)
        facts.append(chip("header " + ("committed " if committed else "drafts ") + ", ".join(f"r{r}" for r in revs)
                          + ("" if committed else " · not committed"), tooltip=str(drafts[-1].get("claim") or "")))
    lines: list[ft.Control] = [head,
                               ft.Text(c.get("label") or "no label in the registry", size=12, color=pal.text,
                                       selectable=True),
                               ft.Text(f"Reason: {why}", size=12, color=pal.muted, selectable=True),
                               ft.Row(facts, spacing=6, wrap=True)]
    extra = [f"{k}: {_kv(c[k]) if isinstance(c[k], dict) else c[k]}" for k in ("span", "fragility_ratio", "backlog")
             if c.get(k) is not None]
    if extra:
        lines.append(ft.Text(" · ".join(extra), size=12, color=pal.muted, selectable=True))
    return _tagged(card(ft.Column(lines, spacing=6)), f"card:{c.get('card_id')}")


def _gate_block(gate: dict) -> ft.Control:
    pal = active()
    st = str(gate.get("status") or "UNKNOWN")
    token = "success" if st == "FROZEN" else "warning" if st == "NOT_FROZEN" else "error"
    lines: list[ft.Control] = [ft.Row([ft.Text("Gate package", size=15, weight=ft.FontWeight.W_600, color=pal.text),
                                       chip(f"gate package {st}", token)], spacing=10, wrap=True)]
    if st != "FROZEN":
        lines.append(ft.Text("No macro card runs before the freeze: every card stays NOT RUN until the package is "
                             "frozen and its formal run is recorded (P11).", size=12, color=pal.muted))
    lines += [ft.Text("• " + str(r), size=12, color=pal.text, selectable=True) for r in gate.get("reasons") or []]
    return card(ft.Column(lines, spacing=6))


def _techfund_row(d: dict) -> ft.Control:
    pal = active()
    run = str(d.get("run_status") or d.get("verdict") or "NOT_RUN")
    why = str(d.get("blocked_by") or "no reason recorded")
    lines: list[ft.Control] = [
        ft.Row([ft.Text(str(d.get("card_id")), size=13, weight=ft.FontWeight.W_600, color=pal.text),
                chip(str(d.get("class") or "class ?")),
                _tagged(verdict_chip(run, tooltip=why), "verdict"),
                chip(f"build status: {d.get('build_status') or '—'}"),
                chip(f"instrument book: {d.get('instrument_book') or '—'}")], spacing=6, wrap=True),
        ft.Text(str(d.get("hypothesis") or ""), size=12, color=pal.text, italic=True, selectable=True),
        ft.Text(f"Reason: {why}", size=12, color=pal.muted, selectable=True)]
    lab = d.get("lab_reference")
    if isinstance(lab, dict) and lab.get("label"):
        lines.append(ft.Text(str(lab["label"]), size=12, color=pal.muted, selectable=True))
    return _tagged(card(ft.Column(lines, spacing=6)), f"card:{d.get('card_id')}")


def _cry1_lines(results) -> list[str]:
    out = []
    for venue, body in (results or {}).items():
        if not isinstance(body, dict):
            continue
        if "decision" in body:
            out.append(f"{venue}: {body['decision']} — {body.get('reason', '')}")
            continue
        for k, v in body.items():
            if isinstance(v, dict) and "decision" in v:
                out.append(f"{venue} · {k}: {v['decision']} — {v.get('reason', '')}")
            elif isinstance(v, dict):
                out.append(f"{venue} · {k}: {_kv(v)}")
            elif k == "trigger" and v:
                out.append(f"{venue}: {v}")
    return out


def _cry1_row(r: dict) -> ft.Control:
    pal = active()
    lines: list[ft.Control] = [
        ft.Row([ft.Text(f"{r.get('item', 'CRY-1')}: {r.get('addition', '')}", size=13, weight=ft.FontWeight.W_600,
                        color=pal.text),
                chip(str(r.get("label") or "vendor data, labelled trial, not a formal card run"), "error"),
                chip(f"register {r.get('register_id', '—')}")], spacing=6, wrap=True),
        ft.Text(f"Card {r.get('card', '—')}: {r.get('c3_verdict', '')}", size=12, color=pal.text, selectable=True)]
    if r.get("status"):
        lines.append(ft.Text(f"{r['status']}: {r.get('reason', '')}", size=12, color=pal.muted, selectable=True))
    lines += [ft.Text("• " + ln, size=12, color=pal.muted, selectable=True) for ln in _cry1_lines(r.get("results"))]
    return card(ft.Column(lines, spacing=4))


def cards_blocks(cards: list[dict], verdicts: list[dict], gate_status: dict, headers: list[dict], *,
                 techfund: list[dict] = (), cry1: list[dict] = ()) -> list[ft.Control]:
    """cards = `cards.list_cards(...)` rows (+ the refusal cards), verdicts = rows of `cards/verdicts.jsonl`,
    gate_status = {status, reasons}, headers = header dicts (drafts and committed); techfund = the tech-fund
    `*.draft.json` dicts, cry1 = the `cry1_*.json` results. Missing or malformed inputs fail closed: one error
    notice and nothing else."""
    if not isinstance(cards, list) or not isinstance(verdicts, list) or not isinstance(gate_status, dict) \
            or not isinstance(headers, list):
        return [notice("Model cards not shown: the card registry, verdict chain or gate status is missing or invalid "
                       "(fail closed).", "error", icon=ft.Icons.ERROR_OUTLINE)]
    last = {r.get("card_id"): r for r in verdicts if isinstance(r, dict)}          # later rows win
    drafts: dict[str, list[dict]] = {}
    for h in headers:
        if isinstance(h, dict):
            drafts.setdefault(h.get("card_id"), []).append(h)
    blocks: list[ft.Control] = [
        notice("Read-only records. A verdict chip shows only a gate result; BUILD-AS-INSURANCE, FORWARD-SIM and "
               "refusal are dispositions, shown beside it. Labels are printed verbatim.", "accent",
               icon=ft.Icons.LOCK_OUTLINE),
        ft.Row([chip(f"{len(cards)} cards"), chip(f"{len(verdicts)} verdict rows")], spacing=6, wrap=True),
        _gate_block(gate_status)]
    for key, title, caption in GROUPS:
        rows = [c for c in cards if isinstance(c, dict) and _group(c) == key]
        if rows:
            blocks.append(ft.Container(ft.Column([_heading(title, caption)] + [
                _card_row(c, last.get(c.get("card_id")), gate_status, drafts.get(c.get("card_id"), [])) for c in rows],
                spacing=8, horizontal_alignment=STRETCH), data=key))
    blocks.append(ft.Container(ft.Column(
        [_heading("Tech-fund card drafts — not run, not a recommendation",
                  "Proposals pending owner confirmation; Council v2.0 governs on conflict.")]
        + ([_techfund_row(d) for d in techfund if isinstance(d, dict)]
           or [notice("No tech-fund card drafts found under docs/techfund.", "accent")]), spacing=8, horizontal_alignment=STRETCH), data="techfund"))
    blocks.append(ft.Container(ft.Column(
        [_heading("CRY-1 control results (crypto card C3)",
                  "Vendor data, labelled trials, not formal card runs; the stored C3 verdict is not rewritten.")]
        + ([_cry1_row(r) for r in cry1 if isinstance(r, dict)]
           or [notice("No CRY-1 results found under docs/techfund.", "accent")]), spacing=8, horizontal_alignment=STRETCH), data="cry1"))
    return blocks


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_inputs(macro_dir=None, cards_root=None) -> dict:
    """The keyword arguments of `cards_blocks`, read once. Raises on a broken verdict chain, a committed header or
    card that does not re-hash, or an unreadable store (the caller shows the error and no numbers)."""
    import config
    from core.ficc import macro_artifacts as MA
    from core.quant import cards as K, gate_package as GP, refusal as R
    from core.rules.macro_rules import load_store
    from core.skills.macro_daily import CARDS_ROOT, GOVERNANCE_LOG
    macro_dir = Path(macro_dir or config.macro_dir())
    store, root = load_store(rulings_log=macro_dir / GOVERNANCE_LOG), Path(cards_root or CARDS_ROOT)   # effective store (S1)
    cards = K.list_cards(root, store)
    for c in cards:
        if c.get("notional"):
            c["notional"]["value"] = store.get(c["notional"]["ref"])
    for rule, spec in (("R-11", R.CARD_S1), ("R-12", R.CARD_S2)):
        rec = R.REFUSAL_RECORDS.get(rule, {})
        cards.append({**spec, "rule_id": rule, "source": rec.get("source"), "span": rec.get("span"),
                      "fragility_ratio": rec.get("fragility_ratio"), "backlog": rec.get("backlog")})
    return {"cards": cards,
            "verdicts": K.read_chain(K.verdicts_path(root), K.VERDICT_ROW),
            "gate_status": {"status": GP.package_state(store, macro_dir),
                            "reasons": GP.freeze_reasons(store, MA.GIT_HASH, macro_dir)},
            "headers": K.committed_headers(root) + [_json(p) for p in sorted((root / "headers").glob("*.draft.json"))],
            "techfund": [_json(p) for p in sorted(TF_DOCS.glob("*.draft.json"))],
            "cry1": [_json(p) for p in sorted(TF_DOCS.glob("cry1_*.json"))]}


def view_shell(page: ft.Page, load: Callable[[], dict], render: Callable[[dict], list[ft.Control]]) -> ft.Control:
    """Refresh button + host: `render(load())` on `page.run_thread`, two-tier except, re-read on every Refresh."""
    pal = active()
    busy = ft.ProgressRing(visible=False, width=20, height=20)
    status = ft.Text("", size=12, color=pal.muted)
    host = ft.Column(spacing=14, horizontal_alignment=STRETCH)

    def refresh(e=None) -> None:
        busy.visible = True
        status.value = "Reading… (local files, read-only)"
        page.update()

        def worker():
            try:
                blocks = render(load())
            except (ValueError, OSError, RuntimeError) as exc:
                blocks = [notice(str(exc), "error", icon=ft.Icons.ERROR_OUTLINE)]
            except Exception as exc:
                blocks = [notice(f"{type(exc).__name__}: {exc}", "error", icon=ft.Icons.ERROR_OUTLINE)]
            host.controls = blocks
            busy.visible = False
            status.value = ""
            page.update()

        page.run_thread(worker)

    refresh()
    return ft.Column([ft.Row([ft.Button("Refresh", icon=ft.Icons.REFRESH, on_click=refresh), busy, status],
                             spacing=10, wrap=True),
                      ft.Column([host], scroll=ft.ScrollMode.AUTO, expand=True, horizontal_alignment=STRETCH)],
                     spacing=14, expand=True)


def build_cards_view(page: ft.Page) -> ft.Control:
    return view_shell(page, load_inputs, lambda d: cards_blocks(d["cards"], d["verdicts"], d["gate_status"],
                                                               d["headers"], techfund=d["techfund"], cry1=d["cry1"]))
