"""Golden-fixture generator and md5 freeze (TASK-M1-22; spec L22, L5492, L1493 (5), L6018; brief
spec_goldens_fixtures B.9, D.1; rulings section 6).

Run:  python docs/macro_fixtures.py --reference /home/claude/quantgen_macro_data --retrieved-at-utc 2026-10-02T09:00:00Z
          --licence "<licence>" --owner "<owner>" [--out tests/fixtures/macro] [--manifest tests/fixtures/macro/MANIFEST.csv]

Reads every reference file of D.1 through the data layer's provenance contract, writes one fixture per manifest row
("values unchanged; provenance fields and value_status added"), computes its md5 and appends the manifest rows.
It refuses, listing every missing file, when the reference directory or any file is absent (it is absent on this
machine: every golden that needs them stays NOT_RUN). A regeneration before the M7 freeze must reproduce the same
md5s or is a fixture change logged in the manifest with the tests it re-baselines (L5492): `freeze` refuses a row
whose md5 differs from the listed one instead of overwriting it.

No clock is read here: `retrieved_at_utc` is an argument (the retrieval instant recorded in CATALOG.md).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.notrun import MANIFEST, MANIFEST_COLUMNS, load_manifest, md5_of  # noqa: E402

PROVENANCE_FIELDS = ("series_id", "obs_date", "session_date", "obs_utc", "available_at_utc", "available_at_source",
                     "retrieved_at_utc", "value_status", "vintage", "content_hash")       # section 4.1 L1274-1281
VALUE_STATUSES = ("official_close", "vendor_close", "live_snapshot", "provisional_intraday", "first_release",
                  "revised", "vendor_derived", "vendor_derived_across_gap")               # L1280, schema L3639
AVAILABLE_AT_SOURCES = ("published", "calendar_bound", "inferred_from_retrieval")       # L3642
FRED_IDS = ("DGS10", "DEXKOUS", "DTWEXBGS", "NASDAQ100", "DTB3", "DEXJPUS", "PCEPILFE", "PCEPI", "CPIAUCSL", "CPILFESL",
            "UNRATE", "SAHMREALTIME", "THREEFYTP10", "BAMLH0A0HYM2", "BAA10Y", "DCOILBRENTEU", "USEPUINDXD")

# (fixture id, path under the reference directory, series, value_status, available_at_source, market, tests) — D.1.
# Backfilled history is `calendar_bound`, never `inferred_from_retrieval` (L1278). Result tables carry no rows of
# their own provenance: they are copied byte-for-byte and md5-listed.
REFERENCE_FILES: tuple[tuple[str, str, str, str, str, str, str], ...] = (
    ("F01", "krx_kospi_official_close_1997-01-03_2026-10-02.csv", "KOSPI_OFFICIAL_CLOSE", "official_close", "calendar_bound", "KR", "I-16;T-SAT-01;T-RLAYER-01;T-PRINT-01;I-01;I-11;G-POST-01"),
    ("F02", "ecos_bok_call_rate_1997_2026-10.csv", "BOK_CALL_RATE", "first_release", "published", "KR", "I-16;T-ROLE-02;T-EXCESS-01"),
    ("F03", "kodex200_price.csv", "KODEX200_PRICE", "official_close", "calendar_bound", "KR", "T-CAPS-01;G-POST-01"),
    ("F04", "kodex_inav.csv", "KODEX200_INAV", "live_snapshot", "published", "KR", "T-FILL-01;T-FILL-02;T-FILL-03"),
    ("F05", "krx_snapshots_1519.csv", "KRX_SNAPSHOT_1519", "live_snapshot", "published", "KR", "T-FILL-01;T-FILL-02;T-FILL-03;T-BAR-01"),
    ("F06", "krx_daily_opens.csv", "KRX_DAILY_OPEN", "official_close", "calendar_bound", "KR", "T-BAR-01;T-BOOK-02"),
    ("F07", "fred_VIXCLS_VXVCLS_2007-12-04_2026-09-30.csv", "VIXCLS;VXVCLS", "vendor_close", "calendar_bound", "US", "G-R08-01;G-R08-02;T-ANNOT-01;T-VIX-01;G-STALE-01"),
    ("F08", "sox_daily.csv", "SOX", "vendor_close", "calendar_bound", "US", "T-PLACEBO-01"),
    ("F09", "trend_indices_daily.csv", "N225;HSI;DAX;FTSE;TAIEX;KOSDAQ", "vendor_close", "calendar_bound", "JP", "G-TR-04"),
    ("F10", "french_daily_mom_1990-01-02_2026-08-31.csv", "FRENCH_MOM_D", "vendor_derived", "published", "US", "G-MOM-01;G-MOM-02;G-MOM-03;G-MOM-04;G-MOM-06;G-MOM-08;G-YRS-01;G-DSR-02;T-R03-01"),
    ("F10", "french_daily_strev.csv", "FRENCH_STREV_D", "vendor_derived", "published", "US", "G-BOOK-01"),
    ("F10", "french_daily_5f_2x3.csv", "FRENCH_MKTRF_D;FRENCH_RF_D;FRENCH_RMW_D", "vendor_derived", "published", "US", "G-BOOK-01;G-US-01;U1"),
    ("F10", "french_daily_regional_mom.csv", "FRENCH_MOM_JP;FRENCH_MOM_EU;FRENCH_MOM_APXJ;FRENCH_MOM_DEVXUS", "vendor_derived", "published", "US", "G-INTL-01"),
    ("F11", "french_monthly_ff_1926-07_2026-08.csv", "FRENCH_FF_M", "vendor_derived", "published", "US", "G-MOM-03;G-MOM-04;G-MOM-05;G-TR-01;G-TR-02;G-TR-03;T-TREND-02"),
    ("F13", "yahoo_KS11_1996-12_2026-10-02.csv", "KS11", "vendor_close", "calendar_bound", "KR", "G-KR-01;G-KR-02;G-KR-02b;G-KR-02c;G-KR-03;G-KR-04;G-POST-01;T-VT-01;T-LABEL-01;T-COST-01;I-02;I-07"),
    ("F14", "yahoo_GSPC_1990_2026-10-01.csv", "GSPC", "vendor_close", "calendar_bound", "US", "U1;G-EST-01;G-EST-02;G-EST-03;G-TR-04;T-CORR-01;T-TZ-01"),
    ("F15", "yahoo_SPY_2015-12_2026-10-01.csv", "SPY", "vendor_close", "calendar_bound", "US", "G-B5-02"),
    ("F16", "yahoo_KRWX_2004_2026-10-01.csv", "KRWX", "vendor_close", "calendar_bound", "FX", "G-POST-01;G-REF-01"),
    ("F17", "yahoo_TNX_2015_2026-10-01.csv", "TNX", "vendor_close", "calendar_bound", "US", "G-US-03;G-REF-02"),
    ("F17", "yahoo_RUT_2015_2026-10-01.csv", "RUT", "vendor_close", "calendar_bound", "US", "G-US-04"),
    *(("F18", f"fred_snapshot_2026-10-02/{fid}.csv", fid, "first_release", "calendar_bound", "US", "G-STALE-01;T-H15-01;T-H10-02;T-MISS-01;G-US-02;G-REF-02") for fid in FRED_IDS),
    ("F19", "px2_cash_IRSTCI01KRM156N_monthly.csv", "IRSTCI01KRM156N", "first_release", "published", "KR", "T-EXCESS-01;I-09"),
    ("F20", "results/QX_DLA_postpatch.csv", "", "", "", "", "G-POST-01;T-FIX-01"),
    ("F21", "results/QX_DLA_korea_grid.csv", "", "", "", "", "G-KR-L01;G-KR-L02;G-KR-L03;G-KR-L04;G-KR-L05;G-KR-L06;G-KR-L07;G-KR-L08;I-07"),
    ("F22", "results/QX_EX1_qf3_trial_corr_diff.csv", "", "", "", "", "T-NEFF-01"),
    *(("F23", f"results/{name}.csv", "", "", "", "", "G-DSR-02;G-YRS-01;G-TR-01;G-PWR-01;G-PWR-02;G-R08-01;G-EST-01")
      for name in ("QX_DLB_r03_dsr", "QX_DLB_r03_years", "QX_DLB_trend_cards", "QX_DLB_power_se", "QX_DLB_power_sim", "QX_DLB_r08")),
    ("F24", "results/QX_DLA_ladder.csv", "", "", "", "", "G-LAD-01;G-LAD-02;G-LAD-03"),
    ("F27", "krx_005930_000660_closes_mcap.csv", "005930;000660", "official_close", "calendar_bound", "KR", "G-POST-01;T-FILL-02"),
    ("F28", "treasury_par_yield_daily_posting_times.csv", "UST_PAR_YIELD", "first_release", "published", "US", "G-US-02a;G-REF-02;T-H15-01"),
)
CATALOG = "CATALOG.md"


class ReferenceMissing(FileNotFoundError):
    """The reference directory or some of its files are absent; `.missing` lists them."""

    def __init__(self, ref_dir: Path, missing: list[str]) -> None:
        self.ref_dir, self.missing = ref_dir, missing
        lines = "\n".join(f"  {m}" for m in missing)
        super().__init__(f"refused: reference directory {ref_dir} is {'absent' if not ref_dir.is_dir() else 'incomplete'}; "
                         f"{len(missing)} file(s) missing, no fixture generated:\n{lines}")


class FixtureChanged(ValueError):
    """A regenerated fixture's md5 differs from the frozen one (L5492): log the change, never overwrite silently."""


