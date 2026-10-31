"""Read-only input regressions; every adversarial edit is in a temporary tree.

These tests never calculate strategy performance or modify the real caches.
"""
from __future__ import annotations

from contextlib import contextmanager
import csv
import hashlib
import io
import json
from pathlib import Path
import shutil
import tempfile

from research_lab import data
from tests.compliance_fixtures import directory_link


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "research_lab/data_manifest.json"


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


@contextmanager
def _tree(assets=("SPY",)):
    """Copy only declared public inputs; nothing points back to the originals."""
    original_manifest = (ROOT / MANIFEST).read_bytes()
    manifest = json.loads(original_manifest)
    original_hashes = {}
    with tempfile.TemporaryDirectory(prefix="tradegen_research_data_") as folder:
        home = Path(folder).resolve()
        target = home / MANIFEST
        target.parent.mkdir(parents=True)
        target.write_bytes(original_manifest)
        for asset in assets:
            relative = manifest["selection"][asset]["path"]
            assert relative.startswith("docs/asset_expansion/cache/") and ".." not in Path(relative).parts
            source = ROOT / relative
            original_hashes[relative] = _sha(source.read_bytes())
            target = home / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        try:
            yield home, manifest
        finally:
            assert (ROOT / MANIFEST).read_bytes() == original_manifest
            for relative, fingerprint in original_hashes.items():
                assert _sha((ROOT / relative).read_bytes()) == fingerprint


