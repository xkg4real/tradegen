"""Synthetic quote-cadence evidence. The Ed25519 key exists only in memory per test."""
from copy import deepcopy
from pathlib import Path
from unittest import TestCase
from tempfile import TemporaryDirectory

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from tools.research import didm_upside_candidate as c
from tools.research import direction_forecast_adapter as fa
from tools.research._study_common import HashChainedLog, atomic_publish_json_ascii, canonical_ascii_bytes, sha256_ascii


class QuoteCandidate(TestCase):
    def setUp(self):
        self.key = Ed25519PrivateKey.generate()
        self.t = dict(rule=c.RULE,market="KRW-BTC",scope="spot",registered_at=290,start=300,end=9000,
                      interval_seconds=10,ttl_seconds=25,max_lag_seconds=3,fee_bps="1",slippage_bps="1",
                      momentum_bps="10",max_spread_bps="20",notional_krw="200",horizon_seconds=3600,
                      hurdle_bps=30,confidence="0.75",models={"M":"a"*64,"B1":"b"*64},
                      witness_public_key=self.key.public_key().public_bytes_raw().hex(),witness_program_sha256="e"*64)
        self.q0 = self.q(1000,9990,10000)
        self.q1 = self.q(1010,10050,10051)
        self.support = dict(quote_sha256=self.q1["sha256"],market="KRW-BTC",at=1010,
                    book=dict(market="KRW-BTC",timestamp=1010212,orderbook_units=[dict(
                        bid_price="10050",ask_price="10051",bid_size="20",ask_size="20")]),
                    status=dict(scope="spot",at=1010,floor_halt=False,daily_stop=False,block_causes=[],complete=True))
        self.snaps = {}
        for role,p in (("M","0.80"),("B1","0.65")):
            f = dict(market=self.t["market"],as_of=500,issued_at=515,horizon_seconds=3600,hurdle_bps=30,
                     probabilities={"up":p,"down":"0.1","neutral":"0.1" if role=="M" else "0.25"},direction="up")
            s = dict(format=fa.FORMAT,producer="test",model=dict(name=role,version="1",sha256=self.t["models"][role],
                     training_cutoff=100,frozen_at=200),generated_at=515,forecasts=[f])
            self.snaps[role] = s | {"snapshot_sha256":fa.preview.model_id(s)}
        e = dict(kind="stage2_forecast",at=515,first_as_of=500,last_as_of=500,
                 models={r:{"forecast":sha256_ascii(s)} for r,s in self.snaps.items()})
        self.event = dict(data=e,sha256=sha256_ascii(e))

    def q(self,at,bid,ask):
        obs = dict(scope="spot",as_of=at,bid_at=at,bid=str(bid),last_trade_at=at,last_trade=str(bid),
                   prior_block_active=False,daily_stop=False,floor_halt=False)
        d = dict(kind="quote",as_of=at,same_second=True,status_stale=False,stripped_causes=[],ask=str(ask),observation=obs)
        return dict(data=d,sha256=sha256_ascii(d))

    def proposed(self, **overrides):
        args = dict(terms_sha=sha256_ascii(self.t),previous=self.q0,current=self.q1,support=self.support,
                    study_head="1"*64,event_row=self.event,snapshots=self.snaps,issued_at=1011)
        return c.propose(self.t,**(args|overrides))

    def receipt(self,proposal,received=1012):
        b = dict(format="tradegen-upside-independent-receipt-v1",program_sha256=self.t["witness_program_sha256"],
                 proposal_sha256=sha256_ascii(proposal),received_at=received)
        return {"body":b,"signature":self.key.sign(canonical_ascii_bytes(b)).hex()}

    def test_quote_updates_before_next_hour_and_has_distinct_fixed_and_model_arms(self):
        p = self.proposed()
        envelope = c.confirm(self.t,p,self.receipt(p),now=1013)
        signals = envelope["signals"]
        self.assertEqual(envelope["eligible_quotes"], [p["eligible_quote"]])
        self.assertEqual([(s["arm"],s["direction"],s["p_up"]) for s in signals],
                         [("q-M","up","0.80"),("q-B1","neutral","0.65"),("q-price","up",None)])
        self.assertTrue(all(s["received_at"]==1012 and s["issued_at"]==1011 and s["as_of"]==1010 for s in signals))
        self.assertFalse(p["eligible_quote"]["blocked"])
        self.assertFalse(p["live_eligible"])

    def test_missing_or_stale_data_censors_depth_and_holds_cancel_with_no_entry(self):
        omitted = self.proposed(support=None)
        self.assertTrue(omitted["eligible_quote"]["blocked"])
        self.assertEqual(c.confirm(self.t,omitted,self.receipt(omitted),now=1014)["eligible_quotes"],[])
        self.assertTrue(all(s["direction"]=="unavailable" and s["p_up"] is None for s in omitted["signals"]))
        for change in ({"floor_halt":True},{"daily_stop":True},{"block_causes":["PATH_EVIDENCE_ENTRY_BLOCK"]}):
            s = deepcopy(self.support)
            s["status"].update(change)
            self.assertTrue(all(f["direction"]=="neutral" for f in self.proposed(support=s)["signals"]))
        s = deepcopy(self.support)
        s["book"]["orderbook_units"][0]["ask_size"]="0.00001"
        self.assertTrue(self.proposed(support=s)["eligible_quote"]["blocked"])
        self.q1["data"]["same_second"] = False
        self.assertTrue(all(s["direction"]=="unavailable" for s in self.proposed()["signals"]))

    def test_costs_or_absent_contiguous_previous_quote_prevent_research_entry(self):
        self.t["fee_bps"]="40"
        self.assertTrue(all(s["direction"]=="neutral" for s in self.proposed()["signals"]))
        self.q0 = self.q(990,9990,10000)
        self.assertTrue(all(s["direction"]=="unavailable" for s in self.proposed()["signals"]))

    def test_future_and_expired_evidence_never_signal(self):
        with self.assertRaisesRegex(ValueError,"QUOTE_NOT_CURRENT"):
            self.proposed(issued_at=1017)
        self.event["data"]["at"]=1011
        with self.assertRaisesRegex(ValueError,"STAGE2_PROSPECTIVE_RECEIPT_REQUIRED"):
            self.proposed()
        self.event["data"]["at"]=515
        self.t["horizon_seconds"]=480
        for r,s in self.snaps.items():
            f = s["forecasts"][0]; f["horizon_seconds"]=480
            s["snapshot_sha256"] = fa.preview.model_id({k:v for k,v in s.items() if k!="snapshot_sha256"})
            self.event["data"]["models"][r]["forecast"]=sha256_ascii(s)
        rejected = self.proposed()["signals"]
        self.assertEqual([s["direction"] for s in rejected[:2]],["unavailable","unavailable"])

    def test_omitted_frozen_model_row_is_unavailable_while_comparators_keep_real_values(self):
        snap=self.snaps["M"]
        snap["forecasts"]=[]
        snap["snapshot_sha256"]=fa.preview.model_id({k:v for k,v in snap.items() if k!="snapshot_sha256"})
        self.event["data"]["models"]["M"]["forecast"]=sha256_ascii(snap)
        m,b,price=self.proposed()["signals"]
        self.assertEqual((m["direction"],m["p_up"]),("unavailable",None))
        self.assertEqual((b["p_up"],price["direction"]),("0.65","up"))

    def test_independent_receipt_rejects_substitution_wrong_program_forgery_and_late_response(self):
        p = self.proposed(); r=self.receipt(p)
        p["signals"][0]["direction"]="neutral"
        with self.assertRaisesRegex(ValueError,"WITNESS_RECEIPT_BINDING"):
            c.confirm(self.t,p,r,now=1014)
        p=self.proposed(); r=self.receipt(p)
        r["signature"]="0"*128
        with self.assertRaisesRegex(ValueError,"WITNESS_SIGNATURE"):
            c.confirm(self.t,p,r,now=1014)
        for received,now in ((1010,1014),(1015,1014),(1035,1040)):
            with self.assertRaisesRegex(ValueError,"WITNESS_RECEIPT_EXPIRED_OR_FUTURE"):
                c.confirm(self.t,p,self.receipt(p,received),now=now)

    def test_exact_frozen_heads_replay_actual_archive_storage_and_exclude_later_quote(self):
        from tools.research import direction_forecast_writer as writer, direction_model_fit as fit
        from tools.research import prospective_direction_study as workflow
        from tools.research.test_direction_model_fit import _make_synthetic_dataset

        bars, features = _make_synthetic_dataset(320)
        frozen = bars[180]["end"]+60
        models = fit.fit_and_freeze_models(feature_table=features,bars=bars,train_start=bars[30]["end"],
            train_end=bars[180]["end"],frozen_at=frozen,horizon_seconds=7200,hurdle_bps=15)
        as_of = bars[280]["end"]
        self.t.update(registered_at=frozen+1,start=frozen+2,end=as_of+7200,horizon_seconds=7200,hurdle_bps=15,
                      models={r:models[r]["sha256"] for r in ("M","B1")},market=models["M"]["market"])
        q_at = as_of+20
        self.q0,self.q1=self.q(q_at-10,9990,10000),self.q(q_at,10050,10051)
        self.support.update(at=q_at,market=self.t["market"])
        self.support["book"].update(timestamp=q_at*1000,market=self.t["market"])
        self.support["status"]["at"]=q_at
        with TemporaryDirectory() as td:
            root = Path(td)
            study, quotes = root/"study",root/"quotes"
            study.mkdir(); quotes.mkdir()
            terms = dict(market=self.t["market"], scope=self.t["scope"], horizon_seconds=7200,hurdle_bps=15,
                         stage2_start=as_of,stage2_end=as_of+7200,
                         forecast_model={"sha256":self.t["models"]["M"]},b1_forecast_model={"sha256":self.t["models"]["B1"]})
            def blob(value):
                digest = sha256_ascii(value); atomic_publish_json_ascii(study/(digest+".json"),value); return digest
            with HashChainedLog(study,workflow.JOURNAL) as log:
                log.append(dict(kind="registered",at=frozen+1,terms=blob(terms),models={r:blob(models[r]) for r in ("M","B1")}))
                result=dict(format="tradegen-direction-stage1-report-v1",mode="final",outcome="PASS",
                            market=self.t["market"],passing_directions=["up"],
                            gate_evidence=dict(study_sha256=sha256_ascii(terms),evaluated_at=as_of-1))
                log.append(dict(kind="final",outcome="PASS",at=as_of-1,report=blob(result)))
                record = dict(kind="stage2_forecast", at=as_of+1, first_as_of=as_of, last_as_of=as_of, models={},
                    sources=blob(dict(run_log_head="2"*64, price_manifests=[{"test":True}],didm_reports=["4"*64])),
                    features=blob(features))
                for r in ("M","B1"):
                    snap,report=writer.build_forecasts_from_model(artifact=models[r],feature_table=features,
                        issued_at=as_of+1,mode="live",start_as_of=as_of,end_as_of=as_of)
                    record["models"][r]={"forecast":blob(snap),"manifest":blob(report)}
                event=log.append(record)
            with HashChainedLog(quotes,"quotes.jsonl") as log:
                log.append(dict(kind="config",schema="tradegen-upbit-quote-recorder-v1",
                                config=dict(market=self.t["market"],scope="spot",interval_seconds=10)))
                log.append(self.q0["data"]); current=log.append(self.q1["data"])
                log.append(self.q(q_at+10,10053,10055)["data"])
            args=c.archived_inputs(self.t,quotes,current["sha256"],study,event["sha256"])
            self.assertEqual(args["current"],current)
            with self.assertRaisesRegex(ValueError, "ISSUANCE_REQUIRES_LATEST_HEADS"):
                c.archived_inputs(self.t,quotes,current["sha256"],study,event["sha256"],latest=True)
            self.support["quote_sha256"]=current["sha256"]
            p=c.propose(self.t,terms_sha=sha256_ascii(self.t),support=self.support,issued_at=q_at+1,**args)
            self.assertEqual(p["quote"],current["sha256"])

    def test_receipted_quote_signal_uses_first_distinct_supported_ask_in_paired_evaluator(self):
        from tools.research import didm_upside_evaluation as evaluate

        p = self.proposed()
        envelope = c.confirm(self.t,p,self.receipt(p),now=1013)
        primed = dict(format="tradegen-upside-terms-v1",market=self.t["market"],scope=self.t["scope"],
                      registered_at=290,start=1000,end=1060,horizon_seconds=60,max_gap_seconds=10,
                      early_seconds=10,move_bps="30",fee_bps="1",slippage_bps="1",fixed_y_bps="200",confidence="0.75",
                      models={s["arm"]:s["model_sha256"] for s in envelope["signals"]},binary_arms=["q-price"],
                      quote_gate="corroborated")
        def confirmed_book(at):
            q = self.q(at,10051,10052)
            supporting = deepcopy(self.support)
            supporting.update(quote_sha256=q["sha256"],at=at)
            supporting["book"].update(timestamp=at*1000)
            supporting["book"]["orderbook_units"][0].update(bid_price="10051",ask_price="10052")
            supporting["status"]["at"]=at
            proposal=self.proposed(previous=self.q(at-10,10051,10052),current=q,support=supporting,issued_at=at+1)
            verified=c.confirm(self.t,proposal,self.receipt(proposal,at+2),now=at+2)
            return verified["eligible_quotes"][0]
        # The evaluator CLI sets this bit only after its raw-book comparison and
        # receipt-backed overlay match. The pure kernel receives that projection.
        quotes = [dict(confirmed_book(i) if i!=1010 else envelope["eligible_quotes"][0],corroborated=True)
                  for i in range(1000,1060,10)]
        verdict = evaluate.evaluate(primed,quotes,envelope["signals"])
        arm=verdict["windows"][0]["arms"]["q-M"]
        self.assertEqual((arm["signal_at"],arm["entry_at"]),(1012,1020))
        self.assertIsNone(verdict["actual_realized_pnl"])
