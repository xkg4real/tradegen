"""The poll checks (E1 plan Task 11; spec 7; contract 15): every row of the check table on its trigger and just
inside it, missing keys and unsigned code, not-set items, the once-a-day rule, alert rows and their re-check, and
the leak scan over every sentence.

Snapshots are built here with every collection empty unless a test gives it, so no test leans on another task's
fixture defaults. `_poll` runs one poll through the pure pipeline the poller uses (contract 16.2 steps 2, 6 and 7) on
in-memory rows; `_due_run` runs `due` alone over synthetic alerts. No later task appends to this module.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone

from core.compliance import model
from execution import checks, positions, snapshot
from tests import execution_fixtures as EF

NOW = EF.NOW                                          # 2026-10-24 09:00 KST
UTC = model.iso_utc(NOW)
ADDRESS = "bc1qfixtureaddress000000000000000000000"    # contract 3.2's Upbit fixture address
SELF_CHECK = frozenset({"okx_perm", "okx_acct_lv", "okx_spot_borrow", "okx_auto_loan", "okx_no_ip"})
KEYS_MISSING = frozenset({"keys_missing"})
UNSIGNED = frozenset({"code_unsigned"})
BROKEN = model.OwnerState.broken("test: the owner log does not verify")
SAMPLE = {"n": 2, "k": 1, "added": 1, "removed": 0, "days": 29, "seconds": 61, "fills": 1, "deposits": 0,
          "withdrawals": 0, "expires": "2026-11-22T00:00:00Z", "when": UTC, "since": "2026-10-23T15:00:00Z",
          "skipped": "FLOOR: not set; OKX: keys not in .env"}
CURRENCY = "\u20a9|\\$|krw|usd|usdt|usdc|btc|\uc6d0"                 # the won sign and the Korean "won" syllable
LEAK = re.compile(f"(?i)({CURRENCY})\\s*[0-9]|[0-9][0-9,.]*\\s*({CURRENCY})")
LONG_RUN = re.compile(r"[A-Za-z0-9]{25,}")


def _snap(venue: str, **fields) -> snapshot.Snapshot:
    """An ok snapshot of `venue` stamped NOW (or `utc=`), every collection empty unless given."""
    return snapshot.Snapshot(**{"venue": venue, "utc": UTC, "ok": True, **fields})


def _failed(venue: str, flags=frozenset(), utc: str = UTC, **extra) -> snapshot.Snapshot:
    return snapshot.failed(venue, utc, f"{venue}: test failure", flags=flags, **extra)


def _new(now: datetime = NOW, **venues) -> dict:
    """Three ok snapshots at `now` worth KRW 30,000 (KIS cash), 20,000 (Upbit cash) and 10,000 (OKX, 10 USDT at
    1,000): equity 60,000, OKX held 10,000. Any venue can be replaced."""
    stamp = model.iso_utc(now)
    base = {"kis": _snap("kis", utc=stamp, cash={"KRW": 30_000.0}),
            "upbit": _snap("upbit", utc=stamp, cash={"KRW": 20_000.0}),
            "okx": _snap("okx", utc=stamp, holdings={"USDT": snapshot.Holding(units=10.0)},
                         prices_krw={"USDT": 1_000.0})}
    base.update(venues)
    return base


def _owner(**changes) -> model.OwnerState:
    """An OK owner state: cap 0.5, floor 21,000, daily loss 5,000 and one signed withdrawal address."""
    fields = {"status": "OK", "head": (5, "a" * 64), "caps": {"okx_equity_share": 0.5},
              "limits": {"total_loss_floor_krw": 21_000.0, "daily_loss_krw": 5_000.0},
              "addresses": frozenset({("okx", "BTC", "bitcoin", ADDRESS, "")})}
    fields.update(changes)
    return model.OwnerState(**fields)


def _prev(**last) -> dict:
    """No prior for any venue, except the given `venue=Prior(...)`."""
    out = {v: checks.Prior(last_ok=None, fails=0) for v in snapshot.VENUES}
    out.update(last)
    return out


def _run(new: dict, prev: dict | None = None, owner: model.OwnerState | None = None, start=None,
         now: datetime = NOW) -> dict:
    """run_checks for one poll as {(venue, text_key): slots}; kind and level always match the catalogue."""
    owner = _owner() if owner is None else owner
    alerts = checks.run_checks(_prev() if prev is None else prev, new, owner, checks.limits_from(owner, start), now)
    for a in alerts:
        assert (a.kind, a.level) == checks.TEXT[a.text_key][:2], a
    found = {(a.venue, a.text_key): dict(a.slots) for a in alerts}
    assert len(found) == len(alerts), alerts
    return found


def _alert(venue: str, text_key: str) -> checks.Alert:
    """A catalogue alert with sample slots, so its row verifies."""
    kind, level, template = checks.TEXT[text_key]
    names = set(re.findall(r"\{(\w+)\}", template)) - {"venue"}
    return checks.Alert(venue=venue, kind=kind, level=level, text_key=text_key, slots={n: SAMPLE[n] for n in names})


def _stored(alerts, now: datetime) -> list[dict]:
    """The rows as alerts.jsonl holds them: canonical JSON read back."""
    return [json.loads(model.canonical_json(checks.row(a, model.iso_utc(now)))) for a in alerts]


def _poll(state: dict, new: dict, now: datetime, owner: model.OwnerState | None = None, start=None) -> dict:
    """One poll on in-memory rows, as poll_once runs the pure part (contract 16.2 steps 2, 6, 7): priors from the
    inquiry rows before this poll, the checks, the not-set info alert (E43), due, then this poll's rows appended."""
    owner = _owner() if owner is None else owner
    prev = checks.priors(state["inquiry"])
    limits = checks.limits_from(owner, start)
    raw = checks.run_checks(prev, new, owner, limits, now)
    done = checks.evaluated(prev, new, owner, limits, now)
    skipped = checks.not_set(new, owner, limits, positions.live_positions(new, now))
    if skipped:
        raw = raw + [checks.Alert(venue="all", kind="NOT_SET", level="info", text_key="NOT_SET",
                                  slots={"skipped": "; ".join(skipped)})]
    fresh, clears = checks.due(raw, done, state["alerts"], now)
    state["inquiry"] += [json.loads(snapshot.dump(new[v])) for v in snapshot.VENUES]
    state["alerts"] += _stored(fresh + clears, now)
    return {"raw": [(a.venue, a.text_key) for a in raw], "fresh": [(a.venue, a.text_key) for a in fresh],
            "clears": [(a.venue, a.text_key) for a in clears], "skipped": skipped, "prev": prev}


def _forged(obj: dict, **changes) -> dict:
    """An inquiry row with `changes` and its snapshot_sha256 recomputed, as a writer forging a line would do."""
    out = dict(obj, **changes)
    out["snapshot_sha256"] = model.sha256_hex(model.canonical_json(
        {k: v for k, v in out.items() if k != "snapshot_sha256"}))
    return out


def _due_run(polls, start: datetime = NOW) -> list[tuple[list[str], list[str]]]:
    """due over a list of (raw alerts, done pairs), one poll every 5 minutes from `start`, rows accumulating."""
    rows, out = [], []
    for i, (raw, done) in enumerate(polls):
        now = start + timedelta(minutes=5 * i)
        fresh, clears = checks.due(raw, frozenset(done), rows, now)
        rows += _stored(fresh + clears, now)
        out.append(([a.text_key for a in fresh], [a.text_key for a in clears]))
    return out


