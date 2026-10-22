"""M0 harness tests: T-RO-01 static read-only scan, the test registry, the fixture manifest loader and the
NOT_RUN status (TASK-M0-01, M0-02, M0-03; spec P0, section 9, section 9.5; section 10 item 21).

Every test is a zero-argument callable; `tests/macro_acceptance.py` discovers and wraps them. Tests that
implement a spec test carry `test_ids`.
"""
from __future__ import annotations

import ast
import csv
import json
import re
import tempfile
from pathlib import Path

from tests.acceptance import _code_only, runtime_py
from tests.notrun import MANIFEST, MANIFEST_COLUMNS, NotRun, load_manifest, md5_of, require_fixture, unlisted

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "tests" / "macro_registry.csv"
SPEC = ROOT / "QUANTGEN_Quant_Council_2026-10-03" / "claude_code" / "QUANTGEN_MACRO_INTEGRATION.md"
TEST_ID = re.compile(r"\b(?:T-[A-Z0-9]+(?:-[A-Z0-9]+)*-\d+[a-z]?|I-\d+[a-z]?|G-[A-Z0-9]+-[A-Z0-9]*\d[a-z]?)\b")

# --------------------------------------------------------------------------- #
# T-RO-01: the forbidden surface, listed here (spec L5605; constitution B.7)
# --------------------------------------------------------------------------- #
# Case-insensitive substrings of the executable surface (docstrings and comments stripped).
FORBIDDEN_TEXT_CI = (
    "order_cash", "order-cash", "place_order", "submit_order",        # KIS order endpoints and verbs
    "tttc0802u", "tttc0801u", "vttc0802u",                           # KIS order TR ids
    "/v1/orders", "/v1/withdraws", "/v1/deposits/generate_coin_address",   # Upbit
    "/api/v3/order", "/sapi/v1/capital/withdraw", "/sapi/v1/capital/deposit",  # Binance
    "private_key", "seed_phrase",
)
FORBIDDEN_TEXT_CS = ("KIS_ACCOUNT", "CANO", "ACNT_PRDT_CD")           # an account number implies an order path
FORBIDDEN_PATH_RE = re.compile(r"/uapi/[^\s'\"]*/trading/")           # every KIS trading domain
# Top-level modules of order-submission clients; an import anywhere fails.
FORBIDDEN_IMPORTS = frozenset({
    "ccxt", "web3", "pyupbit", "binance", "python_binance", "ib_insync", "alpaca", "alpaca_trade_api",
    "mojito", "pykis", "kiwoom", "okx", "bybit", "kucoin", "coinbase", "cbpro", "MetaTrader5", "oandapyV20",
    "eth_account", "bitcoinlib", "bitcoin",
})
# Call names of order, cancel, withdrawal, deposit-address and transfer paths (attribute or bare calls).
FORBIDDEN_CALLS = frozenset({
    "place_order", "submit_order", "create_order", "send_order", "new_order", "order_cash", "cancel_order",
    "create_market_order", "create_limit_order", "buy_market_order", "sell_market_order",
    "buy_limit_order", "sell_limit_order", "withdraw", "withdraw_coin", "withdraw_krw", "create_withdrawal",
    "transfer", "transfer_funds", "deposit_address", "get_deposit_address", "create_deposit_address",
    "fetch_deposit_address", "generate_coin_address", "sign_transaction", "send_transaction", "send_raw_transaction",
})
MUTATING_HTTP = frozenset({"post", "put", "delete", "patch"})
MUTATING_URL_WORDS = ("order", "withdraw", "transfer", "deposit")
# The simulated order book API (core/engine/orders.py) and its UI handlers are the only legitimate
# order-shaped names: OrderBook.place/fill/cancel/reject/cancel_all_open, Evaluator.sweep_cancellations,
# and the bare `fill_order` / `cancel_order` handlers of ui/trading_page.py that call `runtime.book`.
ALLOWED_BARE_CALLS = {"ui/trading_page.py": {"fill_order", "cancel_order"}}
# Only the engine package (and the macro engine feed named in the rulings) may import the book itself.
ORDERS_IMPORTERS_ALLOWED = ("core/engine/", "core/skills/macro_daily.py", "core/skills/pipeline.py")
ORDERS_NAMES = {"OrderBook", "SimulatedOrder", "OrderStatus", "order_id"}
WORKFLOW_YAML = ROOT / "core" / "skills" / "macro_workflows"


