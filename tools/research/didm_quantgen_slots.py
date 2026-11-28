"""Fetch explicitly queued GDELT files with an owner's QUANTGEN interpreter.

Launched by didm_run_log only for the official collect_daily module invocation.
The upstream newest/day CLI cannot name individual files in a partial backfill.
Use its GDELT API and persist rows before reporting any completed file pair.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys


def main(args):
    if not 3 <= len(args) <= 10:
        return 2
    repository, folder, *stamps = args
    root = Path(repository).resolve(strict=True)
    destination = Path(folder).resolve(strict=True)
    if (not (root / "tools/didm/collect_daily.py").is_file()
            or destination.is_relative_to(root) or len(set(stamps)) != len(stamps)):
        return 2
    for stamp in stamps:
        try:
            dt = datetime.strptime(stamp, "%Y%m%d%H%M%S")
        except ValueError:
            return 2
        if dt.strftime("%Y%m%d%H%M%S") != stamp or dt.minute % 15 or dt.second:
            return 2

    sys.path.insert(0, str(root))
    from tools.didm import collect_daily as collector
    from data.didm import gdelt

    with collector.PointInTimeStore(destination / "didm_store.sqlite") as store:
        for stamp in stamps:
            try:
                rows, fetched, missing = collector.gdelt_ingest.ingest_stamps(
                    gdelt.fetch_bytes_optional, [stamp], collector._now(), kinds=("events", "gkg"))
                collector._stamp_completed_batch(rows)
                added = store.append_many(rows)
            except Exception:
                # A failure for one slot does not alter the receipts for earlier slots.
                continue
            expected = {stamp + ".export.CSV.zip", stamp + ".gkg.csv.zip"}
            if len(fetched) == 2 and set(fetched) == expected and not missing:
                print(f"GDELT backfill files 2 ({stamp}:events, {stamp}:gkg), "
                      f"rows {len(rows)}, new {added}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
