# Standing deployment and multi-day arming

Date: 2026-11-12 (Asia/Seoul).
Status: proposed. The owner approved this design in conversation on 2026-11-12. Nothing is implemented. Merging this
document approves the design only. It signs nothing, arms nothing and sends no order. It changes `tools/signer/sign.py`
and the owner-log fold in design. The implementation PR that makes those changes is reviewed and merged by the owner
like any other.
Builds on: [controlled launcher, current planner and study runbook](2026-11-12-controlled-launch-and-planner-design.md)
(below, "the base design"). Its code lands after the base design's code (base design, section 9).

Owner financial parameters remain private and are not written here. This is software design, not legal, tax or
investment advice. Neither the software nor its author is a licensed advisor.

## 1. Owner decisions (2026-11-12)

- **Q3.** Once armed, the app keeps trading until the owner says stop, or until the app stops itself under a safety
  rule (for example a Windows update restart). Multi-day standing arming is included in this design.
- **Q4.** One signature pair covers at most 7 days. The study freezes `review_max_age_seconds` at 30 days, so one
  study can be traded for up to 30 days after it ends, with a new signature pair every 7 days.
- **Q6.** After a safety stop, the app sells automatically any holding that the strategy no longer manages (6.4).

## 2. Why every session is one day today

- A prepared session is valid only on its Seoul date (`session.py:221`).
- Owner tools accept a window of at most one day (`launch.py:107`).
- A review approval lasts at most 24 hours (`review_auth.py:27`, `:101`; `tools/signer/sign.py:1220`, `:1270`).
- Arming is a signature on one session id (`owner.py:155`; `sign.py:209`), and nothing but a `system_disarm` closes it
  (`owner.py:509-522`).

Standing deployment keeps the daily session. It changes only who arms each session, and for how long one review
lasts.

## 3. The schedule

The private file `schedule.json` (schema `tradegen.schedule/1`) holds:

| Field | Rule |
|---|---|
| `deployment_id` | Matches the driver's window id pattern (`driver.py:34`), at most 90 characters |
| `first_start` | A UTC instant on a bar boundary |
| `window_seconds` | A multiple of the protocol's bar. The default is 172,800 (48 hours), the same shape as the study. The maximum is 259,200 (72 hours), the universe window cap. |
| `count` | At least 1 |

- Window `k` (from 0) has `deployment_id` `<deployment_id>.w<k>`. It starts at
  `first_start + k * (window_seconds + bar_seconds)` and ends `window_seconds` later. The one-bar gap between windows
  is for the handoff (5.1).
- The span from `first_start` to the end of the last window is at most 7 days, else `SCHEDULE_TOO_LONG`.
- `launch.py:107` is raised from one day to 72 hours, so `export-driver` and `setup-history` accept each window. The
  rehearsal reads its window with the same function (`rehearsal.py:327`), so it can then rehearse a 48-hour window
  too. It stays dry.
- The fixed driver still targets zero at each window end (`driver.py:297`). A standing deployment therefore trades in
  48-hour blocks, like the study, and starts every window flat.

## 4. Two owner signatures per period

### 4.1 `review-approve` in schedule form

- **Body.** The review body gains `schema_version: 2` and a `schedule` object with the four fields of section 3 and
  the protocol's `bar_seconds`. Its `driver_identity` is the identity of window 0.
- **Window match.** For window `k`, a driver identity is accepted when it equals the body's `driver_identity` except
  that its `deployment_window_digest` is the digest of window `k`.
- **Lifetime.** For `schema_version: 2`, `expires_at - issued_at` is at most 604,800 seconds (7 days). Version 1 keeps
  the 24-hour limit. Every other bound is unchanged: `expires_at` is no later than the request's `review_deadline`
  (`review_auth.py:100-101`), and no later than the study end plus `review_max_age_seconds` (`strategy.py:539-542`).
- **Audit.** In schedule form, the private account audit's `deployment_window_digest` field carries the schedule
  digest. The digest domains differ, so a schedule digest can never equal a window digest. `live.py` checks the
  audit against the schedule. The rehearsal keeps checking it against its one window (`rehearsal.py:332`).