# --------------------------------------------------------------------------- #
# The catalogue
# --------------------------------------------------------------------------- #
def test_catalogue_kinds_levels_and_slots_are_consistent():
    assert len(checks.KINDS) == 13 and len(set(checks.KINDS)) == 13
    assert len(checks.TEXT) == 24
    slot_names = checks.INT_SLOTS | checks.TIME_SLOTS | checks.ITEM_SLOTS
    for key, (kind, level, template) in checks.TEXT.items():
        assert kind in checks.KINDS, key
        assert level in ("red", "amber", "info"), key
        assert (level == "info") == (key == "NOT_SET"), key
        names = set(re.findall(r"\{(\w+)\}", template)) - {"venue"}
        assert names <= slot_names, (key, names)
    assert dict(checks.VENUE_NAMES) == {"kis": "KIS", "upbit": "Upbit", "okx": "OKX", "all": "TRADEGEN"}
    assert len(checks.NOT_SET_ITEMS) == 11, sorted(checks.NOT_SET_ITEMS)
    assert not any("; " in item for item in checks.NOT_SET_ITEMS)       # the join stays splittable


def test_text_is_the_contract_catalogue_and_render_fills_it():
    # The SHA-256 of contract 15.3's catalogue as canonical JSON: a slip in any key, kind, level or sentence fails.
    assert model.sha256_hex(model.canonical_json(dict(checks.TEXT))) == (
        "1055607ceb02cde19b81297fba5476709e1760278ef626a4b93900828e1fa258")
    order = checks.Alert(venue="upbit", kind="FOREIGN_ORDER", level="red", text_key="FOREIGN_ORDER", slots={"n": 1})
    assert checks.render(order) == "Upbit shows 1 open order(s). E1 places no orders: check the Upbit app now."
    note = checks.Alert(venue="all", kind="NOT_SET", level="info", text_key="NOT_SET",
                        slots={"skipped": "FLOOR: not set"})
    assert checks.render(note) == "Checks skipped (not set): FLOOR: not set."


def test_a_quiet_poll_raises_nothing_and_skips_nothing():
    owner = _owner()
    assert _run(_new()) == {}
    assert checks.not_set(_new(), owner, checks.limits_from(owner, None), positions.live_positions(_new(), NOW)) == ()


def test_limits_from_reads_the_owner_state_and_the_day_start():
    start = (65_000.0, "2026-10-23T15:00:00Z")
    assert checks.limits_from(_owner(), start) == checks.Limits(
        total_loss_floor_krw=21_000.0, daily_loss_krw=5_000.0, okx_equity_share=0.5,
        day_start_equity_krw=65_000.0, day_start_utc="2026-10-23T15:00:00Z")
    assert checks.limits_from(_owner(caps={}, limits={}), None) == checks.Limits(
        total_loss_floor_krw=None, daily_loss_krw=None, okx_equity_share=None, day_start_equity_krw=None,
        day_start_utc=None)
    not_ok = model.OwnerState(status="BROKEN", caps={"okx_equity_share": 0.5}, limits={"daily_loss_krw": 1.0})
    limits = checks.limits_from(not_ok, start)                  # a broken log: every owner fact counts as absent
    assert (limits.total_loss_floor_krw, limits.daily_loss_krw, limits.okx_equity_share) == (None, None, None)
    assert limits.day_start_equity_krw == 65_000.0


# --------------------------------------------------------------------------- #
# The check table, row by row (contract 15.1)
# --------------------------------------------------------------------------- #
def test_key_missing_unsigned_and_auth_errors():
    assert _run(_new(upbit=_failed("upbit", KEYS_MISSING))) == {("upbit", "KEY_MISSING"): {}}
    assert _run(_new(okx=_failed("okx", KEYS_MISSING))) == {("okx", "KEY_MISSING"): {}}
    assert _run(_new(kis=_failed("kis", KEYS_MISSING))) == {("kis", "KEY_MISSING"): {}}
    assert _run(_new(kis=_failed("kis", UNSIGNED))) == {("kis", "KIS_UNSIGNED"): {}}
    assert _run(_new(upbit=_failed("upbit", frozenset({"auth_error"})))) == {("upbit", "KEY_AUTH"): {}}
    assert _run(_new(kis=_failed("kis", frozenset({"auth_error"})))) == {("kis", "KEY_AUTH"): {}}
    assert _run(_new(upbit=_failed("upbit"))) == {}                           # 1 failed poll: nothing yet


def test_venue_scoped_rows_fire_only_on_their_venue():
    # The table's "(okx)", "(upbit)" and "(kis)" rows name that venue in their sentence, so nowhere else.
    okx_only = frozenset({"okx_perm", "okx_spot_borrow", "EVENTS", "derivative_position"})
    assert _run(_new(kis=_failed("kis", okx_only))) == {}
    assert _run(_new(upbit=_failed("upbit", UNSIGNED))) == {}
    kis = _snap("kis", cash={"KRW": 30_000.0}, key_expiry=model.iso_utc(NOW + timedelta(days=1)), earn={"x": 1.0},
                withdrawal_addresses=(snapshot.Address(currency="BTC", net_type="BTC", address=ADDRESS),))
    prev = _prev(kis=checks.Prior(last_ok=_snap("kis", cash={"KRW": 30_000.0}), fails=0))
    assert _run(_new(kis=kis), prev) == {}
    # The same inputs on their own venue do fire (positive control).
    assert set(_run(_new(okx=_failed("okx", okx_only)))) == {
        ("okx", "KEY_OKX_SELF_CHECK"), ("okx", "D15_BORROW"), ("okx", "HARD_BLOCK_EVENTS"),
        ("okx", "HARD_BLOCK_DERIVATIVE")}
    assert _run(_new(kis=_failed("kis", UNSIGNED))) == {("kis", "KIS_UNSIGNED"): {}}


def test_okx_self_check_counts_its_failed_checks():
    assert _run(_new(okx=_failed("okx", frozenset({"okx_perm"})))) == {("okx", "KEY_OKX_SELF_CHECK"): {"n": 1}}
    assert _run(_new(okx=_failed("okx", frozenset({"okx_acct_lv", "okx_no_ip"})))) == {
        ("okx", "KEY_OKX_SELF_CHECK"): {"n": 2}}
    assert _run(_new(okx=_failed("okx", SELF_CHECK))) == {("okx", "KEY_OKX_SELF_CHECK"): {"n": 5},
                                                          ("okx", "D15_BORROW"): {}}
    assert _run(_new(okx=_failed("okx", frozenset({"okx_auto_loan"})))) == {
        ("okx", "KEY_OKX_SELF_CHECK"): {"n": 1}, ("okx", "D15_BORROW"): {}}


def test_upbit_key_expiry_warns_from_30_days():
    def expiry(left: timedelta) -> dict:
        return _run(_new(upbit=_snap("upbit", cash={"KRW": 20_000.0}, key_expiry=model.iso_utc(NOW + left))))
    at_30 = model.iso_utc(NOW + timedelta(days=30))
    assert expiry(timedelta(days=30)) == {("upbit", "KEY_EXPIRY"): {"days": 30, "expires": at_30}}
    assert expiry(timedelta(days=30, seconds=1)) == {}
    assert expiry(timedelta(days=29, hours=23))[("upbit", "KEY_EXPIRY")]["days"] == 29
    assert expiry(-timedelta(hours=1))[("upbit", "KEY_EXPIRY")]["days"] == 0          # already expired
    assert _run(_new(upbit=_snap("upbit", cash={"KRW": 20_000.0}))) == {}               # no key listed


