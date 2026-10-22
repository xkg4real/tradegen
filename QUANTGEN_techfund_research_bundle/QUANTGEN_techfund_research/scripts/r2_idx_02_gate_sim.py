"""r2_idx_02_gate_sim.py -- Task 2: how often QUANTGEN's gate passes strategies with no edge, and its power.

Design (declared before the run):
  Innovations  rebuilt KOSPI daily returns 1995-05-03..2026-09-29 (7,912 obs), de-meaned and rescaled to an
               annualised vol of 15%. Paths are circular block bootstraps with 126-session blocks (keeps the
               volatility clustering and fat tails of the source within half-years). Master paths are 50 x 252
               sessions; a Y-year sample is the first 252*Y sessions (common random numbers across Y and across
               Sharpe levels, which only shift the mean).
  Strategy     x_t = z_t + mu, mu = SR * 0.15 / 252: true annualised (arithmetic) Sharpe SR, cash 0%.
  Benchmark    b_t = rho z_t + sqrt(1 - rho^2) w_t + 0.4 * 0.15 / 252 (Sharpe 0.4, vol 15%, correlation rho),
               w an independent bootstrap path of the same source.
  Gate steps   (approximations of QUANTGEN's gate; steps 1, 4, 6, 7, 9 need a search / costs and are not simulated)
    step 2  90% circular-block-bootstrap percentile interval of the Sharpe (10-session blocks) excludes 0
            (lower 5% quantile > 0). Also reported: the Lo (2002) iid-SE interval.
    step 3  deflated Sharpe >= 0.95 (Bailey and Lopez de Prado 2014) for N in {1, 9, 27, 100} independent
            zero-edge trials: SR0 = sqrt(1/(T-1)) x [(1-g) Phi^-1(1-1/N) + g Phi^-1(1-1/(N e))] per period
            (SR0 = 0 for N = 1), with the path's skewness and kurtosis in the PSR denominator.
    step 5  paired circular block bootstrap (10-session blocks, same resampled days for x and b);
            p = share of resamples with SR*(x) - SR*(b) <= 0; pass when p <= 0.10.
    step 8  >= 60% of the Y consecutive 252-session years have a positive compounded return.
  Resamples    R = 500 per path and test (the gate uses 2,000; with 500 the 5% and 10% quantiles carry a
               resampling SE of roughly 1 pp of coverage, which slightly blurs the threshold but does not bias it).
  Paths        NPATH per cell (all cells share the paths); Monte Carlo SE = sqrt(p(1-p)/NPATH).
  Seeds        path k uses numpy default_rng([11, k, 1]) for the data and default_rng([11, k, 2]) for the
               bootstrap, so any subset of paths can be re-run exactly (validation script).
  Variants     (a) kospi_cbb126 -- the specified design. The de-meaned KOSPI source has medium-horizon
                   dependence (variance ratio 1.23 at 126 sessions, 1.34 at 252), which 126-session blocks carry
                   into the paths: zero unconditional mean, but persistent local drifts.
               (b) kospi_cbb126_signflip -- the same blocks with an independent random sign on every day: keeps
                   |r| (volatility clustering, fat tails), removes all serial dependence in the mean (martingale
                   null). NPATH_SIGN paths.
               (c) iid_normal -- no clustering, no fat tails. NPATH_IID paths.
"""
import math
import sys

import numpy as np
import pandas as pd
from scipy.stats import norm, skew, kurtosis, binom

import r2_idx_common as C

