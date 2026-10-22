"""US-session backtest (exploratory, 2026-10-20): the six current paper accounts with the 10-18/19/20 fixes,
replayed over the last ~60 days of US sessions in the NYSE regular session (13:30-20:00 UTC, EDT). The window is
set in memory only: paper_live/engine.py and config.py are not edited, so the frozen H2 rule digests hold.
Sessions are all on or before 2026-10-19, before the H2 freeze, so they never count toward the gate test."""
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
from paper_live import config as C
assert C.PROFILE == "base"
C.WINDOW_START_UTC = datetime(2026, 10, 20, 13, 30, tzinfo=timezone.utc)   # replay keeps days before this date
C.WINDOW_END_UTC = datetime(2026, 10, 20, 20, 0, tzinfo=timezone.utc)
from paper_live import engine as E, replay as R
digests = __import__("json").loads((E.OUT / "HYPOTHESES_frozen.json").read_text())["digests"]
assert all(E.rule_digest(a) == digests[a["name"]] for a in C.ACCOUNTS), "frozen rule changed"
R.OUTR = E.OUT / "backtest_us_2026-10-20"
orig = R.load
R.load = lambda snapshot=None: orig(snapshot or "us_backtest_5m_60d_20261020")
print("window", R.WS, R.WE, "->", R.OUTR, flush=True)
R.main()