def test_foreign_order_on_an_ok_venue():
    order = snapshot.Order(id="u-open-1", symbol="BTC", side="buy", units=0.0001, price=90_000_000.0)
    other = snapshot.Order(id="u-open-2", symbol="BTC", side="sell", units=0.0001)
    upbit = _snap("upbit", cash={"KRW": 20_000.0}, open_orders=(order,))
    assert _run(_new(upbit=upbit)) == {("upbit", "FOREIGN_ORDER"): {"n": 1}}
    kis = _snap("kis", cash={"KRW": 30_000.0}, open_orders=(order, other))
    assert _run(_new(kis=kis)) == {("kis", "FOREIGN_ORDER"): {"n": 2}}
    assert _run(_new(upbit=_failed("upbit"))) == {}                          # a failed venue lists no orders


def test_holdings_change_explained_by_a_new_fill_and_its_counter():
    last = _snap("okx", holdings={"USDT": snapshot.Holding(units=10.0)}, prices_krw={"USDT": 1_000.0},
                 fills=(snapshot.Move(id="f0", symbol="BTC", counter="USDT", side="buy", units=0.0001),))
    fill = snapshot.Move(id="f1", symbol="BTC", counter="USDT", side="buy", units=0.0001)
    now = _snap("okx", holdings={"USDT": snapshot.Holding(units=3.0), "BTC": snapshot.Holding(units=0.0001)},
                prices_krw={"USDT": 1_000.0, "BTC": 100_000_000.0}, fills=(last.fills[0], fill))
    found = _run(_new(okx=now), _prev(okx=checks.Prior(last_ok=last, fails=0)))
    assert found == {("okx", "HOLDINGS_EXPLAINED"): {"n": 2, "fills": 1, "deposits": 0, "withdrawals": 0}}, found
    # Only the counter changed: the new fill names USDT as its counter, so it explains USDT and counts.
    usdt_only = _snap("okx", holdings={"USDT": snapshot.Holding(units=3.0)}, prices_krw={"USDT": 1_000.0},
                      fills=(last.fills[0], fill))
    found = _run(_new(okx=usdt_only), _prev(okx=checks.Prior(last_ok=last, fails=0)))
    assert found == {("okx", "HOLDINGS_EXPLAINED"): {"n": 1, "fills": 1, "deposits": 0, "withdrawals": 0}}, found
    old_only = _snap("okx", holdings=now.holdings, prices_krw=now.prices_krw, fills=last.fills)   # no new fill
    found = _run(_new(okx=old_only), _prev(okx=checks.Prior(last_ok=last, fails=0)))
    assert found == {("okx", "HOLDINGS_UNEXPLAINED"): {"n": 2, "k": 2, "fills": 0, "deposits": 0,
                                                       "withdrawals": 0}}, found


def test_holdings_change_mixed_case_counts_fills_deposits_and_withdrawals():
    held = {"BTC": 0.0001, "ETH": 0.01, "XRP": 5.0, "SOL": 1.0}
    last = _snap("upbit", cash={"KRW": 20_000.0},
                 holdings={s: snapshot.Holding(units=u) for s, u in held.items()},
                 prices_krw={s: 1.0 for s in held})
    moved = {"BTC": 0.0002, "ETH": 0.02, "XRP": 4.0, "SOL": 2.0, "DOGE": 7.0}   # DOGE new: absent counts as 0
    now = _snap("upbit", cash={"KRW": 21_000.0},
                holdings={s: snapshot.Holding(units=u) for s, u in moved.items()},
                prices_krw={s: 1.0 for s in moved},
                fills=(snapshot.Move(id="u-done-1", symbol="BTC", counter="KRW", side="buy", units=0.0001),),
                deposits=(snapshot.Move(id="u-dep-1", symbol="ETH", side="in", units=0.01),
                          snapshot.Move(id="u-dep-2", symbol="KRW", side="in", units=1_000.0)),
                withdrawals=(snapshot.Move(id="u-wd-1", symbol="XRP", side="out", units=1.0),
                             snapshot.Move(id="u-wd-2", symbol="ADA", side="out", units=1.0)))
    found = _run(_new(upbit=now), _prev(upbit=checks.Prior(last_ok=last, fails=0)))
    # 5 changed: BTC (fill), ETH (deposit), XRP (withdrawal) explained; SOL and DOGE not. The KRW deposit names no
    # changed holding (KRW is cash) and the ADA withdrawal names an unchanged one, so neither is counted.
    assert found == {("upbit", "HOLDINGS_UNEXPLAINED"): {"n": 5, "k": 2, "fills": 1, "deposits": 1,
                                                         "withdrawals": 1}}, found
    assert _run(_new(upbit=now)) == {}                                      # no previous ok snapshot: no compare


def test_holdings_change_ignores_float_noise():
    last = _snap("upbit", holdings={"BTC": snapshot.Holding(units=1.0)}, prices_krw={"BTC": 1.0})
    noise = _snap("upbit", holdings={"BTC": snapshot.Holding(units=1.0 + 1e-13)}, prices_krw={"BTC": 1.0})
    real = _snap("upbit", holdings={"BTC": snapshot.Holding(units=1.0 + 1e-11)}, prices_krw={"BTC": 1.0})
    prev = _prev(upbit=checks.Prior(last_ok=last, fails=0))
    assert _run(_new(upbit=noise), prev) == {}
    assert ("upbit", "HOLDINGS_UNEXPLAINED") in _run(_new(upbit=real), prev)


def test_address_list_changed_and_unsigned():
    signed = snapshot.Address(currency="BTC", net_type="BTC", address=ADDRESS)
    extra = snapshot.Address(currency="ETH", net_type="ETH", address="0xfixture")
    last = _snap("upbit", cash={"KRW": 20_000.0}, withdrawal_addresses=(signed,))
    prev = _prev(upbit=checks.Prior(last_ok=last, fails=0))
    assert _run(_new(upbit=last), prev) == {}                               # signed and unchanged
    renamed = _snap("upbit", cash={"KRW": 20_000.0},                         # net_type alone is not compared (E20)
                    withdrawal_addresses=(snapshot.Address(currency="BTC", net_type="bitcoin", address=ADDRESS),))
    assert _run(_new(upbit=renamed), prev) == {}
    both = _snap("upbit", cash={"KRW": 20_000.0}, withdrawal_addresses=(signed, extra))
    assert _run(_new(upbit=both), prev) == {("upbit", "ADDRESS_CHANGED"): {"added": 1, "removed": 0},
                                            ("upbit", "ADDRESS_UNSIGNED"): {"n": 1}}
    tagged = _snap("upbit", cash={"KRW": 20_000.0}, withdrawal_addresses=(
        snapshot.Address(currency="BTC", net_type="BTC", address=ADDRESS, secondary_address="7"),))
    assert _run(_new(upbit=tagged), prev) == {("upbit", "ADDRESS_CHANGED"): {"added": 1, "removed": 1},
                                              ("upbit", "ADDRESS_UNSIGNED"): {"n": 1}}
    gone = _snap("upbit", cash={"KRW": 20_000.0})
    assert _run(_new(upbit=gone), prev) == {("upbit", "ADDRESS_CHANGED"): {"added": 0, "removed": 1}}
    # The unsigned half is skipped while the owner log is not OK; the changed half still runs.
    assert _run(_new(upbit=both), prev, owner=BROKEN) == {("upbit", "ADDRESS_CHANGED"): {"added": 1, "removed": 0}}
    assert "ADDRESS_LIST: owner log not OK" in checks.not_set(
        _new(upbit=both), BROKEN, checks.limits_from(BROKEN, None), positions.live_positions(_new(upbit=both), NOW))
    # No previous ok snapshot: only the unsigned half can run.
    assert _run(_new(upbit=both)) == {("upbit", "ADDRESS_UNSIGNED"): {"n": 1}}


