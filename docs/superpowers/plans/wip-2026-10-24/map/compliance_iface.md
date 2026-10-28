# Area: compliance_iface — the built compliance interfaces the odds engine consumes

Verified against the tree at git main 995534b (clean). Line numbers are 1-based. "Probe" means a read-only snippet run
with `.venv/Scripts/python.exe -I` on the shipped drafts and a hand-sealed in-memory Context (no file written, no
network); probe scripts are in the scratchpad `odds_plan/probe_screen.py`, `probe2.py` and `probe3.py`.

## gate.screen()

* [screen signature] `screen(plan, ctx, first_stake_krw: float) -> model.Screening`. It never raises: any exception
  becomes a BLOCK Screening with reason "state: internal error <type>".
  EVIDENCE: core/compliance/gate.py:611 `def screen(plan, ctx, first_stake_krw: float) -> model.Screening:`;
  gate.py:616-619 `try: return _screen(plan, ctx, first_stake_krw) except Exception as exc: return _screening(_fallback(None, ctx, f"state: internal error {type(exc).__name__}"), (), None)`
  IMPACT: The odds engine calls it exactly so, as positional (plan, ctx, stake). It must read the verdict from the
  returned Screening, never rely on an exception.

* [P3 duck typing, exact reads] screen reads only `plan.leg`, `leg.venue`, `leg.symbol`, `plan.start` and
  `plan.horizon_days`, each through getattr with a default of None. A plan without a leg gives the malformed
  venue/symbol/asset/counter_symbol reasons, and does not crash.
  EVIDENCE: gate.py:623-625 `leg = getattr(plan, "leg", None)` / `venue_id, symbol = getattr(leg, "venue", None), getattr(leg, "symbol", None)` / `start, horizon = getattr(plan, "start", None), getattr(plan, "horizon_days", None)`;
  probe: no leg gave `('malformed: venue', 'malformed: symbol', 'malformed: asset', 'malformed: counter_symbol')`
  IMPACT: core/odds/plan.py's Plan/Leg must name these four attributes exactly (spec 7.1 does: `venue: str; symbol: str`,
  `start: date; horizon_days: int`, `leg: Leg`). The probe confirmed that a frozen kw_only dataclass Plan/Leg works (ALLOW).
  The model, bracket, sizing, edge_source and fraction fields are invisible to the gate.

* [start must be exactly datetime.date and equal ctx.date] `type(start) is model.date` is required, so a `datetime`
  (a date subclass) or a pandas Timestamp fails with "malformed: plan". A start different from ctx.date fails with
  "malformed: plan start".
  EVIDENCE: gate.py:636-639 `if type(start) is not model.date or type(horizon) is not int or horizon <= 0:` ... `["malformed: plan"]` / `if start != ctx.date:` ... `["malformed: plan start"]`;
  model.py:14 `from datetime import date, datetime, timezone`; probe: `datetime start ('malformed: plan',)`,
  `later start ('malformed: plan start',)`
  IMPACT: Plan.start must be a plain `datetime.date` equal to the Asia/Seoul date of the `now` that was passed to
  load_context. A plan cannot be screened for a future start (P37), so the odds engine must either refuse a start
  other than today or build the context for that day. Its tests must use the fixture ctx date (2026-10-23) as
  plan.start.

* [horizon_days strictly int > 0] `type(horizon) is not int` rejects bool and numpy integers.
  EVIDENCE: gate.py:636; probe: `np.int64 horizon: ('malformed: plan',)`, `bool horizon ('malformed: plan',)`
  IMPACT: plan.py whitelist validation must store `int(horizon_days)` and refuse bool, so that a valid plan never
  reaches screen as malformed.

* [stake type strictness: numpy floats are malformed] The stake becomes `Intent.notional_krw`, checked by gate
  `_number`: `type(value) is float` (finite) or `type(value) is int` (|v| < 2**63). A `numpy.float64` stake is
  therefore BLOCK "malformed: notional_krw".
  EVIDENCE: gate.py:516-519 `def _number(value) -> bool: if type(value) is float: return math.isfinite(value) / return type(value) is int and abs(value) < 2 ** 63`;
  gate.py:117-118 `if not (_number(intent.notional_krw) and intent.notional_krw >= 0): bad.append("notional_krw")`;
  probe: `np.float64 stake: ('malformed: notional_krw',)`, `int stake: ALLOW`
  IMPACT: The odds engine computes stakes with numpy, so it must pass `float(stake)` (a Python float) to screen.
  A test should pin that a numpy stake is converted before the call.

* [zero stake is malformed] For new exposure, `notional_krw > 0` is required. 0, a negative value and NaN all give
  BLOCK, kind "malformed", reason "malformed: notional_krw". The ledger carries this to the odds plan.
  EVIDENCE: gate.py:62-67 `if kind == "new_exposure": ... more += [] if intent.notional_krw > 0 else ["malformed: notional_krw"]`;
  docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:244 `Final: carried — odds plan must not send a zero stake to screen() (it now reports malformed: notional_krw)`;
  probe: `stake 0.0 BLOCK malformed ('malformed: notional_krw',)`, likewise for -1.0 and nan
  IMPACT: STUCK_AT_START (no affordable first stake, after lot rounding and the venue minimum) must be decided by
  the odds engine BEFORE screen is called, and screen must never be called with 0. The odds acceptance suite needs
  a test that a stuck plan yields STUCK_AT_START and not a gate "malformed" refusal.

* [the intent screen builds] screen decides a synthetic cash `buy`: quantity 1.0 (nominal), notional = stake,
  counter = `venue.quote_for(inst)`, and asset and multiple from the approved map. With no venue facts or no map
  entry it uses `""` and 0.0, which decide() reports as malformed.
  EVIDENCE: gate.py:630-633 `# quantity is nominal: a buy's verdict depends on its notional, never on its units` / `intent = Intent(venue=venue_id, symbol=symbol, counter_symbol=venue.quote_for(inst) if inst is not None else "", asset=inst.asset if inst is not None else "", multiple=inst.multiple if inst is not None else 0.0, action="buy", quantity=1.0, notional_krw=first_stake_krw)`
  IMPACT: The stake must be the KRW notional of the first entry; units are irrelevant. On OKX the counter is the
  default quote USDT, never KRW. The odds engine can rebuild this exact Intent to check
  `screening.decision.intent_hash` (probe: `intent hash reproducible True`).

