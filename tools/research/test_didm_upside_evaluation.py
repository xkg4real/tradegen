"""All prices, forecasts, pins and archives in this module are synthetic."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from tools.research import didm_upside_evaluation as ev
from tools.research._study_common import HashChainedLog, sha256_ascii

M = "1"*64
B1 = "2"*64
MARKET = "KRW-BTC"
SCOPE = "synthetic-study"


def terms(**changes):
    return dict(format="tradegen-upside-terms-v1", market=MARKET, scope=SCOPE, registered_at=800,
                start=1000, end=1120, horizon_seconds=60, max_gap_seconds=10, early_seconds=15,
                move_bps="300", fee_bps="0", slippage_bps="0", fixed_y_bps="200", confidence="0.75",
                models={"M":M, "B1":B1}, binary_arms=[]) | changes


def book(at, ask, **changes):
    return dict(at=at, bid_at=at, last_trade_at=at, same_second=True, blocked=False, market=MARKET,
                scope=SCOPE, bid=str(ask-1), ask=str(ask), last_trade=str(ask)) | changes


def books():
    return [book(1000+10*i, ask) for i,ask in enumerate([102,101,102,107,110,106,100,100,100,100,100,100])]


def signal(arm, a, received, direction="up", **changes):
    return dict(arm=arm, market=MARKET, model_sha256=M if arm=="M" else B1, as_of=a, issued_at=a,
                received_at=received, expires_at=1300, direction=direction,
                p_up="0.8" if direction == "up" else "0.1") | changes


def fixture_signals():
    return [signal("M",970,971), signal("B1",970,971,"neutral"), signal("M",1058,1059,"down")]


def write(path, obj):
    path.write_text(json.dumps(obj), encoding="utf8")
    return sha256_ascii(obj)


def archive(root, name, rows):
    with HashChainedLog(root,name) as chain:
        for row in rows:
            chain.append(row)
        return chain.head_sha256


def seed_archives(root, *, corrupt_manifest=False):
    t = terms()
    qroot = root/"quotes"
    froot = root/"forecasts"
    froot.mkdir()
    def seal(obj):
        h=sha256_ascii(obj)
        write(froot/(h+".json"),obj)
        return h
    qs=[{"kind":"config","schema":"tradegen-upbit-quote-recorder-v1",
         "config":{"scope":SCOPE,"market":MARKET,"interval_seconds":10,"app_running":False}}]
    for i,q in enumerate(books(),1):
        qs.append(dict(kind="quote",as_of=q["at"],app_running=False,status_stale=False,stripped_causes=[],
                       same_second=True,ask=q["ask"],observation=dict(scope=SCOPE,sequence=i,as_of=q["at"],
                       bid_at=q["at"],bid=q["bid"],last_trade=q["last_trade"],last_trade_at=q["at"],
                       prior_block_active=False,floor_halt=False,daily_stop=False)))
    qp=archive(qroot,"quotes.jsonl",qs)
    registered={}
    for role in ("M","B1"):
        names=["P1","D2","Q1"] if role=="M" else ["P1"]
        model={"role":role,"market":MARKET,"feature_names":names,"weights":{"coefficients":[[i]*len(names) for i in range(3)]}}
        model["sha256"]=sha256_ascii(model)
        registered[role]=seal(model)
        t["models"][role]=model["sha256"]
    tp = root/"terms.json"
    terms_pin=write(tp,t)
    study={"market":MARKET,"scope":SCOPE,"stage2_start":900,"stage2_end":1200,"horizon_seconds":300,"hurdle_bps":1,
           "forecast_model":{"sha256":t["models"]["M"]},"b1_forecast_model":{"sha256":t["models"]["B1"]}}
    events=[dict(kind="registered",at=701,terms=seal(study),models=registered),dict(kind="stage1_forecast",at=751),
            dict(kind="final",at=850,outcome="PASS")]
    refs={}
    for role,h in t["models"].items():
        model=dict(name="fixture",version="v1",training_cutoff=600,frozen_at=700,sha256=h)
        f=dict(market=MARKET,as_of=970,issued_at=972,horizon_seconds=300,hurdle_bps=1,
               probabilities={"up":"0.8","down":"0.1","neutral":"0.1"},direction="up")
        snap=dict(format="tradegen-direction-forecast-v1",producer="synthetic",model=model,generated_at=972,
                  forecasts=[f])
        snap["snapshot_sha256"]=sha256_ascii(snap)
        man=dict(format="tradegen-direction-forecast-manifest-v1",**ev.FLAGS,role=role,mode="live",model=model,
                 snapshot_sha256=snap["snapshot_sha256"],generated_at=972,issued_at=972,forecast_count=1)
        if corrupt_manifest:
            man["mode"]="batch"
        man["manifest_sha256"]=sha256_ascii(man)
        refs[role]=dict(forecast=seal(snap),manifest=seal(man))
    events.append(dict(kind="stage2_forecast",at=975,first_as_of=970,last_as_of=970,models=refs))
    fp=archive(froot,"prospective.jsonl",events)
    return ["--quotes",str(qroot),"--quotes-head",qp,"--archive",str(froot),"--forecast-head",fp,
            "--terms",str(tp),"--terms-sha256",terms_pin,"--output",str(root/"report.json")]


class UpsideEvaluationTests(unittest.TestCase):
    def test_common_cohort_recalls_false_entries_fixed_exit_and_anticipation(self):
        r = ev.evaluate(terms(),books(),fixture_signals())
        self.assertEqual(r["status"],"DESCRIPTIVE")
        self.assertEqual((r["windows"][0]["onset_at"],r["windows"][0]["crossed_at"]),(1010,1030))
        self.assertEqual(r["windows"][0]["arms"]["M"]["entry_at"],1010)
        m,b,f = (r["paired_complete_windows"][k] for k in ("M","B1","fixed"))
        self.assertEqual((m["recall"],m["early_captures"],m["false_entries"],m["anticipated_signals"]),
                         ("1.00000000",1,0,1))
        self.assertEqual((b["detected_before_cross"],f["false_entries"],f["windows"]),(0,1,2))
        self.assertIsNone(m["median_post_onset_detected_signal_delay_seconds"])
        self.assertEqual(m["mean_fixed_exit_net_bps_per_entry"],"396.03960396")
        self.assertIsNone(r["actual_realized_pnl"])
        self.assertEqual(r["paired_comparisons"]["M_minus_B1"]["windows"],2)

    def test_same_second_receipt_waits_for_a_distinct_later_quote(self):
        sig = [signal("M",999,1010),signal("B1",960,961)]
        r=ev.evaluate(terms(),books(),sig)
        m=r["windows"][0]["arms"]["M"]
        self.assertEqual((m["signal_at"],m["entry_at"],m["post_onset_signal_at"]),(1010,1020,1010))
        self.assertEqual(r["all_complete_windows"]["M"]["late_entries"],0)
        self.assertEqual(r["all_complete_windows"]["M"]["median_post_onset_detected_signal_delay_seconds"],"0.00000000")
        self.assertEqual(r["coverage_excluded_from_paired"],1)

    def test_future_receipt_never_backfills_and_a_later_expiration_cancels_pending_entry(self):
        s=[signal("M",970,1100),signal("B1",970,971,expires_at=1005)]
        r=ev.evaluate(terms(),books(),s)
        self.assertIsNone(r["windows"][0]["arms"]["M"]["entry_at"])
        self.assertIsNone(r["windows"][0]["arms"]["B1"]["entry_at"])
        self.assertEqual(r["status"],"INSUFFICIENT_PAIRED_COVERAGE")
        self.assertIsNone(r["paired_comparisons"]["M_minus_B1"]["mean_net_bps_per_paired_window"])

    def test_quote_gaps_missing_ask_short_book_and_ties(self):
        q=books()
        for modified in (q[:3]+q[4:], [q[0]|{"same_second":False}]+q[1:],
                         [q[0]|{"ask":None}]+q[1:]):
            r=ev.evaluate(terms(),modified,fixture_signals())
            self.assertEqual(sum(r["excluded_windows"].values()),1)
            self.assertEqual(r["status"],"PARTIAL_COHORT")
        r=ev.evaluate(terms(),q[:2],[])
        self.assertEqual(r["excluded_windows"],{"SHORT_OR_MISSING_EDGE":2})
        with self.assertRaisesRegex(ValueError,"TIED_QUOTES"):
            ev.evaluate(terms(),[q[0],q[0]],[])
        with self.assertRaisesRegex(ValueError,"SCOPE|COHORT"):
            ev.evaluate(terms(),[q[0]|{"market":"KRW-ETH"}],[])
        with self.assertRaisesRegex(ValueError,"QUOTE_TIME"):
            ev.evaluate(terms(),[q[0]|{"bid_at":1001}],[])

    def test_the_first_cross_counts_once_and_fees_spread_can_erase_it(self):
        q=[book(1000+10*i,ask) for i,ask in enumerate([100,100,107,99,109,102])]
        kwargs={"end":1060,"models":{}}
        r=ev.evaluate(terms(**kwargs),q,[])
        self.assertEqual((r["windows"][0]["onset_at"],r["windows"][0]["crossed_at"]),(1000,1020))
        self.assertEqual(r["all_complete_windows"]["fixed"]["surge_events"],1)
        costly=ev.evaluate(terms(**kwargs,fee_bps="400",slippage_bps="100"),q,[])
        self.assertIsNone(costly["windows"][0]["crossed_at"])
        self.assertLess(float(costly["all_complete_windows"]["fixed"]["mean_fixed_exit_net_bps_per_entry"]),0)

    def test_gate_is_checked_at_signal_and_execution_and_max_y_is_enforced(self):
        q=books()
        q[1] = q[1]|{"last_trade_at":900,"last_trade":"200"}
        q[2] = q[2]|{"blocked":True}
        r=ev.evaluate(terms(),q,fixture_signals())
        self.assertEqual(r["windows"][0]["arms"]["fixed"]["entry_at"],1040)
        with self.assertRaisesRegex(ValueError,"INVALID_GATE"):
            ev.evaluate(terms(fixed_y_bps="501"),q,[])
        with self.assertRaisesRegex(ValueError,"UNREGISTERED"):
            ev.evaluate(terms(registered_at=1000),q,[])

    def test_unavailable_is_distinct_from_neutral_and_binary_arm_uses_no_probability(self):
        t=terms(models={"q-fixed":M},binary_arms=["q-fixed"])
        s=signal("q-fixed",970,971,model_sha256=M,p_up=None)
        r=ev.evaluate(t,books(),[s,s|{"as_of":1057,"issued_at":1057,"received_at":1058,"direction":"unavailable"}])
        self.assertEqual(r["paired_complete_windows"]["q-fixed"]["windows"],1)
        with self.assertRaisesRegex(ValueError,"BINARY_SIGNAL_INVALID"):
            ev.evaluate(t,books(),[s|{"p_up":"1"}])
        with self.assertRaisesRegex(ValueError,"REVISED_OR_BACKDATED_SIGNAL"):
            ev.evaluate(t,books(),[s,s])

    def test_pinned_original_quote_and_live_forecast_archives_enter_through_normal_cli(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root=Path(directory)
            argv=seed_archives(root)
            self.assertEqual(ev.main(argv),0)
            r=json.loads((root/"report.json").read_text())
            self.assertEqual(r["paired_complete_windows"]["M"]["windows"],2)
            self.assertFalse(r["execution_ready"])
            self.assertEqual(r["attribution"],"COMBINED_FEATURE_CONTRAST")
            self.assertEqual(ev.main(argv),2)  # immutable output
            bad=list(argv)
            bad[bad.index("--quotes-head")+1]="0"*64
            self.assertEqual(ev.main(bad),2)

    def test_new_quote_intent_arriving_between_books_does_not_wait_an_extra_tick(self):
        t=terms(models={"q-M":M})
        f=signal("q-M",1010,1011,model_sha256=M)
        r=ev.evaluate(t,books(),[f])
        self.assertEqual(r["windows"][0]["arms"]["q-M"]["signal_at"],1011)
        self.assertEqual(r["windows"][0]["arms"]["q-M"]["entry_at"],1020)
        late=ev.evaluate(t,books(),[f|{"received_at":1020}])
        self.assertEqual(late["windows"][0]["arms"]["q-M"]["entry_at"],1030)
        self.assertEqual(late["all_complete_windows"]["q-M"]["late_entries"],1)

    def test_authenticated_corroboration_is_common_and_mandatory_at_exit(self):
        t=terms(quote_gate="corroborated")
        self.assertEqual(ev.evaluate(t,books(),[])["excluded_windows"],{"UNAVAILABLE_BOOK":2})
        q=[row|{"corroborated":True} for row in books()]
        q[5]["blocked"]=True
        r=ev.evaluate(t,q,fixture_signals())
        self.assertEqual(r["excluded_windows"],{"EXIT_STATUS_OR_SIZE_UNUSABLE":1})
        self.assertEqual(r["paired_complete_windows"]["fixed"]["fixed_unit_notional_close_to_close_drawdown_bps"],
                         "100.00000000")

    def test_attribution_requires_effective_didm_features_and_excludes_q1_even_when_declared_inactive(self):
        features={"B1":{"declared":["P1"],"class_differentiating_weights":["P1"]},
                  "M":{"declared":["P1","D1","D2"],"class_differentiating_weights":["P1"]}}
        self.assertEqual(ev.attribution(features),"NO_EFFECTIVE_INCREMENTAL_DIDM_FEATURE")
        features["M"]["class_differentiating_weights"].append("D1")
        self.assertEqual(ev.attribution(features),"DIDM_ONLY_FEATURE_CONTRAST_DESCRIPTIVE")
        features["M"]["declared"].append("Q1")
        self.assertEqual(ev.attribution(features),"COMBINED_FEATURE_CONTRAST")

    def test_supplemental_confirmed_envelopes_support_all_arms_and_cannot_substitute_prices(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root=Path(directory)
            argv=seed_archives(root)
            tp=root/"terms.json"
            t=json.loads(tp.read_text())
            t["models"]["q-fixed"]="3"*64
            t.update(binary_arms=["q-fixed"],quote_gate="corroborated")
            argv[argv.index("--terms-sha256")+1]=write(tp,t)
            files=[]
            for i, part in enumerate((books()[:6],books()[6:])):
                path=root/f"extra{i}.json"
                at=part[0]["at"]
                updates=[signal("q-fixed",at,at+1,model_sha256="3"*64,p_up=None)]
                doc={"format":"tradegen-upside-signals-v1","market":MARKET,"scope":SCOPE,
                     "signals":updates,"eligible_quotes":part}
                argv.extend(["--supplemental-signals",str(path),"--supplemental-sha256",write(path,doc)])
                files.append((path,doc))
            self.assertEqual(ev.main(argv),0)
            r=json.loads((root/"report.json").read_text())
            self.assertEqual(r["all_complete_windows"]["q-fixed"]["windows"],2)
            path,doc=files[-1]
            doc["eligible_quotes"][0]["ask"]="123"
            argv[-1]=write(path,doc)
            argv[argv.index("--output")+1]=str(root/"changed.json")
            self.assertEqual(ev.main(argv),2)
            self.assertFalse((root/"changed.json").exists())

    def test_batch_manifest_cannot_be_promoted_to_live(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root=Path(directory)
            self.assertEqual(ev.main(seed_archives(root,corrupt_manifest=True)),2)
            self.assertFalse((root/"report.json").exists())


if __name__ == "__main__":
    unittest.main()