def test_d15_borrow_loans_and_earn():
    assert _run(_new(okx=_failed("okx", frozenset({"okx_spot_borrow"})))) == {
        ("okx", "KEY_OKX_SELF_CHECK"): {"n": 1}, ("okx", "D15_BORROW"): {}}
    kis = _snap("kis", cash={"KRW": 30_000.0},
                loans={"tot_loan_amt": 0.0, "loan_amt": 1.0, "crdt_fncg_amt": 2.0, "rcvb_amt": 0.0})
    assert _run(_new(kis=kis)) == {("kis", "D15_LOAN"): {"n": 2}}
    okx = _snap("okx", holdings={"USDT": snapshot.Holding(units=10.0)}, prices_krw={"USDT": 1_000.0},
                loans={"liab:USDT": 0.5}, earn={"savings:USDT": 5.0, "asset_valuation": 0.0, "auto_lend:USDT": 1.0})
    assert _run(_new(okx=okx)) == {("okx", "D15_LOAN"): {"n": 1}, ("okx", "D15_EARN"): {"n": 2}}
    zero = _snap("okx", holdings={"USDT": snapshot.Holding(units=10.0)}, prices_krw={"USDT": 1_000.0},
                 loans={"liab:USDT": 0.0}, earn={"asset_valuation": 0.0})
    assert _run(_new(okx=zero)) == {}
    # A failed snapshot's loans are not read: the row needs ok.
    failed = snapshot.Snapshot(venue="kis", utc=UTC, ok=False, error="kis: x", loans={"loan_amt": 1.0})
    assert _run(_new(kis=failed)) == {}


def test_hard_block_events_and_derivatives():
    def okx(flags) -> snapshot.Snapshot:
        return _snap("okx", holdings={"USDT": snapshot.Holding(units=10.0)}, prices_krw={"USDT": 1_000.0},
                     flags=frozenset(flags))
    assert _run(_new(okx=okx({"EVENTS"}))) == {("okx", "HARD_BLOCK_EVENTS"): {}}
    assert _run(_new(okx=okx({"derivative_position"}))) == {("okx", "HARD_BLOCK_DERIVATIVE"): {}}
    assert _run(_new(okx=okx({"EVENTS", "derivative_position"}))) == {("okx", "HARD_BLOCK_EVENTS"): {},
                                                                       ("okx", "HARD_BLOCK_DERIVATIVE"): {}}


def test_floor_at_the_floor_and_1_krw_above():
    assert _run(_new(), owner=_owner(limits={"total_loss_floor_krw": 60_000.0})) == {("all", "FLOOR"): {}}
    assert _run(_new(), owner=_owner(limits={"total_loss_floor_krw": 59_999.0})) == {}   # equity = floor + 1


def test_daily_loss_at_the_limit_and_1_krw_less():
    since = "2026-10-23T15:00:00Z"                                          # 00:00 KST, today's first poll
    assert _run(_new(), start=(65_000.0, since)) == {("all", "DAILY_LOSS"): {"since": since}}
    later = "2026-10-23T15:05:00Z"                                          # the slot is the day start's own utc
    assert _run(_new(), start=(65_000.0, later)) == {("all", "DAILY_LOSS"): {"since": later}}
    assert _run(_new(), start=(64_999.0, since)) == {}                      # a loss of 4,999
    assert _run(_new(), start=None) == {}                                   # no day start: nothing to compare


def test_okx_cap_at_the_cap_and_1_krw_above():
    owner = _owner(caps={"okx_equity_share": 0.25})
    def venues(kis_krw: float, okx_usdt: float) -> dict:                    # equity stays 40,000
        return _new(kis=_snap("kis", cash={"KRW": kis_krw}),
                    okx=_snap("okx", holdings={"USDT": snapshot.Holding(units=okx_usdt)}, prices_krw={"USDT": 1.0}))
    assert positions.live_positions(venues(10_000.0, 10_000.0), NOW).equity_krw == 40_000.0
    assert _run(venues(10_000.0, 10_000.0), owner=owner) == {}              # at the cap: 10,000 of 40,000
    assert _run(venues(9_999.0, 10_001.0), owner=owner) == {("okx", "OKX_CAP"): {}}


def test_outage_on_the_third_failed_poll():
    assert _run(_new(upbit=_failed("upbit")), _prev(upbit=checks.Prior(last_ok=None, fails=1))) == {}
    assert _run(_new(upbit=_failed("upbit")), _prev(upbit=checks.Prior(last_ok=None, fails=2))) == {
        ("upbit", "OUTAGE"): {"n": 3, "when": UTC}}
    assert _run(_new(kis=_failed("kis")), _prev(kis=checks.Prior(last_ok=None, fails=7))) == {
        ("kis", "OUTAGE"): {"n": 8, "when": UTC}}
    # `when` is the failed snapshot's own utc, not the poll's clock.
    assert _run(_new(upbit=_failed("upbit")), _prev(upbit=checks.Prior(last_ok=None, fails=2)),
                now=NOW + timedelta(minutes=1)) == {("upbit", "OUTAGE"): {"n": 3, "when": UTC}}
    # Not an outage: KEY_MISSING and KIS_UNSIGNED already say why (E31, E42).
    assert _run(_new(upbit=_failed("upbit", KEYS_MISSING)), _prev(upbit=checks.Prior(last_ok=None, fails=9))) == {
        ("upbit", "KEY_MISSING"): {}}
    assert _run(_new(kis=_failed("kis", UNSIGNED)), _prev(kis=checks.Prior(last_ok=None, fails=9))) == {
        ("kis", "KIS_UNSIGNED"): {}}


def test_clock_skew_reads_the_offset_at_receipt():
    def kis(**fields) -> snapshot.Snapshot:
        return _snap("kis", cash={"KRW": 30_000.0}, **fields)
    assert _run(_new(kis=kis(clock_offset_s=60.0))) == {}
    assert _run(_new(kis=kis(clock_offset_s=61.0))) == {("kis", "CLOCK_SKEW"): {"seconds": 61}}
    assert _run(_new(kis=kis(clock_offset_s=-61.4))) == {("kis", "CLOCK_SKEW"): {"seconds": 61}}
    assert _run(_new(kis=kis(clock_offset_s=61.6))) == {("kis", "CLOCK_SKEW"): {"seconds": 62}}     # rounded
    assert _run(_new(kis=kis(clock_offset_s=60.5))) == {("kis", "CLOCK_SKEW"): {"seconds": 60}}     # half to even
    # A correct clock: KIS answered 90 s after the poll started (read last, E39), with its clock 0.5 s ahead.
    late = kis(server_utc=model.iso_utc(NOW + timedelta(seconds=90)), clock_offset_s=0.5)
    assert _run(_new(kis=late)) == {}
    # A failed snapshot that carries an offset is still checked.
    assert _run(_new(okx=_failed("okx", clock_offset_s=-120.0))) == {("okx", "CLOCK_SKEW"): {"seconds": 120}}