def _scan_files() -> list[Path]:
    files = runtime_py() + sorted(p for p in (ROOT / "docs").glob("*.py"))
    return [p for p in files if p.is_file()]


def _strings_in(node: ast.AST) -> list[str]:
    out = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            out.append(sub.value)
    return out


def _offences(path: Path) -> list[str]:
    rel = path.relative_to(ROOT).as_posix()
    code = _code_only(path)
    low = code.lower()
    hits = [f"{rel}: {n!r}" for n in FORBIDDEN_TEXT_CI if n in low]
    hits += [f"{rel}: {n!r}" for n in FORBIDDEN_TEXT_CS if n in code]
    hits += [f"{rel}: {m.group(0)!r}" for m in FORBIDDEN_PATH_RE.finditer(code)]
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in FORBIDDEN_IMPORTS:
                    hits.append(f"{rel}:{node.lineno}: import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] in FORBIDDEN_IMPORTS:
                hits.append(f"{rel}:{node.lineno}: from {node.module} import ...")
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                if func.attr in FORBIDDEN_CALLS:
                    hits.append(f"{rel}:{node.lineno}: .{func.attr}()")
                if func.attr in MUTATING_HTTP:
                    urls = " ".join(_strings_in(node)).lower()
                    if any(w in urls for w in MUTATING_URL_WORDS):
                        hits.append(f"{rel}:{node.lineno}: .{func.attr}() on an order/withdraw/transfer/deposit URL")
            elif isinstance(func, ast.Name) and func.id in FORBIDDEN_CALLS:
                if func.id not in ALLOWED_BARE_CALLS.get(rel, set()):
                    hits.append(f"{rel}:{node.lineno}: {func.id}()")
    return hits


def _yaml_offences(path: Path) -> list[str]:
    import yaml
    rel = path.relative_to(ROOT).as_posix()
    hits = []

    def walk(value):
        if isinstance(value, dict):
            for v in value.values():
                walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)
        elif isinstance(value, str):
            low = value.lower()
            hits.extend(f"{rel}: {n!r}" for n in FORBIDDEN_TEXT_CI if n in low)
            hits.extend(f"{rel}: {n!r}" for n in FORBIDDEN_TEXT_CS if n in value)
            hits.extend(f"{rel}: {m.group(0)!r}" for m in FORBIDDEN_PATH_RE.finditer(value))
            words = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", value))
            hits.extend(f"{rel}: {w}" for w in sorted(words & (FORBIDDEN_CALLS | FORBIDDEN_IMPORTS)))

    walk(yaml.safe_load(path.read_text(encoding="utf-8")))
    return hits


def test_t_ro_01_no_order_cancel_withdrawal_or_transfer_path():
    """Static scan of core/, data/, ui/, config.py, main.py, docs/*.py and the macro workflow YAML."""
    files = _scan_files()
    assert len(files) > 50, "scan scope collapsed"
    hits = [h for p in files for h in _offences(p)]
    if WORKFLOW_YAML.is_dir():
        hits += [h for p in sorted(WORKFLOW_YAML.glob("*.yaml")) for h in _yaml_offences(p)]
    assert not hits, "order path surface present:\n  " + "\n  ".join(hits)


test_t_ro_01_no_order_cancel_withdrawal_or_transfer_path.test_ids = ["T-RO-01"]


def test_t_ro_01_orders_module_reached_only_through_the_engine():
    """`core/engine/orders` is imported only inside the engine package (plus the macro engine feed)."""
    offenders = []
    for path in _scan_files():
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith(ORDERS_IMPORTERS_ALLOWED[0]) or rel in ORDERS_IMPORTERS_ALLOWED:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and any(a.name == "core.engine.orders" for a in node.names):
                offenders.append(f"{rel}:{node.lineno}")
            elif isinstance(node, ast.ImportFrom):
                if node.module == "core.engine.orders" or (
                        node.module == "core.engine" and {a.name for a in node.names} & ORDERS_NAMES):
                    offenders.append(f"{rel}:{node.lineno}")
    assert not offenders, f"core.engine.orders imported outside the engine: {offenders}"
    api = ast.parse((ROOT / "core/engine/orders.py").read_text(encoding="utf-8"))
    book = next(n for n in api.body if isinstance(n, ast.ClassDef) and n.name == "OrderBook")
    methods = {n.name for n in book.body if isinstance(n, ast.FunctionDef)}
    assert {"place", "fill", "cancel", "reject", "cancel_all_open"} <= methods, methods