def missing_files(ref_dir: Path) -> list[str]:
    names = [CATALOG] + [rel for _, rel, *_ in REFERENCE_FILES]
    return [n for n in names if not (ref_dir / n).is_file()]


def _refuse_available_at(series_id: str, obs_date: date, value_status: str):
    # The library default refuses: the CLI injects `calendar_available_at(...)`; no instant is inferred from retrieval (L1278).
    raise RuntimeError("available_at(series_id, obs_date, value_status) -> (obs_utc, available_at_utc) must be injected "
                       "from core.calendars; no instant is inferred from retrieval")


def calendar_available_at(registry, clocks):
    """`available_at(series_id, obs_date, value_status) -> (obs_utc, available_at_utc)` from the signed calendars:
    a close is observed at the scheduled close and available at its close-print bound (`calendar_bound`); a
    published series at its publication instant. A series with no scheduled instant (live quote, as posted) is
    refused: backfilled history is never `inferred_from_retrieval`. `clocks` is `core.calendars.adapter.CalendarClocks`."""
    def available_at(series_id: str, obs_date: date, value_status: str):
        if not registry.is_series(series_id):
            raise KeyError(f"{series_id}: not a registered series id (every fixture series is named)")
        if registry.obs_kind(series_id) == "close":
            market = registry.market(series_id)
            return clocks.decision_time_utc(market, obs_date), clocks.close_print_bound_utc(market, obs_date)
        due = clocks.publication_instant(series_id, obs_date)
        if due is None:
            raise ValueError(f"{series_id}: no scheduled publication instant; a fixture row never infers one from retrieval")
        return due, due
    return available_at


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("instants must be tz-aware UTC")
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _content_hash(values: list[str]) -> str:
    return hashlib.md5("\x1f".join(values).encode("utf-8")).hexdigest()


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def fixture_rows(src: Path, *, series_id: str, value_status: str, available_at_source: str, retrieved_at_utc: datetime,
                 available_at=_refuse_available_at) -> tuple[list[str], list[dict]]:
    """Reference rows with the section 4.1 provenance fields appended; values are copied unchanged."""
    if value_status not in VALUE_STATUSES or available_at_source not in AVAILABLE_AT_SOURCES:
        raise ValueError(f"{src.name}: value_status {value_status!r} / available_at_source {available_at_source!r}")
    with src.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        fields = list(reader.fieldnames or ())
        if not fields:
            raise ValueError(f"{src.name}: no header")
        date_col = fields[0]
        rows = []
        retrieved = _iso(retrieved_at_utc)
        for raw in reader:
            obs = date.fromisoformat(raw[date_col].strip()[:10])
            obs_utc, avail_utc = available_at(series_id, obs, value_status)
            row = dict(raw)
            row.update({"series_id": series_id, "obs_date": obs.isoformat(), "session_date": obs.isoformat(), "obs_utc": _iso(obs_utc),
                        "available_at_utc": _iso(avail_utc), "available_at_source": available_at_source,
                        "retrieved_at_utc": retrieved, "value_status": value_status,
                        "vintage": retrieved[:10], "content_hash": _content_hash([raw[c] for c in fields])})
            rows.append(row)
    return fields + list(PROVENANCE_FIELDS), rows