# --------------------------------------------------------------------------- #
# Missing keys and unsigned code (E31, E42; E1R2-8, E1R2-9)
# --------------------------------------------------------------------------- #
def test_missing_keys_alert_once_a_day_never_as_an_outage_and_clear_when_ok():
    state = {"inquiry": [], "alerts": []}
    for i in range(5):
        now = NOW + timedelta(minutes=5 * i)
        out = _poll(state, _new(now, upbit=_failed("upbit", KEYS_MISSING, utc=model.iso_utc(now))), now)
        assert [k for k in out["raw"] if k[0] == "upbit"] == [("upbit", "KEY_MISSING")], (i, out["raw"])
        assert out["prev"]["upbit"].fails == 0, i                         # the streak never starts
        assert "Upbit: keys not in .env" in out["skipped"], out["skipped"]
        want = [("upbit", "KEY_MISSING"), ("all", "NOT_SET")] if i == 0 else []
        assert out["fresh"] == want and out["clears"] == [], (i, out)
    now = NOW + timedelta(minutes=25)
    out = _poll(state, _new(now), now)                                      # the keys are back
    assert out["fresh"] == [] and out["clears"] == [("upbit", "KEY_MISSING")], out
    assert out["skipped"] == ()


def test_unsigned_kis_alerts_once_a_day_and_nothing_else():
    state = {"inquiry": [], "alerts": []}
    for i in range(4):
        now = NOW + timedelta(minutes=5 * i)
        out = _poll(state, _new(now, kis=_failed("kis", UNSIGNED, utc=model.iso_utc(now))), now)
        assert [k for k in out["raw"] if k[0] == "kis"] == [("kis", "KIS_UNSIGNED")], (i, out["raw"])
        assert "KIS: code not signed" in out["skipped"]
        assert out["fresh"] == ([("kis", "KIS_UNSIGNED"), ("all", "NOT_SET")] if i == 0 else []), (i, out)
    now = NOW + timedelta(minutes=20)
    out = _poll(state, _new(now), now)                                      # the code is signed
    assert out["clears"] == [("kis", "KIS_UNSIGNED")] and out["fresh"] == [], out


def test_priors_end_a_fail_streak_at_missing_keys_or_unsigned_code():
    def rows(*snaps) -> list[dict]:
        return [json.loads(snapshot.dump(s)) for s in snaps]
    real = _failed("upbit")
    assert checks.priors(rows(real, real, _failed("upbit", KEYS_MISSING)))["upbit"].fails == 0
    assert checks.priors(rows(_failed("upbit", KEYS_MISSING), real, real))["upbit"].fails == 2
    assert checks.priors(rows(_failed("kis"), _failed("kis", UNSIGNED)))["kis"].fails == 0
    assert checks.priors(rows(real, real, _snap("upbit"), real))["upbit"].fails == 1      # an ok poll ends it too
    # The first real failure after the keys arrive: fails == 0 before it, so no OUTAGE until two more.
    state = {"inquiry": rows(*[_failed("okx", KEYS_MISSING)] * 3), "alerts": []}
    out = _poll(state, _new(okx=_failed("okx")), NOW)
    assert out["prev"]["okx"].fails == 0 and ("okx", "OUTAGE") not in out["raw"], out
    # The same once the code is signed: the first real KIS failure after unsigned polls counts from 0.
    state = {"inquiry": rows(*[_failed("kis", UNSIGNED)] * 3), "alerts": []}
    out = _poll(state, _new(kis=_failed("kis")), NOW)
    assert out["prev"]["kis"].fails == 0 and ("kis", "OUTAGE") not in out["raw"], out


def test_three_real_failures_raise_outage_and_a_recovery_clears_it():
    state = {"inquiry": [], "alerts": []}
    for i in range(3):
        now = NOW + timedelta(minutes=5 * i)
        out = _poll(state, _new(now, okx=_failed("okx", utc=model.iso_utc(now))), now)
        assert (("okx", "OUTAGE") in out["raw"]) == (i == 2), (i, out["raw"])
    assert ("okx", "OUTAGE") in out["fresh"]
    now = NOW + timedelta(minutes=15)
    out = _poll(state, _new(now), now)
    assert out["clears"] == [("okx", "OUTAGE")] and out["fresh"] == [], out     # logged, not alerted


# --------------------------------------------------------------------------- #
# Not set (E43; E1R2-12)
# --------------------------------------------------------------------------- #
def test_unset_limits_and_no_live_positions_are_listed_not_alerted():
    unset = _owner(caps={}, limits={})
    poor = _new(kis=_snap("kis", cash={"KRW": 1.0}))                        # far below any floor
    limits = checks.limits_from(unset, (10**9, "2026-10-23T15:00:00Z"))
    assert checks.run_checks(_prev(), poor, unset, limits, NOW) == []
    assert checks.not_set(poor, unset, limits, positions.live_positions(poor, NOW)) == (
        "FLOOR: not set", "DAILY_LOSS: not set", "OKX_CAP: not set")
    assert not {("all", "FLOOR"), ("all", "DAILY_LOSS"), ("okx", "OKX_CAP")} & checks.evaluated(
        _prev(), poor, unset, limits, NOW)
    owner = _owner(limits={"total_loss_floor_krw": 10**9, "daily_loss_krw": 1.0}, caps={"okx_equity_share": 0.01})
    stale = _new(upbit=_failed("upbit"))                                    # no live positions
    limits = checks.limits_from(owner, (10**9, "2026-10-23T15:00:00Z"))
    assert checks.run_checks(_prev(), stale, owner, limits, NOW) == []
    assert checks.not_set(stale, owner, limits, None) == (
        "FLOOR: no live positions", "DAILY_LOSS: no live positions", "OKX_CAP: no live positions")
    new = _new(kis=_failed("kis", UNSIGNED), upbit=_failed("upbit", KEYS_MISSING))
    assert checks.not_set(new, BROKEN, checks.limits_from(BROKEN, None), None) == (
        "KIS: code not signed", "Upbit: keys not in .env", "FLOOR: not set", "DAILY_LOSS: not set",
        "OKX_CAP: not set", "ADDRESS_LIST: owner log not OK")


def test_not_set_returns_only_listed_items_and_reaches_every_one():
    seen: set[str] = set()
    live = positions.live_positions(_new(), NOW)
    flagsets = (frozenset(), KEYS_MISSING, UNSIGNED, frozenset({"auth_error"}))
    for venue in snapshot.VENUES:
        for flags in flagsets:
            new = _new(**{venue: _failed(venue, flags)}) if flags else _new()
            for owner in (_owner(), _owner(caps={}, limits={}), BROKEN):
                for positions_now in (None, live):
                    items = checks.not_set(new, owner, checks.limits_from(owner, None), positions_now)
                    assert set(items) <= checks.NOT_SET_ITEMS, items
                    assert len(set(items)) == len(items), items
                    seen |= set(items)
    assert seen == checks.NOT_SET_ITEMS, sorted(checks.NOT_SET_ITEMS - seen)
    # code_unsigned is a KIS item only: on another venue it skips nothing.
    owner = _owner()
    upbit_unsigned = _new(upbit=_failed("upbit", UNSIGNED))
    assert "KIS: code not signed" not in checks.not_set(upbit_unsigned, owner, checks.limits_from(owner, None), None)


