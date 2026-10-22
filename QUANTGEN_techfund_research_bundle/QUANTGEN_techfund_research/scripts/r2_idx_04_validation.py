"""r2_idx_04_validation.py -- assertion tests and reference reproductions for the round-2 index lab.

V1  no look-ahead: every weight path (centres, neighbours, variants, overlays) is unchanged up to day t when all
    prices after t are perturbed (5 cut dates per market).
V2  timing: the weight decided at the close of t earns only r_{t+1} (impulse test); costs hit the earning day;
    the initial entry is not charged.
V3  macro spec golden values for the KOSPI VT20 (2016-01..2026-10-02, ^KS11 in the spec; rebuilt KOSPI to
    2026-09-29 here): Sharpe, max DD, static comparator, windows, weights.
V4  R4b's indicative Korea VT20 protective card (spec 8.9, KRX ETF 3 bp) re-run with this lab's harness.
V5  reproducibility: bootstrap p-values (seed 11) and simulated gate paths (per-path seeds) are identical on re-run;
    a subset of paths re-simulated alone equals the same paths inside a larger run.
V6  E1's Shiller table reproduced exactly (signal on the average-price 12-month change, TR P&L, flat = 0).
V7  gate simulation sanity: iid-normal pass rates vs analytic values.
V8  SHA-256 of every result file.
"""
import glob
import os

import numpy as np
import pandas as pd

import r2_idx_common as C
import r2_idx_01_protective as P1

ROWS = []


def check(test, what, passed, detail=''):
    ROWS.append(dict(test=test, what=what, passed=bool(passed), detail=detail))
    C.log(('PASS ' if passed else 'FAIL ') + f'{test}: {what} {detail}')


def all_specs(target):
    sets, variants = P1.rule_set(target)
    specs = []
    for rs in list(sets.values()) + list(variants.values()):
        specs.append(rs['spec'])
        specs.extend(rs.get('nbs', []))
    for d in P1.overlay_specs(target).values():
        specs.extend(sp for sp, _ in d.values())
    return specs


def v1_lookahead():
    rng = np.random.default_rng(20261002)
    for mname in ('KOSPI', 'SPY'):
        mk = C.load_market(mname)
        specs = all_specs(mk.cfg['vt_target'])
        n_ok = n_tot = 0
        cuts = np.linspace(mk.i0 + 50, mk.i1 - 50, 5).astype(int)
        for cut in cuts:
            p2 = mk.p.copy()
            p2[cut + 1:] = p2[cut + 1:] * np.exp(np.cumsum(rng.normal(0, 0.03, len(p2) - cut - 1)))
            r2 = mk.r.copy()
            r2[cut + 1:] = p2[cut + 1:] / p2[cut:-1] - 1.0
            mk2 = C.Market(mname, mk.dates, p2, r2, mk.cfg)
            for sp in specs:
                w1 = C.build_weight(sp, mk)[:cut + 1]
                w2 = C.build_weight(sp, mk2)[:cut + 1]
                same = np.array_equal(np.isnan(w1), np.isnan(w2)) and np.allclose(w1[~np.isnan(w1)], w2[~np.isnan(w2)],
                                                                                 rtol=0, atol=1e-12)
                n_ok += same
                n_tot += 1
                # the perturbation must change something after the cut for rules that react to prices (power)
        check('V1', f'{mname}: weights at t unchanged when prices after t are perturbed',
              n_ok == n_tot, f'{n_ok}/{n_tot} spec x cut-date pairs ({len(specs)} specs, 5 cuts)')
        # power: a deliberately look-ahead weight (sign of the NEXT 20-session return) must fail the same test
        detected = 0
        for cut in cuts:
            p2 = mk.p.copy()
            p2[cut + 1:] = p2[cut + 1:] * np.exp(np.cumsum(rng.normal(0, 0.03, len(p2) - cut - 1)))

            def planted(p):
                # a vol target that peeks at the NEXT 20 returns (continuous, uncapped)
                r_ = np.r_[np.nan, p[1:] / p[:-1] - 1.0]
                fut = pd.Series(r_[::-1]).rolling(20, min_periods=20).std().values[::-1]   # std of r_t..r_{t+19}
                fut = np.r_[fut[1:], np.nan]                                                 # -> r_{t+1}..r_{t+20}
                return 0.2 / fut
            a_, b_ = planted(mk.p)[:cut + 1], planted(p2)[:cut + 1]
            detected += not (np.array_equal(np.isnan(a_), np.isnan(b_)) and
                             np.allclose(a_[~np.isnan(a_)], b_[~np.isnan(b_)], rtol=0, atol=1e-12))
        check('V1b', f'{mname}: the same test detects a planted look-ahead rule', detected == len(cuts),
              f'{detected}/{len(cuts)} cut dates')


