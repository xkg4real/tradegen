### Task 12: The report: catalogue, statistics, number formats, flags, rendering, language guard (`core/odds/report.py`)

**Files:**
- Modify: `core/odds/report.py` (Task 9's file, 49 lines; this is its last edit: CONTRACT 2 and the header file map
  list Tasks 9 and 12 for it, and Tasks 13, 14, 17 and 18 only call it (O3-10: Task 17 fills `replay` and never edits
  `render`); anchors: the module docstring, the imports and the constants
  `LADDER` and `COST_DOMINATED_SHARE` at the top (Edit 1); the last field `trades` of the class `ColumnStats`, which
  is the last line of the file (Edit 2, which appends the rest of the module); `ColumnStats` itself is not touched;
  LF, kept; a D14 closure file)
- Create: `tests/odds_report.py` (LF; already listed in `tests/odds_acceptance.MODULES` by Task 1)
- Test: `tests/odds_report.py`

**Interfaces:**
- Consumes:
  - Task 5 (`core.odds.plan`): `REFUSALS`, `REPLAY_SOURCE`; `Refusal(code, sub="", slots={}, detail="")`;
    `Series(symbol, source, dates, open, close, adjustment, status, md5, components=(), proxy_dates=None)`;
    `Plan`, `Leg`, `fixed(f)`; `plan_hash(plan) -> str` (raises ValueError or TypeError where
    `model.canonical_json` refuses, for example on a non-finite stake).
  - Task 6 (`core.odds.costs`): `LIMIT_DOWN_CARRY_COST_MULTIPLIER` (2.0).
  - Task 11 (`core.odds.bold`, which imports nothing from `core.odds`, so no cycle): `ceiling_one_in(w0, l_min,
    target) -> int` (exact `floor((target - l_min) / (w0 - l_min))`; ValueError unless finite `l_min < w0 <
    target`); `ceiling(w0, l_min, target) -> float` (tests only).
  - Task 9 (`core.odds.report`, kept unchanged): `LADDER`, `COST_DOMINATED_SHARE`, `ColumnStats` (CONTRACT 10.1's
    fields in that order; `brackets = field(default=None, compare=False, repr=False)`, its two-line comment naming
    contract 10.1 as Task 9 amends it: two columns compare through `dataclasses.replace(col, brackets=None,
    x_range=0.0 if math.isnan(col.x_range) else col.x_range)`, since a nan `x_range` never equals itself).
  - Task 1: `tests/odds_acceptance.py` (`-m tests.odds_acceptance <pattern>`, every test wrapped hermetic in a temp
    home).
  - `scipy.stats.beta.ppf` (module); `scipy.stats.binomtest` and numpy (tests only).
- Produces (`core/odds/report.py`; Tasks 13, 14, 17 and 18 rely on these exact names and behaviours):
  - Constants: `CP_LEVEL = 0.95`, `DELTA = 1e-4`, `RED_ALPHA = 0.001`, `CARRY =
    costs.LIMIT_DOWN_CARRY_COST_MULTIPLIER`; `CATALOGUE: Mapping[str, str]` (a `MappingProxyType`; every key of
    CONTRACT 10.4 with its exact text, plus `label.yes` "yes" and `label.no` "no": 193 keys); `BANNED_WORDS`,
    `BANNED_PHRASES` (CONTRACT 10.4).
  - Types (`@dataclass(frozen=True, kw_only=True)`, CONTRACT 10.1 fields in order): `HiddenEdge(status, mean, bound,
    range_, n)`, `Flag(code, level, key, slots)`, `OddsReport(plan_hash, plan_index, plan_count, refused, track,
    stake, target, floor, l_min, horizon_days, n, sizing, model_key, model_slots, columns, headline, spread,
    spread_kind, notes, ceiling, structural_cap, structural_sessions, tax_basis, cost_words_key, hidden, flags,
    assumed, replay, comparison, provenance)`.
  - Statistics: `cp_two_sided(k, n, level=CP_LEVEL) -> tuple[float, float]` (ValueError unless 0 <= k <= n and
    n >= 1); `cp_lower(k, n, level) -> float`; `bernstein(v, r, n, delta=DELTA) -> float`; `hidden_range(*, target,
    phi_buy, phi_sell, kappa_bound, m_max, n_checks, carry=CARRY) -> float` (`kappa_bound` is
    `costs.kappa_bound(...)` with mult applied, phi_buy and phi_sell scenario-scaled; `math.inf` when `carry x
    kappa_bound >= 1`); `replay_range(*, target, a_max, c_max, n_checks) -> float` (`c_max` = the scenario's largest
    daily c, already doubled on stress2x); `hidden_edge(col, *, w0, target, l_min) -> HiddenEdge` (ValueError unless
    target > l_min and w0 > 0; status `not_applicable` for a key starting `assumed` or `tested_replay`, `unavailable`
    for a nan range, `unbounded` for an inf range, else `red_gain` / `red_loss` / `pass`; it passes the module's
    `DELTA` to `bernstein` at call time, so a test may swap `report.DELTA` and restore it);
    `ceiling_cells(cols, ceiling) -> tuple[str, float]` (m = `len(cols)`: the caller passes the no-edge cells only).
  - Formats: `fmt_krw(x)`, `_sf2(x, up)`, `fmt_prob(k, n)`, `fmt_end(p, *, upper)` (ValueError at p <= 0),
    `fmt_ceiling(c)`, `fmt_blind(x)`, `fmt_order(lb, c)` (the format follows `c`; design notes); private
    `_sf2_near(x)`, `_point(p, below_one=True)`, `_pct(x)` (two significant figures below 1%), `_pct_up(x)`,
    `_ceiling_text(rep)` (every rendered `{c}` of a ceiling line and of `cap.p`).
  - `say(key, **slots) -> str` (exactly `CATALOGUE[key].format(**slots)`: KeyError on an unknown key or a missing
    slot; an extra slot is ignored); `guard(text) -> list[str]` (`[]` is clean).
  - `build(**fields) -> OddsReport`: copies `model_slots`, `assumed`, `replay`, `provenance` into read-only
    mappings, makes `columns`, `flags`, `notes` tuples; ValueError when a refused report carries columns, flags,
    `hidden` or `spread`, or an accepted one has duplicate column keys, a `headline` that is not a column key, a
    `spread_kind` outside {other, krx, blocks, none}, or `spread is None` disagreeing with `spread_kind == "none"`;
    TypeError on a missing field.
  - `refusal_report(plan_obj, refusal, *, index=1, count=1, provenance=MappingProxyType({})) -> OddsReport`:
    `plan_hash = plan.plan_hash(plan_obj)` for a `plan.Plan` it can hash, else `""` (None, or a non-finite
    number); no columns, no flags, `n = 0`, `ceiling = nan`, `spread_kind = "none"`, `comparison = (0, 0, 0)`.
  - `flags_for(*, headline, no_edge, engine, hidden, ceiling, structural, target, stake, reference, rule_flags, grey,
    series, okx) -> tuple[Flag, ...]` in CONTRACT 10.1's order (signature exactly the contract's; no `track`, so
    ABOVE_ESTIMATED_REFERENCE and BELOW_RESOLUTION read `headline.reached`: design notes).
  - `render(rep) -> str` (CONTRACT 10.4's order, then `guard`; a hit raises `ValueError("rendered text failed the
    language guard: [...]")`, which the CLI turns into exit 4). `say` reads the module global `CATALOGUE` at call
    time, so a test that swaps `report.CATALOGUE` (save/restore) plants a guard hit (Task 18).
  - Private render helpers (for the record; no other task calls them): `_words`, `_plain_count`, `_ceiling_text`,
    `_target_p`,
    `_structural`, `_spread_text`, `_bugs`, `_typical`, `_average`, `_headline_lines`, `_ladder_lines`,
    `_plain_line`, `_ceiling_line`, `_replay_lines`, `_column_lines`, `_card`, `_why`, `_prov_value`, `_prov_lines`;
    tables `_TAX_KEYS`, `_MEMBER_KEYS`, `_LABEL_KEYS`, `_EDGE_KEYS`, `_RUNG_KEYS`, `_SUB_PREFIX`, `_BASE_RATES`,
    `_NOT_IN`, `_PROV_LINES`, `_PROV_HASHES`, `_PROV_COUNTS`, `_MAPPINGS`, `_SPREAD_KINDS`; regexes `_TOKEN`,
    `_CARD_ID`.
  - What the callers pass (Tasks 13, 14, 17 build reports through `build`; render reads exactly this):
    - `model_slots`: `model.bootstrap` / `model.garch` take `symbol`, `first`, `last`, `rows` (strings, `rows` with
      thousands separators); `model.replay` takes `first`, `last`, `rows`, `block`. An OKX card adds `cap` (the cap
      share as text, for example "10%") and `capkrw` (`fmt_krw(cap x stake)`); render prints `okx.cap` exactly
      when `"cap" in model_slots`.
    - `columns`: keys `no_edge/<member>/base` and `/stress2x`, `delist_30`, `delist_100`, `assumed`,
      `replay_no_edge/base` and `/stress2x`, `tested_replay/base`. Render prints the headline column; then, in
      `columns` order, the headline's own stress column (the headline key with its last part replaced by
      `stress2x`), the delisting columns (their `{symbol}` from `model_slots["symbol"]`), `assumed` and
      `tested_replay/base`. Every other member's columns appear only through `spread`.
    - `spread`: `(lowest two-sided lower bound, highest two-sided upper bound)` over the non-headline base members,
      None exactly when `spread_kind == "none"`; `notes`: `((member, check), ...)`, member a `simulate.MEMBERS`
      name, check one of deterministic, statistical, fit, refit.
    - `assumed`: floats `w`, `p0`, `u`, `nb` (`math.inf` allowed), `resolved`, `theta`. `replay`: floats `y0`,
      `y1`, `cut` (= `1.0 - LIVE_SHARPE_MULTIPLIER`, a fraction), `bench_sr`, `haircut_sr`, `diff`, `ci_lo`,
      `ci_hi`, `fstar` (nan unless the stake is Kelly; `kelly.label` prints when it is finite), `h` (the daily moves
      a held sleeve makes: the checks less one, 29 on a 30-day horizon; Task 17), `growth` and `growth_iid`
      (fractions: `block_growth(R1, block, h) - 1` and `(1 + mean R1)^h - 1`). A report with `replay` set prints
      `replay.noedge` after the model line and `replay.lead`, `replay.growth` at the head of the tested column.
    - `tax_basis` one of `plan.TAX_BASES_OK` (`fx.us` prints for `overseas_22pct_over_2.5m`); `cost_words_key`
      `cost.tax` (KRX_stock_book) or `cost.fees` (Q37).
    - `provenance`: CONTRACT 10.1's keys; `code_signed` a bool; `model` in {bootstrap, garch_t, replay}; `members`
      a tuple of member names; `edge_source` in `plan.EDGE_SOURCES`; `components` and `calendar_md5s` tuples of
      (label or file id, md5); `proxy_dates` None or (first ISO date, last ISO date). A missing or empty value
      leaves its line out.
    - `Refusal.sub`: the catalogue suffix for UNSUPPORTED_PRODUCT (`sub.*`), DATA_INVALID (`data.*`) and
      SCREEN_BLOCKED (`screen.*`); MODEL_CHECK_FAILED names its check in `sub` or in `slots["check"]`. String slots:
      PARTIAL_CHUNK `chunk`; NOT_TRADABLE `venue`, `symbol`; SPECIAL_REGIME and SHORT_HISTORY `symbol`;
      DATA_INVALID sub `stale` `days`; SCREEN_BLOCKED sub `row` `row`; ASSUMED_EDGE_UNREACHABLE `w`. `detail` never
      renders.
    - `flags_for`: `hidden` = `hidden_edge(headline, w0=stake, target=target, l_min=l_min)` or None (then no
      HIDDEN_EDGE flag); `no_edge` = every no-edge cell (members x scenarios; on the replay card its base and
      stress2x), never a delisting or edge column; `structural` = (cap, sessions) or None; `grey` = (row id, cap
      text, auto_off ISO date) per `gate.grey_rows` id; `engine` "bootstrap" | "garch" | "replay".

**Plan decisions used:** Q14 (one catalogue, the guard, render guards its own output, provenance as hashes and
labels, `limits.injected`), Q32 (L_min per sizing, HIDDEN_EDGE, CEILING_BREACH, plain sentence and spread counts,
the average line on `g_se`, outward rounding, `cap.p`, the bug-check clause), Q37 (no plan name, no internal name,
book-based cost words), Q43 (COST_DOMINATED amber at 10% of the stake), Q44 (IMPOSSIBLE and no-trade print no
probability of the target), Q46 items 1, 2, 3, 5, 6, 9 (the blind spot rounded down, the bug-check clause only when
true, the ceiling as a percentage from 1%, red flags first, the fresh-seed line, `hidden.unbounded`); Q31 (spread
wording and dropped-member notes), Q38 (the replay card lines), Q29 (the delisting column), Q11 (the OKX cap line),
Q12 (the R note), Q42 (no I/O, no clock). RULINGS O14; RULINGS_ROUND2 R2-4 (`compare.fresh`), R2-7 (the unbounded
wording); RULINGS_ROUND3 O3-10 (193 catalogue keys, `flags_for` reads `headline.reached`, this task renders the
replay card lines).

Covers spec 8 odds items 2 (Bernstein at delta_test 0.05 with 2,000 replications, the hand values, a planted 2 b
flagged red, unavailable for GARCH-t, not applicable to edge columns) and 9 (every report item), and spec 9's "never
prints a probability from a refused run".

Departures from the contract's text (read before Step 3). Each makes a printed claim true or a check stricter. The
controller records them before execution, D1 to D3 in the plan header's "For spec rev 3.3" list (Q46 style) and D4
and D5 as CONTRACT 10.4 errata (O3-10 already rules D3 and D4); until then the executor follows this task text and
does not stop to rule:
- D1 `fmt_order` takes its format from the ceiling `c`, not from `lb` (CONTRACT 10.2 writes `lb < 0.01`). With
  lb >= 1% and c < 0.0001 (a target more than 10,000 times the stake; `check_plan` sets no upper bound), 10.2's
  formula prints the red CEILING_BREACH card's ceiling as "0.00%", against section 0's rule that no text rounds a
  probability to zero. Below 1% both slots print "1 in x.x" (as `fmt_ceiling` does), and the printed order stays
  strict: floor(10/lb) <= 10/lb < 10/c <= ceil(10/c) when lb > c.
- D2 Every rendered ceiling `{c}` (the four ceiling lines, the two assumed ones and `cap.p`) comes from
  `_ceiling_text`, whose "1 in N" below 1% is `bold.ceiling_one_in(stake, l_min, target)`, exact (CONTRACT 9 names
  it as the consumer of that N). 10.2's `fmt_ceiling` floors 1/c of the float ceiling: it prints "1 in 104" for a
  1 in 105 ceiling (11,738 of the N in 100..200,000 come out one low) and "1 in 2,126" for Task 11's exact 2,125, a
  smaller chance than the bound. `fmt_ceiling` keeps 10.2's text; its percentage branch serves `_ceiling_text` from
  1%, and Task 14's calls on its 1,999 and 1,000 fixtures agree with the exact N.
- D3 `flags_for` has no track argument (CONTRACT 10.1), and a compounding card's `reached_outcome` is always 0, so
  from the column alone it cannot tell a compounding card from a moonshot card whose exits all missed T.
  ABOVE_ESTIMATED_REFERENCE and BELOW_RESOLUTION read `headline.reached`
  (10.1 names the plain count, `reached_outcome` on moonshot cards). `reached` is the plain count on compounding
  cards and never below it on moonshot cards, so the amber fires whenever the contract's would, and the bracket
  reference (9.1) is a first-passage value too. The one difference: on a moonshot card where paths touched T but
  every exit missed it (`reached > 0`, `reached_outcome == 0`), the card prints `plain.none` and carries no
  BELOW_RESOLUTION flag. That flag has key "" and never prints, so the text is the same. The tests pin this reading
  (test_below_resolution_rides_on_the_plain_sentence, test_flags_for_emits_each_flag_in_the_contract_order). The
  alternative, a `track` argument in CONTRACT 10.1, would change the `flags_for` calls of Tasks 13, 14 and 17.
- D4 Two catalogue keys beside CONTRACT 10.4's 191: `label.yes` "yes" and `label.no` "no" (193). The `prov.signed`
  line prints the `code_signed` bool, and the rendering rule allows only catalogue labels there. The test pins the
  sha256 of the whole catalogue, computed in the drafting sandbox from an independent extraction of CONTRACT 10.4
  plus these two labels, so any changed character fails it.
- D5 `replay.noedge` prints right after the model line of a replay card. 10.4's render order has no slot for it (a
  gap, not a change); Task 17's test_the_replay_card_renders_its_lines_in_order pins it there.

Design notes (each is a reading inside the contract, none loosens anything):
- `say` is exactly CONTRACT 10.4's `CATALOGUE[key].format(**slots)`: a missing slot is a KeyError, an extra slot is
  ignored. Render passes the whole `model_slots` to the model line, so an OKX card's `cap` and `capkrw` ride there
  (the OddsReport has no other field for them).
- IMPOSSIBLE or no trade (Q44): the structural sentence prints once, in the plain sentence's place (10.4: "ladder;
  plain sentence (or `structural.*`)"), and the headline pair keeps only its floor line, so no line prints a
  probability of the target. Every ladder rung above stake x the structural cap prints `ladder.impossible`, whether
  or not the target itself is above it. After no trade every rung is a structural zero, so the ladder prints only
  its `ladder.spread` line. The IMPOSSIBLE flag is not repeated in the info block.
- The assumed column prints spec 7.5's three sentences unbroken (`assumed.lead`, `assumed.nb` or `assumed.nbmany`,
  `assumed.ceiling`), then its typical and average lines and `hidden.na`; the tested replay column prints
  `replay.lead`, `replay.growth`, its typical and average lines, `ceiling.edge` and `hidden.na`.
