"""Quote-cadence, positive-momentum research candidate. No venue or private key access."""
from __future__ import annotations

import argparse
from fractions import Fraction
from pathlib import Path
import re
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from tools.research import direction_forecast_adapter as forecasts
from tools.research._study_common import (
    DECIMAL_STR_RE, HEX64_RE, MARKET_RE, RESEARCH_FLAGS, StudyError, atomic_publish_json_ascii,
    canonical_ascii_bytes, parse_epoch_int, read_strict_json_file, read_verified_chained_log,
    require, sha256_ascii,
)

RULE = "tradegen-upside-quote-momentum-v1"
ARMS = ("q-M", "q-B1", "q-price")
RATE = 10_000


def _hash(value):
    require(type(value) is str and HEX64_RE.fullmatch(value), "INVALID_DIGEST")
    return value


def _num(value):
    require(type(value) is str and DECIMAL_STR_RE.fullmatch(value), "DECIMAL_REQUIRED")
    return Fraction(value)


def validate_terms(t, expected_sha):
    require(sha256_ascii(t) == _hash(expected_sha) and type(t) is dict and set(t) == {
        "rule", "market", "scope", "registered_at", "start", "end", "interval_seconds", "ttl_seconds",
        "max_lag_seconds", "fee_bps", "slippage_bps", "momentum_bps", "max_spread_bps", "notional_krw",
        "horizon_seconds", "hurdle_bps", "confidence", "models", "witness_public_key", "witness_program_sha256"
    }, "CANDIDATE_TERMS")
    require(t["rule"] == RULE and type(t["market"]) is str and MARKET_RE.fullmatch(t["market"])
            and type(t["scope"]) is str and 0 < len(t["scope"]) < 140, "CANDIDATE_SCOPE")
    start, end = parse_epoch_int(t["start"]), parse_epoch_int(t["end"])
    require(parse_epoch_int(t["registered_at"]) < start < end and type(t["models"]) is dict
            and set(t["models"]) == {"M", "B1"} and len({_hash(s) for s in t["models"].values()}) == 2,
            "PREREGISTRATION_REQUIRED")
    for field in ("witness_public_key", "witness_program_sha256"):
        _hash(t[field])
    cadence = parse_epoch_int(t["interval_seconds"], low=1, high=60)
    ttl = parse_epoch_int(t["ttl_seconds"], low=cadence+1, high=3600)
    parse_epoch_int(t["max_lag_seconds"], low=0, high=cadence-1)
    parse_epoch_int(t["horizon_seconds"], low=max(60,ttl), high=2592000)
    parse_epoch_int(t["hurdle_bps"], high=9999)
    require(all(_num(t[f]) < RATE for f in ("fee_bps","slippage_bps","momentum_bps","max_spread_bps"))
            and _num(t["momentum_bps"]) > 0 and _num(t["notional_krw"]) > 0
            and Fraction(1,2) < _num(t["confidence"]) <= 1, "CANDIDATE_COST_OR_THRESHOLD")


def _book(row, scope):
    obs = row["observation"]
    at = parse_epoch_int(row["as_of"])
    bid, ask = _num(obs["bid"]), _num(row["ask"])
    require(row["kind"] == "quote" and obs["scope"] == scope and obs["as_of"] == at
            and 0 < bid < ask, "QUOTE_BINDING")
    flags = (obs["prior_block_active"], obs["daily_stop"], obs["floor_halt"], row["status_stale"])
    require(all(type(v) is bool for v in (*flags, row["same_second"]))
            and type(row["stripped_causes"]) is list, "QUOTE_STATE_UNKNOWN")
    clear = row["same_second"] and obs["bid_at"] == at and not any(flags) and not row["stripped_causes"]
    return at, bid, ask, clear