def v2_timing():
    r = np.array([np.nan, 0.01, -0.02, 0.03, 0.04, -0.05, 0.02])
    w = np.array([0, 0, 1, 0, 0, 0, 0], float)
    net, h = C.run_book(w, r, 1, 6, 0.0)
    exp = np.zeros(6)
    exp[2] = r[3]                       # decided at close of day 2 -> earns day 3 (index 2 of the window)
    check('V2', 'weight decided at the close of t earns only r_{t+1}', np.allclose(net, exp), str(net))
    w = np.array([1, 1, 1, 0.5, 0.5, 1, 1], float)
    net, h = C.run_book(w, r, 1, 6, 0.001)
    exp = np.array([r[1], r[2], r[3], 0.5 * r[4] - 0.0005, 0.5 * r[5], r[6] - 0.0005])
    check('V2b', 'cost = c x |dw| charged on the earning day; initial entry not charged', np.allclose(net, exp),
          str(np.round(net - exp, 12)))
    mk = C.load_kospi()
    net, h = C.book(mk, dict(kind='sma', n=200, band=0.0), 0.0)
    w = C.build_weight(dict(kind='sma', n=200, band=0.0), mk)
    check('V2c', 'engine held weight = decided weight lagged one session (KOSPI SMA200)',
          np.array_equal(h, w[mk.i0 - 1:mk.i1]), f'{len(h)} sessions compared')


SPEC_GOLD = dict(sr_vt=0.638, sr_bh=0.634, mdd_vt=-0.368, mdd_bh=-0.439, avg_exp=0.925, mdd_static=-0.413,
                 dmdd_gross=4.5, sr_vt_etf=0.635, dmdd_etf=4.4, sr_vt_etf2=0.632,
                 windows={'Jul-2026 crash': (-0.122, -0.386), 'Mar-2026': (-0.079, -0.199), 'Aug-2024': (-0.079, -0.055),
                          'Apr-2025': (-0.117, -0.120), '2020 crash': (-0.258, -0.341), '2020 rebound': (0.259, 0.499),
                          'H1-2026': (0.517, 1.011), '30 Jul-30 Sep 2026': (0.059, 0.222)},
                 weights={'2026-06-22': 0.3024, '2026-06-23': 0.3309, '2026-07-30': 0.2484})
GOLD_WINDOWS = {'Jul-2026 crash': ('2026-06-22', '2026-07-30', False), 'Mar-2026': ('2026-02-27', '2026-03-31', True),
                'Aug-2024': ('2024-07-31', '2024-08-09', True), 'Apr-2025': ('2025-03-28', '2025-04-09', True),
                '2020 crash': ('2020-02-19', '2020-03-19', False), '2020 rebound': ('2020-03-19', '2020-06-08', False),
                'H1-2026': ('2026-01-02', '2026-06-30', True), '30 Jul-30 Sep 2026': ('2026-07-30', '2026-09-30', False)}


