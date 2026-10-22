"""kr_common.py -- shared constants and helpers for the Korea technical-signal data lab (QUANTGEN).

All kr_*.py scripts import this module. Conventions used everywhere:
  * Decide at the close of day t with data through t; returns are earned from t+1.
  * Daily price return r = ChangesRatio/100 (KRX base-price change, split-adjusted, dividends excluded).
  * Wide matrices are (T dates x N codes) float32/bool .npy files in CACHE, opened with mmap.
"""
import os, re, json, math, hashlib
import numpy as np
import pandas as pd

ROOT = '/home/claude/datalab'
RAW = '/home/claude/data_raw/marcap/data'
CACHE = f'{ROOT}/kr/cache'
RES = f'{ROOT}/kr/results'
CHARTS = f'{ROOT}/kr/charts'
SCRIPTS = f'{ROOT}/scripts'
for _d in (CACHE, RES, CHARTS):
    os.makedirs(_d, exist_ok=True)

SEED = 20261002
YEARS = range(1995, 2027)
# KOSDAQ GLOBAL is a premium segment of KOSDAQ (since 2022-11-21): same market for our purposes.
MARKET_CODE = {'KOSPI': 1, 'KOSDAQ': 2, 'KOSDAQ GLOBAL': 2}
LIMIT_CHANGE_DATE = np.datetime64('2015-06-15')   # daily price limit widened from +-15% to +-30%
COST = {'gross': 0.0, 'net35': 0.0035, 'net70': 0.0070}   # KRX stock, per side, every unit traded
INDEX_COST = {'gross': 0.0, 'net3': 0.0003, 'net6': 0.0006}  # KRX ETF implementation of index timing
LIQ_WINDOW = 30            # trading days before a delisting treated as the liquidation-trading window
SUBPERIODS = [('full', '1990-01-01', '2026-12-31'),
              ('1996-2005', '1996-01-01', '2005-12-31'),
              ('2006-2015', '2006-01-01', '2015-12-31'),
              ('2016-2026', '2016-01-01', '2026-12-31')]
YEARS_REPORT = list(range(2015, 2027))

# Event windows: (label, start_close, end_close). Returns are compounded over trading days d with
# start_close < d <= end_close, i.e. from the close of start_close to the close of end_close (the
# last trading day on or before each date is used). Windows that begin at a market peak (2020-02-17,
# 2024-07-11, 2026-06-22) start at that day's close; windows given as 'from day X' after a trough or
# a previous window start at the previous close so that consecutive windows chain without gaps.
# Month-specified windows start at the last close of the previous month.
EVENT_WINDOWS = [
    ('1997-11..1998-06 Asian crisis', '1997-10-31', '1998-06-30'),
    ('2000-03..2000-12 dot-com bust', '2000-02-29', '2000-12-31'),
    ('2008-06..2009-03 GFC', '2008-05-31', '2009-03-31'),
    ('2020-02-17..2020-03-19 COVID crash', '2020-02-17', '2020-03-19'),
    ('2020-03-20..2020-06-30 COVID rebound', '2020-03-19', '2020-06-30'),
    ('2022 full year', '2021-12-31', '2022-12-31'),
    ('2024-07-11..2024-08-05 Aug-2024 crash', '2024-07-11', '2024-08-05'),
    ('2026-01-02..2026-06-22 melt-up', '2025-12-31', '2026-06-22'),
    ('2026-06-22..2026-07-30 crash', '2026-06-22', '2026-07-30'),
    ('2026-07-31..2026-09-29 after crash', '2026-07-30', '2026-09-29'),
]

