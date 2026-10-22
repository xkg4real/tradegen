"""r2_idx_01_protective.py -- Task 1: index trend and vol rules judged as PROTECTIVE cards (spec 8.7) and as
OUTPERFORMANCE cards (gate step 5), the overlay-vs-sleeve question, the 2026 KOSPI windows and E3's claims.

Declared before the run (header = pre-registration; nothing below was searched):
  Markets   KOSPI rebuilt (price), 1996-09-02..2026-09-29, KRX ETF 3 bp per side (2x = 6 bp).
            SPY (unadjusted closes, price), 1999-05-03..2021-03-31, US shares via KIS 50 bp (2x = 100 bp);
            futures 5 bp (2x = 10 bp) reported as a second instrument book.
            (Common window per market = first session at which every centre AND neighbour rule is defined:
            the 15-month and 315-session neighbours need 15 months of history.)
  Rules     (signal at the close of t, position from t+1, cash 0%)
            SMA200   long/flat close > SMA200; binary; onset gap 200 sessions.
                     neighbours: window {150, 200, 250} x band {0%, 1%} (5 cells).
            ENS      E3's multi-speed vote: share of positive 20/60/120/250-session returns (0, 1/4, .., 1).
                     neighbours: set {20/60, 20/60/120/250, 60/120/250} x lookback scale {0.75, 1, 1.25} (8).
                     variant: long/flat when >= 2 of 4 votes are positive (reported, not the centre).
            TSM12    12-month sign of the month-end close, decided at the month-end close, held for the month;
                     binary; onset gap 252 sessions. neighbours: {9, 15} months monthly, {189, 252, 315}-session
                     daily sign (5).
            VT       SMA20 realised vol, cap 1: KOSPI 20% target, SPY 15%.
                     neighbours: window {10, 20, 40} x target {-0.05, 0, +0.05} (8).
            ENSxVT   ENS x VT. neighbours: ENS scale {0.75, 1, 1.25} x VT target {-0.05, 0, +0.05} (8).
            Reference: EWMA(0.94) vol target (spec benchmark 4), same target.
  Episodes  spec 8.6 drawdown episodes covered by the sample (+ 1997-98 and 2000-01 KOSPI peak-to-trough:
            1997 high close -> following low through 1998; 2000 high close -> following low through 2001).
            KOSPI excludes Sep-2026 (a US rates episode; KOSPI +0.7% in that window; R4b also omitted it).
  Overlay   trend as an overlay on buy-and-hold, floored at 0.5: clip(trend, 0.5, 1) (spec P2 literal) and
            0.5 + 0.5 x trend (E3's long/half); with VT the overlay multiplies the VT weight (spec 3.3).
"""
import numpy as np
import pandas as pd

import r2_idx_common as C

ENS = dict(kind='ens', lbs=(20, 60, 120, 250), scale=1.0, map='share')


def rule_set(target):
    vt = dict(kind='vt', window=20, target=target)
    sets = {}
    sets['SMA200'] = dict(spec=dict(kind='sma', n=200, band=0.0), gap=200,
                          nbs=[dict(kind='sma', n=n, band=b) for b in (0.0, 0.01) for n in (150, 200, 250)
                               if not (n == 200 and b == 0.0)])
    sets['ENS'] = dict(spec=ENS, gap=None,
                       nbs=[dict(kind='ens', lbs=lbs, scale=sc, map='share')
                            for lbs in ((20, 60), (20, 60, 120, 250), (60, 120, 250)) for sc in (0.75, 1.0, 1.25)
                            if not (lbs == (20, 60, 120, 250) and sc == 1.0)])
    sets['TSM12'] = dict(spec=dict(kind='tsm_m', months=12), gap=252,
                         nbs=[dict(kind='tsm_m', months=9), dict(kind='tsm_m', months=15),
                              dict(kind='tsm_d', days=189), dict(kind='tsm_d', days=252), dict(kind='tsm_d', days=315)])
    sets['VT'] = dict(spec=vt, gap=None,
                      nbs=[dict(kind='vt', window=w, target=round(target + dt, 2)) for w in (10, 20, 40)
                           for dt in (-0.05, 0.0, 0.05) if not (w == 20 and dt == 0.0)])
    sets['ENSxVT'] = dict(spec=dict(kind='prod', a=ENS, b=vt), gap=None,
                          nbs=[dict(kind='prod', a=dict(kind='ens', lbs=(20, 60, 120, 250), scale=sc, map='share'),
                                    b=dict(kind='vt', window=20, target=round(target + dt, 2)))
                               for sc in (0.75, 1.0, 1.25) for dt in (-0.05, 0.0, 0.05) if not (sc == 1.0 and dt == 0.0)])
    variants = {
        'ENS >=2/4 binary': dict(spec=dict(kind='ens', lbs=(20, 60, 120, 250), scale=1.0, map='binary2'), gap=250),
        'EWMA(0.94) VT': dict(spec=dict(kind='ewma_vt', lam=0.94, target=target), gap=None),
    }
    return sets, variants