def v3_golden():
    cfg = dict(C.MARKET_CFG['KOSPI'])
    cfg['start'] = '2016-01-04'
    mk = C.load_kospi(cfg)
    vt = dict(kind='vt', window=20, target=0.20)
    g, h = C.book(mk, vt, 0.0)
    e1, _ = C.book(mk, vt, 0.0003)
    e2, _ = C.book(mk, vt, 0.0006)
    bh = mk.r_ev
    S = h.mean() * bh
    rows = []

    # spec 9.3 tolerances. Level 1 (reference implementation): Sharpe +-0.01, max DD +-1 pp, windows +-1 pp,
    # weights +-0.02. Level 2 (production feeds, e.g. a different KOSPI series): Sharpe +-0.03, windows +-2 pp;
    # the spec gives no Level-2 value for max DD / weights, so +-2 pp and +-0.02 are used (declared here).
    L2 = {0.01: 0.03, 0.02: 0.02, 1.0: 1.5}

    def gold(item, ours, spec, tol, unit=''):
        t2 = 0.02 if (item.startswith('window') or 'max DD' in item) else L2.get(tol, 3 * tol)
        rows.append(dict(item=item, ours=ours, spec=spec, gap=ours - spec, level1_tol=tol, level2_tol=t2,
                         within_level1=abs(ours - spec) <= tol + 1e-9, within_level2=abs(ours - spec) <= t2 + 1e-9))
    gold('VT20 Sharpe (gross)', C.sharpe(g), SPEC_GOLD['sr_vt'], 0.01)
    gold('Buy-and-hold Sharpe', C.sharpe(bh), SPEC_GOLD['sr_bh'], 0.01)
    gold('VT20 max DD (gross)', C.mdd(g), SPEC_GOLD['mdd_vt'], 0.01)
    gold('Buy-and-hold max DD', C.mdd(bh), SPEC_GOLD['mdd_bh'], 0.01)
    gold('VT20 average exposure', h.mean(), SPEC_GOLD['avg_exp'], 0.02, 'w')
    gold('Static S max DD', C.mdd(S), SPEC_GOLD['mdd_static'], 0.01)
    gold('dMDD VT20 vs S, gross (pp)', (C.mdd(g) - C.mdd(S)) * 100, SPEC_GOLD['dmdd_gross'], 1.0)
    gold('VT20 Sharpe net 3 bp', C.sharpe(e1), SPEC_GOLD['sr_vt_etf'], 0.01)
    gold('VT20 Sharpe net 6 bp', C.sharpe(e2), SPEC_GOLD['sr_vt_etf2'], 0.01)
    gold('dMDD VT20 vs S, net 3 bp (pp)', (C.mdd(e1) - C.mdd(S)) * 100, SPEC_GOLD['dmdd_etf'], 1.0)
    gold('dSR VT20 - buy-and-hold (gross)', C.sharpe(g) - C.sharpe(bh), SPEC_GOLD['sr_vt'] - SPEC_GOLD['sr_bh'], 0.01)
    for lab, (s, e, inc) in GOLD_WINDOWS.items():
        a, b = C.window_slice(mk, s, e, inc)
        sl = slice(a - mk.i0, b - mk.i0 + 1)
        gold(f'window {lab}: VT20', C.cum(g[sl]), SPEC_GOLD['windows'][lab][0], 0.01)
        gold(f'window {lab}: buy-and-hold', C.cum(bh[sl]), SPEC_GOLD['windows'][lab][1], 0.01)
    w = C.build_weight(vt, mk)
    for d, v in SPEC_GOLD['weights'].items():
        i = mk.idx_on_or_before(d)
        gold(f'VT20 weight earning on {d}', w[i - 1], v, 0.02, 'w')
    df = pd.DataFrame(rows)
    C.save_csv(df, 'r2_idx_golden_values.csv')
    n1 = int(df.within_level1.sum())
    n2 = int(df.within_level2.sum())
    check('V3', 'macro spec 9.3 KOSPI VT20 golden values on the rebuilt KOSPI (2016-01-04..2026-09-29)',
          n2 == len(df), f'{n1}/{len(df)} within Level-1 tolerance, {n2}/{len(df)} within Level-2')
    return df


def v4_r4b():
    cfg = dict(C.MARKET_CFG['KOSPI'])
    cfg['start'] = '2016-01-04'
    mk = C.load_kospi(cfg)
    vt = dict(kind='vt', window=20, target=0.20)
    nbs = [dict(kind='vt', window=w_, target=t) for w_ in (10, 20, 40) for t in (0.15, 0.20, 0.25)
           if not (w_ == 20 and t == 0.20)]
    o, er, nr, _ = C.protective_card(mk, vt, (0.0003, 0.0006), neighbours=nbs, pc4_truncate=True)
    ref = [('dMDD vs S 1x (pp)', o['pc1_dmdd_pp_1x'], 4.4, 0.5), ('dMDD vs S 2x (pp)', o['pc1_dmdd_pp_2x'], 4.4, 0.5),
           ('tail-exposure ratio', o['pc2_tail_ratio'], 0.82, 0.02), ('dSR vs S', o['dsr_vs_S_1x'], 0.001, 0.01),
           ('PW block on d^2 (sessions)', o['pc3_block'], 101, 5), ('p_ni at the PW block', o['pc3_p_ni'], 0.21, 0.03),
           ('p_ni at 10-session blocks', o['pc3_p_ni_block10'], 0.24, 0.03),
           ('episodes positive (of 9)', o['pc4_n_positive'], 3, 0), ('largest episode share (Jul-2026)', o['pc4_largest_share'], 0.59, 0.02),
           ('share of years positive', o['pc5_share_years_positive'], 0.73, 0.01), ('plateau share', o['pc6_share_keep'], 0.63, 0.01)]
    rows = [dict(item=k, ours=v, r4b=r, gap=v - r, tol=t, within=abs(v - r) <= t + 1e-9) for k, v, r, t in ref]
    rows.append(dict(item='verdict', ours=o['verdict'], r4b='INSUFFICIENT DATA (inconclusive)', gap=np.nan, tol=np.nan,
                     within=o['verdict'] == 'INSUFFICIENT DATA (inconclusive)'))
    df = pd.DataFrame(rows)
    C.save_csv(df, 'r2_idx_r4b_crosscheck.csv')
    check('V4', "R4b's Korea VT20 protective card (spec 8.9) reproduced by this harness",
          bool(df.within.all()), f"{int(df.within.sum())}/{len(df)} items within tolerance; verdict {o['verdict']}")


