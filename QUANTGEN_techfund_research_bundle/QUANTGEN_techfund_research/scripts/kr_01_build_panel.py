"""kr_01_build_panel.py -- build the wide (date x code) panel from the marcap parquet files.

Input : /home/claude/data_raw/marcap/data/marcap-YYYY.parquet (1995-2026)
Output: /home/claude/datalab/kr/cache/*.npy (memory-mapped matrices), cache/codes_names.csv,
        results/kr_return_flags_events.csv, results/kr_return_flags_summary.csv

Rows kept: Market in {KOSPI, KOSDAQ, KOSDAQ GLOBAL}; code last character '0' (common shares; preferred
and new-share lines have a non-zero last character); Close > 0 (Close = 0 rows are placeholders).
KONEX rows are dropped, so a KONEX->KOSDAQ transfer starts a new listing segment.

Daily return R (float32, NaN = missing), built from r = ChangesRatio/100:
  1. NaN on the first day of each listing segment: new listing, relisting after a gap, first day after a
     KONEX->KOSDAQ transfer (KONEX rows are not in the panel), and a KOSPI<->KOSDAQ transfer day when KRX
     reset the base price (|r - (Close/prevClose-1)| > 0.5%, the 1996-98 transfers); transfers that continue
     the price series (most transfers since 2000) are ordinary days. KOSDAQ<->KOSDAQ GLOBAL = same market.
  2. If |r| > daily limit (15% before 2015-06-15, 30% from then; tolerance 1e-9):
       a. corporate-action day (shares outstanding changed by >0.1%, or KRX adjusted the base price, i.e.
          |r - (Close/prevClose-1)| > 0.5%): keep r if it agrees within 2 pp with the market-cap ratio
          return Marcap_t/Marcap_{t-1}-1 (the share-count change explains the move), else NaN;
       b. no corporate action, inside the last 30 trading days of a listing segment that ends in a
          delisting (KRX liquidation trading [정리매매] has no price limit): keep r (a real, tradable loss;
          setting it to missing would bias long portfolios upward), provided prevClose > 1 KRW (placeholder);
       b'. no corporate action on the day, first traded day after a trading halt of >= 5 sessions (re-opening
          auction / start of liquidation trading later suspended by court injunction, e.g. 2018-09-28): keep r
          (uses only past information), provided prevClose > 1 KRW. Whether the share count changed during the
          halt is reported (events column shares_changed_in_halt) but not used: ChangesRatio already carries
          KRX base-price adjustments such as reverse splits;
       c. otherwise NaN (pre-2000 data errors, e.g. repeated +16.7% prints on zero-volume days).
  A 'strict' copy (ret_strict, cumlog_strict, valid_strict) applies the task's literal rule instead:
  every beyond-limit return without a consistent corporate action is set to missing (a, c only).
  Missing returns are skipped in signals and treated as 0 for a stock still held in a portfolio.
VALID = R finite and Volume > 0 (halt days with zero volume do not count as valid return days).
CL    = cumulative log return (float64), NaN returns contribute 0: the split-adjusted log price.
"""
import os, sys, time
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
sys.path.insert(0, '/home/claude/datalab/scripts')
from kr_common import (RAW, CACHE, RES, YEARS, MARKET_CODE, LIMIT_CHANGE_DATE, LIQ_WINDOW, classify_name)

RESUME_MIN_HALT = 5     # a halt of >= 5 sessions ends with a re-opening auction (no binding daily limit)

COLS = ['Date', 'Code', 'Name', 'Market', 'High', 'Close', 'Volume', 'Amount', 'Marcap', 'Stocks', 'ChangesRatio']
CLS_CODE = {'': 0, 'SPAC': 1, 'REIT': 2, 'INFRA_FUND': 3, 'FUND': 4, 'DR_ETN': 5}


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


def read_year(y, cols, end_date=None):
    df = pq.read_table(f'{RAW}/marcap-{y}.parquet', columns=cols).to_pandas()
    if end_date is not None:
        df = df[df['Date'] <= pd.Timestamp(end_date)]
    df['Code'] = df['Code'].str.zfill(6)
    keep = df['Market'].isin(list(MARKET_CODE)) & (df['Code'].str[-1] == '0') & (df['Close'] > 0)
    return df, keep