test_t_ro_01_orders_module_reached_only_through_the_engine.test_ids = ["T-RO-01"]


def test_t_ro_01_artifact_writers_stamp_read_only():
    """Every artifact carries `read_only: true` (spec L3508): the provenance builder sets it and every shipped
    macro JSON store carries it."""
    stores = [p for p in (ROOT / "data" / "macro").glob("*.json")] if (ROOT / "data" / "macro").is_dir() else []
    for path in stores:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and "version" in payload:
            assert payload.get("read_only") is True, f"{path.name} lacks read_only: true"
    src = ROOT / "core" / "ficc" / "macro_artifacts.py"
    tree = ast.parse(src.read_text(encoding="utf-8"))
    stamped = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if (isinstance(k, ast.Constant) and k.value == "read_only"
                        and isinstance(v, ast.Constant) and v.value is True):
                    stamped = True
        elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and node.value.value is True:
            for target in node.targets:
                if (isinstance(target, ast.Subscript) and isinstance(target.slice, ast.Constant)
                        and target.slice.value == "read_only"):
                    stamped = True
        elif isinstance(node, ast.keyword) and node.arg == "read_only":
            if isinstance(node.value, ast.Constant) and node.value.value is True:
                stamped = True
    assert stamped, "core/ficc/macro_artifacts.py never sets read_only: True"


test_t_ro_01_artifact_writers_stamp_read_only.test_ids = ["T-RO-01"]


# --------------------------------------------------------------------------- #
# Registry (spec section 9.0a / 9.0b)
# --------------------------------------------------------------------------- #
def _registry() -> list[dict[str, str]]:
    with REGISTRY.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        assert reader.fieldnames == ["test_id", "tier", "runs_from", "modules", "clause", "deferred_to",
                                     "feasibility", "implemented_in"], reader.fieldnames
        return list(reader)


def test_registry_has_unique_ids_and_valid_columns():
    rows = _registry()
    ids = [r["test_id"] for r in rows]
    dups = sorted({i for i in ids if ids.count(i) > 1})
    assert not dups, f"duplicate registry ids: {dups}"
    for r in rows:
        assert TEST_ID.fullmatch(r["test_id"]), r["test_id"]
        assert r["tier"] in ("fast", "golden", "freeze"), r
        assert re.fullmatch(r"M(10|[0-9])", r["runs_from"]), r
        assert r["feasibility"] in ("SYNTH", "REFDATA", "OWNER"), r
        assert re.fullmatch(r"R-\d\d(;R-\d\d)*", r["modules"]), r
        clauses = [c for c in r["clause"].split(" | ") if c]
        deferred = [d for d in r["deferred_to"].split(" | ") if d]
        assert len(clauses) == len(deferred), f"{r['test_id']}: clause/deferred_to misaligned"
        assert all(re.fullmatch(r"M(10|[0-9])", d) for d in deferred), r
    assert len(rows) >= 200, len(rows)


test_registry_has_unique_ids_and_valid_columns.test_ids = ["T-HERM-01"]


def test_registry_covers_every_id_of_the_spec_exit_table():
    """Every fully spelled id of section 9.0a (the authoritative exit list) has a registry row with that milestone."""
    lines = SPEC.read_text(encoding="utf-8").split("\n")
    rows = _registry()
    table = {r["test_id"]: r["runs_from"] for r in rows}
    deferred = {r["test_id"]: r["deferred_to"].split(" | ") for r in rows}
    start = next(i for i, l in enumerate(lines) if l.startswith("### 9.0a"))
    end = next(i for i, l in enumerate(lines) if l.startswith("### 9.0b"))
    missing, wrong = [], []
    for line in lines[start:end]:
        m = re.match(r"\|\s*M(\d+)\b[^|]*\|(.*)\|", line)
        if not m:
            continue
        milestone, cell = f"M{m.group(1)}", m.group(2)
        for tid in set(TEST_ID.findall(cell)):
            if tid not in table:
                missing.append(tid)
                continue
            # A row names an id either as its runs_from, as a clause deferred to that row, or with "from M<k>".
            if table[tid] == milestone or milestone in deferred[tid] or f"from {table[tid]}" in cell[cell.index(tid):]:
                continue
            wrong.append(f"{tid}: registry {table[tid]} vs spec row {milestone}")
    assert not missing and not wrong, f"missing {missing}; milestone mismatch {wrong}"