* [no usable state: early return] When ctx is sealed but the owner log is not OK or ctx.active is unusable, screen
  returns BLOCK, kind "new_exposure", with the `_why_no_active` reason, no flags, and window (start, horizon). It
  never calls decide().
  EVIDENCE: gate.py:627 `state = ctx.active if sealed and ctx.owner.ok and _usable(ctx.active) else None`; gate.py:640-642 `if state is None: ... _decision(intent, ctx, None, BLOCK, "new_exposure", [_why_no_active(ctx)])`;
  gate.py:486-489 `return f"state: owner log {ctx.owner.reason or ctx.owner.status}"` / `return f"state: {ctx.active.reason or 'no approved state'}"`;
  probe: `broken BLOCK new_exposure ('state: owner log no owner key yet: owner act 1',) False`
  IMPACT: In the real home today (there is no owner_pubkey.pem; see below) every odds run is refused by the gate.
  The odds engine must word this "state: ..." refusal for the owner and print no probability (spec 9). The reason
  text starts with "state: ".

* [unsealed context] A context that load_context did not seal gives decide's BLOCK "state: context not from
  load_context", with flags () and window None.
  EVIDENCE: gate.py:634-635 `if not sealed: return _screening(decide(intent, ctx), (), None)`; gate.py:47-48; probe: `unsealed ('state: context not from load_context',) ()`
  IMPACT: The odds engine can never hand-build a Context. Production code must use owner.load_context, and tests use
  tests/compliance_fixtures.ctx() (which calls seal_context from tests/, where the guard allows it).