# --------------------------------------------------------------------------- #
# evaluated and the once-a-day rule (E19; E1R2-2)
# --------------------------------------------------------------------------- #
def test_evaluated_names_only_checks_whose_inputs_were_there():
    owner = _owner()
    start = (60_000.0, UTC)
    prev = _prev(upbit=checks.Prior(last_ok=_snap("upbit"), fails=0))
    new = _new(kis=_snap("kis", cash={"KRW": 30_000.0}, clock_offset_s=1.0))
    per_ok = ("KEY_HEALTH", "FOREIGN_ORDER", "D15_LIVE", "HARD_BLOCK_LIVE", "OUTAGE")
    want = ({(v, k) for v in snapshot.VENUES for k in per_ok} | {("kis", "CLOCK_SKEW")}
            | {("upbit", "HOLDINGS_CHANGED"), ("upbit", "ADDRESS_LIST")}
            | {("all", "FLOOR"), ("all", "DAILY_LOSS"), ("okx", "OKX_CAP")})
    assert checks.evaluated(prev, new, owner, checks.limits_from(owner, start), NOW) == frozenset(want)
    assert ("all", "DAILY_LOSS") not in checks.evaluated(prev, new, owner, checks.limits_from(owner, None), NOW)
    # The owner log not OK: no ADDRESS_LIST, and no limit checks (their limits count as absent).
    got = checks.evaluated(prev, new, BROKEN, checks.limits_from(BROKEN, start), NOW)
    assert ("upbit", "ADDRESS_LIST") not in got and ("upbit", "HOLDINGS_CHANGED") in got
    assert not {("all", "FLOOR"), ("all", "DAILY_LOSS"), ("okx", "OKX_CAP")} & got
    # A failed venue: nothing of it, except CLOCK_SKEW when it carries an offset; no live positions either.
    failed = _new(upbit=_failed("upbit", clock_offset_s=2.0))
    got = checks.evaluated(prev, failed, owner, checks.limits_from(owner, start), NOW)
    assert {k for v, k in got if v == "upbit"} == {"CLOCK_SKEW"}, got
    assert not {("all", "FLOOR"), ("all", "DAILY_LOSS"), ("okx", "OKX_CAP")} & got
    assert all(pair != ("all", "NOT_SET") for pair in got)


def test_due_fires_once_per_venue_and_text_key_per_seoul_day():
    order = _alert("upbit", "FOREIGN_ORDER")
    assert _due_run([([order], {("upbit", "FOREIGN_ORDER")})] * 3) == [(["FOREIGN_ORDER"], []), ([], []), ([], [])]
    # The same text_key on another venue is its own key.
    kis_order = _alert("kis", "FOREIGN_ORDER")
    assert _due_run([([order], set()), ([order, kis_order], set())]) == [(["FOREIGN_ORDER"], []),
                                                                         (["FOREIGN_ORDER"], [])]


def test_due_two_text_keys_of_one_kind_are_each_fresh():
    loan, earn = _alert("okx", "D15_LOAN"), _alert("okx", "D15_EARN")
    done = {("okx", "D15_LIVE")}
    assert _due_run([([loan, earn], done)]) == [(["D15_LOAN", "D15_EARN"], [])]          # raised together
    assert _due_run([([loan], done), ([loan, earn], done), ([loan, earn], done)]) == [
        (["D15_LOAN"], []), (["D15_EARN"], []), ([], [])]                                   # D15_LOAN then D15_EARN
    explained, unexplained = _alert("upbit", "HOLDINGS_EXPLAINED"), _alert("upbit", "HOLDINGS_UNEXPLAINED")
    done = {("upbit", "HOLDINGS_CHANGED")}
    assert _due_run([([explained], done), ([unexplained], done), ([unexplained], done)]) == [
        (["HOLDINGS_EXPLAINED"], []), (["HOLDINGS_UNEXPLAINED"], ["HOLDINGS_EXPLAINED"]), ([], [])]


def test_due_a_level_rise_fires_at_once():
    auth, missing = _alert("upbit", "KEY_AUTH"), _alert("upbit", "KEY_MISSING")
    # KEY_AUTH red; then KEY_MISSING amber while KEY_HEALTH is not evaluated (KEY_AUTH not cleared); then KEY_AUTH
    # again: the latest non-clear row of (upbit, KEY_HEALTH) is amber, so it fires; the poll after, it does not.
    assert _due_run([([auth], set()), ([missing], set()), ([auth], set()), ([auth], set())]) == [
        (["KEY_AUTH"], []), (["KEY_MISSING"], []), (["KEY_AUTH"], []), ([], [])]


def test_due_lists_amber_and_info_before_red_within_a_poll():
    auth, missing = _alert("upbit", "KEY_AUTH"), _alert("upbit", "KEY_MISSING")
    note = _alert("all", "NOT_SET")
    rows: list[dict] = []
    fresh, clears = checks.due([auth, missing, note], frozenset(), rows, NOW)
    assert [a.text_key for a in fresh] == ["KEY_MISSING", "NOT_SET", "KEY_AUTH"] and clears == []
    rows += _stored(fresh, NOW)
    fresh, clears = checks.due([auth, missing], frozenset(), rows, NOW + timedelta(minutes=5))
    assert fresh == [] and clears == []                       # the red is its group's latest row: no re-fire


def test_due_clears_only_evaluated_keys_and_a_cleared_key_fires_again():
    order = _alert("upbit", "FOREIGN_ORDER")
    done = {("upbit", "FOREIGN_ORDER")}
    assert _due_run([([order], done), ([], done), ([order], done), ([], set()), ([order], done)]) == [
        (["FOREIGN_ORDER"], []), ([], ["FOREIGN_ORDER"]), (["FOREIGN_ORDER"], []), ([], []), ([], [])]
    rows = _stored([order], NOW)
    _fresh, clears = checks.due([], frozenset(done), rows, NOW + timedelta(minutes=5))
    assert clears == [checks.Alert(venue="upbit", kind="FOREIGN_ORDER", level="clear", text_key="FOREIGN_ORDER",
                                   slots={})]
    assert checks.row(clears[0], UTC)["sent"] is True and checks.verify_row(_stored(clears, NOW)[0])
    # An ok venue's OUTAGE evaluation is the recovery: it clears the poller's OUTAGE_CRASH too (contract 15.1).
    crash = checks.Alert(venue="kis", kind="OUTAGE", level="amber", text_key="OUTAGE_CRASH", slots={"when": UTC})
    assert _due_run([([crash], set()), ([], {("kis", "OUTAGE")})]) == [(["OUTAGE_CRASH"], []), ([], ["OUTAGE_CRASH"])]


def test_a_flaky_venue_neither_clears_nor_refires_foreign_order():
    order = snapshot.Order(id="u-open-1", symbol="BTC", side="buy", units=0.0001, price=90_000_000.0)
    state = {"inquiry": [], "alerts": []}
    times = [NOW + timedelta(minutes=5 * i) for i in range(3)]
    def upbit(now) -> snapshot.Snapshot:
        return _snap("upbit", utc=model.iso_utc(now), cash={"KRW": 20_000.0}, open_orders=(order,))
    out = _poll(state, _new(times[0], upbit=upbit(times[0])), times[0])
    assert out["fresh"] == [("upbit", "FOREIGN_ORDER")], out
    out = _poll(state, _new(times[1], upbit=_failed("upbit", utc=model.iso_utc(times[1]))), times[1])
    assert ("upbit", "FOREIGN_ORDER") not in out["clears"] and ("upbit", "FOREIGN_ORDER") not in out["fresh"], out
    out = _poll(state, _new(times[2], upbit=upbit(times[2])), times[2])
    assert out["fresh"] == [] and out["clears"] == [], out