test_registry_covers_every_id_of_the_spec_exit_table.test_ids = ["T-HERM-01"]


def test_registry_implemented_in_matches_test_ids():
    """`implemented_in` equals the `test_ids` the macro modules carry; every id a test names is registered."""
    from tests.macro_acceptance import implemented_in
    impl = implemented_in()
    rows = _registry()
    stale = [f"{r['test_id']}: {r['implemented_in']!r} != {impl.get(r['test_id'], '')!r}"
             for r in rows if r["implemented_in"] != impl.get(r["test_id"], "")]
    assert not stale, "registry out of sync (python -m tests.macro_acceptance resyncs it): " + "; ".join(stale)
    unknown = sorted(set(impl) - {r["test_id"] for r in rows})
    assert not unknown, f"test_ids not in the registry: {unknown}"


test_registry_implemented_in_matches_test_ids.test_ids = ["T-HERM-01"]


# --------------------------------------------------------------------------- #
# Fixture manifest (spec section 9.5)
# --------------------------------------------------------------------------- #
def test_manifest_lists_every_fixture_with_a_matching_md5():
    rows = load_manifest()
    assert tuple(MANIFEST_COLUMNS) == ("file", "source", "series", "span", "retrieved_at_utc",
                                       "value_status_rule", "md5", "licence", "owner", "tests")
    assert not unlisted(), f"fixtures not listed in MANIFEST.csv (python -m tests.notrun prints rows): {unlisted()}"
    stale = [f"{n}: {md5_of(MANIFEST.parent / n)} != {r['md5']}" for n, r in rows.items()
             if (MANIFEST.parent / n).is_file() and md5_of(MANIFEST.parent / n) != r["md5"].lower()]
    absent = [n for n in rows if not (MANIFEST.parent / n).is_file()]
    assert not stale and not absent, f"stale md5 {stale}; listed but absent {absent}"
    for name in rows:
        require_fixture(name)


test_manifest_lists_every_fixture_with_a_matching_md5.test_ids = ["T-HERM-01"]