# ----------------------------------------------------------------------------------------------
# Security-type exclusions (name based, point in time).  The task lists 스팩, 리츠/REIT, 인프라,
# 선박투자, ETN.  Literal substring matching gives false positives (메리츠 = Meritz financial group,
# 블리츠웨이 = an entertainment company, 두산인프라코어/인프라웨어/바이오인프라 = operating companies)
# and misses the actual fund vehicles (ship-investment funds are named e.g. '동북아12호', '바다로3호';
# 1999-2004 listed mutual funds '박현주1호', '...MF').  The patterns below implement the intent.
# ----------------------------------------------------------------------------------------------
_RX_SPAC = re.compile(r'스팩|SPAC|기업인수목적')
_RX_REIT = re.compile(r'리츠|코크렙|REIT|리얼티\d*$|^교보메리츠|^유레스메리츠|맥쿼리센트럴')
_RX_INFRA = re.compile(r'맥쿼리인프라|발해인프라|인프라펀드|인프라투융자')
_RX_FUND = re.compile(r'선박투자|\d+호|[가-힣]{2,}(?:일|이|삼|사|오|육|칠|팔|구|십|십오)호(?:-?MF)?$|-?MF$|펀드|뮤추얼'
                      r'|경매|베트남(?:개발)?\d$|유전\d|유전$')
_RX_OTHER = re.compile(r'ETN|KDR')
_NOT_REIT = ('인터리츠',)   # 1996-2007 KOSDAQ operating company (pre-dates the 2001 REIT law)


def classify_name(name: str) -> str:
    """Return '' for an operating company, else SPAC / REIT / INFRA_FUND / FUND / DR_ETN."""
    n = re.sub(r'\s+', '', str(name))
    if _RX_SPAC.search(n):
        return 'SPAC'
    nn = n.replace('메리츠', '#').replace('블리츠', '#')
    if n not in _NOT_REIT and (_RX_REIT.search(nn) or _RX_REIT.search(n) and n.startswith(('교보메리츠', '유레스메리츠'))):
        return 'REIT'
    if _RX_INFRA.search(n):
        return 'INFRA_FUND'
    if _RX_FUND.search(n):
        return 'FUND'
    if _RX_OTHER.search(n):
        return 'DR_ETN'
    return ''


# ----------------------------------------------------------------------------------------------
def open_mat(name, mode='r', cache=None):
    return np.load(f'{cache or CACHE}/{name}.npy', mmap_mode=mode)


def load_meta(cache=None):
    dates = np.load(f'{cache or CACHE}/dates.npy')
    codes = np.load(f'{cache or CACHE}/codes.npy', allow_pickle=False)
    return pd.DatetimeIndex(dates), codes


def month_end_idx(dates: pd.DatetimeIndex) -> np.ndarray:
    s = pd.Series(np.arange(len(dates)), index=dates)
    return s.groupby([dates.year, dates.month]).max().values.astype(np.int64)


def week_end_idx(dates: pd.DatetimeIndex) -> np.ndarray:
    """Last trading day of each ISO week on or before Friday (Saturday sessions existed until 1998-12)."""
    wd = dates.weekday
    s = pd.Series(np.arange(len(dates)), index=dates)[wd <= 4]
    iso = s.index.isocalendar()
    return s.groupby([iso.year.values, iso.week.values]).max().sort_values().values.astype(np.int64)


def nw_tstat(x, lags):
    """Newey-West (Bartlett) t-statistic of the mean of x."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < lags + 3:
        return np.nan
    e = x - x.mean()
    v = e @ e / n
    for l in range(1, lags + 1):
        w = 1 - l / (lags + 1)
        v += 2 * w * (e[l:] @ e[:-l]) / n
    if v <= 0:
        return np.nan
    return x.mean() / math.sqrt(v / n)


def max_drawdown(daily_ret):
    r = np.asarray(daily_ret, float)
    r = np.where(np.isfinite(r), r, 0.0)
    if len(r) == 0:
        return np.nan
    w = np.cumprod(1 + r)
    w = np.concatenate([[1.0], w])
    peak = np.maximum.accumulate(w)
    return float((w / peak - 1).min())


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def write_json(obj, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, separators=(',', ':'), allow_nan=False,
                  default=lambda o: None)


def clean_json(x):
    """Recursively replace NaN/inf by None and numpy scalars by Python scalars."""
    if isinstance(x, dict):
        return {k: clean_json(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean_json(v) for v in x]
    if isinstance(x, (np.floating, float)):
        v = float(x)
        return v if math.isfinite(v) else None
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, np.ndarray):
        return clean_json(x.tolist())
    return x
