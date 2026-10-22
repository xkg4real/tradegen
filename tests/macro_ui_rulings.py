"""The Macro page reads the effective rules store: owner rulings in governance_events.jsonl are replayed (S1),
so the D1-D6 table never shows `default` for a decision the owner has ruled on (Sprint 9 review)."""
from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from core.rules import macro_rules as R


def test_owner_items_replay_owner_rulings_from_the_macro_dir():
    from ui import macro_state_panel as P
    saved = os.environ.get("TRADEGEN_MACRO_DIR")
    with tempfile.TemporaryDirectory() as tmp:
        try:
            os.environ["TRADEGEN_MACRO_DIR"] = tmp
            before = {d["decision"]: d for d in P.owner_items()["decisions"]}
            assert before["D2"]["status"] == "default"
            R.apply_owner_ruling(R.SHIPPED_STORE_PATH, Path(tmp) / "governance_events.jsonl", "D2", "-1.5*sigma_book",
                                 "owner", lambda: datetime(2026, 10, 7, tzinfo=timezone.utc))
            after = {d["decision"]: d for d in P.owner_items()["decisions"]}
            assert after["D2"]["status"] == "owner_set" and after["D2"]["value"] == "-1.5*sigma_book", after["D2"]
            assert after["D1"]["status"] == "default"
        finally:
            if saved is None:
                os.environ.pop("TRADEGEN_MACRO_DIR", None)
            else:
                os.environ["TRADEGEN_MACRO_DIR"] = saved


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