def test_due_counts_rows_by_seoul_date():
    order = _alert("upbit", "FOREIGN_ORDER")
    done = frozenset({("upbit", "FOREIGN_ORDER")})
    late = datetime(2026, 10, 24, 14, 59, 59, tzinfo=timezone.utc)       # 23:59:59 KST on 2026-10-24
    rows = _stored([order], late - timedelta(minutes=5))
    assert checks.due([order], done, rows, late) == ([], [])             # the same Seoul day
    fresh, clears = checks.due([order], done, rows, late + timedelta(seconds=1))   # 00:00:00 KST on 2026-10-25
    assert [a.text_key for a in fresh] == ["FOREIGN_ORDER"] and clears == []
    # Yesterday's rows are no reason to clear today either.
    assert checks.due([], done, rows, late + timedelta(seconds=1)) == ([], [])


def test_due_writes_the_not_set_row_once_a_day_and_never_clears_it():
    note = _alert("all", "NOT_SET")
    every = {(v, k) for v in checks.VENUE_NAMES for k in checks.KINDS} - {("all", "NOT_SET")}
    day = [([note], every), ([note], every), ([], every)]
    assert _due_run(day) == [(["NOT_SET"], []), ([], []), ([], [])]
    rows = _stored([note], NOW)
    tomorrow = NOW + timedelta(days=1)
    fresh, clears = checks.due([note], frozenset(every), rows, tomorrow)
    assert [a.text_key for a in fresh] == ["NOT_SET"] and clears == []
    assert checks.row(note, UTC)["sent"] is True and checks.row(note, UTC)["level"] == "info"


def test_due_ignores_rows_that_do_not_verify():
    order = _alert("upbit", "FOREIGN_ORDER")
    good = _stored([order], NOW)[0]
    forged = [dict(good, slots={"n": "21000 KRW"}), dict(good, kind="OUTAGE"), dict(good, utc="2026-13-40T00:00:00Z"),
              dict(good, venue=["upbit"]), dict(good, text_key=["FOREIGN_ORDER"]), "not a row", None]
    fresh, _clears = checks.due([order], frozenset(), forged, NOW + timedelta(minutes=5))
    assert [a.text_key for a in fresh] == ["FOREIGN_ORDER"]               # no forged row mutes it


def test_a_stamp_past_the_last_seoul_date_is_refused_and_never_raises():
    # 9999-12-31T15:00:00Z is 10000-01-01 in Seoul, which datetime cannot hold: refused, never an OverflowError.
    order = _alert("upbit", "FOREIGN_ORDER")
    good = _stored([order], NOW)[0]
    assert checks.verify_row(dict(good, utc="9999-12-31T14:59:59Z"))        # 9999-12-31 23:59:59 KST: still a date
    late = dict(good, utc="9999-12-31T23:59:59Z")
    assert checks.verify_row(late) is False
    fresh, _clears = checks.due([order], frozenset(), [late], NOW)
    assert [a.text_key for a in fresh] == ["FOREIGN_ORDER"]
    forged = _forged(json.loads(snapshot.dump(_snap("upbit"))), utc="9999-12-31T23:59:59Z")
    assert checks.day_start([forged], NOW) is None and checks.priors([forged])["upbit"].last_ok is None


# --------------------------------------------------------------------------- #
# Rows, priors and the day start
# --------------------------------------------------------------------------- #
def test_row_sent_flags_and_shape():
    for key, (kind, level, _template) in checks.TEXT.items():
        alert = _alert("upbit", key)
        r = checks.row(alert, UTC)
        assert set(r) == {"kind", "level", "sent", "slots", "text_key", "utc", "venue"}
        assert r["sent"] is (level == "info") and (r["kind"], r["level"], r["utc"]) == (kind, level, UTC)
    clear = checks.Alert(venue="kis", kind="OUTAGE", level="clear", text_key="OUTAGE")
    later = "2026-10-24T00:05:00Z"                                          # the row carries the utc it is given
    assert checks.row(clear, later) == {"kind": "OUTAGE", "level": "clear", "sent": True, "slots": {},
                                        "text_key": "OUTAGE", "utc": later, "venue": "kis"}
    assert checks.row(_alert("kis", "FOREIGN_ORDER"), UTC)["sent"] is False
    assert checks.row(_alert("kis", "OUTAGE"), UTC)["sent"] is False


def test_verify_row_accepts_every_written_row():
    for key, (kind, _level, _template) in checks.TEXT.items():
        for venue in checks.VENUE_NAMES:
            assert checks.verify_row(_stored([_alert(venue, key)], NOW)[0]), (venue, key)
            clear = checks.Alert(venue=venue, kind=kind, level="clear", text_key=key)
            assert checks.verify_row(_stored([clear], NOW)[0]), (venue, key, "clear")
    for items in (sorted(checks.NOT_SET_ITEMS), ["KIS: code not signed"]):
        note = checks.Alert(venue="all", kind="NOT_SET", level="info", text_key="NOT_SET",
                            slots={"skipped": "; ".join(items)})
        assert checks.verify_row(_stored([note], NOW)[0])


def test_verify_row_refuses_anything_else():
    good = _stored([_alert("upbit", "HOLDINGS_UNEXPLAINED")], NOW)[0]
    note = _stored([_alert("all", "NOT_SET")], NOW)[0]
    expiry = _stored([_alert("upbit", "KEY_EXPIRY")], NOW)[0]
    assert checks.verify_row(good) and checks.verify_row(note) and checks.verify_row(expiry)
    bad = [
        {k: v for k, v in good.items() if k != "sent"},                    # a missing key
        dict(good, extra=1),                                                # an extra key
        dict(good, text_key="NO_SUCH_KEY"), dict(good, text_key=["HOLDINGS_UNEXPLAINED"]),
        dict(good, kind="FOREIGN_ORDER"), dict(good, kind=["HOLDINGS_CHANGED"]),
        dict(good, level="amber"), dict(good, level="info"),                # the key's own level or "clear" only
        dict(good, venue="binance"), dict(good, venue=["upbit"]),
        dict(good, sent="false"), dict(good, sent=0),
        dict(good, utc="2026-10-24 00:00:00"), dict(good, utc="2026-13-40T00:00:00Z"), dict(good, utc=None),
        dict(good, utc="9999-12-31T23:59:59Z"),                             # no Seoul date (10000-01-01)
        dict(good, slots=dict(good["slots"], n=True)),                      # a bool in an int slot
        dict(good, slots=dict(good["slots"], n="2")),                       # a str in an int slot
        dict(good, slots=dict(good["slots"], n=2.0)),
        dict(good, slots=dict(good["slots"], amount=1)),                    # an extra slot
        dict(good, slots={k: v for k, v in good["slots"].items() if k != "k"}),     # a missing slot
        dict(good, slots=[1, 2]),
        dict(good, level="clear"),                                          # a clear row has no slots
        dict(expiry, slots=dict(expiry["slots"], expires="soon")),          # a time slot that is not a stamp
        dict(expiry, slots=dict(expiry["slots"], expires=1792800000)),
        dict(note, slots={"skipped": "FLOOR: not set; the account holds KRW 21000"}),   # not a NOT_SET item
        dict(note, slots={"skipped": "FLOOR: not set; "}),                  # an empty item
        dict(note, slots={"skipped": ""}), dict(note, slots={"skipped": 3}),
        [good], "row", None, 1,
    ]
    for obj in bad:
        assert checks.verify_row(obj) is False, obj