def v5_repro():
    mk = C.load_kospi()
    sp = dict(kind='prod', a=P1.ENS, b=dict(kind='vt', window=20, target=0.20))
    o1, _, _, _ = C.protective_card(mk, sp, (0.0003, 0.0006))
    o2, _, _, _ = C.protective_card(mk, sp, (0.0003, 0.0006))
    keys = ['pc3_p_ni', 'pc3_p_ni_block10', 'o_step5_p_block10', 'pc3_dsr_ci90_lo', 'o_step2_sr_ci90_lo']
    check('V5', 'bootstrap p-values identical on re-run (seed 11)', all(o1[k] == o2[k] for k in keys),
          ', '.join(f'{k}={o1[k]:.4f}' for k in keys))
    import r2_idx_02_gate_sim as G
    src = G.load_source()
    a = G.simulate(6, 'kospi', src=src)
    b = G.simulate(6, 'kospi', src=src)
    c = G.simulate(2, 'kospi', path_ids=[2, 5], src=src)
    same = all(np.array_equal(a[k], b[k]) for k in a)
    sub = all(np.array_equal(a[k][[2, 5]], c[k]) for k in a)
    check('V5b', 'gate simulation identical on re-run; per-path seeds reproduce a subset', same and sub,
          f'rerun identical={same}, subset identical={sub}')


def v6_e1():
    df = pd.read_csv(f'{C.RES}/r2_idx_e1_checks.csv')
    targets = {'1927-01..1991-12': (0.093, 0.113, 0.82, -0.375, 0.111, 0.168, 0.66, -0.818),
               '1992-01..2014-12': (0.116, 0.088, 1.32, -0.117, 0.100, 0.124, 0.81, -0.490),
               '2015-01..2026-09': (0.109, 0.107, 1.02, -0.189, 0.138, 0.119, 1.16, -0.193)}
    ok = True
    det = []
    for w, t in targets.items():
        r = df[(df.window == w) & df.source.str.startswith('Shiller avg (E1')].iloc[0]
        ours = (r.rule_mean, r.rule_vol, r.rule_rv, r.rule_mdd, r.bh_mean, r.bh_vol, r.bh_rv, r.bh_mdd)
        tol = (0.0015, 0.0015, 0.015, 0.0015, 0.0015, 0.0015, 0.015, 0.0015)
        good = all(abs(a - b) <= tt for a, b, tt in zip(ours, t, tol))
        ok &= good
        det.append(f"{w}: R/V {r.rule_rv:.2f} vs {r.bh_rv:.2f}")
    check('V6', "E1's Shiller 12-month-sign table reproduced (rounding tolerance)", ok, '; '.join(det))


def v7_sim_sanity():
    df = pd.read_csv(f'{C.RES}/r2_idx_gate_sim.csv')
    d = df[(df.innovations == 'iid_normal') & (df.step.isin(['step2_bootstrap', 'step3_dsr', 'step5_benchmark']))]
    d = d[d.analytic_iid.notna()]
    gap = (d.pass_rate - d.analytic_iid).abs()
    z = gap / np.maximum(d.mc_se, 0.005)
    check('V7', 'iid-normal simulated pass rates vs analytic normal approximations (steps 2, 3, 5)',
          float(np.mean(z <= 3)) >= 0.95,
          f'share of {len(d)} cells within 3 MC SE: {np.mean(z <= 3):.3f}; max abs gap {gap.max():.3f}')
    d8 = df[(df.innovations == 'iid_normal') & (df.step == 'step8_years')]
    gap8 = (d8.pass_rate - d8.analytic_iid).abs()
    check('V7b', 'iid-normal step-8 pass rates vs the lognormal-binomial formula', float(gap8.max()) <= 0.05,
          f'max abs gap {gap8.max():.3f}')


def v8_hashes():
    for f in sorted(glob.glob(f'{C.RES}/*.csv')) + sorted(glob.glob(f'{C.CHT}/*.json')):
        if os.path.basename(f) == 'r2_idx_validation.csv':
            continue
        ROWS.append(dict(test='V8', what=os.path.relpath(f, C.OUT), passed=True, detail=C.sha256(f)))


def main():
    v1_lookahead()
    v2_timing()
    v3_golden()
    v4_r4b()
    v5_repro()
    v6_e1()
    if os.path.exists(f'{C.RES}/r2_idx_gate_sim.csv'):
        v7_sim_sanity()
    v8_hashes()
    df = pd.DataFrame(ROWS)
    C.save_csv(df, 'r2_idx_validation.csv')
    core = df[df.test != 'V8']
    C.log(f'validation: {int(core.passed.sum())}/{len(core)} checks passed')


if __name__ == '__main__':
    main()