VOL = 0.15
BSR = 0.40
GEN_BLOCK = 126
BOOT_BLOCK = 10
RBOOT = 500
YEARS = [5, 8, 10, 12, 15, 18, 20, 25, 30, 40, 50]
SR_GRID = [0.0, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
IR03 = {0.0: round(BSR + 0.3 * math.sqrt(2.0), 4), 0.5: 0.7, 0.9: round(BSR + 0.3 * math.sqrt(0.2), 4)}
MUS = sorted(set(SR_GRID) | set(IR03.values()))
RHOS = [0.0, 0.5, 0.9]
NTRIALS = [1, 9, 27, 100]
NPATH = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
NPATH_IID = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
NPATH_SIGN = int(sys.argv[3]) if len(sys.argv) > 3 else 2000
EULER = 0.5772156649015329
TMAX = 252 * max(YEARS)


def z_n(N):
    if N <= 1:
        return 0.0
    return (1 - EULER) * norm.ppf(1 - 1.0 / N) + EULER * norm.ppf(1 - 1.0 / (N * math.e))


ZN = np.array([z_n(N) for N in NTRIALS])


def load_source():
    k = pd.read_parquet(C.KOSPI_PARQUET)
    src = k['ret'].astype(float).values[1:]
    z = src - src.mean()
    return z / z.std(ddof=0) * VOL / math.sqrt(C.ANN)


def cbb_path(rng, src, n, block):
    N0 = len(src)
    nb = -(-n // block)
    starts = rng.integers(0, N0, nb)
    idx = (starts[:, None] + np.arange(block)[None, :]) % N0
    return src[idx.ravel()[:n]]


def simulate(npath, gen='kospi', path_ids=None, src=None):
    """Returns dict of boolean pass arrays indexed [path, year, mu (, extra)]."""
    src = load_source() if src is None else src
    sd_d = VOL / math.sqrt(C.ANN)
    mus = np.array(MUS) * VOL / C.ANN
    mub = BSR * VOL / C.ANN
    nY, nM = len(YEARS), len(MUS)
    ids = list(range(npath)) if path_ids is None else list(path_ids)
    P = len(ids)
    out = dict(step2=np.zeros((P, nY, nM), bool), step2_lo=np.zeros((P, nY, nM), bool),
               step3=np.zeros((P, nY, nM, len(NTRIALS)), bool), step5=np.zeros((P, nY, nM, len(RHOS)), bool),
               step8=np.zeros((P, nY, nM), bool), p5=np.zeros((P, nY, nM, len(RHOS)), np.float32),
               sr_hat=np.zeros((P, nY, nM), np.float32))
    ar = np.arange(BOOT_BLOCK)
    for pi, pid in enumerate(ids):
        rg = np.random.default_rng([C.SEED, pid, 1])
        rb = np.random.default_rng([C.SEED, pid, 2])
        if gen == 'kospi':
            z = cbb_path(rg, src, TMAX, GEN_BLOCK)
            w = cbb_path(rg, src, TMAX, GEN_BLOCK)
        elif gen == 'kospi_sign':
            z = cbb_path(rg, src, TMAX, GEN_BLOCK) * rg.choice((-1.0, 1.0), TMAX)
            w = cbb_path(rg, src, TMAX, GEN_BLOCK) * rg.choice((-1.0, 1.0), TMAX)
        else:
            z = rg.standard_normal(TMAX) * sd_d
            w = rg.standard_normal(TMAX) * sd_d
        # step 8: yearly compounded returns for every Sharpe level (first Y years of the master path)
        L = np.log1p(z[None, :] + mus[:, None]).reshape(nM, max(YEARS), 252).sum(-1)       # (nM, 50)
        for iy, Y in enumerate(YEARS):
            T = 252 * Y
            zt, wt = z[:T], w[:T]
            out['step8'][pi, iy] = (L[:, :Y] > 0).mean(1) >= 0.6
            # sample statistics
            mz, sz = zt.mean(), zt.std(ddof=1)
            g3 = skew(zt)
            g4 = kurtosis(zt, fisher=False)
            srd = (mz + mus) / sz                                                       # per-period Sharpe
            out['sr_hat'][pi, iy] = srd * math.sqrt(C.ANN)
            se_lo = np.sqrt((1 + 0.5 * srd ** 2) / T)
            out['step2_lo'][pi, iy] = srd - 1.6448536269514722 * se_lo > 0
            den = np.sqrt(np.maximum(1e-12, 1 - g3 * srd + (g4 - 1) / 4.0 * srd ** 2))
            sr0 = ZN[None, :] * math.sqrt(1.0 / (T - 1))
            dsr = norm.cdf((srd[:, None] - sr0) * math.sqrt(T - 1) / den[:, None])
            out['step3'][pi, iy] = dsr >= 0.95
            # circular block bootstrap with 10-session blocks inside the Y-year sample
            A = np.stack([zt, zt * zt, wt, wt * wt, zt * wt])
            ext = np.concatenate([A, A[:, :BOOT_BLOCK]], axis=1)
            cs = np.concatenate([np.zeros((5, 1)), np.cumsum(ext, axis=1)], axis=1)
            BS = cs[:, BOOT_BLOCK:BOOT_BLOCK + T] - cs[:, :T]
            nfull, rem = divmod(T, BOOT_BLOCK)
            st = rb.integers(0, T, (RBOOT, nfull))
            sums = BS[:, st].sum(-1)                                                    # (5, R)
            if rem:
                BSr = cs[:, rem:rem + T] - cs[:, :T]
                sums += BSr[:, rb.integers(0, T, RBOOT)]
            m_z, m_w = sums[0] / T, sums[2] / T
            v_z = (sums[1] / T - m_z ** 2) * T / (T - 1)
            v_w = (sums[3] / T - m_w ** 2) * T / (T - 1)
            c_zw = (sums[4] / T - m_z * m_w) * T / (T - 1)
            srx = (m_z[None, :] + mus[:, None]) / np.sqrt(v_z)[None, :] * math.sqrt(C.ANN)  # (nM, R)
            out['step2'][pi, iy] = np.quantile(srx, 0.05, axis=1) > 0
            for ir, rho in enumerate(RHOS):
                s = math.sqrt(1 - rho ** 2)
                mb = rho * m_z + s * m_w + mub
                vb = rho ** 2 * v_z + s ** 2 * v_w + 2 * rho * s * c_zw
                srb = mb / np.sqrt(vb) * math.sqrt(C.ANN)
                p5 = ((srx - srb[None, :]) <= 0).mean(1)
                out['p5'][pi, iy, :, ir] = p5
                out['step5'][pi, iy, :, ir] = p5 <= 0.10
        if (pi + 1) % 200 == 0:
            C.log(f'{gen}: {pi + 1}/{P} paths')
    return out


def summarise(res, gen):
    rows = []
    P = res['step2'].shape[0]

    def add(Y, sr, rho, N, step, arr):
        p = float(arr.mean())
        rows.append(dict(innovations=gen, years=Y, true_sr=sr, rho=rho, n_trials=N, step=step, pass_rate=p,
                         mc_se=math.sqrt(max(p * (1 - p), 1e-12) / P), n_paths=P))

    for iy, Y in enumerate(YEARS):
        for im, sr in enumerate(MUS):
            add(Y, sr, np.nan, np.nan, 'step2_bootstrap', res['step2'][:, iy, im])
            add(Y, sr, np.nan, np.nan, 'step2_lo_iid', res['step2_lo'][:, iy, im])
            add(Y, sr, np.nan, np.nan, 'step8_years', res['step8'][:, iy, im])
            for iN, N in enumerate(NTRIALS):
                add(Y, sr, np.nan, N, 'step3_dsr', res['step3'][:, iy, im, iN])
                add(Y, sr, np.nan, N, 'steps2+3+8', res['step2'][:, iy, im] & res['step3'][:, iy, im, iN] &
                    res['step8'][:, iy, im])
            for ir, rho in enumerate(RHOS):
                add(Y, sr, rho, np.nan, 'step5_benchmark', res['step5'][:, iy, im, ir])
                for iN, N in enumerate(NTRIALS):
                    j = res['step2'][:, iy, im] & res['step3'][:, iy, im, iN] & res['step5'][:, iy, im, ir] & \
                        res['step8'][:, iy, im]
                    add(Y, sr, rho, N, 'joint_2_3_5_8', j)
    return pd.DataFrame(rows)


def analytic(rows_df):
    """iid-normal reference values for the same cells."""
    out = []
    for Y in YEARS:
        for sr in MUS:
            out.append(dict(years=Y, true_sr=sr, rho=np.nan, n_trials=np.nan, step='step2_bootstrap',
                            analytic_iid=norm.cdf(sr * math.sqrt(Y) - 1.6448536269514722)))
            q = norm.cdf((sr * VOL - VOL ** 2 / 2) / VOL)
            k = math.ceil(0.6 * Y - 1e-9)
            out.append(dict(years=Y, true_sr=sr, rho=np.nan, n_trials=np.nan, step='step8_years',
                            analytic_iid=float(binom.sf(k - 1, Y, q))))
            for N in NTRIALS:
                out.append(dict(years=Y, true_sr=sr, rho=np.nan, n_trials=N, step='step3_dsr',
                                analytic_iid=norm.cdf(sr * math.sqrt(Y) - z_n(N) - 1.6448536269514722)))
            for rho in RHOS:
                out.append(dict(years=Y, true_sr=sr, rho=rho, n_trials=np.nan, step='step5_benchmark',
                                analytic_iid=norm.cdf((sr - BSR) * math.sqrt(Y) / math.sqrt(2 * (1 - rho))
                                                      - 1.2815515655446004)))
    return pd.DataFrame(out)


def years_for_power(df, levels=(0.5, 0.8)):
    rows = []
    keys = ['innovations', 'true_sr', 'rho', 'n_trials', 'step']
    for k, g in df.groupby(keys, dropna=False):
        g = g.sort_values('years')
        y, p = g['years'].values.astype(float), g['pass_rate'].values
        row = dict(zip(keys, k))
        for lv in levels:
            hit = np.where(p >= lv)[0]
            if len(hit) == 0:
                val = np.nan
                txt = f'>{int(y[-1])}'
            elif hit[0] == 0:
                val = y[0]
                txt = f'<={int(y[0])}'
            else:
                j = hit[0]
                val = y[j - 1] + (lv - p[j - 1]) * (y[j] - y[j - 1]) / (p[j] - p[j - 1])
                txt = f'{val:.1f}'
            row[f'years_{int(lv * 100)}pct'] = val
            row[f'years_{int(lv * 100)}pct_txt'] = txt
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    C.log(f'gate simulation: {NPATH} KOSPI-bootstrap paths, {NPATH_SIGN} sign-flip paths, {NPATH_IID} iid paths, '
          f'R={RBOOT}')
    src = load_source()
    res = simulate(NPATH, 'kospi', src=src)
    df = summarise(res, 'kospi_cbb126')
    res_sign = simulate(NPATH_SIGN, 'kospi_sign', src=src)
    df = pd.concat([df, summarise(res_sign, 'kospi_cbb126_signflip')], ignore_index=True)
    res_iid = simulate(NPATH_IID, 'iid', src=src)
    df = pd.concat([df, summarise(res_iid, 'iid_normal')], ignore_index=True)
    # source diagnostics
    n = len(src)
    cs = np.concatenate([[0.0], np.cumsum(src)])
    diag = [dict(item='source_obs', value=n), dict(item='source_ann_vol', value=float(src.std() * math.sqrt(C.ANN))),
            dict(item='source_skew', value=float(skew(src))), dict(item='source_kurtosis', value=float(kurtosis(src, fisher=False)))]
    for q in (5, 21, 63, 126, 252):
        ov = cs[q:] - cs[:-q]
        diag.append(dict(item=f'variance_ratio_{q}', value=float(ov.var() / (q * src.var()))))
    C.save_csv(pd.DataFrame(diag), 'r2_idx_gate_source_diagnostics.csv')
    an = analytic(df)
    df = df.merge(an, on=['years', 'true_sr', 'rho', 'n_trials', 'step'], how='left')
    C.save_csv(df, 'r2_idx_gate_sim.csv')
    pw = years_for_power(df)
    C.save_csv(pw, 'r2_idx_gate_power_years.csv')
    # supplementary: distribution of the step-5 p at SR = benchmark (no relative edge) as a calibration check
    im = MUS.index(BSR)
    cal = []
    for gname, rr in (('kospi_cbb126', res), ('kospi_cbb126_signflip', res_sign), ('iid_normal', res_iid)):
        for iy, Y in enumerate(YEARS):
            for ir, rho in enumerate(RHOS):
                p = rr['p5'][:, iy, im, ir]
                cal.append(dict(innovations=gname, years=Y, rho=rho, share_p_le_0p10=float((p <= 0.10).mean()),
                                share_p_le_0p05=float((p <= 0.05).mean()), mean_p=float(p.mean()), n_paths=len(p)))
    C.save_csv(pd.DataFrame(cal), 'r2_idx_gate_step5_calibration.csv')
    # chart (c)
    k = df[df.innovations == 'kospi_cbb126']
    series = {}
    for step, sel in (('step2_bootstrap', dict()), ('step8_years', dict()), ('step3_dsr_N9', dict(n_trials=9)),
                      ('step5_rho0.5', dict(rho=0.5)), ('step5_rho0.9', dict(rho=0.9)),
                      ('joint_N1_rho0.5', dict(n_trials=1, rho=0.5)), ('joint_N9_rho0.9', dict(n_trials=9, rho=0.9))):
        base = step.split('_N')[0].split('_rho')[0]
        base = {'step2_bootstrap': 'step2_bootstrap', 'step8_years': 'step8_years', 'step3_dsr': 'step3_dsr',
                'step5': 'step5_benchmark', 'joint': 'joint_2_3_5_8'}[base]
        g = k[k.step == base]
        for col, v in sel.items():
            g = g[np.isclose(g[col], v)]
        series[step] = {f'SR {sr:g}': dict(years=gg.sort_values('years')['years'].tolist(),
                                           pass_rate=np.round(gg.sort_values('years')['pass_rate'].values, 4),
                                           mc_se=np.round(gg.sort_values('years')['mc_se'].values, 4))
                        for sr, gg in g.groupby('true_sr') if sr in SR_GRID}
    C.save_json(dict(title='QUANTGEN gate pass rates vs sample length, by true Sharpe (false pass at SR 0 highlighted)',
                     highlight='SR 0', notes=[
                         'Strategy vol 15%; innovations = circular block bootstrap (126 sessions) of de-meaned rebuilt '
                         'KOSPI returns; benchmark Sharpe 0.4.',
                         f'{NPATH} paths per point, {RBOOT} bootstrap resamples per path and test; seeds fixed.',
                         'step5 compares the strategy Sharpe with a 0.4-Sharpe benchmark: at SR 0 it is a '
                         'false pass only in an absolute sense; at SR 0.4 (no edge vs the benchmark) see '
                         'r2_idx_gate_step5_calibration.csv.'],
                     series=series), 'r2_idx_chart_c_gate_pass_rates.json')
    C.log('done')


if __name__ == '__main__':
    main()