- **Signer.** `review_auth.py` and the `review-approve` mirror in `tools/signer/sign.py` (`_rv_*`) change together and
  share the same test vectors.

### 4.2 A new owner-log kind, `standing_armed`

The owner signs it with `python -m tools.signer.sign event standing_armed --data '{...}'`. Its data:

| Field | Meaning |
|---|---|
| `deployment_id` | The schedule's id |
| `review_sha256` | The sha256 of the signed review document that the launcher loaded |
| `plan_sha256` | The sha256 of the planner's plan file (base design, 6.1) |
| `profile_contract_digest` | The profile's contract digest |
| `valid_until` | A UTC instant, after the signing time and at most 7 days after it |

- **Signing.** `live.py` status prints this object with every field but `valid_until` filled in, so the owner signs
  exactly what the launcher will check. The signer refuses a `valid_until` in the past or more than 7 days ahead.
- **Fold.** The fold treats an entry outside those bounds as a malformed log (`owner.ok` false, every buy blocked),
  like any other malformed entry.
- **Order.** Start `live.py` first, then sign. At startup the launcher closes every arming signed before it started
  (base design, 4.1). An entry signed too early is therefore closed, and must be signed again.
- **Re-arming.** Re-arming after a restart needs only a new `standing_armed` entry with the same `deployment_id`. The
  review stays valid until its own expiry.

### 4.3 The fold

`core/compliance/owner.py` gains:

- **`standing`:** the entries in force, those stamped at or before `now`, not closed, and with `now < valid_until`.
- **Closing.** An entry is closed by a later `system_disarm` whose data is `{"standing_id": <deployment_id>,
  "reason": ...}`. That is a second data shape of the existing system kind. It closes every open entry with that id
  up to its sequence number.
- **`open_armings`** (base design, 4.1) also holds the ids of standing entries that are not closed, as
  `("standing", id)` pairs, next to `("session", id)` pairs.
- **Loosenings.** While a standing entry is not closed, a loosening dated on or after that entry's date does not
  count. This rule is global, not per session, and the date is taken as for session armings (`owner.py:494`).
  Tightenings count at once, as today.
- **Relaxation route.** It also refuses while a standing entry is not closed (`controller.py:457`).

### 4.4 How a session counts as armed

- **The session field.** `PreparedSession` gains `standing_id: str | None`. It enters the session id digest and the
  journal row in the same way as PR 4a's `universe_batch_digest`. For other sessions it is `None` and left out, so
  existing ids do not change.
- **At preparation.** `prepare_launch_session(..., standing=binding)` takes the four fields that `live.py` computes
  from its own files: deployment id, review sha256, plan sha256, and profile contract digest. It requires an entry in
  `ctx.owner.standing` with exactly these fields, a window id under that deployment id, and `expires_at <= valid_until`.
- **At each order.** `verify_session` (`session.py:227`) treats the session as armed when `ctx.session.armed` holds,
  or when `prepared.standing_id` names an entry that is in force at `now`.
- **The preparation rule.** `session.py:138` keeps its meaning. A per-session arming still refuses preparation. A
  standing entry does not.

## 5. What the app does by itself

### 5.1 Windows and the handoff

- **When the schedule loads,** `live.py` runs `setup_history` for every window that has not started yet
  (`launch.py:154-166` requires `now < start`). A window that has already started is skipped, and the app waits for
  the next one.
- **Before window `k` starts,** it composes window `k`'s driver and coordinator.
- **At the gap after window `k - 1`,** it closes the old coordinator right after one of its account captures, then
  starts the new one. The new startup capture must come within `ACCOUNT_AGE` (30 s) of the old coordinator's last
  capture. A miss is the account-chain stop, a safety stop (6.2).
- **Measurement.** The handoff time is measured on the PC before the first standing deployment, like the universe
  measurements in its section 17.

### 5.2 Daily odds and preparation

While a standing entry for this schedule is in force and the coordinator has no live session, the app runs the
base design's `odds` and `prepare` itself:

- **When.**
  - A fixed profile: right after each window's startup unit, and right after each Seoul midnight boundary.
  - A universe profile: right after each Seoul midnight boundary, and after 09:40 KST (universe spec, section 9).
- **Binding.** The preparation is bound to the standing entry (4.4).
- **Retries.** A refusal is retried every 15 minutes. Status shows the last refusal code.
- **Card text.** The card goes to the private status log, with real odds as always.

Refusals that are expected and harmless:

- A fixed profile holding a position: preparation is refused until the account is flat (PLB 4.3, pin 3). Buys wait,
  and the driver's sells continue without a session (`runner.py:437`).
- A universe profile holding the traded coin after a capped buy: the card is stuck at start (PLB-O16, 4.5).
- Stale rules rows, or a review close to expiry.

Each session still ends by Seoul midnight (`session.py:221`; base design, 6.3). At its expiry, the base design
disarms that session (its 4.3). The standing entry stays in force.

### 5.3 Who may prepare

- While a standing entry is not closed, every preparation must be bound to it. An unbound preparation is refused with
  `PREPARATION_STANDING_REQUIRED`.
- While no standing entry is open, the single-session path of the base design is unchanged.

## 6. Stops

### 6.1 The owner stops

- **What closes it.** The owner's `stop`, `disarm` or `close` in the console closes the standing entry. That is
  `Controller.kill` on the live session, plus `system_disarm` with the `standing_id` and reason `owner_requested`.
- **Unlike a single session.** In the base design, `stop` leaves a single-session arming in place. Under a standing
  deployment, `stop` also ends the deployment, because the owner said stop (Q3).
- **No auto-sell.** The owner decides about holdings with `exit` (base design, 4.5).

### 6.2 Safety stops

These end the standing deployment automatically:

- a missed slot or boundary, which ends the window;
- the runner stopped by an unexpected error;
- the account chain stopped;
- a halt;
- the clock moving backward;
- an open arming found at startup, meaning a restart.

Each closes the standing entry (`system_disarm`, reason `safety_<code>`). Then auto-sell starts (6.4). If no current
account observation exists, the disarm is retried at each monitor unit with a red toast, as in base design 4.3.

### 6.3 Normal end

The standing deployment ends normally on any of these:

- `valid_until`;
- the review's expiry;
- the end of the last window.

Each closes the entry with reason `standing_ended`. There is no auto-sell, because each window already ends flat.

### 6.4 Auto-sell after a safety stop (Q6)

- **What it sells.** Every held unit of a coin traded by this profile that the runner no longer manages. That is the
  profile's coin for a fixed profile, and the held coin for a universe profile. Remainders below the minimum order are
  left (PLB 4.5).
- **How.** It sends the same order as the `exit` command (base design, 4.5) through `Coordinator.submit_exit`, at once
  and then once per bar (300 s) while units remain. Each attempt first cancels its own earlier unfilled exit.
- **Alerts.** Every attempt and its result raise a red toast.
- **When it ends.** When the holding is below the minimum order, or when the owner runs `close`.
- **When it cannot act.** It cannot act when the account chain or the book reads have stopped, which is the usual
  case after a reboot. Status then shows `autosell_blocked` with the code. Nothing sells until reads work again under
  the blocker-1 rules. Selling by hand on Upbit stays the owner's choice, outside the app.
- **Clock rollback.** After a clock rollback, the runner refuses protective actions while the time is earlier than the
  last time it saw (`runner.py:473`), so auto-sell waits until then.

**This amends PLB.** PLB 0.1 item 4 and acceptance (f) say that nothing sells on a breach or a halt. Under a standing
deployment, a halt is a safety stop, so the held coin is sold. The controller already allows sells under a halt and
blocks only buys (`controller.py:613-615`). Outside a standing deployment, PLB (f) is unchanged. The owner approved
the list of safety stops, halt included, on 2026-11-12. The owner confirms or reverses this amendment when reviewing
this document (open decision SD-O1, section 9).

## 7. What does not change

- The loss floor, the daily loss rule, the PLB admission cap, the stake pins, and every compliance check at each order.
- The Seoul-date rule for a session, and the 30-second preparation window.
- The rules table and its re-review, due by 2026-12-02. Stale rows block buys under a standing arming too.
- Exits and cancels, which never need an arming.