* [unsigned code blocks screening] new exposure needs `ctx.code_signed is True`; otherwise BLOCK "unsigned code".
  EVIDENCE: gate.py:423-426 `out = [] if ctx.owner.ok and _usable(ctx.active) and state is ctx.active else [_why_no_active(ctx)]` / `return out + ([] if ctx.code_signed is True else ["unsigned code"])`; probe: `unsigned BLOCK ('unsigned code',)`
  IMPACT: See the code-hash finding: adding any core/odds/*.py changes the code hash, so screening is BLOCK
  "unsigned code" until the owner signs a new code_approved.

* [RULE_CHANGE_IN_HORIZON source: Screening.flags] For every venue row matching the leg (via gate._matches with
  the derived class), each of review_by, auto_off and effective_until with `start <= date < start + horizon_days` is
  flagged as (date, field, row_id), sorted. `exit_date` is the earliest flag date. The literal string
  "RULE_CHANGE_IN_HORIZON" does not appear in code.
  EVIDENCE: gate.py:643-651 `first, end = start.toordinal(), start.toordinal() + horizon` ... `for what, when in (("review_by", row.review_by), ("auto_off", row.auto_off), ("effective_until", row.effective_until)): if when is not None and first <= when.toordinal() < end: flags.append((when, what, row.id))` / `return _screening(decide(intent, ctx), tuple(sorted(flags)), (start, horizon))`;
  gate.py:657 `exit_date = flags[0][0] if flags else None`; grep: RULE_CHANGE_IN_HORIZON appears only in the spec (lines 538 and 900)
  IMPACT: report.py raises RULE_CHANGE_IN_HORIZON exactly when `screening.flags` is non-empty, naming each
  (date, field, row). simulate.py force-exits at `screening.exit_date`, or at the next check point when that date is
  not a session (spec 6.3).

* [practical effect: every plan longer than about a month is cut at review_by] Monthly cadence keeps review_by at
  most 31 days after the latest review, and every row in the shipped table has review_by 2026-11-22 or 2026-11-23.
  A 60-day plan from 2026-10-24 gets exit_date 2026-11-22 (crypto, OKX, BITO) or 2026-11-23 (KIS share and etp_1x).
  A 10-day plan gets no flag.
  EVIDENCE: rules.py:524-525 `if (review_by - latest).days > _MAX_REVIEW_DAYS: # P15: monthly`; probe: `kis 005930 ALLOW ... flags= ((datetime.date(2026, 11, 23), 'review_by', 'KR-KIS-KRX-SHARE'),) exit= 2026-11-23`,
  `upbit BTC ALLOW ... flags= ((datetime.date(2026, 11, 22), 'review_by', 'KR-DOMESTIC-SPOT'),)`,
  `upbit short horizon () None`; shipped table: `review_by range 2026-11-22 2026-11-23`
  IMPACT: For any horizon over about 30 days the simulation exits at the review date, by spec 6.3 as built. The
  plan must state this, test a forced exit at a rule date (spec 8 odds 4 "a forced exit at a rule date"), and word
  it for the owner (a review date is not a rule change). Whether a review_by (as opposed to an auto_off or an
  effective_until) should force an exit is listed in the open questions.

* [flags ignore effective_from] The flag scan covers matching venue rows whatever their effective_from, and never
  flags an effective_from inside the window. A row that STARTS mid-horizon (for example a future hard_block) is not
  flagged. No shipped row has a future effective_from today.
  EVIDENCE: gate.py:645-648 (only the three fields listed); shipped table: `max effective_from 2026-10-23`, `future-effective []`
  IMPACT: This gap belongs in the compliance follow-up plan: flag effective_from in [start, end) too, or document it.
  Today nothing is lost.

* [Screening type] Screening is a frozen dataclass with fields decision, allowed, flags, exit_date and
  screening_hash. The window is hashed but not stored as a field. `allowed` means verdict in (ALLOW, ACK_REQUIRED).
  The hash is the sha256 of the canonical JSON of {decision, allowed, flags, exit_date, window}.
  EVIDENCE: model.py:213-219 `class Screening: decision: Decision / allowed: bool # verdict in (ALLOW, ACK_REQUIRED) / flags: tuple[tuple[date, str, str], ...] / exit_date: date | None / screening_hash: str`;
  gate.py:654-660 `allowed = d.verdict in (ALLOW, ACK_REQUIRED)` / `body = {"decision": d, "allowed": allowed, "flags": flags, "exit_date": exit_date, "window": window}`;
  probe: recomputing the hash with window=(plan.start, plan.horizon_days) gave `hash reproducible True`
  IMPACT: To "refuse an unscreened plan" (spec 4 step 3), simulate() can recompute the screening_hash from the
  Screening's fields plus (plan.start, plan.horizon_days), check allowed, check `decision.date == plan.start`, and
  check that decision.intent_hash matches the rebuilt buy Intent. A Screening is NOT registered the way permits and
  contexts are, so a hand-built one is detectable only by these recomputations (this is discipline, not security).

* [Decision fields] verdict, kind, reasons, warnings, intent_hash, state_hash, code_hash, owner_head, ctx_hash,
  date, decision_id and ack. decision_id is the sha256 of all the other fields. ack is (row_id, warning_sha256)
  only when the verdict is ACK_REQUIRED.
  EVIDENCE: model.py:181-199 `class Decision:` ... `ack: tuple[str, str] | None = None # (row_id, warning_sha256) when the verdict is ACK_REQUIRED`; gate.py:546-552 `ack=ack if verdict == ACK_REQUIRED else None`
  IMPACT: The report's provenance can take code_hash, owner_head, state_hash and ctx_hash straight from
  screening.decision. Refusal text comes from decision.reasons, strictest first.

* [reason strings and severity order] Exact prefixes: "conduct: ", "floor: ", "malformed: <field>", "state: <why>",
  "unsigned code", "no row", "stale: review by <date> passed (<id>)", "hard_block: <id>", "out_of_scope: <id>",
  "needs live broker evidence (execution spec): <id>", "requires <item>: <id>", "auto_off <date>: <id>",
  "cap unset: <id>", "cap exceeded: <id>", "leverage <x> above <max>: <id>", "ack required: <id>", and "destination: ...".
  Reasons are sorted conduct, floor, malformed, state, unsigned code, then the rest as produced, with ack required
  last and duplicates dropped.
  EVIDENCE: gate.py:29 `_RANKS = ("conduct: ", "floor: ", "malformed: ", "state: ", "unsigned code")`; gate.py:526-533 `_ranked`;
  gate.py:304-320 (stale, `f"{row.treatment}: {row.id}"`, needs live, requires, leverage, ack required);
  gate.py:327-339 (auto_off, cap unset, cap exceeded); docs/superpowers/plans/2026-10-23-compliance-gate.md:17281-17290 (Appendix A.7 list)
  IMPACT: The odds engine must not parse free text beyond these prefixes. To map a refusal to owner text it should
  match `startswith` on reasons[0] (the strictest) and show the row id. Internal names never reach the rendered
  card (language guard).

* [GREY_LEG: what the gate exposes] Nothing names "grey". For an OKX BTC leg with no session ack, the verdict is
  ACK_REQUIRED, allowed is True, reasons are ('ack required: KR-OKX-SPOT',) and decision.ack is ('KR-OKX-SPOT',
  <sha>). Once acked, the verdict is ALLOW and ack is None, but decision.warnings still carries the rendered OKX
  warning. Only two rows carry a warning: KR-KIS-US-OPTION and KR-OKX-SPOT. auto_off and cap_key exist only on
  grey rows (the loader enforces this).
  EVIDENCE: probe: `okx BTC ACK_REQUIRED new_exposure True ('ack required: KR-OKX-SPOT',) ack= ('KR-OKX-SPOT', '17e7aa29...')`,
  `okx acked ALLOW None ()`, `acked warnings ["OKX is not registered with Korea's FIU. The FSC te"]`,
  `other rows with warnings: ['KR-KIS-US-OPTION', 'KR-OKX-SPOT']`; gate.py:248 `warnings = [render_warning(row, _slots(row, ctx)) for row in rows]`;
  rules.py:479-480 `elif grey is not None: raise Invalid(f"{where}: grey: only a grey row carries a cap and an auto-off date")`
  IMPACT: GREY_LEG cannot be read off the verdict, because an acked grey leg is plain ALLOW. Robust options:
  (a) the odds engine looks up the in-force venue rows of ctx.active.rules that match the leg and checks
  `row.treatment == "grey"`, which needs gate's private `_in_force` and `_matches` or a copy of them; or (b) the
  compliance follow-up adds a public helper (or a Screening field such as `grey_rows`) in gate.py. Option (b)
  changes the code hash. "decision.warnings non-empty" is fragile (the US-option row also has a warning).
  ACK_REQUIRED must count as screenable (allowed True) and still raise GREY_LEG.

* [grey cap depends on the equity passed] An OKX leg is BLOCK "cap exceeded" when held + other reservations + stake
  > cap × ctx.equity_krw, and BLOCK "cap unset" when owner.caps lacks okx_equity_share. A stake of 10,000 against
  equity of 50,000 at a 10% cap is BLOCK. On or after auto_off it is BLOCK "auto_off 2026-12-03: KR-OKX-SPOT".
  EVIDENCE: gate.py:331-339 `cap = _cap(row, ctx)` ... `if held + others + intent.notional_krw > cap * ctx.equity_krw: out.append(f"cap exceeded: {row.id}")`;
  probe: `okx small equity BLOCK ('cap exceeded: KR-OKX-SPOT',)`, `okx nocap BLOCK ('cap unset: KR-OKX-SPOT',)`,
  `okx autooff BLOCK ('stale: review by 2026-11-22 passed (KR-OKX-SPOT)', 'auto_off 2026-12-03: KR-OKX-SPOT')`
  IMPACT: The equity_krw the odds engine passes to load_context (through Positions) decides OKX screening. It must
  be the plan's real equity W (stake_krw), with exposure left empty unless the caller supplies real holdings. A
  bold or fixed stake above cap × W is refused by the gate, so the odds engine should pre-cut the OKX stake by the
  cap or word that refusal.

* [only the first stake is screened] screen decides one buy at `first_stake_krw`. Re-entries and bold-play stakes
  after a win are not screened.
  EVIDENCE: gate.py:612-615 docstring `The plan's single leg decided on ctx.date as a cash buy of first_stake_krw`; spec:535-536 `decides the plan's single leg as a buy at the first stake, which the odds engine computes (7.1)`
  IMPACT: For OKX, later larger stakes could exceed the grey cap even though the first passed. The odds plan must
  either cap every simulated OKX entry at cap × equity, using ctx.owner.caps, or document the gap. Spec Appendix B
  (Gr-5) accepted `first_stake_krw` being passed in.

## Shipped-table verdicts per candidate leg (probe, ctx date 2026-10-24, stake 50,000, horizon 60)

* [verdicts by leg] ALLOW: kis 005930 (KR-KIS-KRX-SHARE), kis 069500 and SPY (KR-KIS-ETP-1X), kis AAPL
  (KR-KIS-US-SHARE), kis BITO (KR-KIS-CRYPTO-FUT-ETF), upbit BTC and USDT, bithumb, coinone and korbit BTC
  (KR-DOMESTIC-SPOT). ACK_REQUIRED: okx BTC. BLOCK: kis 252670 and TQQQ (gated, needs live evidence), kis IBIT
  ("floor: etp_crypto_spot", hard_block), okx USDT ("malformed: counter_symbol": its default quote USDT makes it
  trade against itself), gopax BTC ("malformed: venue": no venue facts).
  EVIDENCE: probe output lines `kis 005930 ALLOW ...` to `gopax BTC BLOCK malformed False ('malformed: asset', 'malformed: counter_symbol', 'malformed: venue')`
  IMPACT: The odds whitelist (share, etp_1x and coin, long, cash, multiple +1) is narrower than the gate's ALLOW
  set: BITO is allowed by the gate but is class etp_crypto_futures_1x. plan.py must refuse with
  UNSUPPORTED_PRODUCT before screening, using the class from the approved map. Odds tests can rely on these
  verdicts with the fixture ctx.

## model.Context and owner limits

* [Context has no limits field] The fields are date, active, snapshot, owner, code_hash, code_signed, session,
  equity_krw, holdings, shorts, exposure and ctx_hash. Limits live in `ctx.owner.limits` and caps in
  `ctx.owner.caps`.
  EVIDENCE: model.py:165-178 `class Context:` (fields listed); model.py:139-140 `caps: Mapping[str, float] = field(default_factory=dict)` / `limits: Mapping[str, float] = field(default_factory=dict)`
  IMPACT: simulate's `limits` argument (spec 4 step 3) should be read from `ctx.owner.limits`, not from a Plan field
  or a Context field. L = limits["total_loss_floor_krw"] and the daily limit = limits["daily_loss_krw"].

* [how unset limits look: absent keys] owner_state keeps only keys that have taken effect. An unset limit is a
  missing key, never 0 or None. A BROKEN owner state has empty caps and limits. Only the keys total_loss_floor_krw
  and daily_loss_krw are produced; caps holds only okx_equity_share.
  EVIDENCE: owner.py:559-561 `caps={k: v for k, v in values.items() if k == "okx_equity_share"}, limits={k: v for k, v in values.items() if k in _LIMIT_KEYS}`;
  owner.py:436 `_LIMIT_KEYS = ("total_loss_floor_krw", "daily_loss_krw")`; probe: `limits on broken {} {}`
  IMPACT: LIMITS_UNSET means `not ctx.owner.ok or not {"total_loss_floor_krw", "daily_loss_krw"} <= set(ctx.owner.limits)`.
  The literal "LIMITS_UNSET" exists only in the spec (575, 700, 1045). The odds engine should check this before any
  simulation.

* [valid limit values] limit_set needs total_loss_floor_krw >= 0 and daily_loss_krw > 0, both keys in one entry.
  cap_set needs key okx_equity_share with 0 < value <= 1. A total_loss_floor_krw of 0 is a valid SET value.
  EVIDENCE: owner.py:150-152 `"cap_set": {"key": _one_of(("okx_equity_share",)), "value": lambda v: _number(v) and 0 < v <= 1}, "limit_set": {"total_loss_floor_krw": lambda v: _number(v) and v >= 0, "daily_loss_krw": lambda v: _number(v) and v > 0}`
  IMPACT: L = 0 is legal and set (floor-safe then means L_min = 0), so it must not be treated as unset. Values reach
  the odds engine as Python floats (owner.py:540 `value, old = float(value), values.get(key)`).

* [the first setting takes effect only the next Asia/Seoul day] An unset value counts as the tightest, so the first
  limit_set or cap_set is a loosening. It counts only when its Asia/Seoul date is before ctx.date, never inside the
  armed session, and never after a halt. A halt floor raises total_loss_floor_krw for good.
  EVIDENCE: owner.py:483-484 `An unset cap or limit counts as the tightest, so setting one is a loosening.`;
  owner.py:525-528 `def loosening_counts(e, on) -> bool: return (e.utc <= now_utc and on < day ...`;
  owner.py:557-558 `values["total_loss_floor_krw"] = max(values["total_loss_floor_krw"], halt_floor)`
  IMPACT: On the day the owner first signs limits, odds runs still say LIMITS_UNSET. The owner-facing refusal text
  should say "limits take effect from the next day" (spec 10, "loosening waits a day"). Odds tests build limits
  through the fixture ctx (tests/compliance_fixtures.py:71 `limits={"total_loss_floor_krw": 21_000.0, "daily_loss_krw": 5_000.0}`)
  or a signed temp log dated the day before.

* [fixture context for odds tests] `tests.compliance_fixtures.ctx(**overrides)` seals a Context with date
  2026-10-23, active = the shipped drafts approved at seq 3, owner OK with cap 0.10, limits {21,000; 5,000} and flag
  age_of_majority, code_signed True, session S1 armed, equity 1,000,000, and no positions.
  EVIDENCE: tests/compliance_fixtures.py:65-78 `def ctx(**overrides): ... date=_date(2026, 10, 23) ... caps={"okx_equity_share": 0.10}, limits={"total_loss_floor_krw": 21_000.0, "daily_loss_krw": 5_000.0} ... code_hash="c" * 64, code_signed=True ... equity_krw=1_000_000.0`
  IMPACT: tests/odds_acceptance.py can reuse it: owner=OwnerState(..., limits={}) for LIMITS_UNSET, code_signed=False,
  and so on. It reads the shipped drafts through `shipped_bytes`, so odds tests that change venues.yaml must pass
  `approved(venues=...)` bytes explicitly. Note the comment at tests/compliance_fixtures.py:91: never import
  `test_key` by name into a test module (the harness collects it).

## owner.load_context

* [real signature: positions are required] `load_context(now, positions, *, session_id=None) -> Context`, not
  `load_context(now)` as the spec writes it. now must be an aware datetime (ValueError otherwise). positions must be
  a `model.Positions` with equity_krw > 0, or active becomes invalid "positions: <field>".
  EVIDENCE: owner.py:964 `def load_context(now: _dt.datetime, positions: model.Positions, *, session_id: str | None = None) -> model.Context:`;
  owner.py:970-976 (ValueError on naive or out-of-range now); owner.py:1004-1006 `problem = _positions_problem(positions)` / `active, snapshot = model.ApprovedState.invalid(f"positions: {problem}"), None`;
  model.py:103-109 `class Positions: equity_krw: float / holdings ... shorts ... exposure`
  IMPACT: The odds engine must build `model.Positions(equity_krw=float(plan.stake_krw))` (or real equity) and pass a
  tz-aware `now`. `rules.check` sets the precedent of `model.Positions(equity_krw=1.0)` "positions play no part" (rules.py:801),
  but for the odds engine equity does matter (the grey cap).

* [what load_context does, side effects included] It verifies the owner log against core/compliance/owner_pubkey.pem
  and the anchors, folds the owner state, loads the in-force rules, instruments and venues from the approved store,
  computes code_hash(REPO_ROOT) and compares it with the latest code_approved, WRITES a snapshot file when the active
  state is valid, and reads the latest snapshot. Any other exception gives a sealed BROKEN context.
  EVIDENCE: owner.py:987-1017 (`_owner_now`, `_approved_now(check)`, `current = code_hash(REPO_ROOT)`, `signed = owner.ok and bool(current) and code_approval(check) == current`, `write_snapshot(active, owner.head)`, `snapshot = latest_snapshot()`);
  owner.py:978-984 (internal error -> BROKEN context)
  IMPACT: load_context is not read-only: it creates <state_root>/compliance/snapshots/*.json. The odds suite must
  run under a temp TRADEGEN_HOME, and the odds plan's "no write outside ~/.tradegen" rule holds (the write goes
  through checked_target). Each call re-hashes the whole code closure from disk.

* [session_id for odds] With session_id None no session ack can match, because owner session_ack data requires a
  non-empty session_id. An OKX leg therefore stays ACK_REQUIRED, which still counts as allowed.
  EVIDENCE: owner.py:156 `"session_ack": {"session_id": _text, "row_id": _text, "warning_sha256": _hex64}`; gate.py:318 `if (ctx.session.session_id, row.id, sha) in ctx.owner.session_acks:`
  IMPACT: The odds engine can call load_context with session_id=None. GREY_LEG detection must not depend on the ack
  state.

* [today's real home] There is no core/compliance/owner_pubkey.pem yet, so load_context returns BROKEN "no owner
  key yet: owner act 1" and every screen is BLOCK.
  EVIDENCE: `ls core/compliance/owner_pubkey.pem` -> `No such file or directory`; owner.py:928-929 `if not PUBKEY_PATH.is_file(): return model.OwnerState.broken("no owner key yet: owner act 1"), None`
  IMPACT: No end-to-end real-home odds run can produce a probability until owner acts 1-5. The odds plan's manual
  checks must expect the refusal, and its tests use a temp home with the test key (tests/compliance_fixtures.py:95-141).

## Calendar approvals

* [calendar approval is NOT in Context] owner.APPROVAL_KINDS includes "calendar", but load_context loads only rules,
  instruments and venues. rules._calendar_line re-reads and re-verifies the log to find the calendar approval,
  because "the Context does not carry it".
  EVIDENCE: owner.py:29 `APPROVAL_KINDS = ("rules", "instruments", "venues", "calendar")`; owner.py:602 `_TABLES = ("rules", "instruments", "venues")`;
  rules.py:903-905 `def _calendar_line(ctx, root: Path, moment) -> str: """The calendar draft (P21) against the latest calendar approval signed by moment (load_context's cut-off) ... The Context does not carry it, so the log is read and verified once more."""`
  IMPACT: The odds engine needs its own "is the calendar set approved" path. The minimal existing recipe is
  rules.py:907-919: `if not ctx.owner.ok` -> unsigned; `log = owner.verify_log(owner._log_lines(owner.log_path()), owner.read_pubkey(owner.PUBKEY_PATH), owner.read_anchors())`;
  `signed = owner.in_force(owner._up_to(log, model.iso_utc(moment))).get("calendar", ("", 0))[0]`;
  `owner.store_get("calendar", signed) is not None`. It uses two private helpers (`_log_lines`, `_up_to`). The
  compliance follow-up should add a public `owner.calendar_in_force(now) -> str | None` (or put the sha into
  Context), which changes the code hash. Otherwise odds must call the privates.

* [calendar set framing and hash] `rules.calendar_stream(data_dir)` frames every regular file directly in the dir,
  sorted by name, as name NUL bytes NUL, and refuses links. `calendar_sha256` is its sha256. It is the one framing
  that store_put and store_get use. The shipped core/calendars/data holds 17 files (MANIFEST.yaml plus 16 yaml).
  EVIDENCE: rules.py:721-737 `def calendar_stream(data_dir: Path) -> bytes:` ... `parts.append(e.name.encode("utf-8") + b"\0" + Path(e.path).read_bytes() + b"\0")`;
  rules.py:740-742 `def calendar_sha256(data_dir: Path) -> str:`; `ls core/calendars/data` (17 entries); plan P21 (compliance-gate.md:16872 `The calendar approval covers every regular file in core/calendars/data/ (17 files ...)`)
  IMPACT: Calendar approval is of the WHOLE set, not per market. CALENDAR_UNSIGNED applies whenever the signed sha is
  missing, its stored copy is missing or altered, or the loaded set differs from it.

* [where approved calendar bytes live, and loading them] The store keeps the files as a plain directory
  `<state_root>/compliance/approved/calendar/<sha256>/`. store_get rebuilds the stream from that directory, checks
  that it hashes to its name, and returns None for a missing, altered or linked set. `core.calendars.store.CalendarSet(data_dir=...)`
  accepts any directory.
  EVIDENCE: owner.py:659-661 `blobs = ([(base / sha / name, data) for name, data in _calendar_files(raw)] if kind == "calendar" ...`;
  owner.py:670-680 `path = store_dir() / kind / (sha256 if kind == "calendar" else f"{sha256}.yaml")` ... `return raw if model.sha256_hex(raw) == sha256 else None`;
  core/calendars/store.py:221-223 `def __init__(self, data_dir: Path | None = None, ...` / `self.data_dir = Path(data_dir) if data_dir is not None else DATA_DIR`
  IMPACT: Spec 4 ("unless the store loads them and the owner log holds a signed approval") fits as: verify with
  store_get(signed), then `CalendarSet(owner.store_dir() / "calendar" / signed)`. That leaves a TOCTOU window
  between the two reads (a residual to document). Do not load the repo draft core/calendars/data unless its
  calendar_sha256 equals the signed sha. Provenance should record the signed calendar sha256 plus CalendarSet.version
  and the per-file md5s.

## venues.yaml: content, approval and the strict loader

* [current venues.yaml, in full] schema tradegen.venues/1, six venues. kis: sections [krx, us], settlement [KRW, USD],
  quote_by_currency true, deposits []. upbit: sections [crypto], settlement [KRW], markets [[BTC, KRW], [USDT, KRW]],
  default_quote KRW, deposits [{symbol BTC, network bitcoin, tag_required false}] (marked UNVERIFIED). bithumb,
  coinone and korbit: sections [crypto], settlement [KRW], markets [[BTC, KRW]], default_quote KRW, deposits []. okx:
  sections [crypto], settlement [USDT, USDC], markets [[BTC, USDT], [BTC, USDC]], default_quote USDT, deposits
  [BTC on bitcoin, no tag] (UNVERIFIED). Sources: Upbit, Bithumb and Coinone API URLs; korbit and okx are
  "UNVERIFIED: owner to confirm before approval". There are no lots, minimums, ticks or fees.
  EVIDENCE: core/odds/venues.yaml:5-49 (e.g. :10 `quote_by_currency: true        # a KRX code trades for KRW, a US ticker for USD`, :16 `markets: [[BTC, KRW], [USDT, KRW]]   # KRW-quoted only (P22)`, :45 `markets: [[BTC, USDT], [BTC, USDC]]`);
  header venues.yaml:2-3 `The compliance plan writes markets, settlement and deposits only; the odds plan adds lots, minimums and ticks later, which changes this file's sha256 and needs a new approval.`
  IMPACT: The odds plan owns adding lots, minimums, the KRX stock tick ladder and fee extras (φ_b, φ_s) to this
  file. Every addition changes its sha256 and needs a new owner `approved {kind: venues}` before the gate (or the
  odds engine reading ctx.active.venues) uses it.

* [ADDING ODDS KEYS TODAY MAKES THE FILE INVALID] The strict loader allows exactly {schema, venues} at the top level
  and, per venue, required {sections, settlement, source} plus optional {markets, quote_by_currency, default_quote,
  deposits}. Any other key raises Invalid "venues: <id>: unknown key(s) [...]". A deposit entry allows exactly
  {symbol, network, tag_required}. An existing test pins that a `minimum_krw` key is refused.
  EVIDENCE: rules.py:636-637 `_VENUE_REQUIRED = frozenset({"sections", "settlement", "source"})` / `_VENUE_OPTIONAL = frozenset({"markets", "quote_by_currency", "default_quote", "deposits"})`;
  rules.py:642 `_keys(entry, where, _VENUE_REQUIRED, _VENUE_OPTIONAL)`; rules.py:701 `_keys(doc, "venues", frozenset({"schema", "venues"}))`;
  rules.py:337-345 `unknown = sorted(...)` / `raise Invalid(f"{where}: unknown key(s) {unknown}")`;
  tests/compliance_tables.py:633 `bad(lambda d: d[v]["upbit"].update(minimum_krw=5000), "venues: upbit: unknown key(s) ['minimum_krw']")`;
  tests/compliance_tables.py:615 `bad(lambda d: d.update(extra=1), "venues: unknown key(s) ['extra']")`
  IMPACT: The odds plan must FIRST extend rules.py: new optional per-venue keys (lots, minimums, fee extras), a
  top-level or kis-only tick-ladder key, and validation for each (finite > 0, extras that only raise costs). Venue
  needs new dataclass fields with defaults so that tests/compliance_tables.py:557 (`kis == rules.Venue(...)` without
  them) still holds. It must amend the :633 and :615 pins (for example change `minimum_krw` to a still-unknown key)
  and keep the schema string or deliberately bump it. If a signed venues.yaml carried keys that the running parser
  refuses, `approved_state` would return invalid and EVERY new-exposure decision would BLOCK (fail closed). Order:
  parser change, then data change, then owner re-approval and code re-sign.

* [venues are approved and loaded through the store] The in-force venues bytes come from
  `store_get("venues", <latest approved sha>)` and are parsed against the approved instrument map. The repo file is
  only a draft, which --check diffs.
  EVIDENCE: owner.py:947-961 `_approved_now`: `raws[kind] = store_get(kind, approvals[kind][0])` ... `return rules.approved_state(raws["rules"], raws["instruments"], raws["venues"], ...)`;
  rules.py:698-711 `def parse_venues(raw: bytes, instruments: InstrumentMap) -> VenueFacts:`; rules.py:778-779 `_DRAFTS = (... ("venues", "core/odds/venues.yaml"))`
  IMPACT: The odds engine must read lots, minimums, ticks and fees from `ctx.active.venues.venues[venue_id]` (the
  APPROVED copy), never from core/odds/venues.yaml on disk. Otherwise an unsigned draft would drive sizing. A
  missing entry gives NOT_TRADABLE (spec 7.2:788).

* [the venue file's URLs must come from research] Every https URL in the shipped drafts must appear verbatim in
  the .md corpus under reports/, research_notes/ or QUANTGEN_techfund_research_bundle/. The shipped venue set is
  pinned to exactly the six venues.
  EVIDENCE: tests/compliance_tables.py (shipped block) `def test_shipped_urls_come_from_the_research():` ... `assert url.encode("utf-8") in known, (kind, url)`;
  `assert set(v) == {"kis", "upbit", "bithumb", "coinone", "korbit", "okx"}` (test_shipped_venue_facts_p22)
  IMPACT: A new minimum or fee source URL must first be recorded in reports/ or research_notes/, or else marked
  "UNVERIFIED: owner to confirm before approval". Adding a seventh venue breaks the P22 pin.

* [Venue API the odds engine can use] Venue has id, sections, settlement, markets {(base, quote)},
  quote_by_currency, default_quote and deposits, plus is_market(inst, counter) and quote_for(inst). quote_for
  returns inst.currency on kis and default_quote elsewhere.
  EVIDENCE: rules.py:306-326 `class Venue:` ... `def quote_for(self, inst: Instrument) -> str: return inst.currency if self.quote_by_currency else self.default_quote`
  IMPACT: The odds engine should take the quote currency of a leg from venue.quote_for(inst): KRW for upbit and the
  KRX codes, USD for the US tickers, USDT for okx BTC. It should never use inst.currency for coins (always KRW).

## instruments.yaml

* [fields per instrument] Each entry has exactly asset, multiple, underlying, class, cost_book, currency, tax_basis
  and source. Parsed into an Instrument, these become section, symbol, asset, multiple (float), underlying, cls
  (the derived class, equal to the declared one), cost_book (the asset's own book), currency, tax_basis and source.
  EVIDENCE: rules.py:571 `_ENTRY_KEYS = frozenset({"asset", "multiple", "underlying", "class", "cost_book", "currency", "tax_basis", "source"})`;
  rules.py:277-288 `class Instrument: section ... cls: str # derived, and equal to the declared class (P10) / cost_book: str | None / currency: str / tax_basis: str / source: str`;
  rules.py:573-574 `_COST_BOOK = {"krx_share": "KRX_stock_book", "krx_etp": "KRX_ETF_line", "us_share": "US_shares_KIS", "us_etp": "US_shares_KIS", "crypto_coin": "crypto_venue"}`
  IMPACT: plan.py's whitelist check reads `inst.cls in {"share", "etp_1x", "coin"} and inst.multiple == 1.0` from
  `ctx.active.instruments.lookup(venue.sections, symbol)`. The cost book (passed to cost_per_side) and the
  tax_basis come from the same approved Instrument, never from symbol-shape inference.

* [every symbol present: 17 entries] krx (KRW): 005930 krx_share/share/KRX_stock_book/krx_small_holder_exempt;
  069500 krx_etp x1 index/etp_1x/KRX_ETF_line/krx_small_holder_exempt; 252670 krx_etp x-2 index/etp_leveraged/
  KRX_ETF_line/unsupported; 114800 krx_etp x-1 index/etp_index_inverse/KRX_ETF_line/unsupported. us (USD, book
  US_shares_KIS, tax overseas_22pct_over_2.5m): TQQQ x3 etp_leveraged; SH x-1 etp_index_inverse; SPY x1 etp_1x;
  AAPL us_share/share; IBIT, FBTC and ETHA crypto_spot/etp_crypto_spot; GDLC and EZPZ crypto_spot_basket/
  etp_crypto_spot; BITO crypto_futures/etp_crypto_futures_1x. crypto (currency KRW, book crypto_venue, tax
  crypto_22pct_from_2027): BTC, USDT and USDC, all coin.
  EVIDENCE: core/compliance/instruments.yaml:9-164 (e.g. :10-18 `"005930": ... class: share / cost_book: KRX_stock_book / currency: KRW / tax_basis: krx_small_holder_exempt`, :35 `tax_basis: unsupported         # futures-based leveraged ETF: tax treatment unverified`, :138-146 BTC);
  test pin `assert len(imap.entries) == 17 and len(facts.venues) == 6` (tests/compliance_tables.py shipped block)
  IMPACT: The odds-eligible legs in the shipped map are kis 005930 and AAPL (share), kis 069500 and SPY (etp_1x),
  and BTC, USDT and USDC on the crypto venues (coin, where a market exists: upbit BTC and USDT, the other domestic
  venues BTC only, okx BTC only). The KRX_stock_book tick table is OWNER_INPUT, hence the venues.yaml ladder.
  "unsupported" tax bases are refused by the report (spec 7.5 item 5). Every source except SPY, 252670 and the coin
  API rows is UNVERIFIED.

## Provenance helpers

* [what the context and decision already carry] The code hash and signed state are ctx.code_hash and
  ctx.code_signed. The owner-log head is ctx.owner.head = (seq, row_sha256), copied into Decision.owner_head. The
  current key fingerprint is ctx.owner.fingerprint ("SHA256:<hex>" of the pem in force; "" when there is no pem).
  The in-force table hashes are ctx.active.hashes {"rules", "instruments", "venues"}, with ctx.active.seq and
  ctx.active.state_hash. The context hash is ctx.ctx_hash.
  EVIDENCE: model.py:136-147 `head: tuple[int, str] = (0, "") # (seq, row_sha256) of the last line` ... `fingerprint: str = ""`;
  rules.py:763-764 `hashes={"rules": file_sha256(rules_raw), "instruments": file_sha256(instruments_raw), "venues": file_sha256(venues_raw)}`;
  model.py:128-130 `def state_hash(self) -> str: return sha256_hex(canonical_json({"hashes": self.hashes, "seq": self.seq})) if self.valid else ""`;
  owner.py:936 `fp = fingerprint(pubkey_raw)`; gate.py:548-551 (Decision copies state_hash, code_hash, owner_head, ctx_hash)
  IMPACT: The report's provenance block (spec 7.5: "the in-force hashes, the owner-log head (seq), the code hash and
  the key fingerprint") reads these fields from ctx or screening.decision. The calendar sha is NOT among them; see the
  calendar finding. The first recorded fingerprint (P20) is only reachable through private
  `owner._first_recorded()` (owner.py:913-918).

* [code hash function] `owner.code_hash(repo_root)` is the sha256 of canonical_json(code_files). code_files is the
  sorted (relpath, sha256) list of core/compliance/*.py, core/odds/*.py (a non-recursive glob), their in-repo import
  closure at any depth (TYPE_CHECKING and `== "__main__"` bodies skipped), ancestor __init__.py files, and the
  RECORD files of cryptography and PyYAML only.
  EVIDENCE: owner.py:767-798 `todo = [p for sub in ("compliance", "odds") for p in sorted((root / "core" / sub).glob("*.py"))]` ... `_RECORD_DISTS = ("cryptography", "PyYAML")` (owner.py:603);
  tools/signer/sign.py:693 (the same glob in the signer copy); tests/compliance_signer.py:630-634 `test_code_files_match_owner`
  IMPACT: (1) The first core/odds/*.py file changes the code hash, so code_signed is False until the owner signs
  code_approved again, and screen BLOCKs "unsigned code". (2) Everything core/odds imports in-repo (config.py,
  core/quant/*, core/calendars/*, data/* clients) joins the signed closure, and later edits to those files unsign
  the gate. numpy, scipy and pandas are NOT hashed (no RECORD entry), so the report must record the numpy version
  separately (spec 7.5). (3) Odds subpackages are only hashed when imported.

* [EXISTING TEST WILL BREAK: closure must not contain config.py or data/] tests/compliance_store.py
  test_code_files_is_the_import_closure asserts that the real-tree closure is exactly core/__init__.py,
  core/isolation.py, core/compliance/*.py and core/odds/*.py, and never config.py or data/.
  EVIDENCE: tests/compliance_store.py:131-141 `expected = {"core/__init__.py", "core/isolation.py"} | {f"core/{sub}/{p.name}" for sub in ("compliance", "odds") for p in (ROOT / "core" / sub).glob("*.py")}` / `assert repo == expected, sorted(repo ^ expected)` / `assert "config.py" not in repo and not any(name.startswith("data/") for name in repo)`;
  spec:584-588 (the closure "for example config.py, core/isolation.py, core/calendars/**, the core/quant and data/ modules they reach")
  IMPACT: As soon as core/odds/bars.py imports a data client, or models.py imports core.quant, this compliance test
  fails. The odds plan must amend it (the expected set becomes the computed closure, still sorted and unique, with
  an explicit list of allowed prefixes) in the same task that adds the first such import. Otherwise it must keep
  every in-repo import out of core/odds/*.py, which is not feasible for bars.py.

## Static guards that already bind core/odds

* [guards whose scope includes core/odds] These apply to core/odds: the raw-text ban (private_key, seed_phrase,
  order_cash, place_order, submit_order, the TTTC ids, r18_research_log, r18_break_log, context_log/,
  tests.reference, reference_mode case-insensitively; CANO, KIS_ACCOUNT and ACNT_PRDT_CD case-sensitively), the
  forbidden and dynamic imports (core.engine.orders, core.quant.forward_sim, core.quant.refusal,
  core.ficc.context_log, core.ficc.macro, core.ficc.flows_log, core.skills.macro_daily; `*`, __import__,
  import_module, exec, eval, importlib.util/machinery, runpy, pkgutil, zipimport, pydoc, timeit, code, cProfile),
  the def-name ban (transfer, withdraw, deposit_address) across all of core/, the seal_context ban outside
  owner.py across all of core/, and an empty core/odds/__init__.py if one exists. These do NOT apply to core/odds:
  the import allowlist, the HTTP verb ban, the wall-clock ban and the main-block rule (compliance only).
  EVIDENCE: tests/compliance_guards.py:233 `hits = [h for rel, src in _scope(COMPLIANCE, ODDS).items() for h in _raw_hits(rel, src)]`;
  :300-301 `for rel, src in _scope(COMPLIANCE, ODDS).items() for h in _forbidden_hits(rel, src) + _dynamic_hits(rel, src)`;
  :244 `_scope(CORE)` for def names; :373-375 seal_context over `_scope(CORE)`; :408 `assert not (ODDS / "__init__.py").exists() or not _init_hits(ODDS / "__init__.py")`;
  :269, :340, :361, :385 use `_scope(COMPLIANCE)` only
  IMPACT: The odds code may import numpy, config, core.quant and data clients, but never the forbidden or dynamic
  modules. The sentence catalogue must not contain upper-case "CANO" (so no "CANONICAL" or "VOLCANO" in caps). A
  core/odds/__init__.py, if created, must be 0 bytes (plan P1 created none; core/odds holds only venues.yaml today).
  core.odds. is already an acting prefix (core/ficc/context_log.py:71-73 `"core.compliance.", "core.odds.")`).

## Compliance follow-up items that touch these interfaces (from the ledger)

* [parked: guards] xml.dom (xml.dom.xmlbuilder DOMBuilder.parseURI and DOMEntityResolver) and
  profile/pdb/bdb/trace are not in the import bans.
  EVIDENCE: execution-ledger.md:242 `Final: parked — xml.dom (incl. xml.dom.xmlbuilder DOMBuilder.parseURI / DOMEntityResolver) and profile/pdb/bdb/trace are not in the import bans — Ruling: park as a small guards follow-up`
  IMPACT: The follow-up adds them to NETWORK_MODULES or DYNAMIC_MODULES in tests/compliance_guards.py. DYNAMIC_MODULES
  also binds core/odds, so check that no odds module needs them.

* [parked: D15 loader hardening] Allow rows may still list financing margin or credit, or action lend or
  sell_short, and load VALID.
  EVIDENCE: execution-ledger.md:243 `Final: parked — D15 is enforced only by row content: an explicit financing: [cash, margin] or action: [..., lend, sell_short] on an allow row still loads VALID`
  IMPACT: A rules.py change: it alters the code hash, the same as the odds parser extension, so batch it with the
  venues-parser change to save the owner a re-sign.

* [carried to execution: interface gaps] Per-session acks are accepted with session None, and the gate never reads
  ctx.session.armed. Other open items: shared reservation_id, a permit edited in place, append_system_entry
  TypeError/OSError, torn-line repair, KEY CHANGED after rotation, a KIS token burnt on refusal, a far-ahead system
  stamp, the signer signing acks as bare hashes, the P20 retired-key rewrite, and H2 halt dating.
  EVIDENCE: execution-ledger.md:239 `Final: carried to the execution spec: ack accepted with session None and gate never reads ctx.session.armed; shared reservation_id; permit edited in place; ...`
  IMPACT: For the execution design (spec 13): permit(intent, ctx) -> Permit | None and verify_permit(p, intent,
  ctx_now) -> (bool, str) (gate.py:569, 586) are registered process-locally (`_ISSUED` weak dict, gate.py:566), so
  permits do not survive a restart. Execution must also supply real positions (P19) and derive notional and
  held_krw from live prices (ledger:244).

## Open questions

- What equity should the odds engine pass in `Positions(equity_krw=...)` to load_context: the plan's stake_krw W,
  or the owner's real total equity? It decides the OKX grey cap (cap × equity), and holdings and exposure are
  unknown to a simulation.
- Should a `review_by` flag force a simulated exit (spec 6.3 says every review_by, auto_off and effective_until
  does)? With the monthly cadence, that caps every horizon at about 30 days. Or should only auto_off and
  effective_until force the exit, with review_by shown as RULE_CHANGE_IN_HORIZON wording only? It needs a ruling
  before simulate.py is written.
- GREY_LEG detection: add a public gate helper or Screening field (a compliance code change and re-sign), or let
  core/odds read gate's private `_in_force`/`_matches` (or copy them)? Something must be chosen, because an acked
  OKX leg is plain ALLOW.
- Calendar approval lookup: add a public `owner.calendar_in_force(now)` (or a Context field), or let core/odds call
  `owner._log_lines` and `owner._up_to` the way rules._calendar_line does? Load CalendarSet from
  `store_dir()/calendar/<sha>` (TOCTOU between store_get and the load) or from the repo draft once its
  calendar_sha256 equals the signed sha?
- Venue odds facts schema: which exact keys (lot size, fractional units, minimum notional per venue/currency, KRX
  stock tick ladder at the top level or under kis, fee extras φ_b and φ_s)? Keep schema `tradegen.venues/1` with
  optional keys, or bump it to /2 (which refuses old signed bytes)?
- Should screen() also flag effective_from inside [start, end) (a row starting mid-horizon)? It is not flagged
  today. Is that a compliance follow-up item?
- Should simulate() take the ctx (so it can rebuild the intent and verify intent_hash and screening_hash), or only
  the Screening plus the Instrument? Is there any requirement to register issued Screenings the way permits are
  (a gate.py change)?
- Re-entries and bold-play stakes after a win are never screened. Must the odds engine cap every simulated OKX
  entry at cap × equity from ctx.owner.caps?
- Does the odds plan amend tests/compliance_store.py:131 to the grown closure (config.py, core/quant, core/calendars,
  data/ clients), and does the owner accept a signed closure that includes network data clients?