def _save(home, manifest, *, fingerprints=True):
    if fingerprints:
        manifest["inventory_sha256"] = _sha(_canonical(manifest["inventory"]))
        manifest["selection_sha256"] = _sha(_canonical(manifest["selection"]))
    (home / MANIFEST).write_text(json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def _rows(home, manifest, asset="SPY"):
    path = home / manifest["selection"][asset]["path"]
    return path, list(csv.reader(io.StringIO(path.read_text(), newline="")))


def _rewrite_rows(home, manifest, rows, asset="SPY", *, rebind_selected=False):
    """Rehash a corrupted fixture so semantic checks, not just raw SHA, run."""
    item = manifest["selection"][asset]
    path = home / item["path"]
    stream = io.StringIO(newline="")
    csv.writer(stream, lineterminator="\n").writerows(rows)
    raw = stream.getvalue().encode()
    path.write_bytes(raw)
    item["source_sha256"] = _sha(raw)
    inventory = next(row for row in manifest["inventory"] if row["path"] == item["path"])
    inventory["sha256"] = _sha(raw)
    inventory["bytes"] = len(raw)
    inventory["rows"] = len(rows) - 1
    if rebind_selected:
        selected = [row for row in rows[1:] if row[0] <= data.CUTOFF]
        item["rows"] = len(selected)
        item["start"], item["end"] = selected[0][0], selected[-1][0]
        item["selected_rows_sha256"] = _sha(_canonical(selected))
    _save(home, manifest)


def _refused(call, containing=""):
    try:
        call()
    except ValueError as exc:
        assert containing in str(exc), str(exc)
        return
    raise AssertionError("invalid research data accepted")


def test_fixed_universe_cutoff_currencies_and_one_manifest_snapshot():
    with _tree(data.ASSETS) as (home, manifest):
        loaded = data.load_assets(root=home)
        assert tuple(loaded) == ("SPY", "QQQ", "GLD", "TLT", "TIGER200", "BTC_KRW", "BTC_USDT", "ETH_USDT")
        assert {item["data_manifest_sha256"] for item in loaded.values()} == {data.manifest_digest(root=home)}
        for asset, item in loaded.items():
            assert type(item["dates"]) is tuple and type(item["close"]) is tuple
            assert len(item["dates"]) == len(item["close"]) == manifest["selection"][asset]["rows"]
            assert item["dates"][-1] == ("2026-09-23" if asset == "TIGER200" else "2026-09-24")
            assert item["source_sha256"] == manifest["selection"][asset]["source_sha256"]
            assert "Previously inspected" in item["prior_use"]
        assert loaded["SPY"]["currency"] == "USD" and loaded["SPY"]["annualization"] == 252
        assert loaded["TIGER200"]["currency"] == "KRW" and loaded["TIGER200"]["annualization"] == 252
        assert loaded["BTC_KRW"]["currency"] == "KRW" and loaded["BTC_KRW"]["annualization"] == 365
        assert loaded["BTC_USDT"]["currency"] == loaded["ETH_USDT"]["currency"] == "USDT"
        assert loaded["SPY"]["adjustment_status"] == "provider_adjusted_close"
        assert loaded["BTC_KRW"]["adjustment_status"] == "unadjusted_spot_close"


def test_raw_byte_tampering_is_rejected_before_numeric_parsing():
    with _tree() as (home, manifest):
        path, _ = _rows(home, manifest)
        path.write_bytes(path.read_bytes() + b"\n")
        _refused(lambda: data.load_series("SPY", root=home), "source hash mismatch")


def test_filtered_row_fingerprint_tampering_cannot_change_the_evaluation_sample():
    with _tree() as (home, manifest):
        manifest["selection"]["SPY"]["selected_rows_sha256"] = "0" * 64
        _save(home, manifest)
        _refused(lambda: data.load_series("SPY", root=home), "filtered-row fingerprint mismatch")


def test_manifest_inventory_and_selection_fingerprints_are_required():
    for field in ("inventory_sha256", "selection_sha256"):
        with _tree() as (home, manifest):
            manifest[field] = "0" * 64
            _save(home, manifest, fingerprints=False)
            _refused(lambda: data.load_series("SPY", root=home), "fingerprint mismatch")
    with _tree() as (home, manifest):
        manifest["selection"]["SPY"]["rows"] -= 1
        _save(home, manifest, fingerprints=False)
        _refused(lambda: data.load_series("SPY", root=home), "fingerprint mismatch")


def test_duplicate_keys_and_nonfinite_manifest_constants_are_rejected():
    with _tree() as (home, _):
        path = home / MANIFEST
        raw = path.read_text()
        path.write_text(raw.replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1', 1))
        _refused(lambda: data.load_series("SPY", root=home), "duplicate")
        path.write_text(raw.replace('"schema_version": 1', '"schema_version": NaN', 1))
        _refused(lambda: data.load_series("SPY", root=home), "nonfinite")
        path.write_text("{not valid JSON}")
        _refused(lambda: data.load_series("SPY", root=home), "invalid research manifest JSON")


def test_self_consistent_fixture_hashes_do_not_legalize_bad_close_values():
    # The external protocol pins the manifest itself. Rebinding here deliberately
    # tests independent semantic defenses, not a claim of unforgeable manifests.
    for value in ("NaN", "inf", "-inf", "1e9999", "0", "-1"):
        with _tree() as (home, manifest):
            _, rows = _rows(home, manifest)
            rows[2][1] = value
            _rewrite_rows(home, manifest, rows)
            _refused(lambda: data.load_series("SPY", root=home), "nonpositive, nonfinite or unordered")
    with _tree() as (home, manifest):
        _, rows = _rows(home, manifest)
        rows[2][1] = ""
        _rewrite_rows(home, manifest, rows)
        _refused(lambda: data.load_series("SPY", root=home), "invalid research date or close")


def test_duplicate_unordered_and_invalid_dates_refuse_even_after_raw_rehash():
    for mutation in ("duplicate", "reverse", "invalid"):
        with _tree() as (home, manifest):
            _, rows = _rows(home, manifest)
            if mutation == "duplicate":
                rows[2][0] = rows[1][0]
            elif mutation == "reverse":
                rows[1], rows[2] = rows[2], rows[1]
            else:
                rows[2][0] = "2026-02-30"
            _rewrite_rows(home, manifest, rows)
            _refused(lambda: data.load_series("SPY", root=home))


def test_unlisted_asset_ids_and_metadata_path_currency_or_calendar_changes_refuse():
    with _tree() as (home, _):
        for asset in ("UNKNOWN", "../owner", "SPY.csv", "spy", None, True):
            _refused(lambda asset=asset: data.load_series(asset, root=home), "outside the fixed research universe")
    for field, value in (("path", "../../unlisted.csv"), ("currency", "KRW"),
                         ("annualization", 365), ("adjustment_status", "audited_total_return")):
        with _tree() as (home, manifest):
            manifest["selection"]["SPY"][field] = value
            _save(home, manifest)
            _refused(lambda: data.load_series("SPY", root=home), "metadata mismatch")
    with _tree() as (home, manifest):
        manifest["cutoff_inclusive"] = "2026-09-25"
        _save(home, manifest)
        _refused(lambda: data.load_series("SPY", root=home), "contract or fingerprint mismatch")


def test_real_directory_aliases_cannot_replace_manifest_or_price_roots():
    with _tree() as (home, _):
        original = home / "research_lab"
        moved = home / "actual_manifest"
        original.rename(moved)
        directory_link(original, moved)
        _refused(lambda: data.load_series("SPY", root=home), "linked research manifest")
    with _tree() as (home, _):
        original = home / "docs/asset_expansion/cache"
        moved = home / "actual_cache"
        original.rename(moved)
        directory_link(original, moved)
        _refused(lambda: data.load_series("SPY", root=home), "linked research data")


def test_missing_crypto_day_is_not_filled_after_consistent_metadata_rebinding():
    with _tree(("BTC_KRW",)) as (home, manifest):
        _, rows = _rows(home, manifest, "BTC_KRW")
        del rows[100]
        _rewrite_rows(home, manifest, rows, "BTC_KRW", rebind_selected=True)
        _refused(lambda: data.load_series("BTC_KRW", root=home), "missing crypto daily bar")


def test_any_manifest_byte_change_changes_the_external_protocol_fingerprint():
    with _tree() as (home, _):
        before = data.manifest_digest(root=home)
        path = home / MANIFEST
        path.write_bytes(path.read_bytes() + b"\n")
        after = data.manifest_digest(root=home)
        assert after != before
        assert data.load_series("SPY", root=home)["data_manifest_sha256"] == after