- `replay["growth"]` and `replay["growth_iid"]` are fractions: `block_growth(R1, block, h) - 1` and
  `(1 + mean R1)^h - 1` (Task 17 passes exactly these; CONTRACT 10.1's comment "block_growth" means that fraction).
  `h` is the moves a held sleeve makes, the checks less one (Task 17's 29-move reading, a correction of CONTRACT Q38
  and 16.1 for the controller), so the hand figures of test_the_replay_card_lines are Task 17's: "2.9%" against
  "2.6%" over 29 days on a 30-day card. Render prints whatever `h` the caller passes.
- The `model.*` texts end with the same price-check sentence that `flag.openclose` / `flag.closeonly` begin with,
  so a card prints it twice. Both are CONTRACT 10.4's text and render order, and the catalogue sha pins them; a
  change belongs to the controller.
- A reference of 0 (the dynamic programme's grid never reaches T) raises no amber: its slot would print a zero.
- T - L_min inside `flags_for` is `(target - stake) / (1 - ceiling)`, exact algebra for `ceiling = (W0 - L_min) /
  (T - L_min)` (41,979,000.0 for the 42,000 / 21,000 / 42,000,000 card).
- `flag.locked`'s `{many}` and every flag's period words come from render, which knows the horizon.
- `hidden.na` prints under each edge column (`assumed`, `tested_replay/base`) from render; it is not a flag.
- A refused report whose plan cannot be hashed has `plan_hash == ""` and its head prints "(none)" (`edge.none`'s
  word).
- Period words: a 28- to 31-day horizon prints "month" / "months", any other "{h}-day period" / "{h}-day periods".
- Typed rates and shares (`assumed.lead`'s `{w}`, `{p0}`, `{u}`) print through `_pct`: the nearest 0.1% from 1%,
  two significant figures in fixed notation below it ("0.050%", never "0.1%" for every rate from 0.03% to 0.149%,
  never 0.0% for a positive value). Costs, resolutions, session shares and gaps print through `_pct_up` (rounded
  up).
- Provenance lines join their values with " / ", print hashes as 16 hex (a key fingerprint without its "SHA256:"
  prefix), md5 lists with ", " in file order, and never a component label or a calendar file id. `decision_id`,
  `screening_hash` and `plan_hash` are stored but not printed: spec 7.5's provenance list does not hold them, and the
  plan hash prints in the head.
- The number-format test adds n = 20,000 to TASKS' n = 2e5 and 1e6: with k <= 1,000 those two never reach a 1% end,
  so "in both formats" needs the third n.

- [ ] **Step 1: Write the failing tests**

  Create `tests/odds_report.py` (LF, UTF-8, no BOM) with exactly this content:

```python
"""Odds plan Task 12: the report (spec 7.5; contract section 10; O14; R2-4, R2-7; Q14, Q32, Q37, Q43, Q44, Q46).

Every report here is built by hand from ColumnStats, so no path is simulated: the statistics, the number formats,
the flags, the render order, the language guard and the refusal cards are tested on exact inputs."""
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import re
from datetime import date
from types import MappingProxyType

import numpy as np
import scipy
from scipy import stats

from core.odds import bold, costs, plan
from core.odds import report as R

W0, T, L = 42_000.0, 42_000_000.0, 21_000.0
CEIL = (W0 - L) / (T - L)                 # bold.ceiling under floor-protected sizing: 1 in 1,999
STOP_CEIL = W0 / T                        # L_min = 0 under stop-based sizing: 1 in 1,000
N = 20_000
_PROB = re.compile(r"1 in |below about|\d\s?%")
_ZERO = re.compile(r"(?<![\d.,])0(?:\.0+)?%|\b1 in 0\b|\babout 0\b")
_CATALOGUE_SHA256 = "61653f4c829c46bede0996726c64dd2c8320c65c81ce9d723a9053d26f630e98"
_REPLAY = {"y0": 2019.0, "y1": 2026.0, "cut": 1.0 - 0.60, "bench_sr": 0.788830441182887,
           "haircut_sr": 0.7296150117404476, "diff": 0.4271945783845257, "ci_lo": 0.03344352887529298,
           "ci_hi": 0.8346050647267628, "fstar": 1.0, "h": 29.0, "growth": 0.02889, "growth_iid": 0.02613}
_ASSUMED = {"w": 0.55, "p0": 0.4987, "u": 0.0213, "nb": 617.0, "resolved": 5_000.0, "theta": 0.21}
_REFUSALS = (
    ("PARTIAL_CHUNK", "", {"chunk": "200,000"}),
    *(("UNSUPPORTED_PRODUCT", sub, {}) for sub in (
        "venue", "feed", "symbol", "class", "multiple", "tax", "horizon", "start", "track", "numbers", "model",
        "sizing", "fraction", "bracket", "edge", "replay", "file", "comparison")),
    ("MULTI_LEG_UNSUPPORTED", "", {}), ("STATE_UNUSABLE", "", {}), ("STATE_UNUSABLE", "code", {}),
    ("LIMITS_UNSET", "", {}), ("LIMITS_UNSET", "cap", {}), ("CALENDAR_UNSIGNED", "", {}),
    ("CALENDAR_COVERAGE", "", {}),
    *(("DATA_INVALID", sub, {"days": "3"} if sub == "stale" else {}) for sub in (
        "now", "series", "sessions", "empty", "stale")),
    ("SYNTHETIC_REFUSED", "", {}), ("NOT_TRADABLE", "", {"venue": "upbit", "symbol": "BTC"}),
    ("SPECIAL_REGIME", "", {"symbol": "005930"}), ("SHORT_HISTORY", "", {"symbol": "KRW-BTC"}),
    ("CARD_NOT_REPRODUCED", "", {}), ("MODEL_NOT_FOR_LIMITED_VENUE", "", {}), ("COST_DOMINATED", "", {}),
    ("STUCK_AT_START", "", {}),
    *(("SCREEN_BLOCKED", sub, {"row": "KR-OKX-SPOT"} if sub == "row" else {}) for sub in (
        "row", "unsigned", "other")),
    ("ASSUMED_EDGE_UNREACHABLE", "", {"w": "55.0%"}),
    *(("MODEL_CHECK_FAILED", check, {}) for check in ("deterministic", "statistical", "fit")),
    ("MODEL_CHECK_FAILED", "", {"check": "refit"}),
)


def _col(**changes) -> R.ColumnStats:
    """A moonshot no-edge base column of N paths: 4 first passages, three quarters at the floor."""
    fields = dict(key="no_edge/bootstrap/base", member="bootstrap", scenario="base", n=N, reached=4,
                  reached_outcome=4, ended_at_or_above=3, at_floor=15_000, running=4_996, locked_at_horizon=0,
                  rungs=(900, 400, 120, 20, 3), median=21_000.0, p5=21_000.0, mean=41_950.0, mean_se=60.0,
                  mean_cost=50.0, g_se=60.0, kept_lo=21_000.0, kept_hi=21_420.0, x_mean=0.5, x_var=4.0e6,
                  x_range=6.0e6, wins=0, losses=0, unresolved=0, band_edge_share=0.0, band_edge_sessions=0,
                  worst_gap=0.0, trades=N)
    fields.update(changes)
    return R.ColumnStats(**fields)


def _series(proxy_dates=None) -> plan.Series:
    return plan.Series(symbol="KRW-BTC", source="UPBIT", dates=("2026-10-22",), open=(1.0,), close=(1.0,),
                       adjustment="none", status="FINAL", md5="0" * 32, proxy_dates=proxy_dates)


def _prov(**changes) -> dict:
    """Every provenance key of contract 10.1, with labels that hold underscores where the real ones do."""
    prov = {"rules_sha": "1" * 64, "instruments_sha": "2" * 64, "venues_sha": "3" * 64, "state_hash": "4" * 64,
            "owner_seq": 7, "owner_row": "5" * 64, "code_hash": "6" * 64, "code_signed": True,
            "fingerprint": "SHA256:" + "7" * 64, "decision_id": "8" * 64, "screening_hash": "9" * 64,
            "series_md5": "a" * 32, "components": (("upbit_daily KRW-BTC", "b" * 32),), "proxy_dates": None,
            "calendar_sha": "", "calendar_version": "", "calendar_md5s": (), "model": "bootstrap",
            "members": ("bootstrap", "bootstrap_half", "bootstrap_double"), "seed_hex": "c" * 64, "n": N,
            "chunk": 2_000, "numpy": np.__version__, "scipy": scipy.__version__, "cryptography": "49.0.0",
            "edge_source": "none", "repo_anchor": "git:" + "d" * 40, "tree_hash": "e" * 64,
            "comparison_id": "c000001", "run_counter": 1, "plan_hash": "ab" * 32}
    prov.update(changes)
    return prov


def _flags(col: R.ColumnStats, **changes) -> tuple:
    fields = dict(headline=col, no_edge=(col,), engine="bootstrap",
                  hidden=R.hidden_edge(col, w0=W0, target=T, l_min=L), ceiling=CEIL, structural=None, target=T,
                  stake=W0, reference=None, rule_flags=(), grey=(), series=_series(), okx=False)
    fields.update(changes)
    return R.flags_for(**fields)


def _rep(*cols: R.ColumnStats, **changes) -> R.OddsReport:
    """A floor-protected moonshot upbit card built by report.build; the flags follow the headline unless given."""
    cols = cols or (_col(), _col(key="no_edge/bootstrap/stress2x", scenario="stress2x", mean=41_900.0,
                                 mean_cost=100.0))
    head = cols[0]
    fields = dict(plan_hash="ab" * 32, plan_index=1, plan_count=2, refused=None, track="moonshot", stake=W0,
                  target=T, floor=L, l_min=L, horizon_days=30, n=head.n, sizing="floor_safe",
                  model_key="model.bootstrap",
                  model_slots={"symbol": "KRW-BTC", "first": "2016-10-24", "last": "2026-10-22", "rows": "3,650"},
                  columns=cols, headline=head.key, spread=(1.0e-5, 6.0e-4), spread_kind="other", notes=(),
                  ceiling=CEIL, structural_cap=None, structural_sessions=None, tax_basis="crypto_22pct_from_2027",
                  cost_words_key="cost.fees", hidden=R.hidden_edge(head, w0=W0, target=T, l_min=L),
                  flags=_flags(head), assumed=None, replay=None, comparison=(2, 1, 3), provenance=_prov())
    fields.update(changes)
    return R.build(**fields)


def _impossible_rep(cap: float = 95.0595, sessions: int = 16) -> R.OddsReport:
    col = _col(reached=0, reached_outcome=0, ended_at_or_above=0, rungs=(900, 400, 120, 20, 0))
    return _rep(col, structural_cap=cap, structural_sessions=sessions, flags=_flags(col, structural=(cap, sessions)),
                tax_basis="krx_small_holder_exempt", cost_words_key="cost.tax", spread_kind="krx",
                model_slots={"symbol": "069500", "first": "2016-10-24", "last": "2026-10-23", "rows": "2,450"})


def _idle_rep() -> R.OddsReport:
    idle = _col(trades=0, reached=0, reached_outcome=0, ended_at_or_above=0, rungs=(0, 0, 0, 0, 0), at_floor=0,
                running=N, median=W0, p5=W0, mean=W0, mean_cost=0.0, kept_lo=None, kept_hi=None)
    return _rep(idle)


def _assumed_rep(sizing: str = "floor_safe", **assumed) -> R.OddsReport:
    head, edge = _col(), _col(key="assumed", mean=40_000.0, x_range=math.nan)
    if sizing == "floor_safe":
        return _rep(head, edge, assumed={**_ASSUMED, **assumed})
    return _rep(head, edge, assumed={**_ASSUMED, **assumed}, sizing="stop_based", l_min=0.0, ceiling=STOP_CEIL,
                flags=_flags(head, ceiling=STOP_CEIL))


def _replay_rep(**replay) -> R.OddsReport:
    base = _col(key="replay_no_edge/base", member="replay",
                x_range=R.replay_range(target=T, a_max=0.16899731, c_max=0.001, n_checks=30))
    stress = _col(key="replay_no_edge/stress2x", member="replay", scenario="stress2x", mean=41_900.0,
                  mean_cost=100.0)
    tested = _col(key="tested_replay/base", member="replay", mean=44_100.0, x_range=math.nan)
    hidden = R.hidden_edge(base, w0=W0, target=T, l_min=L)
    return _rep(base, stress, tested, model_key="model.replay",
                model_slots={"first": "2019-10-23", "last": "2026-09-25", "rows": "2,530", "block": "10"},
                spread=None, spread_kind="none", hidden=hidden,
                flags=_flags(base, no_edge=(base, stress), engine="replay", hidden=hidden),
                replay={**_REPLAY, **replay}, provenance=_prov(model="replay", members=(),
                                                               edge_source=plan.REPLAY_SOURCE))


def _okx_rep() -> R.OddsReport:
    col = _col(band_edge_sessions=12, band_edge_share=0.0123, worst_gap=0.0456, locked_at_horizon=40,
               mean_cost=4_200.0, mean=37_800.0)
    rule = ((date(2026, 11, 22), "review_by", "KR-OKX-SPOT"), (date(2026, 12, 3), "auto_off", "KR-OKX-SPOT"),
            (date(2026, 12, 5), "effective_until", "KR-OKX-SPOT"))
    flags = _flags(col, reference=1e-6, rule_flags=rule, grey=(("KR-OKX-SPOT", "10.0%", "2026-12-03"),),
                   series=_series(("2021-01-01", "2021-03-04")), okx=True)
    return _rep(col, flags=flags, model_slots={"symbol": "BTC-USDT", "first": "2016-10-24", "last": "2026-10-22",
                                               "rows": "3,650", "cap": "10.0%", "capkrw": "4,200"})


def _refused(code: str, sub: str = "", slots=None, plan_obj=None) -> R.OddsReport:
    return R.refusal_report(plan_obj, plan.Refusal(code=code, sub=sub, slots=slots or {}, detail="internal detail_x"),
                            provenance=_prov())


def _fixture_reports() -> list[R.OddsReport]:
    return [_rep(), _rep(track="compounding"), _rep(horizon_days=10), _impossible_rep(), _idle_rep(),
            _assumed_rep(), _assumed_rep("stop_based"), _replay_rep(), _replay_rep(fstar=math.nan), _okx_rep(),
            _rep(_col(n=10**6, reached=0, reached_outcome=0, ended_at_or_above=0, rungs=(9, 8, 7, 6, 0),
                      at_floor=750_000, running=250_000)),
            _refused("SCREEN_BLOCKED", "row", {"row": "KR-OKX-SPOT"}), _refused("STATE_UNUSABLE", "code")]


def _printed(text: str) -> float:
    """The probability a printed interval end states."""
    if text.startswith("1 in "):
        return 1.0 / float(text[5:].replace(",", ""))
    assert text.endswith("%"), text
    return float(text[:-1]) / 100.0


def _raises(call, exc=ValueError) -> str:
    try:
        call()
    except exc as e:
        return str(e)
    raise AssertionError(f"expected {exc.__name__}")


# --------------------------------------------------------------------------- #
# Types and constants
# --------------------------------------------------------------------------- #
def test_column_stats_fields_are_the_contract_list():
    names = [f.name for f in dataclasses.fields(R.ColumnStats)]
    assert names == ["key", "member", "scenario", "n", "reached", "reached_outcome", "ended_at_or_above",
                     "at_floor", "running", "locked_at_horizon", "rungs", "median", "p5", "mean", "mean_se",
                     "mean_cost", "g_se", "kept_lo", "kept_hi", "x_mean", "x_var", "x_range", "wins", "losses",
                     "unresolved", "brackets", "band_edge_share", "band_edge_sessions", "worst_gap", "trades"], names
    brackets = next(f for f in dataclasses.fields(R.ColumnStats) if f.name == "brackets")
    assert brackets.default is None and brackets.compare is False and brackets.repr is False
    with_arrays = _col(brackets=(np.zeros(3), np.ones(3)))
    assert with_arrays == _col() and dataclasses.replace(with_arrays, brackets=None) == _col()


def test_report_types_and_constants_are_the_contract_ones():
    assert [f.name for f in dataclasses.fields(R.HiddenEdge)] == ["status", "mean", "bound", "range_", "n"]
    assert [f.name for f in dataclasses.fields(R.Flag)] == ["code", "level", "key", "slots"]
    assert [f.name for f in dataclasses.fields(R.OddsReport)] == [
        "plan_hash", "plan_index", "plan_count", "refused", "track", "stake", "target", "floor", "l_min",
        "horizon_days", "n", "sizing", "model_key", "model_slots", "columns", "headline", "spread", "spread_kind",
        "notes", "ceiling", "structural_cap", "structural_sessions", "tax_basis", "cost_words_key", "hidden",
        "flags", "assumed", "replay", "comparison", "provenance"]
    assert (R.CP_LEVEL, R.DELTA, R.RED_ALPHA) == (0.95, 1e-4, 0.001)
    assert R.CARRY == costs.LIMIT_DOWN_CARRY_COST_MULTIPLIER == 2.0
    assert R.LADDER == (1.10, 1.25, 2.0, 10.0) and R.COST_DOMINATED_SHARE == 0.10
    assert R.BANNED_WORDS == ("best", "optimal", "recommended", "safe", "guaranteed", "sure", "ideal", "risk-free",
                              "low-risk", "proven", "should")
    assert R.BANNED_PHRASES == ("worth trying", "good chance", "likely to reach")


# --------------------------------------------------------------------------- #
# Statistics
# --------------------------------------------------------------------------- #
def test_clopper_pearson_at_zero_and_at_63():
    lo, hi = R.cp_two_sided(0, 10**6)
    assert lo == 0.0 and abs(hi - 2.9957277863525433e-06) < 1e-18, hi
    assert abs(hi - (1.0 - 0.05 ** (1.0 / 10**6))) < 1e-12
    assert R.fmt_prob(0, 10**6) == "below about 3 in 1,000,000"
    none = _col(n=10**6, reached=0, reached_outcome=0, ended_at_or_above=0, rungs=(9, 8, 7, 6, 0), at_floor=750_000,
                running=250_000)
    text = R.render(_rep(none))
    assert "this plan never reached KRW 42,000,000 before income tax (below resolution: under about 3 in 1,000,000;" \
        in text
    lo, hi = R.cp_two_sided(63, 10**6)
    assert abs(lo - 4.8411e-05) < 1e-9 and abs(hi - 8.0604e-05) < 1e-9, (lo, hi)
    lo, hi = R.cp_two_sided(5, 5)
    assert math.isclose(lo, float(stats.beta.ppf(0.025, 5, 1)), rel_tol=1e-12) and hi == 1.0
    _raises(lambda: R.cp_two_sided(3, 2))


def test_clopper_pearson_matches_scipy_binomtest():
    for n in (1, 7, 2_000, 200_000):
        for k in sorted(k for k in {1, 2, 3, n // 2, n - 1, n} if 1 <= k <= n):
            ci = stats.binomtest(k, n).proportion_ci(confidence_level=0.95, method="exact")
            lo, hi = R.cp_two_sided(k, n)
            assert math.isclose(lo, ci.low, rel_tol=1e-9, abs_tol=1e-15), (k, n, lo, ci.low)
            assert math.isclose(hi, ci.high, rel_tol=1e-9, abs_tol=1e-15), (k, n, hi, ci.high)


def test_cp_lower_is_the_one_sided_bound():
    assert R.cp_lower(0, 100, 0.95) == 0.0
    for k, n, level in ((1, 100, 0.95), (63, 10**6, 0.95), (63, 10**6, 1.0 - 0.001 / 6)):
        assert R.cp_lower(k, n, level) == float(stats.beta.ppf(1.0 - level, k, n - k + 1))
    assert R.cp_lower(63, 10**6, 1.0 - 0.001 / 6) < R.cp_two_sided(63, 10**6)[0] < R.cp_lower(63, 10**6, 0.95)


def test_bernstein_hand_values():
    assert abs(R.bernstein(1.0, 10.0, 10**6, 1e-4) - 0.004850869883696696) < 1e-15
    assert abs(R.bernstein(0.25, 1.0, 2_000, 0.05) - 0.038213360783937035) < 1e-15
    assert R.bernstein(1.0, 10.0, 10**6) == R.bernstein(1.0, 10.0, 10**6, R.DELTA)


def test_bernstein_false_alarm_rate_at_delta_005_is_at_most_005():
    """2,000 replications of a bounded, skewed, mean-zero X (range 10), each judged by hidden_edge itself at
    delta_test 0.05 (report.DELTA swapped and restored): the alarm rate's upper bound <= 0.05."""
    rng = np.random.default_rng(20261024)
    reps, n = 2_000, 1_000
    x = np.where(rng.random((reps, n)) < 0.1, 9.0, -1.0)
    cols = [_col(n=n, x_mean=float(m), x_var=float(v), x_range=10.0)
            for m, v in zip(x.mean(axis=1), x.var(axis=1, ddof=1))]
    saved = R.DELTA
    try:
        R.DELTA = 0.05
        verdicts = [R.hidden_edge(col, w0=W0, target=T, l_min=L) for col in cols]
    finally:
        R.DELTA = saved
    assert verdicts[0].bound == R.bernstein(cols[0].x_var, 10.0, n, delta=0.05)
    assert R.hidden_edge(cols[0], w0=W0, target=T, l_min=L).bound == R.bernstein(cols[0].x_var, 10.0, n)
    alarms = sum(v.status != "pass" for v in verdicts)
    assert R.cp_two_sided(alarms, reps)[1] <= 0.05, alarms


def test_a_planted_edge_of_twice_the_bound_is_red_with_both_wordings():
    rng = np.random.default_rng(7)
    x = np.where(rng.random(200_000) < 0.1, 9.0, -1.0)
    v, n = float(x.var(ddof=1)), int(x.size)
    b = R.bernstein(v, 10.0, n)
    clean = _col(n=n, x_mean=float(x.mean()), x_var=v, x_range=10.0)
    assert R.hidden_edge(clean, w0=W0, target=T, l_min=L).status == "pass"
    for shift, status, key, words in ((2.0 * b, "red_gain", "hidden.gain", "makes money without any edge"),
                                      (-2.0 * b, "red_loss", "hidden.loss", "loses more than its costs explain")):
        col = _col(n=n, x_mean=float(x.mean()) + shift, x_var=v, x_range=10.0)
        hidden = R.hidden_edge(col, w0=W0, target=T, l_min=L)
        assert hidden.status == status and hidden.bound == b and hidden.n == n, hidden
        flags = _flags(col, hidden=hidden)
        assert (flags[0].code, flags[0].level, flags[0].key) == ("HIDDEN_EDGE", "red", key), flags[0]
        text = R.render(_rep(col, hidden=hidden, flags=flags))
        assert f"BUG CHECK FAILED: this plan {words}" in text and "Do not use these numbers." in text


# --------------------------------------------------------------------------- #
# HIDDEN_EDGE range and wording
# --------------------------------------------------------------------------- #
def test_hidden_range_hand_value_carries_phi_sell_in_the_numerator():
    # k_x = 2 x 0.01; V_max = (1,000 + 2 x 5) / 0.98 x e^0.1; C_max = k_x V_max + 2 x max(3, 5); R = V_max + 10 C_max
    r = R.hidden_range(target=1_000.0, phi_buy=3.0, phi_sell=5.0, kappa_bound=0.01, m_max=0.1, n_checks=10)
    assert math.isclose(r, 1466.803217048658, rel_tol=1e-12), r
    one = R.hidden_range(target=1_000.0, phi_buy=3.0, phi_sell=5.0, kappa_bound=0.01, m_max=0.1, n_checks=10,
                         carry=1.0)
    assert math.isclose(one, 1284.1075251844732, rel_tol=1e-12), one
    assert math.isclose(R.replay_range(target=T, a_max=0.16899731, c_max=0.001, n_checks=30), 50570823.6306,
                        rel_tol=1e-12)


def test_hidden_range_is_unbounded_at_k_x_one_and_says_so():
    just = R.hidden_range(target=T, phi_buy=0.0, phi_sell=0.0, kappa_bound=0.4999, m_max=0.05, n_checks=60)
    assert math.isfinite(just) and just > T
    assert R.hidden_range(target=T, phi_buy=0.0, phi_sell=0.0, kappa_bound=0.5, m_max=0.05, n_checks=60) == math.inf
    col = _col(x_range=math.inf)
    hidden = R.hidden_edge(col, w0=W0, target=T, l_min=L)
    assert hidden.status == "unbounded" and hidden.bound == math.inf
    flags = _flags(col, hidden=hidden)
    assert [(f.level, f.key) for f in flags if f.code == "HIDDEN_EDGE"] == [("info", "hidden.unbounded")]
    text = R.render(_rep(col, hidden=hidden, flags=flags))
    assert "The bug check is unavailable for this plan (no finite range):" in text
    assert "the bug checks are coarser than these ranges" in text


def test_hidden_edge_is_unavailable_for_garch_and_does_not_apply_to_edge_columns():
    garch = _col(key="no_edge/garch_t/base", member="garch_t", x_range=math.nan)
    hidden = R.hidden_edge(garch, w0=W0, target=T, l_min=L)
    assert hidden.status == "unavailable" and math.isnan(hidden.bound)
    flags = _flags(garch, hidden=hidden, engine="garch")
    assert [f.code for f in flags if f.code.startswith("CHECKS") or f.code.startswith("CLOSE")] == \
        ["CLOSE_ONLY_CHECKS"]
    text = R.render(_rep(garch, hidden=hidden, flags=flags, model_key="model.garch"))
    assert "The bug check is unavailable for GARCH-t: a bounded shock does not bound the volatility" in text
    assert "Model: GARCH-t fitted to the daily won returns of KRW-BTC" in text
    loud = dict(x_mean=1e9, x_var=1.0, x_range=10.0)                     # red on any no-edge column
    assert R.hidden_edge(_col(**loud), w0=W0, target=T, l_min=L).status == "red_gain"
    for key in ("assumed", "tested_replay/base"):
        assert R.hidden_edge(_col(key=key, **loud), w0=W0, target=T, l_min=L).status == "not_applicable"
    assert R.render(_assumed_rep()).count("The bug check does not apply to edge columns.") == 1
    assert R.render(_replay_rep()).count("The bug check does not apply to edge columns.") == 1
    _raises(lambda: R.hidden_edge(_col(), w0=W0, target=L, l_min=L))


def test_the_pass_sentence_prints_the_blind_spot_rounded_down_and_the_model_disclaimer():
    hidden = R.HiddenEdge(status="pass", mean=0.0, bound=8_000.3, range_=1.0e9, n=N)
    flags = _flags(_col(), hidden=hidden)
    flag = next(f for f in flags if f.code == "HIDDEN_EDGE")
    assert (flag.level, flag.key) == ("info", "hidden.pass")
    assert dict(flag.slots) == {"b": "8,000", "pct": "19.1%", "m": "1 in 5,247"}, dict(flag.slots)
    assert R.fmt_blind(8_000.3 / 41_979_000.0) == "1 in 5,247" and R.fmt_blind(0.0234) == "2.4 percentage points"
    text = R.render(_rep(hidden=hidden, flags=flags))
    assert "raised the chance of the target by up to 1 in 5,247. It does not test whether the model itself is right." \
        in text and "5,248" not in text
    coarse = R.HiddenEdge(status="pass", mean=0.0, bound=5.0e7, range_=1.0e12, n=N)
    flags = _flags(_col(), hidden=coarse)
    assert [f.key for f in flags if f.code == "HIDDEN_EDGE"] == ["hidden.coarse"]
    text = R.render(_rep(hidden=coarse, flags=flags))
    assert "is too coarse to say anything about the chance of the target. It does not test whether the model" in text
    edge = R.HiddenEdge(status="pass", mean=0.0, bound=41_979_000.0, range_=1.0e12, n=N)     # b == T - L_min exactly
    assert [f.key for f in _flags(_col(), hidden=edge) if f.code == "HIDDEN_EDGE"] == ["hidden.coarse"]


# --------------------------------------------------------------------------- #
# Number formats
# --------------------------------------------------------------------------- #
def test_fmt_end_never_narrows_the_clopper_pearson_interval():
    formats = set()
    for n in (20_000, 200_000, 1_000_000):
        for k in range(1, 1_001):
            lo, hi = R.cp_two_sided(k, n)
            low, high = R.fmt_end(lo, upper=False), R.fmt_end(hi, upper=True)
            assert _printed(low) <= lo and _printed(high) >= hi, (k, n, low, high, lo, hi)
            formats |= {low.endswith("%"), high.endswith("%")}
    assert formats == {True, False}
    lo, hi = R.cp_two_sided(4_700, 200_000)
    assert (R.fmt_end(lo, upper=False), R.fmt_end(hi, upper=True)) == ("2.2%", "2.5%")
    _raises(lambda: R.fmt_end(0.0, upper=False))


def test_k63_renders_the_spec_example():
    assert R.fmt_prob(63, 10**6) == "about 1 in 16,000"
    col = _col(n=10**6, reached=63, reached_outcome=63, ended_at_or_above=50, rungs=(9_000, 5_000, 1_000, 200, 50),
               at_floor=750_000, running=249_937)
    text = R.render(_rep(col))
    assert "this plan reached KRW 42,000,000 before income tax in 63, about 1 in 16,000 (counting noise alone: " \
        "between 1 in 12,000 and 1 in 21,000;" in text


def test_spread_ends_are_outward_and_a_k0_member_prints_below_about():
    lo2, hi9 = R.cp_two_sided(2, N)[0], R.cp_two_sided(9, N)[1]
    a, b = R.fmt_end(hi9, upper=True), R.fmt_end(lo2, upper=False)
    assert _printed(a) >= hi9 and _printed(b) <= lo2
    assert f"; other models give {a} to {b};" in R.render(_rep(spread=(lo2, hi9)))
    text = R.render(_rep(spread=(0.0, hi9), spread_kind="krx"))
    assert f"; the same model with other block lengths gives {a} to below about 3 in 20,000; no second model " \
        "family is available for KRX;" in text
    text = R.render(_rep(spread=(lo2, hi9), spread_kind="blocks",
                         notes=(("garch_t", "deterministic"), ("garch_refit", "refit"))))
    assert f"; the same model with other block lengths gives {a} to {b}; GARCH-t was left out because its " \
        "deterministic check failed; the GARCH-t refit was left out because its refit check failed;" in text
    text = R.render(_rep(spread=None, spread_kind="none", notes=(("bootstrap_half", "statistical"),)))
    assert "; no other model could be run here; the bootstrap at half the block length was left out because its " \
        "statistical check failed;" in text


def test_fmt_ceiling_is_an_upper_bound_in_both_formats():
    assert R.fmt_ceiling(0.6667) == "a 66.7% chance"
    assert R.fmt_ceiling(1.0 / 3.0) == "a 33.4% chance"
    assert R.fmt_ceiling(5.0025e-4) == "1 in 1,999"
    assert R.fmt_ceiling(CEIL) == "1 in 1,999" and R.fmt_ceiling(STOP_CEIL) == "1 in 1,000"
    assert R.fmt_ceiling(0.01) == "a 1.0% chance"
    assert R.fmt_ceiling(1.0 / 1999.6) == "1 in 1,999"           # floor, never round: 1 in 2,000 would understate it


def test_the_ceiling_prints_the_exact_one_in_n():
    """A card's "1 in N" is bold.ceiling_one_in, exact: floor(1 / c) of the float ceiling gives 104 for 1 in 105
    and 2,126 for 1 in 2,125 (a smaller chance than the bound)."""
    target = 105 * W0
    ceiling = bold.ceiling(W0, 0.0, target)
    assert R.fmt_ceiling(ceiling) == "1 in 104" and bold.ceiling_one_in(W0, 0.0, target) == 105
    for k, p in ((4, "about 1 in 5,000."), (200, "at most 1 in 105, the ceiling (the simulated 200 in 20,000 is")):
        col = _col(reached=k, reached_outcome=k)
        hidden = R.hidden_edge(col, w0=W0, target=target, l_min=0.0)
        flags = _flags(col, ceiling=ceiling, target=target, hidden=hidden)
        assert not any(f.code == "CEILING_BREACH" for f in flags), k
        text = R.render(_rep(col, sizing="stop_based", l_min=0.0, target=target, ceiling=ceiling, hidden=hidden,
                             flags=flags))
        assert "No plan without a real edge can beat 1 in 105." in text and "1 in 104" not in text
        assert f"Chance of reaching KRW 4,410,000 before income tax: {p}" in text
    target, low = 89_276_487.5, 7.3
    ceiling = bold.ceiling(W0, low, target)
    assert R.fmt_ceiling(ceiling) == "1 in 2,126" and bold.ceiling_one_in(W0, low, target) == 2_125
    hidden = R.hidden_edge(_col(), w0=W0, target=target, l_min=low)
    text = R.render(_rep(floor=low, l_min=low, target=target, ceiling=ceiling, hidden=hidden,
                         flags=_flags(_col(), ceiling=ceiling, target=target, hidden=hidden)))
    assert "No plan without a real edge that keeps this floor can beat 1 in 2,125." in text and "2,126" not in text


def test_fmt_order_keeps_the_printed_order_of_a_breach():
    assert R.fmt_order(1.0 / 1998.5, 1.0 / 1999.0) == ("1 in 1,998.5", "1 in 1,999.0")
    assert R.fmt_order(0.020001, 0.02) == ("2.01%", "2.00%")
    assert R.fmt_order(0.02, 4.2e-5) == ("1 in 50.0", "1 in 23,809.6")       # the ceiling picks the format
    rng = np.random.default_rng(3)
    for c in rng.uniform(1e-5, 0.2, 500):
        lb = float(c) * (1.0 + float(rng.uniform(1e-9, 1e-3)))
        shown_lb, shown_c = R.fmt_order(lb, float(c))
        assert _printed(shown_lb) > _printed(shown_c), (lb, c, shown_lb, shown_c)
    for lb, c in zip(rng.uniform(0.01, 0.9, 500), rng.uniform(1e-7, 0.01, 500)):    # a far target: lb >= 1% > c
        shown_lb, shown_c = R.fmt_order(float(lb), float(c))
        assert _printed(shown_lb) > _printed(shown_c) and not _ZERO.search(shown_lb + " " + shown_c), (lb, c)


def test_point_estimates_round_to_two_figures_and_never_to_zero():
    assert R._sf2(12_406.38, up=False) == 12_000 and R._sf2(20_656.35, up=True) == 21_000
    assert R._sf2(99.5, up=True) == 100 and R._sf2(99.5, up=False) == 99
    assert R.fmt_prob(1, 10**6) == "about 1 in 1,000,000" and R.fmt_prob(3, N) == "about 1 in 6,700"
    assert R.fmt_prob(4_800, 200_000) == "about 2.4%"
    assert R.fmt_prob(9_999, 10_000) == "above 99.9%" and R.fmt_prob(10_000, 10_000) == "about 100.0%"
    assert R.fmt_krw(41_950.4) == "41,950" and R.fmt_krw(np.float64(-1_234.6)) == "-1,235"
    for n in (1, 2_000, 10**6):
        for k in (0, 1, n // 2, n):
            assert not _ZERO.search(R.fmt_prob(k, n)), (k, n)
    for p in (1e-9, 0.0099, 0.01, 0.5, 1.0):
        for upper in (True, False):
            assert not _ZERO.search(R.fmt_end(p, upper=upper)), (p, upper)


def test_a_no_edge_estimate_above_the_ceiling_without_a_breach_prints_cap_p():
    col = _col(reached=12, reached_outcome=12, ended_at_or_above=11, rungs=(900, 400, 120, 20, 11))
    assert 12 / N > CEIL and R.ceiling_cells((col,), CEIL)[0] == ""        # counting noise, no breach
    text = R.render(_rep(col))
    cap = "at most 1 in 1,999, the ceiling (the simulated 12 in 20,000 is above it only through counting noise)"
    assert f"Chance of reaching KRW 42,000,000 before income tax: {cap}." in text
    assert f"before income tax in 12, {cap} (counting noise alone:" in text
    assert "your target (KRW 42,000,000): at most 1 in 1,999, the ceiling (the simulated 11 in 20,000 is above it" \
        in text
    assert "about 1 in 1,700" not in text and "about 1 in 1,800" not in text
    level = _col(reached=20, reached_outcome=20)                  # k / n equals the ceiling: not above it
    assert 20 / N == STOP_CEIL and R.ceiling_cells((level,), STOP_CEIL)[0] == ""
    text = R.render(_rep(level, sizing="stop_based", l_min=0.0, ceiling=STOP_CEIL,
                         flags=_flags(level, ceiling=STOP_CEIL)))
    assert "Chance of reaching KRW 42,000,000 before income tax: about 1 in 1,000." in text and "at most" not in text


def test_the_bug_check_clause_is_chosen_by_comparison():
    col = _col()
    lo, hi = R.cp_two_sided(col.reached_outcome, col.n)
    finer = R.HiddenEdge(status="pass", mean=0.0, bound=0.5 * (hi - lo) * (T - L), range_=1.0e9, n=N)
    coarser = R.HiddenEdge(status="pass", mean=0.0, bound=2.0 * (hi - lo) * (T - L), range_=1.0e9, n=N)
    text = R.render(_rep(col, hidden=finer, flags=_flags(col, hidden=finer)))
    assert "; the bug check's resolution is printed below, and nothing here covers the model being wrong)" in text
    for hidden in (coarser, None, R.HiddenEdge(status="unavailable", mean=0.0, bound=math.nan, range_=math.nan, n=N)):
        text = R.render(_rep(col, hidden=hidden, flags=_flags(col, hidden=hidden)))
        assert "; the bug checks are coarser than these ranges, and nothing here covers the model being wrong)" \
            in text and "resolution is printed below" not in text


# --------------------------------------------------------------------------- #
# Flags and the card
# --------------------------------------------------------------------------- #
def test_ceiling_breach_amber_and_red_with_m_cells():
    n = 200_000
    quiet = tuple(_col(n=n, reached=200, key=f"no_edge/bootstrap/base{i}") for i in range(9))
    assert R.ceiling_cells((_col(n=n, reached=230),), STOP_CEIL)[0] == "amber"
    assert R.ceiling_cells((_col(n=n, reached=250),), STOP_CEIL) == ("red", R.cp_lower(250, n, 1.0 - 0.001))
    assert R.ceiling_cells((_col(n=n, reached=250), *quiet), STOP_CEIL) == ("amber", R.cp_lower(250, n, 0.95))
    assert R.ceiling_cells((_col(n=n, reached=260), *quiet), STOP_CEIL)[0] == "red"
    assert R.ceiling_cells(quiet, STOP_CEIL) == ("", R.cp_lower(200, n, 0.95))
    assert R.ceiling_cells((), STOP_CEIL) == ("", 0.0)
    for k, level, key, text in ((230, "amber", "breach.amber", "Preliminary evidence, about 5% false-alarm rate"),
                                (250, "red", "breach.red", "Do not use these numbers: a no-edge result beats the "
                                                           "ceiling of 1 in 1,000.0 beyond counting noise")):
        col = _col(n=n, reached=k, reached_outcome=k)
        flags = _flags(col, ceiling=STOP_CEIL)
        breach = [f for f in flags if f.code == "CEILING_BREACH"]
        assert [(f.level, f.key) for f in breach] == [(level, key)], breach
        rendered = R.render(_rep(col, sizing="stop_based", l_min=0.0, ceiling=STOP_CEIL, flags=flags))
        assert text in rendered
        assert "Chance of reaching KRW 42,000,000 before income tax: about" in rendered     # no cap.p after a breach


def test_the_average_line_follows_the_two_g_se_rule():
    agrees = _col(mean=W0 - 50.0 + 1.99 * 60.0, g_se=60.0, mean_se=55.0)     # outside 2 x mean_se, inside 2 x g_se
    text = R.render(_rep(agrees))
    assert "Averaged over all simulated months: about KRW 41,950 (fees average KRW 50; the simulation's own " \
        "average, KRW 42,069 ± 55, agrees). That average includes rare jackpots and is not what usually " \
        "happens." in text
    differs = _col(mean=W0 - 50.0 + 2.01 * 60.0, g_se=60.0, mean_se=55.0)
    text = R.render(_rep(differs))
    assert "The simulation's own average, KRW 42,071 ± 55, does not match your stake minus the average fees " \
        "(KRW 41,950); see the bug check below." in text
    assert "an average gain of KRW 2,100, only if the edge in this column is real." in R.render(_replay_rep())
    assert "an average loss of KRW 2,000, even with the edge in this column." in R.render(_assumed_rep())


def test_typical_result_first_and_red_flags_before_any_number():
    n = 200_000
    col = _col(n=n, reached=250, reached_outcome=250, x_mean=1.0e6)
    hidden = R.hidden_edge(col, w0=W0, target=T, l_min=0.0)
    assert hidden.status == "red_gain"
    flags = _flags(col, ceiling=STOP_CEIL, hidden=hidden)
    lines = R.render(_rep(col, sizing="stop_based", l_min=0.0, ceiling=STOP_CEIL, hidden=hidden,
                          flags=flags)).splitlines()
    assert lines[0] == "Plan 1 of 2 (abababababababab)"
    assert lines[1].startswith("BUG CHECK FAILED: this plan makes money without any edge")
    assert lines[2].startswith("Do not use these numbers: a no-edge result beats the ceiling")
    assert lines[3].startswith("Model: a two-point bootstrap") and lines[4].startswith("Stop-based sizing")

    def at(prefix: str) -> int:
        return next(i for i, line in enumerate(lines) if line.startswith(prefix))
    order = [at("The middle month ends with"), at("In about 7.5% of months you end at your floor"),
             at("Averaged over all simulated months: about"), at("Chance of reaching"),
             at("Chance of ending at your floor"), at("Ended at or above:"), at("In 200,000 made-up months"),
             at("Tax:"), at("No plan without")]
    assert order == sorted(order), order


def test_the_compounding_headline_and_the_period_words():
    col = _col(reached_outcome=0, reached=4, ended_at_or_above=3)
    text = R.render(_rep(col, track="compounding"))
    assert "Was worth KRW 42,000,000 at some price check in 4 of 20,000 made-up months (about 1 in 5,000); ended " \
        "at or above it in 3 (about 1 in 6,700)." in text
    assert "this plan reached KRW 42,000,000 before income tax in 4, about 1 in 5,000" in text
    assert "Ended at or above:\n+10% (KRW 46,200): about 4.5%" in text
    locked = _col(reached=5, reached_outcome=3)                   # a locked exit missed T on two moonshot paths
    text = R.render(_rep(locked))
    assert "before income tax: about 1 in 6,700." in text and "before income tax in 3, about 1 in 6,700" in text
    assert "before income tax in 5, about 1 in 4,000" in R.render(_rep(locked, track="compounding"))
    text = R.render(_rep(horizon_days=10))
    assert "The middle 10-day period ends with KRW 21,000." in text and "In 20,000 made-up 10-day periods" in text


def test_tax_ceiling_research_base_rates_boxes_limits_and_footer_are_present():
    text = R.render(_rep())
    for key in ("tax.crypto", "research.estimate", "baserate.kalshi", "baserate.esma", "baserate.sebi",
                "baserate.krderiv", "baserate.kr2020", "notin.title", "notin.close", "limits.injected", "footer"):
        assert R.say(key) in text, key
    for key in R._NOT_IN:
        assert "\n- " + R.say(key) + "\n" in text, key
    for dated in ("2025-26", "27 March 2018", "FY26", "2020 to H1 2025", "In a 2020 study of 204,004"):
        assert dated in text, dated
    assert "No plan without a real edge that keeps this floor can beat 1 in 1,999." in text
    assert "Floor-protected sizing: your floor of KRW 21,000 holds even if this position goes to zero." in text
    assert "NumPy and SciPy are outside the signed code hash." in text and "data/macro" in text
    stop = R.render(_rep(sizing="stop_based", l_min=0.0, ceiling=STOP_CEIL, flags=_flags(_col(), ceiling=STOP_CEIL)))
    assert "No plan without a real edge can beat 1 in 1,000." in stop
    assert "Stop-based sizing: a gap past the stop can take you below your floor of KRW 21,000." in stop
    krx = R.render(_rep(tax_basis="krx_small_holder_exempt", cost_words_key="cost.tax"))
    assert R.say("tax.krx") in krx and "(fees and the securities transaction tax average KRW 50;" in krx
    us = R.render(_rep(tax_basis="overseas_22pct_over_2.5m"))
    assert R.say("tax.overseas") in us and R.say("fx.us") in us and R.say("fx.us") not in text


def test_impossible_and_no_trade_print_no_probability_of_the_target():
    rep = _impossible_rep()
    assert [f.code for f in rep.flags if f.code in ("IMPOSSIBLE", "BELOW_RESOLUTION")] == ["IMPOSSIBLE"]
    lines = R.render(rep).splitlines()
    sentence = "IMPOSSIBLE for this buy-and-hold plan: KRX's daily band allows at most 96× in these 16 sessions."
    assert lines.count(sentence) == 1
    assert not any(line.startswith(("Chance of reaching", "In 20,000 made-up")) for line in lines)
    target = next(line for line in lines if line.startswith("your target (KRW"))
    assert target == "your target (KRW 42,000,000): IMPOSSIBLE for this buy-and-hold plan"
    assert not _PROB.search(sentence) and not _PROB.search(target)

    def at(rows: list[str], prefix: str) -> int:
        return next(i for i, line in enumerate(rows) if line.startswith(prefix))
    # in the plain sentence's place: after the floor line and the ladder, right before the tax line
    assert at(lines, "Chance of ending at your floor") < at(lines, "Ended at or above:") < at(lines, "Middle result")
    assert lines.index(sentence) == at(lines, "Middle result") + 1 == at(lines, "Tax:") - 1
    assert "10 times your stake (KRW 420,000): about 1 in 1,000" in lines        # 10x is inside the 95x cap
    low = R.render(_impossible_rep(cap=5.0, sessions=3)).splitlines()
    assert "10 times your stake (KRW 420,000): IMPOSSIBLE for this buy-and-hold plan" in low
    assert "2 times your stake (KRW 84,000): about 1 in 170" in low
    idle = _idle_rep()
    assert not any(f.code in ("IMPOSSIBLE", "BELOW_RESOLUTION") for f in idle.flags)
    lines = R.render(idle).splitlines()
    notrade = "No simulated month made a trade, so these numbers describe holding cash."
    assert lines.count(notrade) == 1
    assert lines.index(notrade) == at(lines, "Middle result") + 1 == at(lines, "Tax:") - 1
    assert not any(line.startswith(("Chance of reaching", "In 20,000 made-up", "your target (KRW",
                                    "Ended at or above")) for line in lines)
    assert "No simulated month ended at your floor." in lines


def test_below_resolution_rides_on_the_plain_sentence():
    col = _col(reached=0, reached_outcome=0, ended_at_or_above=0, rungs=(900, 400, 120, 20, 0))
    flags = _flags(col)
    below = [f for f in flags if f.code == "BELOW_RESOLUTION"]
    assert [(f.level, f.key) for f in below] == [("info", "")]
    text = R.render(_rep(col, flags=flags))
    assert "this plan never reached KRW 42,000,000 before income tax (below resolution: under about 3 in 20,000;" \
        in text
    assert "Chance of reaching KRW 42,000,000 before income tax: below about 3 in 20,000." in text
    # flags_for counts first passages: 3 paths touched T but every exit missed it, so the plain sentence (moonshot
    # outcomes) prints plain.none while BELOW_RESOLUTION, which never prints, stays off
    touched = _col(reached=3, reached_outcome=0, ended_at_or_above=0, rungs=(900, 400, 120, 20, 0))
    assert not any(f.code == "BELOW_RESOLUTION" for f in _flags(touched))
    text = R.render(_rep(touched, flags=_flags(touched)))
    assert "this plan never reached KRW 42,000,000 before income tax (below resolution: under about 3 in 20,000;" \
        in text


def test_no_probability_slot_renders_as_zero():
    for rep in _fixture_reports():
        text = R.render(rep)
        assert not _ZERO.search(text), _ZERO.search(text)


def test_the_comparison_lines():
    text = R.render(_rep(comparison=(3, 2, 4)))
    lines = ("You compared 3 plans (and tried 2 typed win rates) in this session. The highest-looking figure is the "
             "luckiest of 3.",
             "This plan has been run in 4 comparisons, each on its own market seed; the highest-looking of its "
             "figures is the luckiest of 4.",
             R.say("compare.caption"),
             "Before arming, this plan must be run again on a fresh market seed; that rerun belongs to execution and "
             "is not built yet.",
             R.say("footer"))
    where = [text.index(line) for line in lines]
    assert where == sorted(where), where
    assert R.say("compare.caption") not in R.render(_rep(track="compounding"))


def test_flags_for_emits_each_flag_in_the_contract_order():
    rep = _okx_rep()
    assert [(f.code, f.level, f.key) for f in rep.flags] == [
        ("HIDDEN_EDGE", "info", "hidden.pass"), ("ABOVE_ESTIMATED_REFERENCE", "amber", "flag.reference"),
        ("GREY_LEG", "amber", "flag.grey"), ("PROXY_DATA", "info", "flag.proxy"),
        ("PROXY_DATA", "info", "flag.proxyfx"), ("CHECKS_AT_OPEN_CLOSE", "info", "flag.openclose"),
        ("BAND_EDGE_SESSIONS", "info", "flag.bandedge"), ("LIMIT_GAP", "info", "flag.gap"),
        ("LOCKED_AT_HORIZON", "info", "flag.locked"), ("COST_DOMINATED", "amber", "flag.cost"),
        ("RULE_CHANGE_IN_HORIZON", "amber", "rule.review"), ("RULE_CHANGE_IN_HORIZON", "amber", "rule.end"),
        ("RULE_CHANGE_IN_HORIZON", "amber", "rule.end")]
    text = R.render(rep)
    expected = (
        "Each simulated OKX entry is capped at 10.0% of this plan's stake (KRW 4,200), the cap the gate applies.",
        "Above the estimated reference: this plan's chance of the target is above what this bracket's simulated "
        "outcomes could reach with any stake (about 1 in 1,000,000).",
        "OKX is a grey venue (rule KR-OKX-SPOT): each armed session needs your acknowledgement of its warning, "
        "everything you hold there is capped at 10.0% of your equity, and the gate turns it off on 2026-12-03.",
        "Costs average KRW 4,200, 10.0% of your stake.",
        "From 2026-11-22 this plan opens no new position unless you re-approve rule KR-OKX-SPOT; it keeps and may "
        "close what it holds.",
        "On 2026-12-03 rule KR-OKX-SPOT ends (the gate turns this venue off), so the plan closes its position at the "
        "first price check on or after that date and opens no new one.",
        "On 2026-12-05 rule KR-OKX-SPOT ends (the rule expires), so the plan closes",
        "Prices for this leg are a stand-in: Binance BTCUSDT times Upbit KRW-USDT",
        "From 2021-01-01 to 2021-03-04, before Upbit listed KRW-USDT, Yahoo's KRW=X rate stands in for it.",
        "12 simulated sessions (1.3% of all) opened at a KRX daily limit and stayed there until the close.",
        "The worst stop fill was 4.6% below its stop level.",
        "In about 1 in 500 of months the position was still locked at the lower daily limit at the end",
        "Bug check passed with a resolution of KRW")
    where = [text.index(line) for line in expected]
    assert where[1:4] == sorted(where[1:4]) and max(where[1:7]) < min(where[7:]), where      # amber, then info
    plain = _flags(_col(), engine="replay")
    assert "CLOSE_ONLY_CHECKS" in [f.code for f in plain] and "CHECKS_AT_OPEN_CLOSE" not in [f.code for f in plain]
    assert not any(f.code == "ABOVE_ESTIMATED_REFERENCE" for f in _flags(_col(), reference=0.0))
    assert not any(f.code == "ABOVE_ESTIMATED_REFERENCE" for f in _flags(_col(), reference=0.5))
    # the two-sided lower bound is compared, not the point: 4 in 20,000 has 5.4e-5 < 1e-4 < 2e-4
    assert not any(f.code == "ABOVE_ESTIMATED_REFERENCE" for f in _flags(_col(), reference=1e-4))
    # first passages are counted (no track argument): 8 passages bound 1.7e-4 > 1e-4 though 4 outcomes bound 5.4e-5
    locked = _col(reached=8, reached_outcome=4)
    assert [f.key for f in _flags(locked, reference=1e-4) if f.code == "ABOVE_ESTIMATED_REFERENCE"] == \
        ["flag.reference"]
    assert not any(f.code == "COST_DOMINATED" for f in _flags(_col(mean_cost=4_199.0)))


def test_the_stress_and_delisting_columns():
    head = _col()
    stress = _col(key="no_edge/bootstrap/stress2x", scenario="stress2x", mean=41_900.0, mean_cost=100.0)
    other = _col(key="no_edge/bootstrap_half/stress2x", member="bootstrap_half", scenario="stress2x")
    d30 = _col(key="delist_30", mean=29_500.0, mean_cost=12_500.0)
    text = R.render(_rep(head, stress, other, d30))
    assert text.count("With costs doubled:") == 1
    assert "With costs doubled:\nThe middle month ends with KRW 21,000." in text
    assert "(fees average KRW 100; the simulation's own average, KRW 41,900 ± 60, agrees)" in text
    assert "If KRW-BTC were delisted right after you buy, losing 30% of its value:" in text
    assert "(fees and the delisting stress loss average KRW 12,500;" in text


def test_the_assumed_column_lines():
    text = R.render(_assumed_rep())
    assert "These numbers are only as true as the win rate you typed (55.0%). This bracket's no-edge win rate is " \
        "49.9% (2.1% of brackets end unresolved)." in text
    assert "Telling them apart would take about 617 recorded brackets." in text
    assert "Without the edge you typed, no plan that keeps this floor can beat 1 in 1,999." in text
    paragraph = (R.say("assumed.lead", w="55.0%", p0="49.9%", u="2.1%"), R.say("assumed.nb", nb="617"),
                 R.say("assumed.ceiling", c="1 in 1,999"), "The middle month ends with KRW 21,000.")
    assert "\n" + "\n".join(paragraph) + "\n" in text           # spec 7.5's three sentences unbroken, then typical
    assert [R._pct(x) for x in (0.0003, 0.0005, 0.0008, 0.0014, 0.0099, 0.0213, 0.55)] == [
        "0.030%", "0.050%", "0.080%", "0.14%", "0.99%", "2.1%", "55.0%"]
    small = R.render(_assumed_rep(w=0.0008, p0=0.0005))
    assert "the win rate you typed (0.080%). This bracket's no-edge win rate is 0.050% (2.1% of brackets" in small
    many = R.render(_assumed_rep(nb=math.inf))
    assert "Telling them apart would take more recorded brackets than the 5,000 this simulation resolved." in many
    assert "Without the edge you typed, no plan can beat 1 in 1,000." in R.render(_assumed_rep("stop_based"))


def test_the_replay_card_lines():
    text = R.render(_replay_rep())
    for part in ("Model: the tested strategy's own out-of-sample daily results, 2019-10-23 to 2026-09-25 (2,530 "
                 "sessions), resampled in blocks of about 10 days.",
                 R.say("replay.noedge"), R.say("kelly.label"),
                 "on its own 2019–2026 out-of-sample results, with 40% of its average return removed.",
                 "had a Sharpe ratio of 0.79, against 0.73 for this replay after the cut.",
                 "was +0.43 Sharpe (90% range +0.03 to +0.83).",
                 "this column's average growth over 29 days is 2.9%, against 2.6% if its days were independent.",
                 "Without the edge assumed here, no plan that keeps this floor can beat 1 in 1,999.",
                 "; no other model could be run here;", "Price checks at the close only.\n"):
        assert part in text, part
    lines = text.splitlines()
    assert lines.index(R.say("replay.noedge")) == lines.index(next(x for x in lines if x.startswith("Model:"))) + 1
    assert R.say("kelly.label") not in R.render(_replay_rep(fstar=math.nan))


# --------------------------------------------------------------------------- #
# The language guard
# --------------------------------------------------------------------------- #
def test_guard_positive_controls_and_rules():
    for bad in ("the best plan", "floor-safe sizing", "a good chance", "plan_hash", "Risk-Free", "a LOW-RISK bet",
                "you Should", "worth   trying", "likely\nto reach", "{x}", "a } b", "xS_C3", "OPTIMAL"):
        assert R.guard(bad), bad
    assert R.guard("the S_C3 replay (S_C3)") == []
    assert R.guard("Floor-protected sizing: measured, recommend, ensure, pressure, safety-net") == []


def test_the_catalogue_is_the_contract_text_and_every_template_passes_the_guard():
    blob = json.dumps(dict(R.CATALOGUE), sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    assert hashlib.sha256(blob).hexdigest() == _CATALOGUE_SHA256
    assert len(R.CATALOGUE) == 193 and isinstance(R.CATALOGUE, MappingProxyType)
    for key, template in R.CATALOGUE.items():
        filled = R.say(key, **{name: "1" for name in re.findall(r"\{([a-z0-9]+)\}", template)})
        assert R.guard(filled) == [], (key, R.guard(filled))
    _raises(lambda: R.say("no.such.key"), KeyError)
    _raises(lambda: R.say("plan.head", i="1"), KeyError)


def test_rendered_reports_and_the_krx_provenance_pass_the_guard():
    md5s = (("holidays_KRX", "1a" * 16), ("kr_regime_tags", "2b" * 16), ("kr_sessions", "3c" * 16))
    prov = _prov(calendar_sha="4d" * 32, calendar_version="1.0.0-fixture", calendar_md5s=md5s,
                 members=("bootstrap", "bootstrap_half", "garch_refit"), edge_source=plan.REPLAY_SOURCE,
                 model="bootstrap", proxy_dates=("2021-01-01", "2021-03-04"))
    text = R.render(_rep(provenance=prov, tax_basis="krx_small_holder_exempt", cost_words_key="cost.tax",
                         spread_kind="krx"))
    assert R.guard(text) == []
    for internal in ("holidays", "kr_sessions", "regime_tags", "bootstrap_half", "garch_refit", "crypto_trend",
                     "upbit_daily", "floor_safe", "plan_hash", "replay:", "decision", "8888888888888888",
                     "9999999999999999"):
        assert internal not in text, internal
    for line in ("Recorded with this report:", "code hash: 6666666666666666", "code signed: yes",
                 "owner log entry: 7 / 5555555555555555", "key fingerprint: 7777777777777777",
                 "tables in force: 1111111111111111 / 2222222222222222 / 3333333333333333 / 4444444444444444",
                 "price history: aaaaaaaaaaaaaaaa / bbbbbbbbbbbbbbbb / 2021-01-01 / 2021-03-04",
                 "calendar: 1.0.0-fixture / 4d4d4d4d4d4d4d4d / 1a1a1a1a1a1a1a1a, 2b2b2b2b2b2b2b2b, 3c3c3c3c3c3c3c3c",
                 "market seed: cccccccccccccccc", "paths and chunk: 20,000 / 2,000",
                 f"NumPy, SciPy, cryptography: {np.__version__} / {scipy.__version__} / 49.0.0",
                 "repository: git:" + "d" * 40, "tree hash: eeeeeeeeeeeeeeee", "comparison and run: c000001 / 1",
                 "model and members: two-point bootstrap / the two-point bootstrap, the bootstrap at half the block "
                 "length, the GARCH-t refit", "edge source: the S_C3 replay"):
        assert "\n" + line + "\n" in text, line
    unsigned = R.render(_rep(provenance=_prov(code_signed=False)))
    assert "\ncode signed: no\n" in unsigned
    for rep in _fixture_reports():
        assert R.guard(R.render(rep)) == []


def test_a_banned_slot_value_or_catalogue_text_makes_render_raise():
    slots = {"first": "2016-10-24", "last": "2026-10-22", "rows": "3,650"}
    for bad in (_rep(model_slots={**slots, "symbol": "BEST"}), _rep(model_slots={**slots, "symbol": "KRW_BTC"}),
                _rep(plan_hash="{oops}"), _refused("SHORT_HISTORY", slots={"symbol": "SAFE"})):
        assert "rendered text failed the language guard" in _raises(lambda: R.render(bad))
    saved = R.CATALOGUE
    try:
        R.CATALOGUE = MappingProxyType({**saved, "footer": "This is the optimal plan."})
        assert "rendered text failed the language guard" in _raises(lambda: R.render(_rep()))
    finally:
        R.CATALOGUE = saved
    assert R.render(_rep())


# --------------------------------------------------------------------------- #
# Refusals
# --------------------------------------------------------------------------- #
def test_a_refused_report_renders_no_computed_probability():
    codes = set()
    for code, sub, slots in _REFUSALS:
        rep = _refused(code, sub, slots)
        assert rep.columns == () and rep.flags == () and rep.hidden is None and rep.spread is None
        assert rep.refused.code == code and math.isnan(rep.ceiling) and rep.n == 0
        text = R.render(rep)
        lines = text.splitlines()
        assert lines[0] == "Plan 1 of 1 (none)" and lines[1].startswith("Refused: ") and "{" not in lines[1]
        assert lines[2] == R.say("refused.none") and lines[3] == R.say("footer") and lines[4] == R.say("prov.head")
        assert "detail" not in text
        scrubbed = text.replace(R.say("sub.bracket"), "").replace("(55.0%)", "")
        assert not _PROB.search(scrubbed), (code, sub, scrubbed)
        codes.add(code)
    assert codes == set(plan.REFUSALS)
    assert "Refused: the chosen model failed its refit check, so no numbers are shown." in R.render(
        _refused("MODEL_CHECK_FAILED", "", {"check": "refit"}))
    assert "Refused: the data given to the engine did not pass its checks: the last price is more than 3 days " \
        "before the start." in R.render(_refused("DATA_INVALID", "stale", {"days": "3"}))
    assert "Refused: upbit BTC cannot be costed or sized from the signed venue table:" in R.render(
        _refused("NOT_TRADABLE", "", {"venue": "upbit", "symbol": "BTC"}))


def test_the_plan_name_never_renders():
    p = plan.Plan(name="my best plan_v2", track="moonshot", stake_krw=W0, target_krw=T, fx_krw_per_usd=1_400.0,
                  start=date(2026, 10, 23), horizon_days=30, leg=plan.Leg(venue="upbit", symbol="BTC",
                                                                          model="bootstrap"),
                  fraction=plan.fixed(1.0))
    rep = R.refusal_report(p, plan.Refusal(code="SCREEN_BLOCKED", sub="row", slots={"row": "KR-OKX-SPOT"}),
                           index=2, count=3)
    text = R.render(rep)
    assert "best" not in text and "v2" not in text and rep.plan_hash == plan.plan_hash(p)
    assert text.splitlines()[:2] == [f"Plan 2 of 3 ({plan.plan_hash(p)[:16]})",
                                     "Refused: the compliance gate blocks this leg: rule KR-OKX-SPOT."]
    nan_plan = dataclasses.replace(p, stake_krw=math.nan)
    assert R.refusal_report(nan_plan, plan.Refusal(code="UNSUPPORTED_PRODUCT", sub="numbers")).plan_hash == ""


def test_build_freezes_mappings_and_refuses_inconsistent_reports():
    rep = _rep()
    assert isinstance(rep.provenance, MappingProxyType) and isinstance(rep.model_slots, MappingProxyType)
    assert isinstance(rep.columns, tuple) and rep.headline == "no_edge/bootstrap/base"
    for bad in (dict(headline="no_edge/garch_t/base"), dict(spread=None), dict(spread_kind="wide"),
                dict(spread=(0.0, 1e-4), spread_kind="none")):
        _raises(lambda bad=bad: _rep(**bad))
    _raises(lambda: _rep(_col(), _col()))
    refused = _refused("STUCK_AT_START")
    fields = {f.name: getattr(refused, f.name) for f in dataclasses.fields(refused)}
    _raises(lambda: R.build(**{**fields, "columns": (_col(),)}))
    _raises(lambda: R.build(**{**fields, "flags": _flags(_col())}))
    _raises(lambda: R.build(**{k: v for k, v in fields.items() if k != "provenance"}), TypeError)
```

- [ ] **Step 2: Run to verify it fails**

  Overlap check with the PowerShell tool (it must print nothing; otherwise wait and re-run):

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then from the repo root in Git Bash:

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_report/
```

  Expected: one line `PASS odds_report/test_column_stats_fields_are_the_contract_list` (Task 9's class is already
  there), 40 lines `FAIL odds_report/test_... AttributeError: module 'core.odds.report' has no attribute '<name>'`
  (for example `'say'`, `'build'`, `'cp_two_sided'`, `'HiddenEdge'`), then `1/41 passed, 40 failed, 0 not run` and
  exit code 1. An `odds_report/import` FAIL instead means a Task 5, 6, 9 or 11 name is missing: stop and check those
  tasks.

- [ ] **Step 3: Implement**

  3a. Read `core/odds/report.py` (Task 9's file, 49 lines; the follow-up never touches it) and list its top-level
  names. Run the overlap check of Step 2 first (PowerShell tool; it must print nothing), then from the repo root in
  Git Bash:

```bash
.venv/Scripts/python.exe -I -c "import ast; t = ast.parse(open('core/odds/report.py', encoding='utf-8').read()); print([getattr(n, 'name', None) or n.targets[0].id for n in t.body if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.Assign))])"
```

  Expected: `['LADDER', 'COST_DOMINATED_SHARE', 'ColumnStats']`. Both old texts below are quoted from Task 9's Step 3.
  DRIFT RULE: if Task 9's review changed its docstring, imports or comments, make the same change to the current text
  (keep Task 9's lines, add the imports and constants of the new text) and record a one-line ruling in the ledger's
  "Drift rulings"; if `ColumnStats` no longer ends with the `trades` field, or Task 9 added another top-level name,
  append the block of Edit 2 after the file's last line instead and record that; if a `ColumnStats` field differs
  from CONTRACT 10.1, stop and rule (`test_column_stats_fields_are_the_contract_list` pins the list).

  3b. Edit 1 (anchor: the module docstring, the imports and the two constants at the top of the file). Old text,
  exactly:

```python
"""The odds report (spec 7.5; odds plan contract section 10). This first part holds what the path engine fills: the
outcome ladder, the cost share of the COST_DOMINATED flag and the statistics of one simulated column. simulate
imports report, never the reverse. Pure: no clock, no file, no network."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

LADDER = (1.10, 1.25, 2.0, 10.0)                  # x W0; then the target (simulate reads report.LADDER)
COST_DOMINATED_SHARE = 0.10                       # Q43 (simulate reads report.COST_DOMINATED_SHARE)
```

  New text:

```python
"""The odds report (spec 7.5; odds plan contract section 10): column statistics, the bug checks, honest number
formats, the flags, the one sentence catalogue, rendering and the language guard. simulate imports report, never
the reverse. Pure: no clock, no file, no network (Q42)."""
from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

import numpy as np
from scipy import stats

from core.odds import bold, costs, plan

LADDER = (1.10, 1.25, 2.0, 10.0)                  # x W0; then the target (simulate reads report.LADDER)
COST_DOMINATED_SHARE = 0.10                       # Q43 (simulate reads report.COST_DOMINATED_SHARE)
CP_LEVEL = 0.95
DELTA = 1e-4                                      # HIDDEN_EDGE's delta (spec 7.5)
RED_ALPHA = 0.001                                 # CEILING_BREACH red: one-sided 1 - RED_ALPHA / m
CARRY = costs.LIMIT_DOWN_CARRY_COST_MULTIPLIER
```

  3c. Edit 2 (anchor: the last field of the class `ColumnStats`, the file's last line). The old text is exactly this
  one line, indented four spaces: `    trades: int                   # paths with an entry fill` (the comment column is
  Task 9's). The new text is that same line, then two empty lines, then the block below through its last line
  `    return text` (the file's final newline stays where it is). Nothing else in `ColumnStats` changes. The file holds
  non-ASCII catalogue text (`±`, `×`, `ü`, `–`), which test_16 allows; keep it UTF-8 with LF endings.

```python
@dataclass(frozen=True, kw_only=True)
class HiddenEdge:
    """HIDDEN_EDGE on one no-edge column: a drift check of the simulator, never a check of the model (Q32)."""
    status: str      # "pass" | "red_gain" | "red_loss" | "unavailable" (GARCH-t) | "unbounded" (k_x >= 1, 10.3)
                     # | "not_applicable"
    mean: float
    bound: float
    range_: float
    n: int


@dataclass(frozen=True, kw_only=True)
class Flag:
    code: str
    level: str                     # "red" | "amber" | "info"
    key: str                       # a CATALOGUE key; "" for a flag another line carries (BELOW_RESOLUTION)
    slots: Mapping[str, str]


@dataclass(frozen=True, kw_only=True)
class OddsReport:
    """One plan card (spec 7.5). A refused report has no columns, no flags and no probability."""
    plan_hash: str
    plan_index: int
    plan_count: int
    refused: plan.Refusal | None
    track: str
    stake: float
    target: float
    floor: float
    l_min: float                   # the floor under floor_safe sizing (replay legs included), else 0.0 (Q32)
    horizon_days: int
    n: int
    sizing: str                    # "floor_safe" | "stop_based": picks the ceiling wording
    model_key: str                 # model.bootstrap | model.garch | model.replay
    model_slots: Mapping[str, str]     # the model line's slots; an OKX card adds cap and capkrw (okx.cap)
    columns: tuple[ColumnStats, ...]
    headline: str                  # the headline column's key
    spread: tuple[float, float] | None     # (lowest lower, highest upper) bound over the other base members
    spread_kind: str               # "other" | "krx" | "blocks" | "none" (Q31)
    notes: tuple[tuple[str, str], ...]     # (member, failed check) of each dropped member
    ceiling: float                 # bold.ceiling(stake, l_min, target)
    structural_cap: float | None
    structural_sessions: int | None
    tax_basis: str
    cost_words_key: str            # cost.tax for KRX_stock_book, else cost.fees (Q37)
    hidden: HiddenEdge | None
    flags: tuple[Flag, ...]
    assumed: Mapping[str, float] | None    # w, p0, u, nb (math.inf allowed), resolved, theta
    replay: Mapping[str, float] | None     # y0, y1, cut, bench_sr, haircut_sr, diff, ci_lo, ci_hi, fstar, h, growth,
                                           # growth_iid
    comparison: tuple[int, int, int]       # (K, J, R)
    provenance: Mapping[str, object]


CATALOGUE: Mapping[str, str] = MappingProxyType({
    # model and sizing
    "model.bootstrap": (
        "Model: a two-point bootstrap of the daily moves of {symbol} in won, {first} to {last} ({rows} sessions), in "
        "which nobody has an edge. Price checks at the open and the close only."
    ),
    "model.garch": (
        "Model: GARCH-t fitted to the daily won returns of {symbol}, {first} to {last} ({rows} sessions), in which "
        "nobody has an edge. Price checks at the close only."
    ),
    "model.replay": (
        "Model: the tested strategy's own out-of-sample daily results, {first} to {last} ({rows} sessions), resampled "
        "in blocks of about {block} days. Price checks at the close only."
    ),
    "sizing.floor": "Floor-protected sizing: your floor of KRW {floor} holds even if this position goes to zero.",
    "sizing.stop": "Stop-based sizing: a gap past the stop can take you below your floor of KRW {floor}.",
    "okx.cap": (
        "Each simulated OKX entry is capped at {cap} of this plan's stake (KRW {capkrw}), the cap the gate applies."
    ),
    "fx.us": (
        "US prices are turned into won with Yahoo's KRW=X rate: the open with the previous day's close and the close "
        "with the same day's close."
    ),
    "kelly.label": "This stake aims at long-run growth, not at reaching your target.",
    "period.month": "month",
    "period.months": "months",
    "period.day": "{h}-day period",
    "period.days": "{h}-day periods",
    # typical result and average
    "typical.median": "The middle {one} ends with KRW {median}.",
    "typical.floor": (
        "In {p} of {many} you end at your floor, keeping between KRW {lo} and KRW {hi}, and can no longer trade."
    ),
    "typical.nofloor": "No simulated {one} ended at your floor.",
    "average.agrees": (
        "Averaged over all simulated {many}: about KRW {expected} ({costwords} average KRW {cost}; the simulation's "
        "own average, KRW {mean} ± {se}, agrees). That average includes rare jackpots and is not what usually happens."
    ),
    "average.differs": (
        "The simulation's own average, KRW {mean} ± {se}, does not match your stake minus the average {costwords} (KRW "
        "{expected}); see the bug check below."
    ),
    "average.gain": (
        "Averaged over all simulated {many}: an average gain of KRW {gain}, only if the edge in this column is real."
    ),
    "average.loss": (
        "Averaged over all simulated {many}: an average loss of KRW {loss}, even with the edge in this column."
    ),
    "cost.fees": "fees",
    "cost.tax": "fees and the securities transaction tax",
    "cost.delist": "{base} and the delisting stress loss",
    # headline, ladder, plain sentence, precision
    "headline.moonshot": "Chance of reaching KRW {target} before income tax: {p}.",
    "headline.compounding": (
        "Was worth KRW {target} at some price check in {k} of {n} made-up {many} ({pk}); ended at or above it in {k2} "
        "({pk2})."
    ),
    "headline.floor": "Chance of ending at your floor: {p}.",
    "ladder.head": "Ended at or above:",
    "ladder.rung": "{label} (KRW {value}): {p}",
    "ladder.impossible": "{label} (KRW {value}): IMPOSSIBLE for this buy-and-hold plan",
    "ladder.p10": "+10%",
    "ladder.p25": "+25%",
    "ladder.x2": "2 times your stake",
    "ladder.x10": "10 times your stake",
    "ladder.target": "your target",
    "ladder.spread": "Middle result KRW {median}; 5th percentile KRW {p5}.",
    "plain.hit": (
        "In {n} made-up {many} (from a model in which nobody has an edge, not real history), this plan reached KRW "
        "{target} before income tax in {k}, {about} (counting noise alone: between {hi} and {lo}; {spread}; {bugs}, "
        "and nothing here covers the model being wrong)."
    ),
    "plain.none": (
        "In {n} made-up {many} (from a model in which nobody has an edge, not real history), this plan never reached "
        "KRW {target} before income tax (below resolution: under about 3 in {n}; {spread}; {bugs}, and nothing here "
        "covers the model being wrong)."
    ),
    "bugs.coarser": "the bug checks are coarser than these ranges",
    "bugs.finer": "the bug check's resolution is printed below",
    "cap.p": "at most {c}, the ceiling (the simulated {k} in {n} is above it only through counting noise)",
    "spread.other": "other models give {a} to {b}",
    "spread.krx": (
        "the same model with other block lengths gives {a} to {b}; no second model family is available for KRX"
    ),
    "spread.blocks": "the same model with other block lengths gives {a} to {b}",
    "spread.none": "no other model could be run here",
    "spread.dropped": "{member} was left out because its {check} check failed",
    "member.bootstrap": "the two-point bootstrap",
    "member.half": "the bootstrap at half the block length",
    "member.double": "the bootstrap at twice the block length",
    "member.garch": "GARCH-t",
    "member.refit": "the GARCH-t refit",
    "check.deterministic": "deterministic",
    "check.statistical": "statistical",
    "check.fit": "fit",
    "check.refit": "refit",
    "structural.impossible": (
        "IMPOSSIBLE for this buy-and-hold plan: KRX's daily band allows at most {cap}× in these {s} sessions."
    ),
    "structural.notrade": "No simulated {one} made a trade, so these numbers describe holding cash.",
    # tax, ceiling, base rates
    "tax.krx": (
        "Tax: this KRX holding is treated as a small holder's, so its gains pay no capital gains tax here; any "
        "securities transaction tax is inside the costs."
    ),
    "tax.overseas": (
        "Tax: overseas share gains above KRW 2.5 million a year are taxed at 22%. Not simulated: these numbers are "
        "before income tax."
    ),
    "tax.crypto": (
        "Tax: crypto gains are due to be taxed at 22% from 2027 (unless postponed again). Not simulated: these numbers "
        "are before income tax."
    ),
    "ceiling.noedge": "No plan without a real edge that keeps this floor can beat {c}.",
    "ceiling.nofloor": "No plan without a real edge can beat {c}.",
    "ceiling.edge": "Without the edge assumed here, no plan that keeps this floor can beat {c}.",
    "ceiling.edgenf": "Without the edge assumed here, no plan can beat {c}.",
    "research.estimate": (
        "The research found no measured chance of this account growing 1,000 times in a month. Its reasoned estimates: "
        "0.01% or less in general, roughly 0.01% to 0.03% for long far-out-of-the-money US options, and below 0.01% "
        "for domestic crypto spot."
    ),
    "baserate.kalshi": (
        "Kalshi takers lost about 32% of the amount staked and makers about 10% (Bürgi, Deng and Whelan working paper, "
        "2025-26; not re-verified)."
    ),
    "baserate.esma": "74-89% of EU retail CFD accounts lose money (national regulators' data, ESMA, 27 March 2018).",
    "baserate.sebi": "87.7% of Indian retail equity-derivatives traders lost in FY26 (SEBI).",
    "baserate.krderiv": (
        "Korean retail lost about KRW 458 billion a year on overseas derivatives, 2020 to H1 2025, with no profitable "
        "year."
    ),
    "baserate.kr2020": (
        "In a 2020 study of 204,004 Korean retail accounts, 46% lost money, and 62% of new investors did."
    ),
    # columns
    "column.stress": "With costs doubled:",
    "column.delist": "If {symbol} were delisted right after you buy, losing {h}% of its value:",
    "assumed.lead": (
        "These numbers are only as true as the win rate you typed ({w}). This bracket's no-edge win rate is {p0} ({u} "
        "of brackets end unresolved)."
    ),
    "assumed.nb": "Telling them apart would take about {nb} recorded brackets.",
    "assumed.nbmany": "Telling them apart would take more recorded brackets than the {r} this simulation resolved.",
    "assumed.ceiling": "Without the edge you typed, no plan that keeps this floor can beat {c}.",
    "assumed.ceilingnf": "Without the edge you typed, no plan can beat {c}.",
    "replay.lead": (
        "This replays a tested bitcoin trend strategy (S_C3) on its own {y0}–{y1} out-of-sample results, with {cut}% "
        "of its average return removed. Most of that return came from bitcoin rising in those years, which the no-edge "
        "column leaves out: just holding bitcoin then had a Sharpe ratio of {bench}, against {cutsr} for this replay "
        "after the cut. Its tested advantage over holding bitcoin was {diff} Sharpe (90% range {lo} to {hi}). Backtest "
        "edges often shrink or vanish in live trading; read this as the hopeful case."
    ),
    "replay.growth": (
        "Resampled in blocks that keep its streaks, this column's average growth over {h} days is {g}, against {g0} if "
        "its days were independent."
    ),
    "replay.noedge": (
        "No-edge column: the same strategy's daily moves, each given a fair coin for its direction, with its costs "
        "kept."
    ),
    # flags
    "hidden.gain": (
        "BUG CHECK FAILED: this plan makes money without any edge (average KRW {x}, limit KRW {b}). Do not use these "
        "numbers."
    ),
    "hidden.loss": (
        "BUG CHECK FAILED: this plan loses more than its costs explain (average KRW {x}, limit KRW {b}). Do not use "
        "these numbers."
    ),
    "hidden.pass": (
        "Bug check passed with a resolution of KRW {b} ({pct} of your stake): it would not notice a hidden edge (a "
        "simulator error that makes money without an edge) that raised the chance of the target by up to {m}. It does "
        "not test whether the model itself is right."
    ),
    "hidden.coarse": (
        "Bug check passed, but its resolution (KRW {b}, {pct} of your stake) is too coarse to say anything about the "
        "chance of the target. It does not test whether the model itself is right."
    ),
    "hidden.unavailable": (
        "The bug check is unavailable for GARCH-t: a bounded shock does not bound the volatility, so no finite range "
        "exists."
    ),
    "hidden.unbounded": (
        "The bug check is unavailable for this plan (no finite range): at the lowest price this model can reach, the "
        "cost rate has no useful bound."
    ),
    "hidden.na": "The bug check does not apply to edge columns.",
    "breach.amber": (
        "Preliminary evidence, about 5% false-alarm rate per check: rerun with more paths. A no-edge result's lower "
        "bound, {lb}, is above the ceiling of {c}."
    ),
    "breach.red": (
        "Do not use these numbers: a no-edge result beats the ceiling of {c} beyond counting noise ({lb}), so the "
        "model or the simulator has a bug."
    ),
    "flag.reference": (
        "Above the estimated reference: this plan's chance of the target is above what this bracket's simulated "
        "outcomes could reach with any stake ({ref}). The reference is an estimate, not a bound."
    ),
    "flag.grey": (
        "OKX is a grey venue (rule {row}): each armed session needs your acknowledgement of its warning, everything "
        "you hold there is capped at {cap} of your equity, and the gate turns it off on {off}."
    ),
    "flag.proxy": (
        "Prices for this leg are a stand-in: Binance BTCUSDT times Upbit KRW-USDT, because OKX's own prices are not "
        "loaded."
    ),
    "flag.proxyfx": "From {d0} to {d1}, before Upbit listed KRW-USDT, Yahoo's KRW=X rate stands in for it.",
    "flag.openclose": "Price checks at the open and the close only: a stop can fill well below its level after a gap.",
    "flag.closeonly": "Price checks at the close only.",
    "flag.bandedge": (
        "{count} simulated sessions ({share} of all) opened at a KRX daily limit and stayed there until the close."
    ),
    "flag.gap": "The worst stop fill was {gap} below its stop level.",
    "flag.locked": (
        "In {p} of {many} the position was still locked at the lower daily limit at the end, valued at the locked "
        "price less the doubled exit charge."
    ),
    "flag.cost": "Costs average KRW {cost}, {pct} of your stake.",
    "rule.review": (
        "From {date} this plan opens no new position unless you re-approve rule {row}; it keeps and may close what it "
        "holds."
    ),
    "rule.end": (
        "On {date} rule {row} ends ({what}), so the plan closes its position at the first price check on or after that "
        "date and opens no new one."
    ),
    "rule.auto": "the gate turns this venue off",
    "rule.until": "the rule expires",
    # refusals
    "refused.head": "Refused: {why}",
    "refused.none": "No numbers are shown for a refused plan.",
    "why.PARTIAL_CHUNK": "the path count must be a whole multiple of {chunk}.",
    "why.UNSUPPORTED_PRODUCT": "this plan uses something the odds engine does not support: {what}.",
    "sub.venue": "only KIS, Upbit and OKX legs",
    "sub.feed": "only BTC on OKX, the one OKX market with a price feed",
    "sub.symbol": "a symbol the signed instrument map lists for this venue",
    "sub.class": "only shares, 1x ETFs and coins",
    "sub.multiple": "only products that move one for one with their underlying",
    "sub.tax": "a tax basis the engine can describe",
    "sub.horizon": "a horizon of 1 to 366 days",
    "sub.start": "a plan that starts today (the Asia/Seoul date)",
    "sub.track": "a moonshot or compounding track",
    "sub.numbers": "a positive stake, a target above the stake and a positive won-dollar rate",
    "sub.model": "the two-point bootstrap or GARCH-t",
    "sub.sizing": "stop-based sizing only with a bracket",
    "sub.fraction": "Kelly only on the tested-strategy replay, bold play only with a bracket",
    "sub.bracket": "a take-profit above 0 and a stop between 0 and 100%",
    "sub.edge": "a typed win rate between 0 and 1, with a bracket and the two-point bootstrap",
    "sub.replay": "the tested-strategy replay only as an Upbit bitcoin holding",
    "sub.file": "a plan file the engine can read",
    "sub.comparison": "a comparison id this engine issued earlier",
    "why.MULTI_LEG_UNSUPPORTED": "this plan has more than one leg; only single-leg plans are supported.",
    "why.STATE_UNUSABLE": (
        "the signed owner state is not usable (no owner key yet, a broken owner log, unapproved tables, or code "
        "changed since you signed it), so nothing new is allowed."
    ),
    "why.LIMITS_UNSET": (
        "your total-loss floor and daily loss limit are not both set, or an OKX leg has no OKX cap. Limits you set "
        "take effect from the next day."
    ),
    "why.CALENDAR_UNSIGNED": (
        "KRX and US plans need the calendar set you signed; it is missing or does not match. Only crypto plans run "
        "until then."
    ),
    "why.CALENDAR_COVERAGE": "this horizon runs past the end of the signed calendar.",
    "why.DATA_INVALID": "the data given to the engine did not pass its checks: {what}.",
    "data.now": "the run's clock reading is not today's",
    "data.series": "the price history",
    "data.sessions": "the session list",
    "data.empty": "the horizon holds no trading session of this market",
    "data.stale": "the last price is more than {days} days before the start",
    "why.SYNTHETIC_REFUSED": "the price history is made-up data, not market prices.",
    "why.NOT_TRADABLE": (
        "{venue} {symbol} cannot be costed or sized from the signed venue table: a minimum order, lot size or fixed "
        "charge is missing, or a date in the horizon is outside a signed tick or tax table."
    ),
    "why.SPECIAL_REGIME": (
        "{symbol} has fewer than 60 KRX sessions of history before the start, so it may still be in a special "
        "reference-price regime."
    ),
    "why.SHORT_HISTORY": "{symbol} has fewer than 250 daily bars of history before the start.",
    "why.CARD_NOT_REPRODUCED": (
        "the tested strategy did not reproduce its validated card, so its column cannot be shown."
    ),
    "why.MODEL_NOT_FOR_LIMITED_VENUE": (
        "GARCH-t is not available for a KRX leg, whose daily band that model does not include."
    ),
    "why.MODEL_CHECK_FAILED": "the chosen model failed its {check} check, so no numbers are shown.",
    "why.COST_DOMINATED": "costs take the whole win of this bracket, or a single exit could cost the whole position.",
    "why.STUCK_AT_START": (
        "can't open: no first stake is affordable after your floor, the reserved exit charge and lot rounding; the "
        "largest stake is below the venue minimum."
    ),
    "why.SCREEN_BLOCKED": "the compliance gate blocks this leg: {what}.",
    "screen.row": "rule {row}",
    "screen.unsigned": "the current code is not signed yet",
    "screen.other": "see the gate's own check",
    "why.ASSUMED_EDGE_UNREACHABLE": "the win rate you typed ({w}) cannot be reached by tilting this bracket's moves.",
    # closing boxes
    "notin.title": "Not in these numbers:",
    "notin.tax": "income tax (estimated, not simulated)",
    "notin.fx": "won-dollar moves beyond the historical range in the data, and the timing of the KRW=X rate",
    "notin.upbit": "Upbit withdrawal holds after a KRW deposit, and the Upbit-to-OKX route closing without notice",
    "notin.freeze": "exchange freezes or failure",
    "notin.delist": "delistings and Upbit warnings (survivorship)",
    "notin.krx": "KRX halts, VI auctions, designations, resets and other special reference-price regimes",
    "notin.intraday": "intraday moves",
    "notin.unfilled": "unfilled orders beyond what is modelled",
    "notin.broker": "broker refusals",
    "notin.hacked": "hacked or locked accounts",
    "notin.rules": "rule changes",
    "notin.close": "Most of these make the real result worse; none makes a no-edge plan better.",
    "limits.injected": (
        "How these numbers were made: unsigned loading code supplies the price history, the session list and the "
        "replay. This report records their hashes but cannot check them against any signed source. The calendar files "
        "used carry the hash you signed; the session dates taken from them, and the KRX Saturday rule read from "
        "data/macro, are not re-checked here. The replay matches its pinned results; the card and results-file hashes "
        "it reports come from unsigned code. NumPy and SciPy are outside the signed code hash."
    ),
    "compare.caption": (
        "With no real edge, a higher chance of the target generally comes from putting more of your stake at risk, "
        "sooner. Check P(at your floor) beside it. Higher here means riskier, not better."
    ),
    "compare.k": (
        "You compared {k} plans (and tried {j} typed win rates) in this session. The highest-looking figure is the "
        "luckiest of {k}."
    ),
    "compare.r": (
        "This plan has been run in {r} comparisons, each on its own market seed; the highest-looking of its figures is "
        "the luckiest of {r}."
    ),
    "compare.fresh": (
        "Before arming, this plan must be run again on a fresh market seed; that rerun belongs to execution and is not "
        "built yet."
    ),
    "plan.head": "Plan {i} of {k} ({hash})",
    "prov.head": "Recorded with this report:",
    "prov.line": "{label}: {value}",
    "prov.code": "code hash",
    "prov.signed": "code signed",
    "prov.owner": "owner log entry",
    "prov.key": "key fingerprint",
    "prov.tables": "tables in force",
    "prov.data": "price history",
    "prov.calendar": "calendar",
    "prov.seed": "market seed",
    "prov.paths": "paths and chunk",
    "prov.versions": "NumPy, SciPy, cryptography",
    "prov.repo": "repository",
    "prov.tree": "tree hash",
    "prov.comparison": "comparison and run",
    "prov.model": "model and members",
    "prov.edge": "edge source",
    "label.bootstrap": "two-point bootstrap",
    "label.garch": "GARCH-t",
    "label.replay": "tested-strategy replay",
    "label.yes": "yes",
    "label.no": "no",
    "edge.none": "none",
    "edge.assumed": "a typed win rate",
    "edge.replay": "the S_C3 replay",
    "footer": (
        "These numbers describe rules you wrote, run in a model. They are not advice, and TRADEGEN does not recommend "
        "any plan. A higher chance of reaching the target does not make a plan better."
    ),
})
BANNED_WORDS = ("best", "optimal", "recommended", "safe", "guaranteed", "sure", "ideal", "risk-free", "low-risk",
                "proven", "should")
BANNED_PHRASES = ("worth trying", "good chance", "likely to reach")
_TOKEN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_CARD_ID = re.compile(r"\bS_C3\b")


def say(key: str, **slots) -> str:
    """CATALOGUE[key].format(**slots): KeyError on an unknown key or a missing slot."""
    return CATALOGUE[key].format(**slots)


def guard(text: str) -> list[str]:
    """The language guard (spec 7.5, Q14): banned whole words (a hyphenated token also part by part), banned
    phrases, any underscore outside the card id S_C3, any brace. Returns the hits; [] is clean."""
    low = text.lower()
    hits = []
    for token in _TOKEN.findall(low):
        parts = (token, *token.split("-")) if "-" in token else (token,)
        hits += [f"word: {p}" for p in parts if p in BANNED_WORDS]
    flat = " ".join(low.split())
    hits += [f"phrase: {p}" for p in BANNED_PHRASES if p in flat]
    if "_" in _CARD_ID.sub("", text):
        hits.append("underscore")
    if "{" in text or "}" in text:
        hits.append("brace")
    return hits


# statistics (section 10.2) ---------------------------------------------------- #
def cp_two_sided(k: int, n: int, level: float = CP_LEVEL) -> tuple[float, float]:
    """Clopper-Pearson: two-sided at `level` for k > 0; for k = 0 the one-sided upper bound (spec 7.5 item 7)."""
    if not 0 <= k <= n or n < 1:
        raise ValueError(f"report: need 0 <= k <= n and n >= 1, got k={k}, n={n}")
    if k == 0:
        return 0.0, float(stats.beta.ppf(level, 1, n))
    lo = float(stats.beta.ppf((1.0 - level) / 2.0, k, n - k + 1))
    hi = 1.0 if k == n else float(stats.beta.ppf((1.0 + level) / 2.0, k + 1, n - k))
    return lo, hi


def cp_lower(k: int, n: int, level: float) -> float:
    """The one-sided Clopper-Pearson lower bound at `level`; 0 at k = 0."""
    return 0.0 if k == 0 else float(stats.beta.ppf(1.0 - level, k, n - k + 1))


def bernstein(v: float, r: float, n: int, delta: float = DELTA) -> float:
    """The empirical Bernstein bound b_delta (Maurer-Pontil): v the ddof-1 sample variance, r the full range."""
    log_term = math.log(4.0 / delta)
    return math.sqrt(2.0 * v * log_term / n) + 7.0 * r * log_term / (3.0 * (n - 1))


def hidden_range(*, target, phi_buy, phi_sell, kappa_bound, m_max, n_checks, carry=CARRY) -> float:
    """HIDDEN_EDGE's range R of a bootstrap column, fixed before the run (section 10.3): phi_buy and phi_sell are
    scenario-scaled, kappa_bound is costs.kappa_bound (mult applied); inf when k_x = carry x kappa_bound >= 1."""
    k_x = carry * kappa_bound
    if k_x >= 1.0:
        return math.inf
    v_max = (target + carry * phi_sell) / (1.0 - k_x) * math.exp(m_max)
    c_max = k_x * v_max + carry * max(phi_buy, phi_sell)
    return v_max + n_checks * c_max


def replay_range(*, target, a_max, c_max, n_checks) -> float:
    """HIDDEN_EDGE's range R of a replay no-edge column (section 10.3); c_max is the scenario's largest daily c."""
    v_max = target * (1.0 + a_max)
    return v_max + n_checks * c_max * v_max


def hidden_edge(col, *, w0, target, l_min) -> HiddenEdge:
    """HIDDEN_EDGE on a column: red when |mean X| > bernstein(x_var, x_range, n); unavailable for GARCH-t (range
    nan), unbounded when the range fixed in advance is inf, not_applicable on an edge column (spec 7.5); DELTA is
    read at call time."""
    if not target > l_min or not w0 > 0:
        raise ValueError(f"report: hidden_edge needs target > l_min and w0 > 0, got {target}, {l_min}, {w0}")
    r = col.x_range
    if col.key.startswith(("assumed", "tested_replay")):
        return HiddenEdge(status="not_applicable", mean=col.x_mean, bound=math.nan, range_=r, n=col.n)
    if math.isnan(r):
        return HiddenEdge(status="unavailable", mean=col.x_mean, bound=math.nan, range_=r, n=col.n)
    if math.isinf(r):
        return HiddenEdge(status="unbounded", mean=col.x_mean, bound=math.inf, range_=r, n=col.n)
    b = bernstein(col.x_var, r, col.n, DELTA)
    status = "red_gain" if col.x_mean > b else "red_loss" if col.x_mean < -b else "pass"
    return HiddenEdge(status=status, mean=col.x_mean, bound=b, range_=r, n=col.n)


def ceiling_cells(cols, ceiling) -> tuple[str, float]:
    """CEILING_BREACH over the no-edge cells `cols` (first-passage counts; the caller leaves out delisting and edge
    columns): ("red", lb) when a one-sided 1 - RED_ALPHA/m lower bound is above the ceiling, ("amber", lb) when a
    95% one is, else ("", the worst 95% lower bound); m = len(cols); exact float comparisons."""
    cols = tuple(cols)
    if not cols:
        return "", 0.0
    red = max(cp_lower(c.reached, c.n, 1.0 - RED_ALPHA / len(cols)) for c in cols)
    if red > ceiling:
        return "red", red
    amber = max(cp_lower(c.reached, c.n, CP_LEVEL) for c in cols)
    return ("amber" if amber > ceiling else ""), amber


# number formats (section 10.2; Q32: no claim is rounded in its own favour) ----- #
def fmt_krw(x) -> str:
    return f"{round(float(x)):,}"


def _sf2(x: float, up: bool) -> int:
    """x (>= 10) to 2 significant figures, rounded up or down (12,406 -> 12,000 down; 20,656 -> 21,000 up)."""
    whole = math.ceil(x) if up else math.floor(x)
    q = 10 ** max(len(str(whole)) - 2, 0)
    return -(-whole // q) * q if up else whole // q * q


def _sf2_near(x: float) -> int:
    """x (>= 10) to the nearest 2 significant figures (15,873 -> 16,000)."""
    q = 10 ** max(len(str(math.floor(x))) - 2, 0)
    return math.floor(x / q + 0.5) * q


def _point(p: float, below_one: bool = True) -> str:
    """A point estimate p > 0, nearest: "about x.x%" from 1%, else "about 1 in N" (N to 2 significant figures)."""
    if p >= 0.01:
        text = f"{100.0 * p:.1f}"
        return "above 99.9%" if text == "100.0" and below_one else f"about {text}%"
    return f"about 1 in {_sf2_near(1.0 / p):,}"


def fmt_prob(k, n) -> str:
    """The point estimate k/n; k = 0 is "below about 3 in n", never zero."""
    return f"below about 3 in {n:,}" if k == 0 else _point(k / n, k < n)


def fmt_end(p: float, *, upper: bool) -> str:
    """An interval end rounded outward: an upper end up, a lower end down (Q32). p must be > 0."""
    if not p > 0:
        raise ValueError("report: an interval end of 0 prints through fmt_prob ('below about 3 in n')")
    if p >= 0.01:
        return f"{(math.ceil(1000.0 * p) if upper else math.floor(1000.0 * p)) / 10:.1f}%"
    return f"1 in {_sf2(1.0 / p, up=not upper):,}"


def fmt_ceiling(c: float) -> str:
    """The ceiling, an upper bound: "1 in floor(1/c)" below 1%, else "a ceil(1000 c)/10 % chance". The float 1/c can
    floor one off either way; a card's ceiling slot goes through _ceiling_text, whose N is exact."""
    if c < 0.01:
        return f"1 in {math.floor(1.0 / c):,}"
    return f"a {math.ceil(1000.0 * c) / 10:.1f}% chance"


def fmt_blind(x: float) -> str:
    """HIDDEN_EDGE's blind spot b / (T - L_min), an upper bound: "1 in floor(1/x)" below 1%, else points up."""
    if x < 0.01:
        return f"1 in {math.floor(1.0 / x):,}"
    return f"{math.ceil(1000.0 * x) / 10:.1f} percentage points"


def fmt_order(lb: float, c: float) -> tuple[str, str]:
    """Breach slots for lb > c, rounded so the printed order matches the comparison (an alarm is never hidden). The
    ceiling picks the format, so a ceiling below 1% never prints as 0.00%."""
    if c < 0.01:
        return f"1 in {math.floor(10.0 / lb) / 10:,.1f}", f"1 in {math.ceil(10.0 / c) / 10:,.1f}"
    return f"{math.ceil(10_000.0 * lb) / 100:.2f}%", f"{math.floor(10_000.0 * c) / 100:.2f}%"


def _pct(x: float) -> str:
    """A share or a typed rate: the nearest 0.1% from 1%, two significant figures below it (0.050%); a positive
    value never prints as 0.0% and never in scientific notation."""
    if 0 < x < 0.01:
        return f"{100.0 * x:.{1 - math.floor(math.log10(100.0 * x))}f}%"
    return f"{100.0 * x:.1f}%"


def _pct_up(x: float) -> str:
    """A cost, a resolution, a share of sessions or a gap as a percentage rounded up to 0.1%."""
    return f"{math.ceil(1000.0 * x) / 10:.1f}%"


# the report object ----------------------------------------------------------- #
_MAPPINGS = ("model_slots", "assumed", "replay", "provenance")
_SPREAD_KINDS = ("other", "krx", "blocks", "none")


def build(**fields) -> OddsReport:
    """An OddsReport with every mapping frozen; ValueError when a refused report carries numbers, or an accepted one
    has duplicate column keys, a headline that is not a column, or a spread that disagrees with its kind."""
    for name in _MAPPINGS:
        if fields.get(name) is not None:
            fields[name] = MappingProxyType(dict(fields[name]))
    for name in ("columns", "flags", "notes"):
        fields[name] = tuple(fields.get(name, ()))
    rep = OddsReport(**fields)
    keys = [c.key for c in rep.columns]
    if rep.refused is not None:
        if rep.columns or rep.flags or rep.hidden is not None or rep.spread is not None:
            raise ValueError("report: a refused report carries no numbers")
        return rep
    if len(set(keys)) != len(keys) or rep.headline not in keys:
        raise ValueError(f"report: headline {rep.headline!r} must be one of the unique column keys {keys}")
    if rep.spread_kind not in _SPREAD_KINDS or (rep.spread is None) != (rep.spread_kind == "none"):
        raise ValueError(f"report: spread {rep.spread!r} does not match its kind {rep.spread_kind!r}")
    return rep


def refusal_report(plan_obj, refusal: plan.Refusal, *, index: int = 1, count: int = 1,
                   provenance: Mapping[str, object] = MappingProxyType({})) -> OddsReport:
    """The report of a refused plan: no columns, no flags, no probability; plan_obj may be malformed or None."""
    try:
        digest = plan.plan_hash(plan_obj) if isinstance(plan_obj, plan.Plan) else ""
    except (TypeError, ValueError):        # a plan too malformed to hash (a non-finite number) still gets its card
        digest = ""
    return build(plan_hash=digest, plan_index=index, plan_count=count, refused=refusal,
                 track=str(getattr(plan_obj, "track", "")), stake=math.nan, target=math.nan, floor=math.nan,
                 l_min=math.nan, horizon_days=0, n=0, sizing="", model_key="", model_slots={}, columns=(),
                 headline="", spread=None, spread_kind="none", notes=(), ceiling=math.nan, structural_cap=None,
                 structural_sessions=None, tax_basis="", cost_words_key="", hidden=None, flags=(), assumed=None,
                 replay=None, comparison=(0, 0, 0), provenance=provenance)


# flags ----------------------------------------------------------------------- #
def flags_for(*, headline: ColumnStats, no_edge: tuple[ColumnStats, ...], engine: str, hidden: HiddenEdge | None,
              ceiling: float, structural: tuple[float, int] | None, target: float, stake: float,
              reference: float | None, rule_flags: tuple, grey: tuple[tuple[str, str, str], ...],
              series: plan.Series, okx: bool) -> tuple[Flag, ...]:
    """Every flag of the card in contract 10.1's order. rule_flags = Screening.flags; grey = (row id, cap text,
    auto_off ISO date) per grey row; structural = (cap, sessions) or None. There is no track argument, so the
    reference and below-resolution checks read the headline's first-passage count `reached` (the plain count on
    compounding cards, never below it on moonshot cards; the bracket reference estimates first passage too), and
    flag.locked's {many} is left to render, which knows the horizon."""
    flags: list[Flag] = []

    def add(code: str, level: str, key: str, **slots: str) -> None:
        flags.append(Flag(code=code, level=level, key=key, slots=MappingProxyType(slots)))

    span = (target - stake) / (1.0 - ceiling)       # = T - L_min, since ceiling = (W0 - L_min) / (T - L_min)
    if hidden is not None:
        b = hidden.bound
        if hidden.status in ("red_gain", "red_loss"):
            key = "hidden.gain" if hidden.status == "red_gain" else "hidden.loss"
            add("HIDDEN_EDGE", "red", key, x=fmt_krw(hidden.mean), b=fmt_krw(b))
        elif hidden.status == "pass" and b >= span:
            add("HIDDEN_EDGE", "info", "hidden.coarse", b=fmt_krw(b), pct=_pct_up(b / stake))
        elif hidden.status == "pass":
            add("HIDDEN_EDGE", "info", "hidden.pass", b=fmt_krw(b), pct=_pct_up(b / stake), m=fmt_blind(b / span))
        elif hidden.status in ("unavailable", "unbounded"):
            add("HIDDEN_EDGE", "info", "hidden." + hidden.status)
        else:
            add("HIDDEN_EDGE", "info", "hidden.na")
    level, lb = ceiling_cells(no_edge, ceiling)
    if level:
        shown_lb, shown_c = fmt_order(lb, ceiling)
        add("CEILING_BREACH", level, "breach." + level, lb=shown_lb, c=shown_c)
    k = headline.reached
    # a zero reference (its grid never reaches T) prints nothing: no probability slot renders as zero
    if reference is not None and reference > 0 and cp_two_sided(k, headline.n)[0] > reference:
        add("ABOVE_ESTIMATED_REFERENCE", "amber", "flag.reference", ref=_point(reference))
    if structural is not None and target > stake * structural[0]:
        add("IMPOSSIBLE", "info", "structural.impossible", cap=f"{math.ceil(structural[0]):,}",
            s=f"{structural[1]:,}")
    elif k == 0 and headline.trades > 0:
        add("BELOW_RESOLUTION", "info", "")
    for row, cap, off in grey:
        add("GREY_LEG", "amber", "flag.grey", row=row, cap=cap, off=off)
    if okx:
        add("PROXY_DATA", "info", "flag.proxy")
    if series.proxy_dates:
        add("PROXY_DATA", "info", "flag.proxyfx", d0=series.proxy_dates[0], d1=series.proxy_dates[1])
    if engine == "bootstrap":
        add("CHECKS_AT_OPEN_CLOSE", "info", "flag.openclose")
    else:
        add("CLOSE_ONLY_CHECKS", "info", "flag.closeonly")
    if headline.band_edge_sessions > 0:
        add("BAND_EDGE_SESSIONS", "info", "flag.bandedge", count=f"{headline.band_edge_sessions:,}",
            share=_pct_up(headline.band_edge_share))
    if headline.worst_gap > 0:
        add("LIMIT_GAP", "info", "flag.gap", gap=_pct_up(headline.worst_gap))
    if headline.locked_at_horizon > 0:
        add("LOCKED_AT_HORIZON", "info", "flag.locked", p=fmt_prob(headline.locked_at_horizon, headline.n))
    if headline.mean_cost >= COST_DOMINATED_SHARE * stake:
        add("COST_DOMINATED", "amber", "flag.cost", cost=fmt_krw(headline.mean_cost),
            pct=_pct_up(headline.mean_cost / stake))
    for when, what, row in rule_flags:
        if what == "review_by":
            add("RULE_CHANGE_IN_HORIZON", "amber", "rule.review", date=when.isoformat(), row=row)
        else:
            add("RULE_CHANGE_IN_HORIZON", "amber", "rule.end", date=when.isoformat(), row=row,
                what=say("rule.auto" if what == "auto_off" else "rule.until"))
    return tuple(flags)


# rendering (section 10.4 render order) --------------------------------------- #
_TAX_KEYS = {"krx_small_holder_exempt": "tax.krx", "overseas_22pct_over_2.5m": "tax.overseas",
             "crypto_22pct_from_2027": "tax.crypto"}
_MEMBER_KEYS = {"bootstrap": "member.bootstrap", "bootstrap_half": "member.half",
                "bootstrap_double": "member.double", "garch_t": "member.garch", "garch_refit": "member.refit"}
_LABEL_KEYS = {"bootstrap": "label.bootstrap", "garch_t": "label.garch", "replay": "label.replay"}
_EDGE_KEYS = {"none": "edge.none", "assumed": "edge.assumed", plan.REPLAY_SOURCE: "edge.replay"}
_RUNG_KEYS = ("ladder.p10", "ladder.p25", "ladder.x2", "ladder.x10")          # one per LADDER entry
_SUB_PREFIX = {"UNSUPPORTED_PRODUCT": "sub.", "DATA_INVALID": "data.", "SCREEN_BLOCKED": "screen."}
_BASE_RATES = ("baserate.kalshi", "baserate.esma", "baserate.sebi", "baserate.krderiv", "baserate.kr2020")
_NOT_IN = ("notin.tax", "notin.fx", "notin.upbit", "notin.freeze", "notin.delist", "notin.krx", "notin.intraday",
           "notin.unfilled", "notin.broker", "notin.hacked", "notin.rules")
_PROV_LINES = (("prov.code", ("code_hash",)), ("prov.signed", ("code_signed",)),
               ("prov.owner", ("owner_seq", "owner_row")), ("prov.key", ("fingerprint",)),
               ("prov.tables", ("rules_sha", "instruments_sha", "venues_sha", "state_hash")),
               ("prov.data", ("series_md5", "components", "proxy_dates")),
               ("prov.calendar", ("calendar_version", "calendar_sha", "calendar_md5s")),
               ("prov.seed", ("seed_hex",)), ("prov.paths", ("n", "chunk")),
               ("prov.versions", ("numpy", "scipy", "cryptography")), ("prov.repo", ("repo_anchor",)),
               ("prov.tree", ("tree_hash",)), ("prov.comparison", ("comparison_id", "run_counter")),
               ("prov.model", ("model", "members")), ("prov.edge", ("edge_source",)))
_PROV_HASHES = frozenset({"code_hash", "owner_row", "fingerprint", "rules_sha", "instruments_sha", "venues_sha",
                          "state_hash", "series_md5", "calendar_sha", "seed_hex", "tree_hash"})
_PROV_COUNTS = frozenset({"owner_seq", "n", "chunk", "run_counter"})


def _words(h: int) -> dict[str, str]:
    """The {one} / {many} slots: a month for a 28- to 31-day horizon, else an h-day period."""
    if 28 <= h <= 31:
        return {"one": say("period.month"), "many": say("period.months")}
    return {"one": say("period.day", h=h), "many": say("period.days", h=h)}


def _plain_count(track: str, col: ColumnStats) -> int:
    """Q32: REACHED outcomes on moonshot cards, first passages on compounding cards."""
    return col.reached_outcome if track == "moonshot" else col.reached


def _ceiling_text(rep: OddsReport) -> str:
    """The ceiling slot {c}: below 1% "1 in N" with N = bold.ceiling_one_in, exact (floor(1 / c) of the float
    ceiling can print N - 1 or N + 1), else fmt_ceiling's percentage."""
    if rep.ceiling < 0.01:
        return f"1 in {bold.ceiling_one_in(rep.stake, rep.l_min, rep.target):,}"
    return fmt_ceiling(rep.ceiling)


def _target_p(rep: OddsReport, col: ColumnStats, k: int) -> str:
    """A target probability slot: the point estimate, or cap.p when it is above the ceiling and no breach fired."""
    if k / col.n > rep.ceiling and not any(f.code == "CEILING_BREACH" for f in rep.flags):
        return say("cap.p", c=_ceiling_text(rep), k=f"{k:,}", n=f"{col.n:,}")
    return fmt_prob(k, col.n)


def _structural(rep: OddsReport, col: ColumnStats, words) -> str | None:
    """Q44: the IMPOSSIBLE or no-trade sentence that replaces every probability of the target, else None."""
    for f in rep.flags:
        if f.code == "IMPOSSIBLE":
            return say(f.key, **f.slots)
    return say("structural.notrade", **words) if col.trades == 0 else None


def _spread_text(rep: OddsReport, n: int) -> str:
    """Q31: the spread wording of the members actually run, outward ends, then each dropped member's note."""
    if rep.spread is None:
        text = say("spread.none")
    else:
        lo, hi = rep.spread
        low = fmt_prob(0, n) if lo <= 0 else fmt_end(lo, upper=False)
        text = say("spread." + rep.spread_kind, a=fmt_end(hi, upper=True), b=low)
    for member, check in rep.notes:
        text += "; " + say("spread.dropped", member=say(_MEMBER_KEYS[member]), check=say("check." + check))
    return text


def _bugs(rep: OddsReport, width: float) -> str:
    """Q32: bugs.finer only when HIDDEN_EDGE passed and its blind spot is below the headline interval's width."""
    h = rep.hidden
    if h is None or h.status != "pass" or not h.bound / (rep.target - rep.l_min) < width:
        return say("bugs.coarser")
    return say("bugs.finer")


def _typical(col: ColumnStats, words) -> list[str]:
    out = [say("typical.median", median=fmt_krw(col.median), **words)]
    if col.at_floor > 0:
        out.append(say("typical.floor", p=fmt_prob(col.at_floor, col.n), lo=fmt_krw(col.kept_lo),
                       hi=fmt_krw(col.kept_hi), **words))
    else:
        out.append(say("typical.nofloor", **words))
    return out


def _average(rep: OddsReport, col: ColumnStats, words, *, edge: bool, delist: bool = False) -> str:
    """Spec 7.5 item 2: agrees within 2 x g_se of the stake minus the average cost; edge columns state gain or loss."""
    if edge:
        if col.mean > rep.stake:
            return say("average.gain", gain=fmt_krw(col.mean - rep.stake), **words)
        return say("average.loss", loss=fmt_krw(rep.stake - col.mean), **words)
    costwords = say(rep.cost_words_key)
    if delist:
        costwords = say("cost.delist", base=costwords)
    expected = rep.stake - col.mean_cost
    if abs(col.mean - expected) <= 2.0 * col.g_se:
        return say("average.agrees", expected=fmt_krw(expected), costwords=costwords, cost=fmt_krw(col.mean_cost),
                   mean=fmt_krw(col.mean), se=fmt_krw(col.mean_se), **words)
    return say("average.differs", mean=fmt_krw(col.mean), se=fmt_krw(col.mean_se), costwords=costwords,
               expected=fmt_krw(expected))


def _headline_lines(rep: OddsReport, col: ColumnStats, words, structural: str | None) -> list[str]:
    """The headline pair; under a structural sentence (Q44) only the floor line (the sentence prints in the plain
    sentence's place, after the ladder)."""
    floor = say("headline.floor", p=fmt_prob(col.at_floor, col.n))
    if structural is not None:
        return [floor]
    if rep.track == "moonshot":
        head = say("headline.moonshot", target=fmt_krw(rep.target), p=_target_p(rep, col, col.reached_outcome))
    else:
        head = say("headline.compounding", target=fmt_krw(rep.target), k=f"{col.reached:,}", n=f"{col.n:,}",
                   pk=_target_p(rep, col, col.reached), k2=f"{col.ended_at_or_above:,}",
                   pk2=_target_p(rep, col, col.ended_at_or_above), **words)
    return [head, floor]


def _ladder_lines(rep: OddsReport, col: ColumnStats) -> list[str]:
    """The ladder: every rung above stake x the structural cap is IMPOSSIBLE; after no trade no rung prints."""
    tail = [say("ladder.spread", median=fmt_krw(col.median), p5=fmt_krw(col.p5))]
    if col.trades == 0:
        return tail
    cap = rep.structural_cap
    rungs = [(key, m * rep.stake) for key, m in zip(_RUNG_KEYS, LADDER)] + [("ladder.target", rep.target)]
    out = [say("ladder.head")]
    for (key, value), k in zip(rungs, col.rungs):
        label = say(key)
        if cap is not None and value > rep.stake * cap:
            out.append(say("ladder.impossible", label=label, value=fmt_krw(value)))
        else:
            p = _target_p(rep, col, k) if key == "ladder.target" else fmt_prob(k, col.n)
            out.append(say("ladder.rung", label=label, value=fmt_krw(value), p=p))
    return out + tail


def _plain_line(rep: OddsReport, col: ColumnStats, words) -> str:
    k = _plain_count(rep.track, col)
    lo, hi = cp_two_sided(k, col.n)
    common = {"n": f"{col.n:,}", "target": fmt_krw(rep.target), "spread": _spread_text(rep, col.n),
              "bugs": _bugs(rep, hi - lo), **words}
    if k == 0:
        return say("plain.none", **common)
    return say("plain.hit", k=f"{k:,}", about=_target_p(rep, col, k), hi=fmt_end(hi, upper=True),
               lo=fmt_end(lo, upper=False), **common)


def _ceiling_line(rep: OddsReport, floor_key: str, nofloor_key: str) -> str:
    return say(floor_key if rep.sizing == "floor_safe" else nofloor_key, c=_ceiling_text(rep))


def _replay_lines(rep: OddsReport) -> list[str]:
    """The tested column's lead and growth lines (Q38), from the replay card's own figures."""
    r = rep.replay
    return [say("replay.lead", y0=f"{int(r['y0'])}", y1=f"{int(r['y1'])}", cut=f"{round(100.0 * r['cut'])}",
                bench=f"{r['bench_sr']:.2f}", cutsr=f"{r['haircut_sr']:.2f}", diff=f"{r['diff']:+.2f}",
                lo=f"{r['ci_lo']:+.2f}", hi=f"{r['ci_hi']:+.2f}"),
            say("replay.growth", h=f"{int(r['h'])}", g=f"{100.0 * r['growth']:.1f}%",
                g0=f"{100.0 * r['growth_iid']:.1f}%")]


def _column_lines(rep: OddsReport, words) -> list[str]:
    """The other columns in report order: stress 2x, delisting, assumed, tested replay (Q29-Q31, Q38). The assumed
    column prints spec 7.5's three sentences together (lead, brackets, ceiling), then its typical and average."""
    stress = rep.headline.rsplit("/", 1)[0] + "/stress2x"
    out: list[str] = []
    for col in rep.columns:
        if col.key == stress:
            out += [say("column.stress"), *_typical(col, words), _average(rep, col, words, edge=False)]
        elif col.key in ("delist_30", "delist_100"):
            out += [say("column.delist", symbol=rep.model_slots["symbol"], h=col.key.split("_")[1]),
                    *_typical(col, words), _average(rep, col, words, edge=False, delist=True)]
        elif col.key == "assumed":
            a = rep.assumed
            out.append(say("assumed.lead", w=_pct(a["w"]), p0=_pct(a["p0"]), u=_pct(a["u"])))
            out.append(say("assumed.nb", nb=f"{math.ceil(a['nb']):,}") if a["nb"] <= a["resolved"]
                       else say("assumed.nbmany", r=f"{int(a['resolved']):,}"))
            out += [_ceiling_line(rep, "assumed.ceiling", "assumed.ceilingnf"), *_typical(col, words),
                    _average(rep, col, words, edge=True), say("hidden.na")]
        elif col.key == "tested_replay/base":
            out += [*_replay_lines(rep), *_typical(col, words), _average(rep, col, words, edge=True),
                    _ceiling_line(rep, "ceiling.edge", "ceiling.edgenf"), say("hidden.na")]
    return out


def _card(rep: OddsReport) -> list[str]:
    """Everything between the plan head and the footer of an accepted report, in section 10.4's order."""
    col = next(c for c in rep.columns if c.key == rep.headline)
    words = _words(rep.horizon_days)
    structural = _structural(rep, col, words)
    out = [say(f.key, **{**words, **f.slots}) for f in rep.flags if f.level == "red"]
    out.append(say(rep.model_key, **rep.model_slots))
    if rep.replay is not None:
        out.append(say("replay.noedge"))
    out.append(say("sizing.floor" if rep.sizing == "floor_safe" else "sizing.stop", floor=fmt_krw(rep.floor)))
    if "cap" in rep.model_slots:
        out.append(say("okx.cap", **rep.model_slots))
    if rep.tax_basis == "overseas_22pct_over_2.5m":
        out.append(say("fx.us"))
    if rep.replay is not None and math.isfinite(rep.replay.get("fstar", math.nan)):
        out.append(say("kelly.label"))
    out += _typical(col, words)
    out.append(_average(rep, col, words, edge=False))
    out += _headline_lines(rep, col, words, structural)
    out += _ladder_lines(rep, col)
    out.append(_plain_line(rep, col, words) if structural is None else structural)
    out.append(say(_TAX_KEYS[rep.tax_basis]))
    out.append(_ceiling_line(rep, "ceiling.noedge", "ceiling.nofloor"))
    out.append(say("research.estimate"))
    out += [say(key) for key in _BASE_RATES]
    out += _column_lines(rep, words)
    for level in ("amber", "info"):
        out += [say(f.key, **{**words, **f.slots}) for f in rep.flags
                if f.level == level and f.key and f.code != "IMPOSSIBLE"]
    out += [say("notin.title"), *("- " + say(key) for key in _NOT_IN), say("notin.close")]
    out.append(say("limits.injected"))
    k, j, r = rep.comparison
    out += [say("compare.k", k=f"{k:,}", j=f"{j:,}"), say("compare.r", r=f"{r:,}")]
    if rep.track == "moonshot":
        out.append(say("compare.caption"))
    out.append(say("compare.fresh"))
    return out


def _why(ref: plan.Refusal) -> str:
    """The refusal sentence: the code's why.* text with its sub-reason and its number, date, symbol or row slots."""
    slots = dict(ref.slots)
    if ref.code in _SUB_PREFIX:
        slots["what"] = say(_SUB_PREFIX[ref.code] + ref.sub, **slots)
    elif ref.code == "MODEL_CHECK_FAILED":
        slots["check"] = say("check." + (ref.sub or slots.get("check", "")))
    return say("why." + ref.code, **slots)


def _prov_value(key: str, value) -> str:
    if key in _PROV_HASHES:
        return str(value).removeprefix("SHA256:")[:16]
    if key in _PROV_COUNTS:
        return f"{int(value):,}"
    if key == "code_signed":
        return say("label.yes" if value is True else "label.no")
    if key in ("components", "calendar_md5s"):
        return ", ".join(str(md5)[:16] for _, md5 in value)       # never a label or a file id (they hold "_")
    if key == "proxy_dates":
        return " / ".join(value)
    if key == "model":
        return say(_LABEL_KEYS[value])
    if key == "members":
        return ", ".join(say(_MEMBER_KEYS[m]) for m in value)
    if key == "edge_source":
        return say(_EDGE_KEYS[value])
    return str(value)                  # versions, repo_anchor, comparison_id, calendar_version


def _prov_lines(prov: Mapping[str, object]) -> list[str]:
    """Q14: hashes (16 hex), versions, dates, counts, the repo anchor, the comparison id and catalogue labels only."""
    out = []
    for label, keys in _PROV_LINES:
        values = [_prov_value(k, prov[k]) for k in keys if prov.get(k) not in (None, "", ())]
        if values:
            out.append(say("prov.line", label=say(label), value=" / ".join(values)))
    return [say("prov.head"), *out] if out else []


def render(rep: OddsReport) -> str:
    """The card text (section 10.4's order); ValueError when the text fails the language guard (the CLI exits 4)."""
    lines = [say("plan.head", i=f"{rep.plan_index:,}", k=f"{rep.plan_count:,}",
                 hash=rep.plan_hash[:16] or say("edge.none"))]
    if rep.refused is not None:
        lines += [say("refused.head", why=_why(rep.refused)), say("refused.none")]
    else:
        lines += _card(rep)
    lines.append(say("footer"))
    lines += _prov_lines(rep.provenance)
    text = "\n".join(lines) + "\n"
    hits = guard(text)
    if hits:
        raise ValueError(f"rendered text failed the language guard: {hits[:5]}")
    return text
```

  3d. Check the result: it parses, lists 70 top-level names in this order (`CATALOGUE` is an annotated assignment,
  which the check skips), holds no CR byte, and (when Task 9's file was exactly its plan text, its two-line
  `brackets` comment naming the amended contract 10.1 idiom included) has the sha256 the drafting sandbox computed
  from Task 9's Step 3 block and Edits 1 and 2 here. Run the overlap check of Step 2 first (PowerShell tool; it must
  print nothing), then
  from the repo root in Git Bash:

```bash
.venv/Scripts/python.exe -I -c "import ast, hashlib; b = open('core/odds/report.py', 'rb').read(); t = ast.parse(b.decode('utf-8')); n = [getattr(x, 'name', None) or x.targets[0].id for x in t.body if isinstance(x, (ast.ClassDef, ast.FunctionDef, ast.Assign))]; print(len(n), n[:12], n[-1], b.count(b'\r'), hashlib.sha256(b).hexdigest())"
```

  Expected: `70 ['LADDER', 'COST_DOMINATED_SHARE', 'CP_LEVEL', 'DELTA', 'RED_ALPHA', 'CARRY', 'ColumnStats',
  'HiddenEdge', 'Flag', 'OddsReport', 'BANNED_WORDS', 'BANNED_PHRASES'] render 0
  4bb51b738c9e434523cba74528b1abc8801adef35ff29809fdf53b41dd482006` (1,059 lines). A different hash after a recorded
  drift ruling is expected; then the count, the names and the `0` (no CR byte) must still match.

- [ ] **Step 4: Run to verify it passes**

  Run the overlap check of Step 2 (PowerShell tool; it must print nothing) before EACH Python command below. All
  run from the repo root in Git Bash.

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_report/
```

  Expected: 41 PASS lines, then `41/41 passed, 0 failed, 0 not run` (exit code 0; about 6 s of tests in the drafting
  sandbox, budget 12 s).

  The suites that build `ColumnStats` through the engine must be unchanged (each ends `N/N passed, 0 failed, 0 not
  run` with the same N as at the end of its own task: Task 9, 10 and 11 respectively):

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_simulate/
.venv/Scripts/python.exe -m tests.odds_acceptance odds_locks/
.venv/Scripts/python.exe -m tests.odds_acceptance odds_bold/
```

  Guards (each ends with `0 failed, 0 not run`): the odds guards (allowlist imports, no clock, no I/O, no re-export,
  flat package) and the compliance guards and store, which scan `core/odds` raw text, the catalogue included:

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_guards/
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_guards/
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_store/
```

  Core-wide scans (this task changes `core/`; each must end with no FAIL): T-RO-01, T-TF-GOV-06 (the `haircut_sr`
  key sits beside no 0.4 multiplier), the Kish scan, T-TREND-04, the r18 names, then the cockpit suite (test_08,
  test_09, test_16 for the UTF-8 catalogue, test_18), restoring the results file afterwards:

```bash
.venv/Scripts/python.exe -m tests.macro_m0_harness
.venv/Scripts/python.exe -m tests.macro_tf_gov
.venv/Scripts/python.exe -m tests.macro_m7_ledger
.venv/Scripts/python.exe -m tests.macro_m8_forward
.venv/Scripts/python.exe -m tests.macro_m6_context
KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' ANTHROPIC_API_KEY='<unset>' GS_CLIENT_ID='<unset>' GS_CLIENT_SECRET='<unset>' FINVIZ_API_KEY='<unset>' ALPACA_API_KEY='<unset>' ALPACA_SECRET_KEY='<unset>' FXMACRODATA_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite cockpit; echo "exit $?"; git checkout -- qa/acceptance_results.json
git status --short
```

  Expected `git status --short`: exactly ` M core/odds/report.py`, `?? tests/odds_report.py` and the one allowed
  `?? docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md` line. Add the odds_report run time to the
  ledger's "Runs" section.

- [ ] **Step 5: Commit**

```bash
git add core/odds/report.py tests/odds_report.py
git grep -n -i -E "order_cash|order-cash|place_order|submit_order|tttc0802u|tttc0801u|vttc0802u|private_key|seed_phrase|/v1/orders|/v1/withdraws|/v1/deposits|/api/v3/order|/sapi/v1/capital|/uapi/|r18_research_log|r18_break_log|context_log/|tests\.reference|reference_mode|reference_only" -- core/odds/report.py
git grep -n -E "CANO|KIS_ACCOUNT|ACNT_PRDT_CD|0\.4 *[*x]|kish|__import__|import_module|\bexec\b|\beval\b|\bopen\(" -- core/odds/report.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  Both `git grep` commands print nothing (exit code 1; they run after the `git add` because `git grep` does not
  search untracked files): no banned word, route, 40% literal or dynamic call in the catalogue or the code. The two
  stat outputs must be identical (both files are LF): `core/odds/report.py | 1016 +++-` (1013 insertions,
  3 deletions), `tests/odds_report.py | 876 +++`, `2 files changed, 1889 insertions(+), 3 deletions(-)`. Then:

```bash
git commit -m "feat(odds): report catalogue, honest number formats, flags and language guard" -m "Odds plan Task 12 (spec 7.5; O14, R2-4, R2-7; Q14, Q32, Q37, Q43, Q44, Q46): one sentence catalogue, Clopper-Pearson and empirical Bernstein, outward formats, every flag, render with its own guard, refusal cards with no number." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