def test_manifest_loader_refuses_unlisted_absent_changed_and_unlicensed():
    tmp = Path(tempfile.mkdtemp())
    (tmp / "ok.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (tmp / "drift.csv").write_text("a,b\n1,3\n", encoding="utf-8")
    header = ",".join(MANIFEST_COLUMNS)
    rows = [f"ok.csv,synthetic(seed=11),A,2026-01-01..2026-01-02,2026-10-02T07:00:00Z,official_close,{md5_of(tmp / 'ok.csv')},CC0,harness,T-HERM-01",
            f"gone.csv,synthetic(seed=11),A,,2026-10-02T07:00:00Z,official_close,{'0' * 32},CC0,harness,T-HERM-01",
            f"drift.csv,synthetic(seed=11),A,,2026-10-02T07:00:00Z,official_close,{'0' * 32},CC0,harness,T-HERM-01"]
    manifest = tmp / "MANIFEST.csv"
    manifest.write_text(header + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
    assert require_fixture("ok.csv", manifest=manifest) == tmp / "ok.csv"
    for name, needle in (("unlisted.csv", "not in"), ("gone.csv", "absent"), ("drift.csv", "md5")):
        try:
            require_fixture(name, manifest=manifest)
        except NotRun as exc:
            assert exc.reason.startswith("REFDATA: ") and needle in exc.reason, exc.reason
        else:
            raise AssertionError(f"{name} was not refused")
    assert unlisted(manifest) == []
    (tmp / "extra.csv").write_bytes(b"x")
    assert [n for n, _ in unlisted(manifest)] == ["extra.csv"]
    for bad in (rows[0].replace("CC0", ""), rows[0].replace("harness", ""), rows[0].replace(md5_of(tmp / "ok.csv"), "")):
        manifest.write_text(header + "\n" + bad + "\n", encoding="utf-8")
        try:
            load_manifest(manifest)
        except ValueError as exc:
            assert "not a fixture" in str(exc)
        else:
            raise AssertionError("a row without licence, owner and md5 was accepted")
    manifest.write_text("file,md5\nok.csv,x\n", encoding="utf-8")
    try:
        load_manifest(manifest)
    except ValueError as exc:
        assert "header" in str(exc)
    else:
        raise AssertionError("a wrong header was accepted")


test_manifest_loader_refuses_unlisted_absent_changed_and_unlicensed.test_ids = ["T-HERM-01"]


# --------------------------------------------------------------------------- #
# Runner: NOT_RUN is a third status; the GATE leak is closed
# --------------------------------------------------------------------------- #
def test_runner_records_not_run_as_a_third_status():
    import io
    from contextlib import redirect_stderr, redirect_stdout
    from tests import run_all

    def skipped():
        raise NotRun("REFDATA: probe fixture")

    def failing():
        raise ValueError("boom")

    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        rows = run_all.run([("probe/skipped", skipped), ("probe/ok", lambda: None), ("probe/fail", failing)])
    assert [r["status"] for r in rows] == ["NOT_RUN", "PASS", "FAIL"]
    assert rows[0]["reason"] == "REFDATA: probe fixture" and rows[0]["detail"] == ""
    assert "reason" not in rows[1] and rows[2]["detail"].startswith("ValueError")
    ok = lambda: None                                                  # noqa: E731
    ok.test_ids = ["T-RO-01"]
    later = lambda: None                                               # noqa: E731
    later.test_ids = ["T-CRYPTO-01"]
    clause = lambda: None                                              # noqa: E731
    clause.test_ids = ["T-CAP-01"]           # runs_from M0; its "overlay cannot emit 0" clause is deferred to M2
    entries = [("macro/a", ok), ("macro/b", later), ("macro/macro_m2_risk/test_cap", clause), ("engine/c", lambda: None)]
    assert [n for n, _ in run_all.select(entries, milestone="M0")] == ["macro/a"]
    assert [n for n, _ in run_all.select(entries, milestone="M2")] == ["macro/a", "macro/macro_m2_risk/test_cap"]
    assert [n for n, _ in run_all.select(entries, milestone="M10")] == ["macro/a", "macro/b", "macro/macro_m2_risk/test_cap"]
    assert [n for n, _ in run_all.select(entries, suite="engine")] == ["engine/c"]


test_runner_records_not_run_as_a_third_status.test_ids = ["T-HERM-01"]


def test_every_macro_module_runs_alone_under_the_guard():
    """`python -m tests.<module>` (the single-module run) arms the hermetic guard and exits 1 on a FAIL or on no tests:
    every macro module ends with the shared `run_module` main, never an unguarded loop or nothing at all."""
    import io
    from contextlib import redirect_stderr, redirect_stdout
    from tests import macro_acceptance as MA
    tail = ['if __name__ == "__main__":', "    from tests.macro_acceptance import run_module",
            "    raise SystemExit(run_module(globals()))"]
    bad = [p.name for p in sorted((ROOT / "tests").glob("macro_*.py"))
           if p.name != "macro_acceptance.py" and p.read_text(encoding="utf-8").rstrip().splitlines()[-3:] != tail]
    assert not bad, f"modules without the guarded main: {bad}"

    def test_armed():
        assert MA._DEPTH > 0, "guard not armed"

    def test_skipped():
        raise NotRun("REFDATA: probe")

    def test_broken():
        raise ValueError("boom")

    with redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()):
        codes = [MA.run_module({"test_armed": test_armed, "test_skipped": test_skipped}),
                 MA.run_module({"test_armed": test_armed, "test_broken": test_broken}), MA.run_module({"helper": test_armed})]
    assert codes == [0, 1, 1], (codes, out.getvalue())
    assert "PASS test_armed" in out.getvalue() and "NOT_RUN test_skipped REFDATA: probe" in out.getvalue()


test_every_macro_module_runs_alone_under_the_guard.test_ids = ["T-HERM-01"]


def test_gate_bootstrap_b_is_not_leaked_by_the_expansion_suite():
    """expansion/gate_noise_vs_edge sets GATE['bootstrap_B'] = 300; it must be restored before any later suite."""
    from core.quant import validate as V
    assert V.GATE["bootstrap_B"] == 2000, V.GATE["bootstrap_B"]
    src = (ROOT / "tests" / "expansion_acceptance.py").read_text(encoding="utf-8")
    assert re.search(r"finally:\s*\n\s*V\.GATE\[\"bootstrap_B\"\] = saved_b", src), "GATE restore missing"


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