## 8. Files and tests

| File | Change |
|---|---|
| `execution_launch/review_auth.py` | Review body version 2 with `schedule`; a 7-day limit for version 2; the window-`k` identity match (4.1) |
| `tools/signer/sign.py` | The mirror of 4.1 in `review-approve`; the new event kind `standing_armed` and its checks (4.2) |
| `core/compliance/owner.py` | The `standing_armed` schema; `standing`, `open_armings` with standing ids, the `system_disarm` standing shape, the loosening rule (4.3) |
| `execution_control/session.py` | `PreparedSession.standing_id`; the standing check at preparation and in `verify_session` (4.4) |
| `execution_control/controller.py` | Write `system_disarm` with `standing_id`; the relaxation route refuses while a standing entry is open |
| `execution_launch/runner.py` | Pass `standing` to `prepare_session` |
| `execution_launch/coordinator.py` | Safety-stop detection and auto-sell (6.2, 6.4) |
| `tools/owner/launch.py` | Window cap 72 hours (section 3) |
| `tools/owner/live.py` | The schedule, the handoff, daily odds and preparation, standing status (5) |
| `docs/owner-runtime-operations.md`, `docs/first-trade-owner-checklist.md` | The standing steps |

Tests, by behaviour. All of them use fakes and a temporary home.

- A version-2 review is accepted for each window of its schedule and refused for a window outside it, and refused
  beyond 7 days. Version 1 keeps 24 hours. `sign.py` and `review_auth.py` agree on shared vectors.
- The signer refuses a `standing_armed` entry with `valid_until` in the past or more than 7 days ahead. The fold
  treats a hand-made one as malformed.
- A standing entry arms only matching sessions. A changed review, plan, profile or deployment id is not armed.
- A `system_disarm` with `standing_id` closes the entry. A new entry with the same id re-arms.
- A loosening signed during a standing period does not count until the entry closes. A tightening counts at once.
- An unbound preparation is refused while a standing entry is open.
- Each safety stop closes the entry and starts auto-sell. A normal end and an owner stop do not auto-sell.
- Auto-sell repeats once per bar, cancels its previous exit first, and stops when flat or on `close`.
- A handoff over 30 seconds is a safety stop.

Closure files among these need the one final `code_approved` (base design, section 9). The change to `sign.py` is the
one the hard rules reserve for the owner's approval. This document asks for that approval in design, and the
implementation PR asks for it again.

## 9. Open owner decisions and defaults

| Id | Question | Default in this document | Alternative |
|---|---|---|---|
| SD-O1 | Does a halt during a standing deployment auto-sell (6.4)? | Yes, as approved on 2026-11-12; this amends PLB (f) for standing deployments | No: a halt closes the standing entry but sells nothing, and PLB (f) stays as written |
| SD-O2 | Window length | 48 hours, the study's shape | 24 to 72 hours, a multiple of the bar |
| SD-O3 | Retry interval for a refused daily preparation | 15 minutes | Any interval of at least one bar |
| SD-O4 | Order of signing | Start the launcher, then sign `standing_armed` | None. Signing first is closed at startup by design (Q2). |

## 10. Risks and real odds

- **Unattended trading.** For up to 7 days the app trades without the owner watching. Every rule still applies, but
  nobody reviews each day's card before it trades. The card is still computed and logged each day, and a refused card
  still blocks the session.
- **Restarts.** A restart ends the deployment, and after a reboot of more than 30 seconds, auto-sell cannot act until
  the account chain works again (6.4).
- **A longer review.** A review that lasts 7 days rather than 24 hours lets a stale judgement run longer. The 30-day
  `review_max_age_seconds` bound still caps it from the study end.
- **No edge.** Standing arming adds no edge. With no real edge, the chance of reaching a target `T` from `W0` is at
  most `LB / (T - W0 + LB)` (PLB 7.1). Trading for longer does not raise that bound. It only spends the budget faster
  or slower. This is not legal, tax or investment advice.
