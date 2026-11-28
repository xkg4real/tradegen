"""The odds CLI (spec 4, 7.5 "Comparing plans"; O12, O15; Q12, Q15, Q45). Unsigned; it places no trade.

    python -m core.oddsdata.run --plan <plan.json> [--comparison <id>] [--paths N] [--refetch]

For each plan of the file: owner.load_context with the plan's stake as the equity (one context per distinct stake:
within one invocation the moment, the positions and the compliance home are the same, so the contexts would be
equal), then simulate.precheck, before any bar is loaded, any seam is called or the odds state is written. The plans
that pass form one comparison (inputs.begin_run, called once); each then gets its bars, its calendar and sessions
(KRX and US), the S_C3 replay (replay legs) and runs simulate.simulate. Every card goes through report.render, which
refuses its own banned output. Exit 0 when every plan is reported, 2 when any plan is refused (its named reason
printed), 4 on any exception ("crash: <type>: <text>" on stderr, nothing on stdout); --help prints the usage and
exits 0. It never writes the owner log. The default `now` of main() is the only wall clock in core/oddsdata."""
from __future__ import annotations

import argparse
import dataclasses
import sys
from datetime import datetime, timezone
from pathlib import Path

from core.compliance import model, owner
from core.odds import plan, report, simulate
from core.oddsdata import bars, inputs, replay

from core.odds_plan_file import load_plans


def _inputs(p: plan.Plan, ctx, now: datetime, begun: tuple, refetch: bool, replayed) -> plan.Inputs:
    """The injected data of a plan that passed the precheck: its bars, then (KRX and US) the signed calendar and
    the sessions, then (replay legs) the S_C3 replay. An unsigned calendar goes in as its error, never replaced by
    the shipped default, so simulate refuses CALENDAR_UNSIGNED (or CALENDAR_COVERAGE) by name."""
    _, inst = plan.instrument(p, ctx)
    market = plan.MARKET[(p.leg.venue, inst.section)]
    series = bars.load_leg(p, inst, now, refetch=refetch)
    cal, sha, error = (None, "", "") if market == "CRYPTO" else inputs.calendar_for(now)
    info = ((), (), (), "", error) if error else inputs.sessions(market, p.start, p.horizon_days, cal)
    return inputs.build_inputs(p, now, series=series, sessions_info=info, calendar_sha=sha,
                               replay=replayed if p.leg.edge_source == plan.REPLAY_SOURCE else None, run=begun)


def _run(args: argparse.Namespace, now: datetime) -> tuple[int, list[str]]:
    """(exit code, every plan's card in file order). A card refused here carries the context's provenance, as
    simulate's own refused cards do, except the card of a plan object the loader could not read: no context exists
    for it."""
    entries = load_plans(Path(args.plan).read_bytes())
    count, cards, refused, passing, contexts = len(entries), {}, False, [], {}
    for i, entry in enumerate(entries, start=1):
        if isinstance(entry, plan.Refusal):
            cards[i], refused = report.render(report.refusal_report(None, entry, index=i, count=count)), True
            continue
        stake = float(entry.stake_krw)
        if stake not in contexts:                                # Q11: the plan's stake is the equity
            contexts[stake] = owner.load_context(now, model.Positions(equity_krw=stake))
        ctx = contexts[stake]
        why = simulate.precheck(entry, ctx, args.paths)          # Q45: before any data, seam or state write
        if why is None:
            passing.append((i, entry, ctx))
        else:
            cards[i], refused = report.render(report.refusal_report(
                entry, why, index=i, count=count, provenance=simulate.context_provenance(ctx))), True
    if passing:
        typed = [p.leg.assumed_p for _, p, _ in passing if p.leg.edge_source == "assumed"]
        try:
            begun = inputs.begin_run(args.comparison, [plan.plan_hash(p) for _, p, _ in passing], typed)
        except ValueError as exc:                                # unknown id; no odds state written
            if args.comparison is None:
                raise
            why = plan.Refusal(code="UNSUPPORTED_PRODUCT", sub="comparison", detail=str(exc))
            for i, p, ctx in passing:
                cards[i] = report.render(report.refusal_report(p, why, index=i, count=count,
                                                               provenance=simulate.context_provenance(ctx)))
            refused = True
        else:
            replayed = None
            for i, p, ctx in passing:
                if p.leg.edge_source == plan.REPLAY_SOURCE and replayed is None:
                    replayed = replay.replay_s_c3()              # one replay (about 5 s) serves every replay plan
                rep = simulate.simulate(p, ctx, _inputs(p, ctx, now, begun, args.refetch, replayed),
                                        n_paths=args.paths)
                cards[i] = report.render(dataclasses.replace(rep, plan_index=i, plan_count=count))
                refused = refused or rep.refused is not None
    return (2 if refused else 0), [cards[i] for i in range(1, count + 1)]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m core.oddsdata.run", exit_on_error=False,
                                     description="Print the odds of every plan in a plan file.")
    parser.add_argument("--plan", required=True, help="the plan file (schema tradegen.odds_plan/1)")
    parser.add_argument("--comparison", help="a comparison id an earlier run printed: run these plans on its seed")
    parser.add_argument("--paths", type=int, help="paths per column, a whole multiple of the chunk size")
    parser.add_argument("--refetch", action="store_true", help="download the price history again, not from the cache")
    return parser


def main(argv=None, *, now: datetime | None = None) -> int:
    """The CLI's exit code (module docstring). stdout and stderr switch to UTF-8 first, as tests/run_all.py does."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    if now is None:
        now = datetime.now(timezone.utc)
    args = None
    try:
        args = _parser().parse_args(argv)
        code, cards = _run(args, now)
        print("\n".join(cards), end="")          # every card ends in a newline
    except SystemExit as exc:              # with exit_on_error=False only --help leaves argparse this way
        if args is None and exc.code == 0:
            return 0
        print(f"crash: SystemExit: {exc.code}", file=sys.stderr)
        return 4
    except Exception as exc:               # Q15: any failure, argparse errors included, is a crash
        print(f"crash: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 4
    return code


if __name__ == "__main__":
    raise SystemExit(main())