def overlay_specs(target):
    vt = dict(kind='vt', window=20, target=target)
    out = {}
    for nm, base, gap in (('ENS', ENS, None), ('SMA200', dict(kind='sma', n=200, band=0.0), 200),
                          ('TSM12', dict(kind='tsm_m', months=12), 252)):
        out[nm] = {'sleeve (0 allowed)': (base, gap),
                   'overlay clip[0.5,1]': (dict(kind='ovl', base=base, how='clip'), None),
                   'overlay 0.5+0.5x (E3 long/half)': (dict(kind='ovl', base=base, how='lin'), None)}
    out['ENSxVT'] = {'sleeve (0 allowed)': (dict(kind='prod', a=ENS, b=vt), None),
                     'overlay clip[0.5,1]': (dict(kind='prod', a=dict(kind='ovl', base=ENS, how='clip'), b=vt), None),
                     'overlay 0.5+0.5x (E3 long/half)': (dict(kind='prod', a=dict(kind='ovl', base=ENS, how='lin'), b=vt),
                                                         None)}
    return out


SWEEP_STARTS = {'KOSPI': ['1996-06-03', '1996-09-02', '1997-01-03', '1999-01-04', '2001-01-02', '2006-01-02',
                          '2011-01-03', '2016-01-04'],
                'SPY': ['1999-05-03', '2001-01-02', '2006-01-03', '2011-01-03']}

KOSPI_WINDOWS = [   # KR round-1 lab convention: returns after the start close through the end close
    ('2026-01-02..06-22 melt-up', '2025-12-30', '2026-06-22'),
    ('2026-06-22..07-30 crash', '2026-06-22', '2026-07-30'),
    ('2026-07-31..09-29 rebound', '2026-07-30', '2026-09-29'),
]