def check_quote(t, quote_row, support):
    """Normalized quote for the paired evaluator; authenticating the support uses the witness receipt."""
    q = quote_row["data"]
    at, bid, ask, clear = _book(q, t["scope"])
    obs = q["observation"]
    normalized = dict(market=t["market"], scope=t["scope"], at=at, bid_at=obs["bid_at"],
                      bid=obs["bid"], ask=q["ask"], same_second=q["same_second"],
                      last_trade=obs["last_trade"], last_trade_at=obs["last_trade_at"])
    if support is None:
        return dict(normalized, blocked=True), False
    require(type(support) is dict and set(support) == {"quote_sha256","market","at","book","status"}
            and support["quote_sha256"] == _hash(quote_row["sha256"]) and support["at"] == at
            and support["market"] == t["market"], "QUOTE_SUPPORT_BINDING")
    book, risk = support["book"], support["status"]
    require(type(book) is dict and book["market"] == t["market"] and type(book["timestamp"]) is int
            and book["timestamp"]//1000 == at and type(book["orderbook_units"]) is list
            and 0 < len(book["orderbook_units"]) <= 100, "BOOK_OR_TIMESTAMP_MISSING")
    top = book["orderbook_units"][0]
    require(_num(top["bid_price"]) == bid and _num(top["ask_price"]) == ask, "BOOK_TOP_CHANGED")
    require(type(risk) is dict and set(risk) == {"scope","at","floor_halt","daily_stop","block_causes","complete"}
            and risk["scope"] == t["scope"] and risk["at"] == at
            and all(type(risk[f]) is bool for f in ("floor_halt","daily_stop","complete"))
            and type(risk["block_causes"]) is list and all(type(c) is str for c in risk["block_causes"]),
            "RISK_STATUS_UNKNOWN")
    adequate = (min(ask*_num(top["ask_size"]), bid*_num(top["bid_size"])) >= _num(t["notional_krw"])
                and (ask-bid)*RATE <= bid*_num(t["max_spread_bps"]))
    available = risk["complete"] and not q["status_stale"] and q["same_second"] and obs["bid_at"] == at
    blocked = not (available and clear and adequate) or risk["daily_stop"] or risk["floor_halt"] or bool(risk["block_causes"])
    return dict(normalized, blocked=blocked), available


def propose(terms, *, terms_sha, previous, current, support, study_head, event_row, snapshots, issued_at):
    """Issue from a verified archive prefix and the newest already-available Stage 2 program record."""
    validate_terms(terms, terms_sha)
    prior_at, _, prev_ask, prev_clear = _book(previous["data"], terms["scope"])
    book, available = check_quote(terms, current, support)
    at = book["at"]
    require(prior_at < at and terms["start"] <= at <= parse_epoch_int(issued_at) < terms["end"]
            and issued_at-at <= terms["max_lag_seconds"], "QUOTE_NOT_CURRENT")
    event = event_row["data"]
    require(event["kind"] == "stage2_forecast" and parse_epoch_int(event["at"]) < at
            and set(snapshots) == {"M","B1"}, "STAGE2_PROSPECTIVE_RECEIPT_REQUIRED")
    # Earlier ask vs current bid includes the spread. Per-leg costs compound.
    buy_cost = (1+_num(terms["fee_bps"])/RATE)*(1+_num(terms["slippage_bps"])/RATE)
    sell_net = (1-_num(terms["fee_bps"])/RATE)*(1-_num(terms["slippage_bps"])/RATE)
    trigger = (not book["blocked"] and prev_clear and at-prior_at == terms["interval_seconds"]
               and _num(book["bid"])*sell_net >= prev_ask*buy_cost*(1+_num(terms["momentum_bps"])/RATE))
    signals = []
    for arm in ARMS:
        expires = min(at+terms["ttl_seconds"], terms["end"])
        p_up = None
        yes = trigger
        observed = (available and at-prior_at == terms["interval_seconds"] and previous["data"]["same_second"]
                    and previous["data"]["observation"]["bid_at"] == prior_at)
        if arm != "q-price":
            role = arm[2:]
            snap = forecasts.check_snapshot(snapshots[role])
            require(sha256_ascii(snap) == event["models"][role]["forecast"]
                    and snap["model"]["sha256"] == terms["models"][role] and len(snap["forecasts"]) <= 1
                    and snap["model"]["training_cutoff"] <= snap["model"]["frozen_at"] <= terms["registered_at"]
                    and snap["generated_at"] <= event["at"], "FORECAST_BINDING")
            if not snap["forecasts"]:
                observed = False  # The frozen writer omits incomplete feature rows and rounded ties.
            else:
                f = snap["forecasts"][0]
                require(f["market"] == terms["market"] and f["hurdle_bps"] == terms["hurdle_bps"]
                        and f["horizon_seconds"] == terms["horizon_seconds"]
                        and event["first_as_of"] == event["last_as_of"] == f["as_of"]
                        and snap["model"]["frozen_at"] < f["as_of"]
                        and f["issued_at"] <= snap["generated_at"], "FORECAST_NOT_POINT_IN_TIME")
                model_expiry = f["as_of"] + f["horizon_seconds"]
                if issued_at < model_expiry:
                    expires = min(expires, model_expiry)
                else:
                    observed = False
                p_up = f["probabilities"]["up"]
                yes = yes and f["direction"] == "up" and _num(p_up) >= _num(terms["confidence"])
        require(issued_at < expires, "FORECAST_OR_COHORT_EXPIRED")
        signals.append(dict(arm=arm, market=terms["market"], model_sha256=sha256_ascii([RULE,terms_sha,arm]),
                            as_of=at, issued_at=issued_at, expires_at=expires, direction=("up" if yes else "neutral") if observed else "unavailable",
                            p_up=p_up if observed else None))
    return dict(**RESEARCH_FLAGS, format=RULE, terms_sha256=terms_sha, market=terms["market"], scope=terms["scope"],
                previous_quote=_hash(previous["sha256"]), quote=_hash(current["sha256"]), support=sha256_ascii(support),
                study_head=_hash(study_head), forecast_event=_hash(event_row["sha256"]), eligible_quote=book, quote_corroborated=available, signals=signals)