def test_priors_from_inquiry_rows():
    first = _snap("upbit", utc="2026-10-23T23:50:00Z", cash={"KRW": 1.0})
    second = _snap("upbit", utc="2026-10-23T23:55:00Z", cash={"KRW": 2.0})
    rows = [json.loads(snapshot.dump(s)) for s in (
        first, _snap("kis", utc="2026-10-23T23:50:00Z"), second, _failed("upbit", utc="2026-10-23T23:57:00Z"),
        _failed("upbit", utc="2026-10-23T23:58:00Z"))]
    tampered = dict(json.loads(snapshot.dump(_snap("upbit", utc="2026-10-23T23:59:00Z"))), cash={"KRW": 9.0})
    month_13 = _forged(json.loads(snapshot.dump(_snap("upbit", utc="2026-10-23T23:59:30Z"))),
                       utc="2026-13-40T00:00:00Z")
    got = checks.priors(rows + [tampered, month_13, {"venue": "upbit"}])    # all three are skipped
    assert got["upbit"] == checks.Prior(last_ok=second, fails=2), got["upbit"]
    assert got["kis"].last_ok is not None and got["kis"].fails == 0
    assert got["okx"] == checks.Prior(last_ok=None, fails=0)
    assert set(got) == set(snapshot.VENUES)
    assert checks.priors([]) == {v: checks.Prior(last_ok=None, fails=0) for v in snapshot.VENUES}


def test_day_start_is_todays_first_poll_with_live_positions():
    def poll(stamp: str, **venues) -> list[dict]:
        new = _new(datetime.fromisoformat(stamp), **venues)
        return [json.loads(snapshot.dump(new[v])) for v in snapshot.VENUES]
    yesterday = poll("2026-10-23T14:59:59Z")                                # 23:59:59 KST, the day before
    no_live = poll("2026-10-23T15:00:00Z", upbit=_failed("upbit", utc="2026-10-23T15:00:00Z"))
    first = poll("2026-10-23T15:05:00Z", kis=_snap("kis", utc="2026-10-23T15:05:00Z", cash={"KRW": 31_000.0}))
    later = poll("2026-10-23T15:10:00Z")
    hour_25 = [_forged(r, utc="2026-10-23T25:00:00Z") for r in poll("2026-10-23T15:01:00Z")]   # skipped
    assert checks.day_start(yesterday + no_live + hour_25 + first + later, NOW) == (61_000.0, "2026-10-23T15:05:00Z")
    assert checks.day_start(yesterday, NOW) is None
    assert checks.day_start(yesterday + no_live, NOW) is None
    assert checks.day_start([], NOW) is None
    # At 23:59:59 KST the poll at 23:59:59 KST is today's first.
    assert checks.day_start(yesterday, datetime(2026, 10, 23, 14, 59, 59, tzinfo=timezone.utc)) == (
        60_000.0, "2026-10-23T14:59:59Z")


# --------------------------------------------------------------------------- #
# The leak scan (contract 15.3)
# --------------------------------------------------------------------------- #
def _zoo() -> list[checks.Alert]:
    """Three polls whose fixtures hold balances (21000, 0.0001) and the fixture address and that raise every check
    table text_key between them."""
    order = snapshot.Order(id="0000123456", symbol="005930", side="buy", units=1.0, price=60_000.0)
    kis_last = _snap("kis", cash={"KRW": 21_000.0}, holdings={"005930": snapshot.Holding(units=2.0)},
                     prices_krw={"005930": 61_000.0})
    kis = _snap("kis", cash={"KRW": 21_000.0}, deposit_krw=21_000.0, holdings={"005930": snapshot.Holding(units=1.0)},
                prices_krw={"005930": 61_000.0}, loans={"tot_loan_amt": 21_000.0}, open_orders=(order,),
                clock_offset_s=75.0)
    upbit_last = _snap("upbit", cash={"KRW": 20_000.0}, holdings={"BTC": snapshot.Holding(units=0.0002)},
                       prices_krw={"BTC": 100_000_000.0})
    upbit = _snap("upbit", cash={"KRW": 20_000.0}, holdings={"BTC": snapshot.Holding(units=0.0001)},
                  prices_krw={"BTC": 100_000_000.0}, key_expiry=model.iso_utc(NOW + timedelta(days=10)),
                  withdrawals=(snapshot.Move(id="u-wd-1", symbol="BTC", side="out", units=0.0001),),
                  withdrawal_addresses=(snapshot.Address(currency="BTC", net_type="BTC", address=ADDRESS),))
    okx = _snap("okx", holdings={"USDT": snapshot.Holding(units=10.0)}, prices_krw={"USDT": 1_400.0},
                loans={"liab:USDT": 3.0}, earn={"savings:USDT": 5.0}, flags=frozenset({"EVENTS",
                                                                                       "derivative_position"}))
    owner = _owner(caps={"okx_equity_share": 0.01}, limits={"total_loss_floor_krw": 200_000.0,
                                                            "daily_loss_krw": 5_000.0}, addresses=frozenset())
    prev = _prev(kis=checks.Prior(last_ok=kis_last, fails=0), upbit=checks.Prior(last_ok=upbit_last, fails=0),
                 okx=checks.Prior(last_ok=None, fails=2))
    new = {"kis": kis, "upbit": upbit, "okx": okx}
    alerts = checks.run_checks(prev, new, owner, checks.limits_from(owner, (200_000.0, "2026-10-23T15:00:00Z")), NOW)
    new = dict(new, okx=_failed("okx", SELF_CHECK))
    alerts += checks.run_checks(prev, new, owner, checks.limits_from(owner, None), NOW)
    new = {"kis": _failed("kis", UNSIGNED), "upbit": _failed("upbit", frozenset({"auth_error"})),
           "okx": _failed("okx", KEYS_MISSING)}
    alerts += checks.run_checks(prev, new, owner, checks.limits_from(owner, None), NOW)
    return alerts


def test_no_balance_or_address_in_any_sentence():
    for text in ("KRW 21000", "21,000 KRW", "\u20a921000", "21000\uc6d0", "0.0001 BTC", "$5", "usdt 10", "5usd"):
        assert LEAK.search(text), text                                      # the scan catches what it must
    assert LONG_RUN.search(ADDRESS) and not LEAK.search("OKX failed 3 polls in a row")
    texts = [template for _kind, _level, template in checks.TEXT.values()]
    for key in checks.TEXT:
        for venue in checks.VENUE_NAMES:
            texts.append(checks.render(_alert(venue, key)))
    zoo = _zoo()
    raised = {a.text_key for a in zoo}
    poller_own = {"OUTAGE_CRASH", "CRASH_UNLOGGED", "EVIDENCE_BROKEN", "NOT_SET"}
    assert raised == set(checks.TEXT) - poller_own, sorted(set(checks.TEXT) - poller_own - raised)
    for a in zoo:
        assert checks.verify_row(_stored([a], NOW)[0]), a                  # every check alert's row verifies
        texts.append(checks.render(a))
    note = checks.Alert(venue="all", kind="NOT_SET", level="info", text_key="NOT_SET",
                        slots={"skipped": "; ".join(sorted(checks.NOT_SET_ITEMS))})
    texts.append(checks.render(note))
    for text in texts:
        assert not LEAK.search(text), text
        assert not LONG_RUN.search(text), text
        for needle in ("21000", "21,000", "0.0001", "61000", "bc1q", "fixtureaddress", ADDRESS):
            assert needle not in text, (needle, text)