def main():
    score, epis, nbrows, wins, ovl_rows, sweep = [], [], [], [], [], []
    keep_paths = {}
    for mname in ('KOSPI', 'SPY'):
        mk = C.load_market(mname)
        cfg = mk.cfg
        sets, variants = rule_set(cfg['vt_target'])
        C.log(mname, 'eval', mk.ev_dates[0].date(), mk.ev_dates[-1].date(), 'sessions', mk.i1 - mk.i0 + 1)
        for bname, costs in cfg['books'].items():
            for rname, rs in list(sets.items()) + list(variants.items()):
                o, er, nr, paths = C.protective_card(mk, rs['spec'], costs, neighbours=rs.get('nbs', ()),
                                                     binary_gap=rs['gap'])
                o.update(book=bname, rule_id=rname, set='centre' if rname in sets else 'variant')
                score.append(o)
                for e in er:
                    e.update(book=bname, rule_id=rname)
                epis.extend(er)
                for n in nr:
                    n.update(book=bname, rule_id=rname)
                nbrows.extend(nr)
                keep_paths[(mname, bname, rname)] = paths
                C.log(f"{mname} {bname} {rname}: dMDD {o['pc1_dmdd_pp_1x']:+.1f} tail {o['pc2_tail_ratio']:.2f} "
                      f"dSR {o['dsr_vs_S_1x']:+.3f} p_ni {o['pc3_p_ni']:.3f} (blk {o['pc3_block']}) "
                      f"eps {o['pc4_n_positive']}/{o['pc4_n_episodes']} yrs {o['pc5_share_years_positive']:.2f} "
                      f"plateau {o['pc6_share_keep']} -> {o['verdict']} | if-suff {o['verdict_if_sufficient']}")
            # overlay vs sleeve
            for tname, d in overlay_specs(cfg['vt_target']).items():
                for vname, (spec, gap) in d.items():
                    o, er, _, _ = C.protective_card(mk, spec, costs, binary_gap=gap)
                    row = dict(market=mname, book=bname, trend=tname, form=vname, rule=o['rule'],
                               avg_exposure=o['avg_exposure'],
                               min_exposure=float(C.build_weight(spec, mk)[mk.i0 - 1:mk.i1].min()),
                               sharpe_1x=o['sharpe_rule_1x'], dsr_vs_S_1x=o['dsr_vs_S_1x'], mdd_1x=o['mdd_rule_1x'],
                               mdd_S=o['mdd_S'], mdd_buy_hold=o['mdd_buy_hold'], pc1_dmdd_pp_1x=o['pc1_dmdd_pp_1x'],
                               pc1_dmdd_pp_2x=o['pc1_dmdd_pp_2x'], pc2_tail_ratio=o['pc2_tail_ratio'],
                               pc3_p_ni=o['pc3_p_ni'], pc4_n_positive=o['pc4_n_positive'],
                               pc4_n_episodes=o['pc4_n_episodes'], pc4_largest_share=o['pc4_largest_share'],
                               pc5_share_years_positive=o['pc5_share_years_positive'],
                               turnover_per_year=o['turnover_per_year'], verdict=o['verdict'],
                               verdict_if_sufficient=o['verdict_if_sufficient'])
                    for e in er:
                        if e['episode'].startswith(('Jul-2026', 'GFC', '2022', '2020 crash', '1997-98', '2000-01')):
                            row[f"ep_{e['episode'].split(' (')[0]}"] = e['rule_return']
                    if mname == 'KOSPI':
                        for lab, s_, e_ in KOSPI_WINDOWS:
                            a, b = C.window_slice(mk, s_, e_, False)
                            net1, _ = C.book(mk, spec, costs[0])
                            row[f'win_{lab.split()[0]}'] = C.cum(net1[a - mk.i0:b - mk.i0 + 1])
                    ovl_rows.append(row)
        # start-date sensitivity of the centre rules (plateau share taken from the primary window)
        for bname, costs in cfg['books'].items():
            prim = {o['rule_id']: o for o in score if o['market'] == mname and o['book'] == bname}
            for st in SWEEP_STARTS[mname]:
                c2 = dict(cfg)
                c2['start'] = st
                mk2 = C.Market(mname, mk.dates, mk.p, mk.r, c2)
                for rname, rs in sets.items():
                    try:
                        o, _, _, _ = C.protective_card(mk2, rs['spec'], costs, binary_gap=rs['gap'], pc4_truncate=True,
                                                       pc6_override=prim[rname]['pc6_share_keep'])
                    except AssertionError:
                        continue                    # rule not yet defined at this start
                    sweep.append({k: o[k] for k in (
                        'market', 'rule', 'start', 'end', 'n_sessions', 'avg_exposure', 'sharpe_rule_1x',
                        'sharpe_buy_hold', 'mdd_rule_1x', 'mdd_S', 'mdd_buy_hold', 'pc1_dmdd_pp_1x', 'pc1_dmdd_pp_2x',
                        'pc2_tail_ratio', 'dsr_vs_S_1x', 'pc3_block', 'pc3_p_ni', 'pc4_n_positive', 'pc4_n_episodes',
                        'pc4_largest_share', 'pc4_largest_episode', 'pc5_share_years_positive', 'pc5_n_years',
                        'pc6_share_keep', 'onsets_declustered', 'pc7_pass', 'verdict', 'verdict_reasons',
                        'verdict_if_sufficient', 'verdict_if_sufficient_reasons', 'o_step5_p_block10')} |
                        dict(book=bname, rule_id=rname, primary=(st == cfg['start'])))
                C.log(f'{mname} {bname} sweep start {st} done')
        # windows (KOSPI 2026 windows + spec cost episodes), primary book
        bname = cfg['primary_book']
        c1 = cfg['books'][bname][0]
        allrules = {'buy-and-hold': dict(kind='bh')}
        allrules.update({k: v['spec'] for k, v in sets.items()})
        allrules['ENS >=2/4 binary'] = variants['ENS >=2/4 binary']['spec']
        wlist = []
        if mname == 'KOSPI':
            for lab, s, e in KOSPI_WINDOWS:
                a, b = C.window_slice(mk, s, e, False)
                wlist.append((lab, a, b))
        wlist += [(f'spec cost episode: {lab}', a, b) for lab, a, b in C.cost_episodes(mk)]
        wlist += [(f'PC-4 episode: {lab}', a, b) for lab, a, b in C.drawdown_episodes(mk, info=True)]
        for rid, spec in allrules.items():
            net, h = C.book(mk, spec, 0.0 if rid == 'buy-and-hold' else c1)
            S = h.mean() * mk.r_ev
            for lab, a, b in wlist:
                sl = slice(a - mk.i0, b - mk.i0 + 1)
                wins.append(dict(market=mname, book=bname, rule_id=rid, rule=C.spec_label(spec), window=lab,
                                 first_return=str(mk.dates[a].date()), last_return=str(mk.dates[b].date()),
                                 cum_return=C.cum(net[sl]), S_cum_return=C.cum(S[sl]),
                                 buy_hold=C.cum(mk.r[a:b + 1]), avg_exposure_in_window=float(h[sl].mean()),
                                 exposure_first_day=float(h[sl][0])))
    sc = pd.DataFrame(score)
    C.save_csv(sc, 'r2_idx_protective_scorecard.csv')
    C.save_csv(pd.DataFrame(epis), 'r2_idx_protective_episodes.csv')
    C.save_csv(pd.DataFrame(nbrows), 'r2_idx_plateau_neighbours.csv')
    C.save_csv(pd.DataFrame(wins), 'r2_idx_windows.csv')
    C.save_csv(pd.DataFrame(sweep), 'r2_idx_start_date_sensitivity.csv')
    ov = pd.DataFrame(ovl_rows)
    C.save_csv(ov, 'r2_idx_overlay_vs_sleeve.csv')
    ocols = ['market', 'book', 'rule_id', 'rule', 'set', 'start', 'end', 'sharpe_rule_1x', 'sharpe_rule_2x',
             'sharpe_buy_hold', 'dsr_vs_S_1x', 'o_step5_p_block10', 'o_step5_p_blockpw', 'pc3_block', 'o_step5_pass',
             'o_step2_sr_ci90_lo', 'o_step2_sr_ci90_hi', 'o_step2_pass', 'o_step3_psr0', 'o_step6_pass',
             'pc5_share_years_positive', 'bh_share_years_positive', 'pc5_pass', 'cagr_rule_1x', 'cagr_buy_hold',
             'mdd_rule_1x', 'mdd_buy_hold', 'cardO_verdict']
    C.save_csv(sc[ocols], 'r2_idx_outperformance.csv')
    # ---------------------------------------------------------------- chart (b): scorecard
    card_cols = ['market', 'book', 'rule_id', 'rule', 'set', 'avg_exposure', 'turnover_per_year', 'sharpe_rule_1x',
                 'sharpe_buy_hold', 'mdd_rule_1x', 'mdd_S', 'mdd_buy_hold', 'pc1_dmdd_pp_1x', 'pc1_dmdd_pp_2x',
                 'pc1_pass_1x', 'pc1_pass_2x', 'pc2_tail_ratio', 'pc2_pass', 'dsr_vs_S_1x', 'dsr_vs_S_2x', 'pc3_block',
                 'pc3_p_ni', 'pc3_pass', 'pc4_n_positive', 'pc4_n_episodes', 'pc4_largest_share',
                 'pc4_largest_episode', 'pc4_pass', 'pc5_share_years_positive', 'pc5_share_years_lagging_S',
                 'pc5_pass', 'pc6_share_keep', 'pc6_n_neighbours', 'pc6_pass', 'onsets_declustered', 'pc7_pass',
                 'verdict', 'verdict_reasons', 'verdict_if_sufficient', 'verdict_if_sufficient_reasons',
                 'o_step5_p_block10', 'cardO_verdict']
    C.save_json(dict(title='Protective-card (CARD-P, spec 8.7) scorecard: index trend and vol rules',
                     notes=['Indicative verdicts in the spec 8.7 order (sufficiency, REJECT, inconclusive, REVISE, '
                            'PASS); not a run of QUANTGEN\'s gate.',
                            'S = buy-and-hold x the rule\'s average exposure; with 0% cash Sharpe(S) = Sharpe(B&H).',
                            'pc3_p_ni: one-sided CBB p of dSR* <= -0.10, block max(10, PW(d), PW(d^2)), 2,000 '
                            'resamples, seed 11. o_step5_p_block10: gate step 5 (dSR vs buy-and-hold <= 0), '
                            '10-session blocks.',
                            'KOSPI 1996-09-02..2026-09-29 (rebuilt, price); SPY 1999-05-03..2021-03-31 (price).'],
                     rows=sc[card_cols].to_dict(orient='records')), 'r2_idx_chart_b_scorecard.json')
    # ---------------------------------------------------------------- chart (a): KOSPI 2024-2026 curves
    mk = C.load_kospi()
    vt = dict(kind='vt', window=20, target=0.20)
    specs = {'buy_and_hold': dict(kind='bh'), 'trend_ENS': ENS, 'VT20': vt,
             'trend_x_VT20': dict(kind='prod', a=ENS, b=vt), 'SMA200': dict(kind='sma', n=200, band=0.0)}
    a = mk.idx_on_or_after('2024-01-02')
    b = mk.i1
    curves = dict(dates=[str(d.date()) for d in mk.dates[a:b + 1]], nav={}, exposure={})
    for nm, sp in specs.items():
        net, h = C.run_book(C.build_weight(sp, mk), mk.r, a, b, 0.0 if nm == 'buy_and_hold' else 0.0003)
        curves['nav'][nm] = np.round(np.cumprod(1 + net), 5)
        curves['exposure'][nm] = np.round(h, 4)
    curves['title'] = 'KOSPI (rebuilt) 2024-01-02..2026-09-29: buy-and-hold, trend, VT20 and trend x VT20 (net 3 bp)'
    curves['notes'] = ['NAV = growth of 1 from the 2023-12-28 close; exposure = weight held that day (decided at '
                       'the previous close).',
                       'trend_ENS = share of positive 20/60/120/250-session returns (E3 multi-speed vote); '
                       'VT20 = min(1, 0.20 / SMA20 vol); trend_x_VT20 = product.',
                       'Windows to mark: 2026-01-02..06-22 melt-up, 06-22..07-30 crash, 07-31..09-29 rebound.']
    C.save_json(curves, 'r2_idx_chart_a_kospi_2024_2026.json')
    # ---------------------------------------------------------------- E3 claims
    e3 = e3_checks()
    C.save_csv(pd.DataFrame(e3), 'r2_idx_e3_checks.csv')
    C.log('done')