def confirm(t, proposal, receipt, *, now):
    """Independent research program attests the exact proposal, evidence, rights and receipt time."""
    require(type(receipt) is dict and set(receipt) == {"body","signature"}, "WITNESS_RECEIPT_REQUIRED")
    b = receipt["body"]
    require(type(b) is dict and set(b) == {"format","proposal_sha256","program_sha256","received_at"}
            and b["format"] == "tradegen-upside-independent-receipt-v1"
            and b["proposal_sha256"] == sha256_ascii(proposal) and b["program_sha256"] == t["witness_program_sha256"],
            "WITNESS_RECEIPT_BINDING")
    require(type(receipt["signature"]) is str and re.fullmatch("[a-f0-9]{128}", receipt["signature"]), "WITNESS_SIGNATURE")
    try:
        key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(t["witness_public_key"]))
        key.verify(bytes.fromhex(receipt["signature"]), canonical_ascii_bytes(b))
    except (InvalidSignature, ValueError):
        raise StudyError("WITNESS_SIGNATURE") from None
    received = parse_epoch_int(b["received_at"])
    require(received <= parse_epoch_int(now) and all(s["issued_at"] <= received < s["expires_at"]
            for s in proposal["signals"]), "WITNESS_RECEIPT_EXPIRED_OR_FUTURE")
    return dict(format="tradegen-upside-signals-v1", market=t["market"], scope=t["scope"],
                signals=[dict(s,received_at=received) for s in proposal["signals"]],
                eligible_quotes=[proposal["eligible_quote"]] if proposal["quote_corroborated"] else [])


def _through(rows, head):
    for i, row in enumerate(rows):
        if row["sha256"] == head:
            return rows[:i+1]
    raise StudyError("ARCHIVE_HEAD_MISMATCH")