def generate(ref_dir: Path, out_dir: Path, *, retrieved_at_utc: datetime, licence: str, owner: str,
             available_at=_refuse_available_at, check_fixture=None) -> list[dict]:
    """Write every fixture under `out_dir`; return its manifest rows (S1's ten columns). Refuses when any reference
    file is absent. `check_fixture(path)` (core/ficc/pit.check_fixture, T-FIX-01) runs on every close-type fixture."""
    ref_dir, out_dir = Path(ref_dir), Path(out_dir)
    missing = missing_files(ref_dir)
    if missing:
        raise ReferenceMissing(ref_dir, missing)
    if not licence.strip() or not owner.strip():
        raise ValueError("licence and owner are required: a file without them is not a fixture (L6035)")
    rows_out = []
    for fid, rel, series, value_status, source, _market, tests in REFERENCE_FILES:
        src, dst = ref_dir / rel, out_dir / Path(rel).name
        if value_status:                                       # data file: provenance added
            fields, rows = fixture_rows(src, series_id=series.split(";")[0], value_status=value_status,
                                        available_at_source=source, retrieved_at_utc=retrieved_at_utc,
                                        available_at=available_at)
            buf = []
            writer = csv.DictWriter(_Buf(buf), fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
            _atomic_write(dst, "".join(buf))
            span = f"{rows[0]['obs_date']}..{rows[-1]['obs_date']}" if rows else ""
            rule = f"{value_status}; available_at_source = {source}"
            if check_fixture is not None and value_status in ("official_close", "vendor_close", "live_snapshot"):
                check_fixture(dst)
        else:                                                  # result table: copied byte-for-byte
            _atomic_write(dst, src.read_text(encoding="utf-8"))
            span, rule = "result table", "result table; not an acting input"
        rows_out.append({"file": dst.name, "source": f"/home/claude/quantgen_macro_data/{rel} ({fid}, per CATALOG.md)",
                         "series": series, "span": span, "retrieved_at_utc": _iso(retrieved_at_utc),
                         "value_status_rule": rule, "md5": md5_of(dst), "licence": licence, "owner": owner,
                         "tests": tests})
    return rows_out


class _Buf:
    def __init__(self, parts): self.parts = parts
    def write(self, s): self.parts.append(s)


def freeze(manifest: Path, rows: list[dict]) -> int:
    """Append the rows the manifest lacks; a listed file whose md5 differs raises FixtureChanged (L5492); an
    identical row is left alone. Returns the number of rows appended."""
    manifest = Path(manifest)
    listed = load_manifest(manifest) if manifest.is_file() else {}
    changed = [f"{r['file']}: {listed[r['file']]['md5']} -> {r['md5']}" for r in rows
               if r["file"] in listed and listed[r["file"]]["md5"].lower() != r["md5"].lower()]
    if changed:
        raise FixtureChanged("regeneration does not reproduce the frozen md5 (a fixture change must be logged in the "
                             "manifest with the tests it re-baselines, L5492): " + "; ".join(changed))
    new = [r for r in rows if r["file"] not in listed]
    text = manifest.read_text(encoding="utf-8") if manifest.is_file() else ",".join(MANIFEST_COLUMNS) + "\n"
    if not text.endswith("\n"):
        text += "\n"
    buf: list[str] = []
    csv.DictWriter(_Buf(buf), fieldnames=MANIFEST_COLUMNS, lineterminator="\n").writerows(new)
    _atomic_write(manifest, text + "".join(buf))
    return len(new)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--reference", required=True, help="the frozen reference directory (/home/claude/quantgen_macro_data)")
    p.add_argument("--out", default=str(MANIFEST.parent))
    p.add_argument("--manifest", default=str(MANIFEST))
    p.add_argument("--retrieved-at-utc", default=None, help="ISO-8601 UTC instant of the retrieval (from CATALOG.md)")
    p.add_argument("--licence", default="")
    p.add_argument("--owner", default="")
    args = p.parse_args(argv)
    ref = Path(args.reference)
    missing = missing_files(ref)
    if missing:
        print(ReferenceMissing(ref, missing))
        return 2
    if not args.retrieved_at_utc:
        p.error("--retrieved-at-utc is required when generating")
    retrieved = datetime.strptime(args.retrieved_at_utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    from core.calendars.adapter import CalendarClocks            # the shipped set: refuses until the owner signs
    from core.ficc import contracts, pit
    registry, clocks = contracts.default_registry(), CalendarClocks()
    rows = generate(ref, Path(args.out), retrieved_at_utc=retrieved, licence=args.licence, owner=args.owner,
                    available_at=calendar_available_at(registry, clocks),
                    check_fixture=lambda p: pit.check_fixture(p, registry=registry, clocks=clocks))
    added = freeze(Path(args.manifest), rows)
    print(f"{len(rows)} fixtures written under {args.out}; {added} manifest rows appended to {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