def e3_checks():
    """E3's KOSPI/SPY claims. E3 used 5 bp, its own clipped KOSPI proxy and a 1996 start; we report the round-1
    window (1996-06-03, closest to E3's) and our primary window (1996-09-02)."""
    rows = []

    def add(window, claim, e3val, ours, note=''):
        rows.append(dict(window=window, claim=claim, e3_value=e3val, ours=ours, note=note))

    vt = dict(kind='vt', window=20, target=0.20)
    ensvt = dict(kind='prod', a=ENS, b=vt)
    for start in ('1996-06-03', '1996-09-02'):
        cfg = dict(C.MARKET_CFG['KOSPI'])
        cfg['start'] = start
        mk = C.load_kospi(cfg)
        win = f'KOSPI {start}..2026-09-29'
        res = {}
        for nm, sp in (('ens', ENS), ('ensvt', ensvt),
                       ('ens_lin_vt', dict(kind='prod', a=dict(kind='ovl', base=ENS, how='lin'), b=vt)),
                       ('ens_clip_vt', dict(kind='prod', a=dict(kind='ovl', base=ENS, how='clip'), b=vt))):
            for c in (0.0003, 0.0005):
                net, h = C.book(mk, sp, c)
                S = h.mean() * mk.r_ev
                res[(nm, c)] = dict(sr=C.sharpe(net), srS=C.sharpe(S), mdd=C.mdd(net), mddS=C.mdd(S),
                                    tail=C.tail_ratio(h, mk.r_ev), turn=C.turnover_per_year(h, mk.ev_dates),
                                    net=net, S=S, h=h, x=h.mean())
        r = res[('ens', 0.0005)]
        add(win, 'KOSPI multi-speed long/flat (ens vote share) Sharpe vs static S, 5 bp', '0.60 vs 0.41',
            f"{r['sr']:.2f} vs {r['srS']:.2f}", 'S Sharpe = buy-and-hold Sharpe (0% cash)')
        add(win, 'KOSPI ens long/flat max drawdown vs S', '-35.3% vs -48.1%', f"{r['mdd']:.1%} vs {r['mddS']:.1%}",
            f"buy-and-hold max drawdown {C.mdd(mk.r_ev):.1%} (E3 -69.8%)")
        add(win, 'KOSPI ens turnover / tail ratio', '12.1 turns/yr; tail 0.77',
            f"{r['turn']:.1f} units/yr; tail {r['tail']:.2f}", 'turnover here = sum|dw| per year')
        r = res[('ensvt', 0.0005)]
        add(win, 'KOSPI trend x VT20 Sharpe vs S', '0.65 vs 0.41', f"{r['sr']:.2f} vs {r['srS']:.2f}")
        add(win, 'KOSPI trend x VT20 max drawdown vs S', '-26.7% vs -43.9%', f"{r['mdd']:.1%} vs {r['mddS']:.1%}")
        uw = C.underwater_episodes(mk, -0.20)
        ben, det = [], []
        for lab, a, b, depth in uw:
            sl = slice(a - mk.i0, b - mk.i0 + 1)
            bb = C.cum(r['net'][sl]) - C.cum(r['S'][sl])
            ben.append(bb)
            det.append(f'{lab} BH {depth:.1%} benefit {bb:+.1%}')
        ben = np.array(ben)
        pos = ben[ben > 0]
        add(win, 'KOSPI trend x VT20 beats S in 8 of 8 drawdowns (largest share 31%)', '8/8; 31%',
            f"{(ben > 0).sum()}/{len(ben)}; largest {pos.max() / pos.sum():.0%}",
            'episodes = buy-and-hold under-water spells deeper than -20%, peak close -> trough close: ' + ' | '.join(det))
        er = C.episode_rows(mk, r['net'], r['S'], C.drawdown_episodes(mk))
        bb = np.array([e['benefit_vs_S'] for e in er])
        add(win, 'Same claim on the spec 8.6 PC-4 episode set (+1997-98, 2000-01)', '(not stated by E3)',
            f"{(bb > 0).sum()}/{len(bb)} positive; largest {bb[bb > 0].max() / bb[bb > 0].sum():.0%}")
        a, b = C.window_slice(mk, '2026-06-22', '2026-07-30', False)
        sl = slice(a - mk.i0, b - mk.i0 + 1)
        rr = res[('ens', 0.0003)]
        add(win, 'No trend protection in the 22 Jun-30 Jul 2026 crash (ens L/F vs buy-and-hold)', '-30.7% vs -38.0%',
            f"{C.cum(rr['net'][sl]):.1%} vs {C.cum(mk.r[a:b + 1]):.1%}",
            f"exposure on the first crash day {rr['h'][sl][0]:.2f}; mean {rr['h'][sl].mean():.2f}; E3's proxy "
            f"gives -38.0% for buy-and-hold, the rebuilt index -38.6%")
        v = res[('ensvt', 0.0003)]
        add(win, 'trend x VT20 in the Jul-2026 crash', '-9.5%', f"{C.cum(v['net'][sl]):.1%}")
        for key, lab in (('ens_lin_vt', '0.5 + 0.5 x votes'), ('ens_clip_vt', 'clip(votes, 0.5, 1)')):
            l = res[(key, 0.0003)]
            d_sleeve = (v['mdd'] - v['mddS']) * 100
            d_ovl = (l['mdd'] - l['mddS']) * 100
            d_ovl_sleeveS = (l['mdd'] - v['mddS']) * 100
            add(win, f'Overlay with floor 0.5 ({lab}) x VT20: PC-1 improvement falls from +17.3 to +8.1 pp',
                '+17.3 -> +8.1 pp', f"{d_sleeve:+.1f} -> {d_ovl:+.1f} pp (vs own S)",
                f"absolute max DD {v['mdd']:.1%} -> {l['mdd']:.1%}; overlay MDD vs the sleeve's S {d_ovl_sleeveS:+.1f} pp; "
                f"tail ratio {v['tail']:.2f} -> {l['tail']:.2f}; KOSPI 3 bp")
    sp = C.load_spy()
    for nm, spec in (('SMA200', dict(kind='sma', n=200, band=0.0)),
                     ('ens x VT20', dict(kind='prod', a=ENS, b=dict(kind='vt', window=20, target=0.20)))):
        net, h = C.book(sp, spec, 0.0005)
        S = h.mean() * sp.r_ev
        add('SPY 1999-05-03..2021-03-31', f'SPY {nm} 1999-2021 at 5 bp: Sharpe rule / B&H(=S); MDD rule / S / B&H',
            {'SMA200': '0.38 / 0.40; -30.0% / -43.8% (S 0.72) / -56.5%',
             'ens x VT20': '0.41 vs S 0.37; -27.3% vs S -41.3%; tail 0.51'}[nm],
            f"{C.sharpe(net):.2f} / {C.sharpe(sp.r_ev):.2f}; {C.mdd(net):.1%} / {C.mdd(S):.1%} (S {h.mean():.2f}) / "
            f"{C.mdd(sp.r_ev):.1%}; tail {C.tail_ratio(h, sp.r_ev):.2f}", 'E3 window starts in 1999 (month not stated)')
    return rows


if __name__ == '__main__':
    main()