def archived_inputs(t, quote_dir, quote_head, study_dir, study_head, *, latest=False):
    from tools.research import direction_forecast_writer as writer, prospective_direction_study as study
    from tools.research.upbit_quote_recorder import QUOTE_RECORDER_SCHEMA

    study_dir = study.private_dir(study_dir)
    study.status(study_dir, _hash(study_head))
    evidence, current_study = read_verified_chained_log(study_dir, study.JOURNAL, pinned_head=study_head)
    within = _through(evidence, study_head)
    quotes, current_quotes = read_verified_chained_log(study.private_dir(quote_dir), "quotes.jsonl", pinned_head=_hash(quote_head))
    require(not latest or (current_study == study_head and current_quotes == quote_head), "ISSUANCE_REQUIRES_LATEST_HEADS")
    qs = _through(quotes, quote_head)
    require(len(qs) >= 3 and qs[0]["data"]["kind"] == "config" and qs[0]["data"]["schema"] == QUOTE_RECORDER_SCHEMA
            and all(q["data"]["kind"] == "quote" for q in qs[-2:]), "TWO_CONTIGUOUS_QUOTES_REQUIRED")
    config = qs[0]["data"]["config"]
    require((config["market"],config["scope"],config["interval_seconds"])
            == (t["market"],t["scope"],t["interval_seconds"]), "QUOTE_SCOPE_OR_CADENCE")
    at = qs[-1]["data"]["as_of"]
    require(within and within[0]["data"]["kind"] == "registered"
            and all(parse_epoch_int(row["data"]["at"]) < at for row in within), "STUDY_RECEIPT_NOT_PRIOR")
    phase = [row for row in within if row["data"]["kind"] == "stage2_forecast"]
    finals = [row for row in within if row["data"]["kind"] == "final"]
    require(phase and len(finals) == 1 and finals[0]["data"]["outcome"] == "PASS"
            and finals[0]["seq"] < phase[-1]["seq"]
            and not any(r["data"]["kind"] == "stage2_review" for r in within), "STAGE2_PROSPECTIVE_RECEIPT_REQUIRED")
    reg = study.load(study_dir, within[0]["data"]["terms"])
    require(reg["forecast_model"]["sha256"] == t["models"]["M"]
            and reg["b1_forecast_model"]["sha256"] == t["models"]["B1"], "UPSTREAM_MODEL_PINS_CHANGED")
    require((reg["market"], reg["scope"], reg["horizon_seconds"], reg["hurdle_bps"])
            == (t["market"],t["scope"],t["horizon_seconds"],t["hurdle_bps"])
            and reg["stage2_start"] <= at < reg["stage2_end"], "STUDY_SCOPE_OR_WINDOW_CHANGED")
    final, event = finals[0]["data"], phase[-1]
    result = study.load(study_dir, final["report"])
    require(result["format"] == "tradegen-direction-stage1-report-v1" and result["mode"] == "final"
            and result["outcome"] == "PASS" and result["market"] == t["market"]
            and "up" in result["passing_directions"]
            and result["gate_evidence"]["study_sha256"] == within[0]["data"]["terms"]
            and result["gate_evidence"]["evaluated_at"] == final["at"]
            and final["at"] < reg["stage2_start"] <= final["at"] + 14*86400, "POSITIVE_STAGE1_GATE_REQUIRED")
    source = study.load(study_dir,event["data"]["sources"])
    _hash(source["run_log_head"])
    require(source["price_manifests"], "STAGE2_SOURCE_RECEIPTS_REQUIRED")
    feature_table = study.load(study_dir,event["data"]["features"])
    for role in ("M","B1"):
        refs = event["data"]["models"][role]
        manifest = study.load(study_dir,refs["manifest"])
        snap = study.load(study_dir,refs["forecast"])
        model = study.load(study_dir,within[0]["data"]["models"][role])
        names = set(model["feature_names"])
        if role == "M":
            require(names & {"D1","D2","D3"} and (not names & {"D1","D2"} or source["didm_reports"])
                    and ("D3" not in names or source["didm_exports"]), "DIDM_INPUT_REQUIRED")
        rebuilt = writer.build_forecasts_from_model(artifact=model, feature_table=feature_table,
            issued_at=event["data"]["at"], mode="live", expected_model_sha256=t["models"][role],
            start_as_of=event["data"]["first_as_of"], end_as_of=event["data"]["last_as_of"])
        require(model["role"] == role and rebuilt == (snap,manifest), "STAGE2_FORECAST_RECEIPT_MISMATCH")
    return dict(previous=qs[-2], current=qs[-1], study_head=study_head, event_row=event,
                snapshots={r:study.load(study_dir,event["data"]["models"][r]["forecast"]) for r in ("M","B1")})


def main(argv=None):
    from tools.research.prospective_direction_study import private_dir
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("propose","confirm"))
    for key in ("terms","support","quote-dir","study-dir","out"):
        p.add_argument("--"+key, required=True, type=Path)
    for key in ("terms-sha","quote-head","study-head"):
        p.add_argument("--"+key, required=True)
    p.add_argument("--proposal", type=Path)
    p.add_argument("--receipt", type=Path)
    a = p.parse_args(argv)
    def read(path):
        require(path is not None, "PRIVATE_INPUT_REQUIRED")
        private_dir(path.parent)
        return read_strict_json_file(path,max_bytes=16*1024*1024)[0]
    t, support = read(a.terms), read(a.support)
    private_dir(a.out.parent)
    validate_terms(t,a.terms_sha)
    kwargs = archived_inputs(t,a.quote_dir,a.quote_head,a.study_dir,a.study_head,latest=a.action=="propose")
    supplied = read(a.proposal) if a.action == "confirm" else None
    when = supplied["signals"][0]["issued_at"] if supplied else int(time.time())
    proposal = propose(t,terms_sha=a.terms_sha,support=support,issued_at=when,**kwargs)
    if a.action == "confirm":
        require(proposal == supplied, "PROPOSAL_DOES_NOT_REPLAY")
        result = confirm(t,proposal,read(a.receipt),now=int(time.time()))
    else:
        require(int(time.time())-proposal["eligible_quote"]["at"] <= t["max_lag_seconds"], "QUOTE_NOT_CURRENT")
        result = proposal
    atomic_publish_json_ascii(a.out,result)
    print(sha256_ascii(result))


if __name__ == "__main__":
    main()