def main(end_date=None, cache=CACHE, res=RES, write_reports=True):
    """end_date/cache/res are used by the look-ahead truncation test in kr_06_validation.py."""
    CACHE, RES = cache, res
    t0 = time.time()
    years = [y for y in YEARS if end_date is None or y <= pd.Timestamp(end_date).year]
    # ---------------- pass 1: calendar and code list ----------------
    all_dates, code_set = [], set()
    for y in years:
        df, keep = read_year(y, ['Date', 'Code', 'Market', 'Close'], end_date)
        all_dates.append(df['Date'].values.astype('datetime64[D]'))
        code_set.update(df.loc[keep, 'Code'].unique())
    dates = np.unique(np.concatenate(all_dates))
    codes = np.array(sorted(code_set))
    T, N = len(dates), len(codes)
    np.save(f'{CACHE}/dates.npy', dates)
    np.save(f'{CACHE}/codes.npy', codes)
    cpos = pd.Series(np.arange(N), index=codes)
    log(f'calendar {T} days {dates[0]}..{dates[-1]}, {N} common-share codes')

    def mm(name, dtype, fill):
        a = np.lib.format.open_memmap(f'{CACHE}/{name}.npy', mode='w+', dtype=dtype, shape=(T, N))
        a[:] = fill
        return a

    E = mm('exists', bool, False)
    CLOSE = mm('close', np.float32, np.nan)
    HIGH = mm('high', np.float32, np.nan)
    AMT = mm('amount', np.float32, np.nan)
    MCAP = mm('marcap', np.float32, np.nan)
    TRADED = mm('traded', bool, False)
    MKT = mm('mkt', np.int8, 0)
    NCLS = mm('namecls', np.int8, 0)
    CR = mm('_tmp_changesratio', np.float32, np.nan)      # ChangesRatio/100 (temporary file)
    STK = mm('_tmp_stocks', np.float32, np.nan)           # shares outstanding (temporary; float32 suffices for
                                                          # the 0.1% share-change test)

    cls_cache, name_rows, profile_rows = {}, [], []
    for y in years:
        df, keep = read_year(y, COLS, end_date)
        df = df[keep]
        ti = np.searchsorted(dates, df['Date'].values.astype('datetime64[D]'))
        ci = cpos.reindex(df['Code'].values).values
        assert not np.isnan(ci).any()
        ci = ci.astype(np.int64)
        close = df['Close'].values.astype(np.float64)
        high = df['High'].values.astype(np.float64)
        high = np.where(high > 0, high, close)          # zero-volume days carry High = 0
        E[ti, ci] = True
        CLOSE[ti, ci] = close
        HIGH[ti, ci] = high
        AMT[ti, ci] = df['Amount'].values
        MCAP[ti, ci] = df['Marcap'].values
        TRADED[ti, ci] = df['Volume'].values > 0
        MKT[ti, ci] = df['Market'].map(MARKET_CODE).values.astype(np.int8)
        for n in df['Name'].unique():
            if n not in cls_cache:
                cls_cache[n] = CLS_CODE[classify_name(n)]
        NCLS[ti, ci] = df['Name'].map(cls_cache).values.astype(np.int8)
        CR[ti, ci] = df['ChangesRatio'].values / 100.0
        STK[ti, ci] = df['Stocks'].values
        g = df.groupby(['Code', 'Name', 'Market'])['Date'].agg(['min', 'max', 'size']).reset_index()
        name_rows.append(g)
        prof = df.groupby('Market').agg(rows=('Code', 'size'), n_codes=('Code', 'nunique'),
                                        zero_volume_share=('Volume', lambda v: float((v == 0).mean())),
                                        first_date=('Date', 'min'), last_date=('Date', 'max')).reset_index()
        prof.insert(0, 'year', y)
        profile_rows.append(prof)
        log(f'{y}: {len(df):,} rows')
    for a in (E, CLOSE, HIGH, AMT, MCAP, TRADED, MKT, NCLS, CR, STK):
        a.flush()
    del E, CLOSE, HIGH, AMT, MCAP, TRADED, MKT, NCLS, CR, STK      # unmap: keeps resident memory low

    nm = pd.concat(name_rows).groupby(['Code', 'Name', 'Market']).agg(
        first=('min', 'min'), last=('max', 'max'), n=('size', 'sum')).reset_index()
    nm['cls'] = nm['Name'].map(lambda n: classify_name(n))
    if write_reports:
        nm.sort_values(['Code', 'first']).to_csv(f'{CACHE}/codes_names.csv', index=False)
        pd.concat(profile_rows).to_csv(f'{RES}/kr_data_profile.csv', index=False, float_format='%.6g')

    # ---------------- derived flags and cleaned returns ----------------
    lim = np.where(dates < LIMIT_CHANGE_DATE, 0.15, 0.30).astype(np.float32)[:, None]
    OUT = {'ret': (np.float32, np.nan), 'cumlog': (np.float64, np.nan), 'valid': (bool, False),
           # 'strict' variant for the sensitivity run: liquidation/resumption beyond-limit returns also missing
           'ret_strict': (np.float32, np.nan), 'cumlog_strict': (np.float64, np.nan), 'valid_strict': (bool, False),
           'first': (bool, False),
           'beyond_nonca': (bool, False)}     # beyond-limit day without corporate action (observable at t)
    for k, (dt, fill) in OUT.items():
        a = mm(k, dt, fill); a.flush(); del a
    rd = lambda n: np.load(f'{CACHE}/{n}.npy', mmap_mode='r')
    events = []
    counts = dict(rows=0, first=0, beyond=0, keep_ca=0, drop_ca=0, keep_liq=0, keep_resume=0, drop_other=0,
                  drop_placeholder=0)
    CH = 300
    for c0 in range(0, N, CH):
        c1 = min(N, c0 + CH)
        e = np.array(rd('exists')[:, c0:c1])
        mk = np.array(rd('mkt')[:, c0:c1])
        cl = np.array(rd('close')[:, c0:c1]).astype(np.float64)
        mc = np.array(rd('marcap')[:, c0:c1]).astype(np.float64)
        r = np.array(rd('_tmp_changesratio')[:, c0:c1]).astype(np.float64)
        st = np.array(rd('_tmp_stocks')[:, c0:c1]).astype(np.float64)
        TRADED_c = np.array(rd('traded')[:, c0:c1])
        ep = np.zeros_like(e); ep[1:] = e[:-1]
        mkp = np.zeros_like(mk); mkp[1:] = mk[:-1]
        clp = np.full_like(cl, np.nan); clp[1:] = cl[:-1]
        mcp = np.full_like(mc, np.nan); mcp[1:] = mc[:-1]
        stp = np.full_like(st, np.nan); stp[1:] = st[:-1]
        with np.errstate(invalid='ignore', divide='ignore'):
            raw = cl / clp - 1
            rmc = mc / mcp - 1
        # A KOSPI<->KOSDAQ transfer day is a relisting (first day) only if KRX reset the base price
        # (ChangesRatio disagrees with the close-to-close change); modern transfers continue the price series.
        reset = ~(np.abs(r - raw) <= 0.005)
        first = e & (~ep | ((mk != mkp) & reset))
        cont = e & ~first                              # continuing day with a usable previous row
        with np.errstate(invalid='ignore', divide='ignore'):
            shr = cont & (np.abs(st / stp - 1) > 0.001)
            badj = cont & (np.abs(r - raw) > 0.005)
        ca = shr | badj
        beyond = cont & (np.abs(r) > lim + 1e-9)
        # days to the end of the current listing segment (0 = last day); segments that run to the
        # last calendar date are not delistings -> large value.
        BIG = 10**6
        dte = np.full(e.shape, BIG, dtype=np.int32)     # last calendar date: alive -> BIG
        for t in range(T - 2, -1, -1):
            nxt = dte[t + 1].astype(np.int64)
            cur = np.where(e[t], np.where(e[t + 1], np.minimum(nxt + 1, BIG), 0), BIG)
            dte[t] = cur
        liq = dte <= (LIQ_WINDOW - 1)
        # trading-halt run length before t (consecutive listed zero-volume days ending at t-1) and whether
        # the share count changed during that halt (then the resumption price is not comparable)
        trc = TRADED_c
        halt = np.zeros(e.shape, dtype=np.int32)
        shalt = np.zeros(e.shape, dtype=bool)
        run = np.zeros(e.shape[1], dtype=np.int32)
        srun = np.zeros(e.shape[1], dtype=bool)
        for t in range(1, T):
            h = e[t - 1] & ~trc[t - 1]
            run = np.where(h, run + 1, 0)
            srun = np.where(h, srun | shr[t - 1], False)
            halt[t] = run
            shalt[t] = srun
        resume = trc & (halt >= RESUME_MIN_HALT)       # shalt is reported, not used (ChangesRatio already
                                                         # carries KRX base-price adjustments, e.g. reverse splits)
        keep_ca = beyond & ca & (np.abs(r - rmc) <= 0.02)
        drop_ca = beyond & ca & ~keep_ca
        placeholder = cont & (clp <= 1)
        keep_liq = beyond & ~ca & liq & ~placeholder
        keep_res = beyond & ~ca & ~liq & resume & ~placeholder
        drop_other = beyond & ~ca & ~keep_liq & ~keep_res
        good = cont & ~drop_ca & ~drop_other & ~placeholder
        rr = np.where(good, r, np.nan)
        assert np.nanmin(rr) > -1.0, 'return <= -100% survived cleaning'
        tr = TRADED_c
        rs = np.where(good & ~keep_liq & ~keep_res, r, np.nan)
        vals = {'ret': rr.astype(np.float32), 'valid': np.isfinite(rr) & tr, 'first': first,
                'beyond_nonca': beyond & ~ca, 'cumlog': np.cumsum(np.log1p(np.nan_to_num(rr, nan=0.0)), axis=0),
                'ret_strict': rs.astype(np.float32), 'valid_strict': np.isfinite(rs) & tr,
                'cumlog_strict': np.cumsum(np.log1p(np.nan_to_num(rs, nan=0.0)), axis=0)}
        for k, v in vals.items():
            a = np.load(f'{CACHE}/{k}.npy', mmap_mode='r+')
            a[:, c0:c1] = v
            a.flush(); del a
        del vals
        counts['rows'] += int(e.sum()); counts['first'] += int(first.sum()); counts['beyond'] += int(beyond.sum())
        counts['keep_ca'] += int(keep_ca.sum()); counts['drop_ca'] += int(drop_ca.sum())
        counts['keep_liq'] += int(keep_liq.sum()); counts['drop_other'] += int(drop_other.sum())
        counts['keep_resume'] += int(keep_res.sum())
        counts['drop_placeholder'] += int((placeholder & ~beyond).sum())
        for lab, m in (('keep_ca', keep_ca), ('drop_ca', drop_ca), ('keep_liq', keep_liq), ('keep_resume', keep_res),
                       ('drop_other', drop_other), ('drop_placeholder', placeholder & ~beyond)):
            ti, cj = np.nonzero(m)
            for a, b in zip(ti, cj):
                events.append((str(dates[a]), codes[c0 + b], lab, float(r[a, b]), float(raw[a, b]),
                               float(rmc[a, b]), float(clp[a, b]), float(cl[a, b]), int(dte[a, b]) if dte[a, b] < 10**6 else -1,
                               bool(tr[a, b]), int(mk[a, b]), int(halt[a, b]), bool(shalt[a, b])))
        log(f'derived cols {c0}-{c1}')
    for k in ('_tmp_changesratio', '_tmp_stocks'):
        os.remove(f'{CACHE}/{k}.npy')

    ev = pd.DataFrame(events, columns=['date', 'code', 'category', 'r_changesratio', 'r_close_close', 'r_marcap',
                                       'prev_close', 'close', 'days_to_delisting', 'traded', 'market',
                                       'halt_days_before', 'shares_changed_in_halt'])
    nm_last = nm.sort_values('last').groupby('Code')['Name'].last()
    ev['name'] = ev['code'].map(nm_last)
    ev['year'] = ev['date'].str[:4].astype(int)
    if write_reports:
        ev.to_csv(f'{RES}/kr_return_flags_events.csv', index=False)
        summ = ev.groupby(['year', 'category']).size().unstack(fill_value=0)
        summ.to_csv(f'{RES}/kr_return_flags_summary.csv')
        pd.Series(counts).to_csv(f'{RES}/kr_return_flags_totals.csv', header=['count'])
    log('counts', counts)
    log(f'done in {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
