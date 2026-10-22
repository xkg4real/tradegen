# council_pages — digest of the two Quant Council HTML pages

Sources (all local, read completely via python extraction; line numbers below are HTML source lines):
- QC = `C:/Users/whydi/OneDrive/Desktop/QUANTGEN/QUANTGEN_Quant_Council_2026-10-03/pages/QUANTGEN_Quant_Council.html` — 363,667 bytes, 811 lines; `<style>` L12–L207 (15,405 chars); body L208–L487; `<script type="application/json" id="qg-data">` L488 (one 292,572-char line); app script L489–L811 (34,132 chars).
- ML = `C:/Users/whydi/OneDrive/Desktop/QUANTGEN/QUANTGEN_Quant_Council_2026-10-03/pages/QUANTGEN_Macro_Neural_Link.html` — 373,902 bytes, 767 lines; `<style>` L12–L188 (14,092 chars); body L189–L459; JSON L460 (286,049-char line); app script L461–L767 (34,726 chars).
- App comparison: `ui/macro_page.py` (233 lines), `core/theme.py` (43 lines), plus `ui/components.py`, `ui/strategy_lab_page.py`, `ui/runs_page.py`, `tests/flet_api_guard.py`, `main.py` (grepped only).
- Council README (`QUANTGEN_Quant_Council_2026-10-03/README.md` L13–14): "pages/ — offline copies of the two visual pages … open in any browser; data are embedded, and fonts fall back to system fonts when offline."

Re-extraction one-liner (reproducible, no deps):
```python
import re, json, pathlib
s = pathlib.Path(p).read_text(encoding="utf-8")
D = json.loads(re.search(r'<script type="application/json" id="qg-data">(.*?)</script>', s, re.S).group(1))
```

---

## A. Each page

### A.1 QUANTGEN_Quant_Council.html (`<title>` "QUANTGEN Quant Council", L8)

Purpose: narrative + chart record of the 2–3 Oct 2026 Quant Council (seven simulated QF auditors → cross-examination → two data labs → three chairs → adversarial spec review → competitive brief → build plan). Footer L486: "built 3 Oct 2026 from the council's files and local data · all panel members are simulated, fictional composites · not investment advice; QUANTGEN is a read-only research desk with no order path."

Section outline (nav `.brand` "QUANTGEN · COUNCIL", links L211–218):

| # | `section id` | Line | h2 | Figures / hosts |
|---|---|---|---|---|
| hero | `header.hero` | L228–242 | h1 "The quants rebuilt the gate, not the macro" (L229) | `.stats` 4 tiles: **180** audit items · **361** ledger items · **34** modules (16 changed, 14 new, 2 demoted, 2 retired) · **4 / 4** reviewers AGREE; `.bottom` 3 cards (h3 L238–240) |
| 1 | `#audit` | L245 | "Seven quants filed 180 audit items, and most of them hit the measuring tools" (L249) | `#c-audit` stacked bars (L255) + `#lg-audit`; `#t-members` table (L261) |
| 2 | `#debate` | L268 | "The other panels upheld most findings and broke two" (L272) | `#c-xexam` stacked bars (L278) + `#lg-xexam`; `.col` "What the data labs settled" (4 bullets) |
| 2b | `#evidence` | L295 | "Korea protects in crashes, but too narrowly to pass once every variant is counted" (L299) | `#c-kvt` + `#c-kdd` line charts (L305–306, log NAV + drawdown), `details[data-table=kvt]` (L309); `#c-kstart` date bars (L313); `#c-ustart` grouped date bars (L319); `#c-mcs` heat-map table (L325); `#c-trend` + `#c-tdd` (L330–331); `#c-switch` bars (L337) |
| 3 | `#resolutions` | L344 | "Twelve resolutions settle the gate once, blind, before any card runs" (L348) | `#t-res` table (L351, 12 rows); `#c-ledger` bars (L355); `.col` "Red lines that bound the wording" (L359–364) |
| 4 | `#spec` | L370 | "Four reviewers attacked spec v2.0 until each of them agreed" (L374) | `#c-aspec` stacked bars (L380); `.col` "What the review changed" (L385–392, 5 bullets) |
| 5 | `#gap` | L398 | "Against public institutional practice, v2.0 closes most gaps in measurement" (L402) | `#c-gap` dumbbell bars (L408) + `#lg-gap`; `.col` "Where QUANTGEN stands" SWOT (L413–419) |
| 6 | `#build` | L425 | "129 tasks from scaffolding to forward records, with the gate frozen in M7" (L429) | `#c-tasks` bars (L435); `#t-owner` table (L440); `#files` cards (L443) |
| 7 | `#sources` | L447 | "Where the numbers come from" | 4 h4 groups (L451, 459, 466, 474): internal, validation, risk/vol/execution, trend/regimes/factors |

Interactive elements: theme group `#th-auto/#th-light/#th-dark` (`button[aria-pressed]`, L220–222; sets `data-theme` on `<html>`, persists `localStorage['qgqc-theme']` L498/L805, then `redrawAll()`); 8 in-page anchor links; 1 `<details class="dt" data-table="kvt">` lazy table (80 sampled rows, built on first `toggle`, L624–627); SVG hover crosshair + tooltip (`pointermove/pointerdown/pointerleave` on a transparent hit rect, L591–604 in `lineChart`, L705–707 in `dateBars`); stacked-bar segments carry `title` tooltips and `role="img" aria-label` (L639–641); `ResizeObserver` → `requestAnimationFrame(draw)` on every chart host (L607, L709). 13 external source `<a>` (L461–479). No forms, inputs, fetch, canvas, images, iframes, cookies. `addEventListener` ×8, inline `on*=` ×0.

Embedded dataset `#qg-data` (L488) — 10 top-level keys:

| key | shape | sample |
|---|---|---|
| `kvt_mdd` | `[2 × float]` | `[-0.647, -0.453]` (B&H vs VT max drawdown, daily) |
| `kvt` | dict of 5 series, each `1538 × [date, float]`, 1997-04-04 → 2026-10-02 (weekly-ish sampling of daily) | `bh_nav` `["1997-04-04", 1.015]`…`["2026-10-02", 10.34]`; `vt_nav_net_3bp` last 6.716; `static_S_nav` last 8.368; `bh_drawdown` last −0.232; `vt_drawdown` last −0.057 |
| `kstart` | `72 × {start, d, p, v}` monthly starts 1997-02-03 → 2003-01-02 | `{"start":"1997-02-03","d":12.69,"p":0.058,"v":"PASS"}`; v ∈ {`PASS` ×71, `INSUFFICIENT DATA (inconclusive)` ×1 (1998-10-01, d 4.41, p 0.103)}; d range 3.7–12.69 pp |
| `ustart` | dict: `"US via KIS 50bp"` and `"futures 5bp"`, each `44 × {start, d, v}` quarterly 1990-02-01 → 2000-11-01 | futures: `{"start":"1990-02-01","d":3.65,"v":"PASS"}`; counts PASS 11 / REVISE 9 / REJECT 24 (REVISE run 1992-08…1994-08, REJECT run 1994-11…2000-08, PASS 2000-11 d 6.53); KIS 50bp: REJECT 43, `INSUFFICIENT DATA (inconclusive)` 1 (2000-11-01 d 3.36); d range −1.43…+0.18 then 3.36 |
| `mcs` | `42 × {mk, h, est, rel, in90, mse_in90}`; mk ∈ {KOSPI, US}, h ∈ {1,5,21}, est ∈ {SMA20, EWMA94, EWMA97, GARCH_t, GJR_t, LHAR_RNG, COMB} | `{"mk":"KOSPI","h":1,"est":"SMA20","rel":1.0,"in90":false,"mse_in90":false}`; full grid in §D |
| `trend` | dict of 5 monthly series `1190 × ["YYYY-MM", float]` 1927-07 → 2026-08 | `wealth_buy_and_hold` last 16414.3; `wealth_sma10_cashRF_5bp` last 15864.1; `wealth_static_S_cashRF` last 8334.79; `drawdown_buy_and_hold`, `drawdown_sma10_cashRF_5bp` |
| `switches` | `9 × {mk, det, sw, src}` | `{"mk":"US","det":"Markov switching (unpenalised)","sw":16.7,"src":"DLB"}` (all 9 in §D) |
| `ledger_classes` | dict 9 | `VALID-BUILD 140, INFO 95, VALID-ERRATA 67, CONFIRMED 34, CONTEXT-ONLY 9, VALID-SHADOW 7, INVALID 3, OWNER-DECISION 3, CONTESTED 3` |
| `ledger_n` | int | `361` |
| `modules` | `34 × {id, name, change, cls, pri, ms}` | `{"id":"R-01","name":"Point-in-time discipline: value_status, session_date, retrieved_at_utc, provisional-row guard, post-close fixtures","change":"CHANGED","cls":"INVARIANT","pri":"P0","ms":"M1"}`; change ∈ {CHANGED 16, NEW 14, DEMOTED 2, RETIRED 2}; cls ∈ {GOVERNANCE 11, INVARIANT 7, CARD-P 6, CONVENTION 5, CARD-O 3, CONTEXT 2}; pri ∈ {P0 16, P1 14, P2 4}; ms values include the literal `"M7 (frozen before the first card run)"` (R-21, R-22, R-23, R-34) |

Hard-coded data in the script (not in the JSON; see §D): `MEMBERS` (L649–657), cross-exam rows (L666–670), `EST` estimator labels (L722), `RES` 12 resolutions (L746–758), ledger `ORDER` colours (L765), `AK` adversarial rounds (L773–777), capability `A` (L783), milestone `MS` (L791), `OWN` D1–D6 (L797), `FILES` (L801), `VCOL`/`VER` colour maps (L630, L686).

External dependencies: only Google Fonts — `<link rel="preconnect" href="https://fonts.googleapis.com">`, `…fonts.gstatic.com crossorigin`, stylesheet `https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@100..125,500..800&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&display=swap` (L9–11). No JS CDN, no images, no iframes. 13 outbound `<a href>` to papers (L461–479).

Offline behaviour: fully functional — data inline, SVG built with `document.createElementNS` (L504), charts redraw on resize; the font stylesheet request fails silently and `display=swap` + the CSS stacks (`"Archivo","Helvetica Neue",Arial,sans-serif` / `"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif` / `"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace`, L20–22) fall back; `font-stretch` on Archivo (112–125%) is lost on fallback. `localStorage` is wrapped in `try{}catch{}` (L498, L805) so `file://` restrictions never break the page. `color-scheme` follows `prefers-color-scheme` unless `data-theme` is set (L26–43).

### A.2 QUANTGEN_Macro_Neural_Link.html (`<title>` "QUANTGEN Macro Neural Link", L8)

Purpose: the 2 Oct 2026 macro-research page (professors × executives debate → 139 claims → 60 propositions → what survived data), with a 3 Oct stamp "Updated 2026-10-03 after the Quant Council" (`.stamp.flat.v-insuff`, L210). Footer L458: "QUANTGEN macro research · prepared 2 Oct 2026 for GEON KOH · research only, not investment advice."

Section outline (nav `.brand` "QUANTGEN · MACRO", links L193–199):

| # | `section id` | Line | h2 | Figures / hosts |
|---|---|---|---|---|
| hero | `header.hero` | L209–224 | h1 "Macro Neural Link" (L211) | `.stats role=list`: **139** resolved claims · **27** core links · **11** prohibitions · **22** backlog; `.bottom` 3 cards with eyebrows Keep / Keep as a labelled control / Drop (h3 L220–222) |
| 1 | `#link` | L226 | "Where both panels pointed, and where only one did" (L229) | `#classkey` legend (L235); `#c-map` scatter 60 nodes (L236, `role=img`); `details[data-table=map]` (L238); `#toplist` top-6 CORE-LINK list (L242) |
| 2 | `#tape` | L248 | "Cutting into a soft labor market, then hiking into an oil shock" (L251) | `#tape-grid`: `#c-unrate`, `#c-pay`, `#c-infl`+`#lg-infl`, `#c-rates`+`#lg-rates`, `#c-brent`, `#c-krw`, `#c-kospi` (L255–261, each with a `details.dt`); `#eventlist` (L263); `#snap` percentile table (L266) |
| 3 | `#models` | L271 | "The textbook relations held for decades, then broke in this cycle" (L274) | `#c-curve`, `#c-prob`, `#c-sahm`, `#c-phil` (dot plot), `#c-okun`, `#c-sb`, `#c-gold`+`#lg-gold`, `#c-haven` bars (L278–285); "Model-failure ledger" table 13 rows (L289–306) |
| 4 | `#overlays` | L310 | "Volatility rules survived. Macro direction rules did not." (L313) | `#c-rules` bars (L317, 10 rules); `#c-mom`+`#lg-mom` (L318); `#c-kvt`+`#lg-kvt` (L319); `#c-kw` (L320); `#c-sox` (L321); prose "Korea and crypto rules" (L324); "Indicative verdicts in QUANTGEN's gate" table 6 rows (L328–338) + fine print (L339) |
| 5 | `#debate` | L343 | "What the panels disagreed on, and what settled it" (L346) | table 8 rows: Question / Professors / Executives / What settled it (L349–361) |
| 6 | `#build` | L364 | "What the integration spec builds, runs forward, and forbids" (L367) | `.build` 3 columns: "Core links" (6), "Running on paper, or waiting for data" (4), "Prohibited by the evidence" (6) (L371–392); `.files` 3 cards (L394–398) |
| 7 | `#sources` | L401 | "How this was built" (L404) | h4 Data / Official / Papers / Courses and textbooks / Events (press, used for dating) / Limitations (L408–454) |

Interactive elements: same theme toggle (`localStorage['qgml-theme']`, L470/L761); 7 anchor links; **18** `details.dt` lazy tables (`map, unrate, pay, infl, rates, brent, krw, kospi, curve, prob, sahm, phil, okun, sb, gold, mom, kvt, sox`); line-chart hover tooltips with event markers (`EVENTS` 1–7 drawn as numbered circles, L657–665, tooltip shows `k · label` within ±6 days daily / ±30 days monthly, L572); focus-map nearest-dot ring + tooltip (`id · class`, `Professors fp · Executives fe`, label, key; L639–647); snapshot percentile bars (inline-styled divs, L691). ~26 outbound `<a>` (L410–447; one BoK URL carries `&amp;` query params).

Embedded dataset `#qg-data` (L460) — 23 top-level keys:

| key | shape | sample |
|---|---|---|
| `nodes` | `60 × {id, label, fp, fe, cls, dest, ps, es, data, key}` | `{"id":"N-01","label":"Released macro quantities (IP, payrolls, GDP, exports) lag prices: only timestamped market-priced inputs may act; macro quantities are context","fp":6,"fe":10,"cls":"CORE-LINK","dest":"SPEC §1 P1; §5 R-13 context log","ps":"Strong","es":"Strong","data":"Supports","key":"returns->dIP p=2e-8 vs dIP->returns p=0.04; KOSPI leads exports 4-7m (corr 0.52 at k=-5)"}`; cls ∈ {CORE-LINK 27, CONTESTED 15, CORE-PROHIBITION 11, ONE-SIDED 4, UNTESTED 3}; data ∈ {Supports 26, Mixed 15, Contradicts 11, Untested 8}; ps/es free-text ("Strong", "Refuted", "Split", "Moderate", "Silent", "Weak (indirect)", …). Full table in §D |
| `labor` | `unrate 43`, `pay3m 44`, `vu 43` × `["YYYY-MM-01", float]` 2023-01 → 2026-08 | `unrate` last 4.1; `pay3m` last 71.3; `vu` last 1.007 |
| `infl` | `cpi 43`, `corepce 44`, `fedtop 46` monthly | `cpi` 6.33 → 3.35; `corepce` 5.0 → 3.01; `fedtop` 4.5 → 4.0 (to 2026-10-01) |
| `rates` | `y10 144`, `y2 144`, `tips10 144`, `tp 143` weekly 2024-01-05 → 2026-10-02 | y10 4.05 → 5.29; y2 4.4 → 4.88; tips10 1.83 → 2.93; tp 0.18 → 1.02 (to 2026-09-25) |
| `mkts` | `brent 144`, `usdkrw 144`, `kospi 144` weekly | brent 78.3 → 114.0 (2026-09-29); usdkrw 1311.2 → 1356.8 (2026-10-01); kospi 2578.0 → 7004.0 (2026-10-02) |
| `snapshot` | `38 × {variable, latest_date, latest, unit, chg_3m, chg_12m, chg_unit, pctile_vs_history, history_from, history_n}` | `{"variable":"Unemployment rate (UNRATE)","latest_date":"2026-08-01","latest":4.1,"unit":"%","chg_3m":-0.2,"chg_12m":-0.2,"chg_unit":"pp","pctile_vs_history":16.856,"history_from":"1990-01","history_n":439}` (all 38 in §D) |
| `curve` | `spr 801`, `prob 801`, `rec 801` monthly 1960-01 → 2026-09 | spr last 0.96; prob last 9.5; rec is a 0/1 NBER flag (bands via `bandsFromFlag`, L503) |
| `sahm` | `rt 799` monthly 1960-01 → 2026-08 | last −0.07 |
| `phillips` | `5 × {era, slope, se, r2, n}` | `{"era":"1960-1984","slope":-0.39,"se":0.105,"r2":0.176,"n":276}` (all 5 in §D) |
| `okun` | `b 220` quarterly 1970-01 → 2026-04 | last −0.122 |
| `sbcorr` | `c252 432` (1990-10-31 →), `cpce 440` (1990-01-31 →) monthly | c252 last 0.331; cpce last 2.98 |
| `sbbucket` | `3 × {bucket, days, pooled_daily_corr, mean_rolling252_corr, share_days_corr252_pos}` | `<2%` 5016 d, −0.2922, −0.2589, 0.1665; `2-3%` 2619, −0.1143, 0.0404, 0.5323; `>3%` 1523, 0.2107, 0.1763, 0.6395 |
| `gold` | `gold 285`, `fit 285`, `tips 285` monthly 2003-01-31 → 2026-09-30 | gold 368 → 4187; fit 775 → 626; tips 2.19 → 2.93 |
| `haven` | `11 × {ep, spx, usd, y10, gold, krw, sell}` | `{"ep":"GFC 2007-09 (peak-trough)","spx":-54.6,"usd":16.7,"y10":-178.0,"gold":26.8,"krw":67.8,"sell":false}` (all 11 in §D) |
| `b1` | `37 × {rule, series, static_sharpe, rule_sharpe, dSR, share_rule_beats, static_maxdd, rule_maxdd}` | `{"rule":"i_BSC_volscale","series":"Mom","static_sharpe":0.399,"rule_sharpe":0.907,"dSR":0.508,"share_rule_beats":1.0,"static_maxdd":-0.633,"rule_maxdd":-0.28}` (all 37 in §D) |
| `momcurves` | `static 440`, `vs 440`, `vsdm 440` monthly 1990-01-31 → 2026-08-31 (cumulative log return, vol-matched) | static last 1.788; vs 3.527; vsdm 3.991 |
| `momstats` | `{sharpe:{static,vs,vsdm}, mdd:{…}}` | sharpe 0.399 / 0.714 / 0.798; mdd −0.633 / −0.279 / −0.209 |
| `korea_vt` | `bh 327`, `vt 327`, `w 327` daily 2025-06-02 → 2026-10-02 (index 100 at 30 May 2025 close) | bh 100.05 → 259.62; vt → 226.12; w 1.0 → 0.612 |
| `korea_stats` | dict 6 | `crash_bh -0.386304, crash_vt -0.122487, h1_bh 1.0114, h1_vt 0.5168, w_last 0.612, w_next 0.694` |
| `soxbeta` | `b 559`, `r2 559` weekly 2016-01-15 → 2026-10-02 | b 0.205 → 0.515; r2 0.138 → 0.193 |
| `protective` | `302 × {series, variant, period, metric, value}` — **value is a string** | `{"series":"KOSPI","variant":"R-06 KR VT20 \| KRX ETF 3bp","period":"1x","metric":"avg_multiplier","value":"0.9250062551771919"}`; series ∈ {KOSPI, US}; period ∈ {1x, 2x}; 8 variants, 30 metrics (§D) |
| `outperf` | `16 × {series, variant, metric, value}` (string values) | `{"series":"French Mom daily \| US_KIS_50bp x2 legs","variant":"R-03 VS vs unscaled","metric":"dSR","value":"0.27284996966111913"}` (all 16 in §D) |
| `events_all_n` | int | `136` (not rendered anywhere in the script) |

Note: `protective` and `outperf` are loaded but **never rendered** by the ML script (no reference to `D.protective`/`D.outperf`); they are a hidden golden-value fixture.

External dependencies / offline: identical to QC (same three font `<link>`s L9–11; no CDN JS). ~26 outbound anchors to FRED, Ken French, Fed, BoK, IEA, NY Fed, papers, courses and press (L410–447). Offline: fully functional with system-font fallback; `localStorage` guarded.

---

## B. Design language (both pages share one stylesheet; QC appends "council additions" L189–206)

### B.1 Colour tokens (CSS custom properties, `:root` L14–25; dark L26–43)

| token | light | dark | role |
|---|---|---|---|
| `--bg` | `#F5F6F8` | `#0D1015` | page ("plotter-paper ground", comment L13) |
| `--surface` | `#FFFFFF` | `#151920` | figure plates, nav pill, cards |
| `--bed` | `#ECEFF3` | `#181D25` | bar tracks, percentile tracks |
| `--ink` | `#0C0F14` | `#EDF0F5` | primary text |
| `--ink-2` | `#454D5C` | `#A7AFBD` | secondary text, captions |
| `--ink-3` | `#5E6778` | `#8891A1` | eyebrows, axis labels, muted |
| `--rule` | `#D5DAE2` | `#262B35` | 1px borders, table rules |
| `--grid` | `#E6E9EE` | `#20262F` | chart gridlines, bar-row rules |
| `--band` | `rgb(12 15 20 / .07)` | `rgb(237 240 245 / .07)` | recession / quadrant shading |
| `--band-2` | `rgb(232 104 52 / .10)` | `rgb(217 89 38 / .16)` | high-inflation shading |
| `--s1` | `#2a78d6` | `#3987e5` | series 1 (blue) |
| `--s2` | `#eb6834` | `#d95926` | series 2 (orange) |
| `--s3` | `#1baf7a` | `#199e70` | series 3 (green) |
| `--s4` | `#eda100` | `#c98500` | series 4 (amber) |
| `--v-pass` | `#1F744F` | `#71D6A3` | verdict PASS |
| `--v-revise` | `#8F5A00` | `#F7C15F` | verdict REVISE |
| `--v-reject` | `#C12B11` | `#FC7D65` | verdict REJECT |
| `--v-insuff` | `#5E6778` | `#8891A1` | INSUFFICIENT DATA / not built |
| `--focus` | `#FFDD00` | (same) | `:focus-visible` 3px outline |
| `--tip-bg` / `--tip-ink` | `#0C0F14` / `#F5F6F8` | `#EDF0F5` / `#0D1015` | tooltip |
| QC only `--v-revise-soft` | `#E9B65C` | `#B98A3A` | "upheld with qualification" / QUALIFIED segments (L189–191) |
| QC only `--seg-gap` | `var(--surface)` | — | stacked-segment divider |
| `--content` | `1120px` | — | reading-column max width |

Theme mechanics: `color-scheme: light` on `:root`; dark via `@media (prefers-color-scheme: dark) :root:not([data-theme="light"])` and `:root[data-theme="dark"]` (two identical blocks). Charts use `var(--s1)` etc. inside SVG `style` attributes, so a theme switch only needs `redrawAll()` for label placement.

Semantic colour maps in the scripts (verbatim): QC `VCOL = {'FALSE-TRUE':'--v-reject','FALSE-ERROR':'--s1','DESIGN-DEFECT':'--s2','MISSING':'--s4','QUALIFIED':'--v-revise-soft','CONFIRMED':'--v-pass','UNVERIFIABLE':'--v-insuff'}` (L630); `VER = {'PASS':'--v-pass','REVISE':'--v-revise','REJECT':'--v-reject','INSUFFICIENT DATA (inconclusive)':'--v-insuff'}` (L686); ledger `ORDER` = VALID-BUILD `--v-pass`, VALID-ERRATA `--s1`, CONFIRMED `--s3`, VALID-SHADOW `--s4`, CONTEXT-ONLY `--v-insuff`, CONTESTED `--v-revise`, OWNER-DECISION `--s2`, INVALID `--v-reject`, INFO `--rule` (L765); ML `CLS = {'CORE-LINK':{name:'Core link → spec',color:'--v-pass',shape:'circle'},'CORE-PROHIBITION':{'Prohibition → do-not-build','--v-reject','cross'},'CONTESTED':{'Contested → backlog','--v-revise','diamond'},'ONE-SIDED':{'One-sided → backlog','--v-insuff','square'},'UNTESTED':{'Untested → backlog','--v-insuff','triangle'}}` (L602–608); snapshot percentile bar colour `p>=90 → var(--v-reject)`, `p<=10 → var(--s1)`, else `var(--ink-3)` (L691); MCS heat cell `color-mix(in srgb, var(--s1|--s2) {min(60, |1-rel|*400)}%, var(--surface))`, `●` inside / `○` outside the 90% MCS (L726).

### B.2 Typography (L20–22, L47–58, L71–93)

- Display: `--f-display` **Archivo** (variable `wdth 100..125`, `wght 500..800`) → h1 `640 / clamp(38px,6vw,64px) / 1.0`, `font-stretch:112%`, `letter-spacing:-.025em`, `max-width:18ch` (QC L206); h2 `620 / clamp(28px,3.6vw,40px) / 1.08`, stretch 108%; `.stats b` `700 40px/1`, stretch 118%; `.brand` `700 14px`, stretch 125%, `.06em`; `.stamp` `700 11px`, stretch 125%, `.1em` uppercase.
- Body: `--f-body` **IBM Plex Sans** 400/500/600 + italic 400; `body { font: 400 16px/1.6 }`; `.lede clamp(17px,2.1vw,20px)/1.5`; captions 13.5px/1.5; `.fine` 13px; `text-wrap: balance` on headings, `pretty` on p.
- Mono: `--f-mono` **IBM Plex Mono** 400/500 for `.eyebrow` (`500 12px`, `.08em`, uppercase), legends (`400 12px`), table headers (`500 11px`, `.06em`, uppercase, sticky), `.num`/`td.n` with `font-variant-numeric: tabular-nums`, axis labels (`400 11px`), `.chip` (`500 11px`).

### B.3 Spacing / layout

`.wrap { max-width:1120px; padding-inline:max(16px,4vw) }`; `section.sec { padding-block:56px; border-top:1px solid var(--rule) }`; `.sec-head { gap:10px; margin-bottom:28px; max-width:72ch }`; `.hero { padding-block:56px 40px; gap:22px }`; grids `.grid2`/`.grid3` with `gap:16px` collapsing at 900px/760px; `figure.fig { padding:16px 16px 12px; gap:8px; border-radius:4px }`; `.col { padding:18px 18px 14px }`; `.bottom > div { padding:18px 20px }`; tables `th,td { padding:7px 10px }`; `.tblwrap { max-height:320px; overflow:auto }`; `.tblwide table.t { min-width:760px }`; nav `min-height:52px`, sticky, `backdrop-filter: saturate(160%) blur(14px)`, `background: color-mix(in srgb, var(--bg) 88%, transparent)`; `scroll-padding-top:64px`. Radii: 2px (stamps, bars), 4px (plates, tables, tooltip), 999px (chips, theme pill). Breakpoints: 900, 860, 760, 720, 560px.

### B.4 Component vocabulary

| component | selector | spec |
|---|---|---|
| Stamp (verdict) | `.stamp[.flat].v-pass/.v-revise/.v-reject/.v-insuff` | inline-flex, `border:1.5px solid var(--c)` + `outline:1px solid var(--c)` offset 2px (double rule), uppercase Archivo 11px (flat: 10px, no outline). Texts used: "Conditional", "REJECT / forward-sim", "Challenger", "Build", "Retire", "Forward-sim", "Not built" (QC `#t-res`); "Pass", "Not recommended", "Expected insufficient data (v2)", "Reject (instrument)", "Reject" (ML L328–338) |
| Chip | `.chip` | pill, mono 11px, 1px `--rule` border, `--ink-2` (defined, unused in markup) |
| Eyebrow | `.eyebrow` | mono uppercase label above headings ("Step 1 · Quantitative Finance panel", "1 · The neural link") |
| Stat tile | `.stats > div` with `b.num` + `span` | 4-up grid, hairline dividers, 40px Archivo number |
| Bottom-line cards | `.bottom > div` | 3-up joined cards on `--surface` |
| Figure plate | `figure.fig` (+ `.wide` spanning) with `.fig-head h3` + `.now` (mono right-aligned "latest" readout, filled by `setNow`) + chart host + `.legend` + `figcaption` + `details.dt` | all charts live on plates |
| Legend | `.legend span > i` (14×3px swatch; `.dash` dashed; `.box` 12×10) | built by `legend(id, items)` |
| HTML bars | `.bars > .brow { grid: minmax(150px,34%) 1fr 64px }` with `.lab` (+`small`), `.btrack` (`.zero`, `.bar`), `.val` | variants `.btrack.stack .seg` (stacked), `.btrack.dumb .dline/.dot.d0/.d1` (dumbbell), `.brow.axis` |
| SVG line chart | `lineChart(id, opt)` — opt keys: `series[{name,short,data,color,w,dash,gapDays}]`, `log`, `logTicks`, `y0`, `y1`, `yd`, `yfmt`, `vfmt`, `endLabels`, `daily`, `tol`, `height`, `hlines[{y,label,dash}]`, `bands`, `bandFill`, `events`, `x0`, `x1`, `ml`, `mr` | margins `l 44 / r 14 or 74 / t 10 or 22 / b 24`; H default 230 (200 < 480px); nice ticks `[1,2,2.5,5,10]`; time ticks quarters/half-years ≤ 3.2y else `[1,2,5,10,20,25]`y; end-label collision push 13px |
| Date bars | `dateBars(id, groups, {height, yearStep})` | one bar per start, colour by `VER[v]`, grouped with opacity `op` |
| Focus map | custom scatter 0–21 × 0–21, shaded quadrant `≥ 8` both axes, golden-angle jitter `rr = 0.28·√(i+0.6)`, 5 glyph shapes | L617–654 |
| Dot plot | Phillips eras with ±1.96·se whiskers, `lo −0.8 / hi 1.4` | L703–713 |
| Heat-map table | `#c-mcs table.t td.hm` | L722–728 |
| Data table | `table.t` (sticky uppercase mono th, `td.n` right/tabular) inside `.tblwrap` or `.tblwide`; lazy `details.dt` + `summary` with `+`/`−` pseudo-marker | `seriesTable(key, names, arrs, n, dec)` samples ≤ n rows evenly |
| Tooltip | `.tip` absolutely positioned, `--tip-bg`, mono 12px, `.sw` 8px dot, `.ttl` | `placeTip` flips left/up at edges |
| Event list | `ul.events li > .k` numbered 18px circle | ML L263 |
| Build columns | `.build > .col` (eyebrow + h3 + `ul li b`) | ML L371–392 |
| File cards | `.files > .file` dashed `--ink-3` border, `code` filename | QC L443, ML L394 |
| Sources | `.srcs { columns: 2 320px }` with h4 groups | |
| Theme pill | `.nav .theme button[aria-pressed=true] { background: var(--ink); color: var(--bg) }` | |

### B.5 Motion

Minimal: `html { scroll-behavior: smooth }` (off under `prefers-reduced-motion: reduce`, L46); no CSS transitions, keyframes or scroll-triggered animation; hover states only (`a:hover` colour, tooltip show/hide, crosshair opacity .5, dot ring); chart redraw on `ResizeObserver` via `requestAnimationFrame`. Accessibility: `:focus-visible` yellow outline, `aria-pressed`, `role="img"` + `aria-label` on bar tracks and the map, `aria-labelledby` on ML sections, `scroll-padding-top`.

### B.6 Difference from the app's theme (`core/theme.py`, `ui/components.py`, `main.py`)

| aspect | pages | app |
|---|---|---|
| Palette | neutral grey-blue paper (`#F5F6F8`/`#0D1015`), blue accent `#2a78d6`, verdict greens/reds `#1F744F`/`#C12B11` | `Palette` dataclass (`core/theme.py` L12–26): DARK `bg #101417, surface #171d21, surface_2 #1d252a, border #324047, text #e7ecef, muted #9eabb2, accent #4f98a3, accent_soft #233b40, success #6daa45, error #d1637f, on_accent #071012`; LIGHT `bg #f5f7f6, surface #ffffff, surface_2 #edf2f0, border #d2dcda, text #192326, muted #647277, accent #01696f, accent_soft #d8e8e5, success #437a22, error #a12c53, on_accent #ffffff` — teal accent, green/pink semantic pair; no 4-series chart palette and no REVISE/INSUFF tokens (Strategy Lab maps `_TOKEN = {"PASS":"success","REVISE":"accent","REJECT":"error","INSUFFICIENT_DATA":"muted"}`, `ui/strategy_lab_page.py` L32) |
| Mode | auto/light/dark per viewer via `data-theme` + localStorage | `MODES=("dark","light","system")`, `DEFAULT_MODE="system"` but `main.py` L99–102 forces `page.theme_mode = DARK` and `set_mode("dark")` |
| Type | Archivo / IBM Plex Sans / IBM Plex Mono (web fonts) | Flet default (Roboto) + `"Consolas, monospace"` for `mono()` (`ui/components.py` L143); sizes 10–26px (`section` title 26 bold, chip 11, stat value 16) |
| Radii | 2 / 4 / 999 px | `RADII = {"sm":8,"md":12,"lg":16,"pill":999}` — app cards are much rounder |
| Components | stamps (double-rule), plates, HTML bars, inline SVG charts, lazy tables | `chip()` pill with 1px token border on `surface_2`; `card()` 16px padding `lg` radius; `stat()` tile on `surface_2` `md` radius; `notice()`, `empty_state()`, `section()`, `key_value()`; charts are matplotlib PNGs returned as `ft.Image` (`ui/fcharts.py`, `ui/xcharts.py`); tables are `ft.DataTable` with 11px cells (`ui/macro_page.py` L84–103) |
| Motion | smooth scroll only | `AnimatedSwitcher` page transitions `TRANSITION_MS = 180` (`main.py` L112–115) |
| Macro page content | FRED/Yahoo macro tape, model-failure ledger, node map | `ui/macro_page.py`: source dropdown (`auto/fred/synthetic`), Refresh, regime chips (`curve/risk/dollar/breakevens/real yields`), headline `stat` tiles for `DGS2, DGS10, DGS30, T10Y2Y, DFII10, T10YIE, VIXCLS, BAMLH0A0HYM2, DTWEXBGS`, 10-column indicator `DataTable` (`Group, Indicator, Last, 1d, 1w, 1m, 3m, z (1y), pct (1y), Source`), `fcharts.macro_z_chart`, two report buttons routed to `analysis_panel`; overlapping series with the ML `snapshot` (DFII10, DGS10, DGS2, T10YIE, T10Y2Y, VIXCLS, DTWEXBGS, BAMLH0A0HYM2) |

---

## C. Integration options for the Flet 0.85.2 desktop app (ranked)

Facts checked on this machine: `flet 0.85.2` (+ `flet-cli`, `flet-desktop`, `flet-web`; `requirements.txt` pins `flet[all]==0.85.2`); `hasattr(ft.Page, "launch_url") == True`; `"WebView" in dir(ft) == False`; `import flet_webview` → ModuleNotFoundError; `ft.Markdown` exists. Existing repo pattern for opening local artefacts: `os.startfile(str(path))` on Windows / `xdg-open` elsewhere, wrapped in `try/except`, in `ui/runs_page.py` L37–44 (`open_folder`). `tests/flet_api_guard.py` lints every `page.<method>()` call against the installed Flet (so `page.launch_url` is admissible; a `ft.WebView(...)` constructor would also be caught at test time if it did not exist).

**1 (recommended). Ship both files verbatim under the repo and open them in the system browser.**
- Path: `docs/council/QUANTGEN_Quant_Council.html` and `docs/council/QUANTGEN_Macro_Neural_Link.html` (the `docs/` tree already holds the primers and `docs/asset_expansion/cards`; `ui/strategy_lab_page.py` L30–31 resolves `ROOT = Path(__file__).resolve().parents[1]; CARDS_DIR = ROOT / "docs" / "asset_expansion" / "cards"` — reuse the same `ROOT` idiom). Keep the council `README.md` beside them or a one-line `docs/council/README.md` pointing at the spec.
- Launch: `page.launch_url(path.resolve().as_uri())` (file:// URI) with the `runs_page.open_folder` fallback (`os.startfile`) — both are zero-dependency; prefer `os.startfile`/`xdg-open` because it is the proven path in this repo and avoids any Flet client URL filtering. Operator-initiated only; no network.
- Where: Macro page (`ui/macro_page.py` `build_macro_page`, in the header `ft.Row` next to `provider_bar()`/Refresh, L193–200) → "Macro Neural Link" button; Strategy Lab (`ui/strategy_lab_page.py` section one header, L140) → "Quant Council" button. Label buttons with the file name and the "research only, simulated panels" caveat in the tooltip.
- Test (hermetic, in `tests/run_all.py` style): both files exist, each contains exactly one `id="qg-data"` block, `json.loads` succeeds, `QC.ledger_n == 361`, `len(QC.modules) == 34`, `len(ML.nodes) == 60`, no `<script src=` / `<img src=` / `fetch(` (keeps the offline guarantee).
- Offline: works (fonts fall back). Cost: 738 KB of static files; no code path through the engine.

**2. Re-use the embedded data to drive native views (read-only displays; no exposure change).**
- Extraction at build time (one-off script writing `docs/council/council_pages_data.json` = `{"quant_council": QC, "macro_neural_link": ML}`) is simpler and testable than regex at runtime; or lazy-load with the regex above (two 290 KB JSON parses, ~50 ms).
- Candidate native views, in order of value:
  1. **Module status table** (`QC.modules` 34 rows: id, change, cls, pri, ms, name) → Rules page or a Macro-page "v2 modules" card as `ft.DataTable`; colour `change` via `chip()` tokens (NEW→accent, CHANGED→muted, DEMOTED/RETIRED→error). This is the implementation's own progress tracker.
  2. **Owner decisions D1–D6** (`OWN`, QC L797) → the spec says "The Macro page lists every open owner decision" (SPEC L65); but the canonical source is the rules-store registry `owner_decisions.D<n>` (SPEC §7). Use the page list only as seed text; render from the store once M0 lands.
  3. **Node map** (`ML.nodes`) → matplotlib scatter via the `ui/fcharts.py` pattern (`fp` × `fe`, marker by `cls`), plus a `DataTable` with `id, cls, fp, fe, data, dest`; hover is lost (PNG), so add the table.
  4. **Verdict-by-start bars** (`QC.kstart`, `QC.ustart`) and **MCS grid** (`QC.mcs`) → Strategy Lab cards; these are the long-history evidence the local `docs/asset_expansion/cache/*.csv` (SPY/QQQ/^KS200/005930.KS …, no KOSPI index before the ETF era, no French factors) cannot regenerate.
  5. **Golden cross-checks** (`ML.protective`, `ML.outperf`, `QC.kvt_mdd`, `ML.momstats`, `ML.korea_stats`) → test fixtures for M7 (e.g. `sharpe_on 0.6380531424799194` = G-KR-02 0.638; `PC3_p_ni_block10 0.246` = backlog DQ-02 "§8.9 p_ni at 10-session blocks 0.246"; `w_next 0.694` = corrected PAGE value in backlog L1251). Fixture only: never an acting input.
  6. **Macro tape** (`ML.labor/infl/rates/mkts/snapshot`) → do NOT wire into the Macro sheet: the app already pulls FRED/Yahoo live with `value_status`, and the page series are latest-vintage research snapshots dated ≤ 2026-10-02 (ML L451 "Macro series are latest vintage, not as first published"). Display, if at all, under a "research snapshot (static)" label.
- All of this is specification-book/context display; nothing acts, nothing exceeds 1.0, nothing orders.

**3. In-app WebView — not available without a new dependency.** Flet 0.85.2 ships WebView as the separate `flet-webview` package (not installed; `ft.WebView` absent). Adding it changes `requirements.txt`/`pyproject.toml` and the packaged desktop build; the pages' `backdrop-filter`, `color-mix()`, `text-wrap` and variable-font `font-stretch` also need a current Chromium/WebView2. `ft.Markdown` cannot render the SVG charts. Rank last; only if the owner explicitly asks for in-app rendering.

Not recommended: converting the pages into Flet widgets wholesale (two 34 KB chart scripts, 25 SVG charts, 19 lazy tables) — the browser handoff in option 1 gives the same content with zero maintenance.

---

## D. Content present only in the pages (or only as data there) — preserve as data

Legend: **page-only** = not found in the four markdown documents; **also in md** = present but the page carries the machine-readable form.

### D.1 QC `MEMBERS` (script L649–657) — page-only verdict vectors (names/lanes also in `QUANTGEN_Quant_Council_Report.md` L13–19)
`v` order = `AUD_K = ['FALSE-TRUE','FALSE-ERROR','DESIGN-DEFECT','MISSING','QUALIFIED','CONFIRMED','UNVERIFIABLE']`

| id | name | arch | lane | v | total |
|---|---|---|---|---|---|
| QF1 | Kestrel | ETF and options market maker | Costs, KRX microstructure, timing | [2,2,2,4,7,7,1] | 25 |
| QF2 | Ostrava | Low-latency data and infrastructure | Point-in-time data, clocks, staleness | [4,3,7,3,5,6,0] | 28 |
| QF3 | Halcyon | Statistical-arbitrage and ML researcher | Gate statistics, trials, power | [3,3,6,1,7,4,0] | 24 |
| QF4 | Meridian | Multi-strategy pod risk | Vol targets, ladder, caps | [4,3,4,3,5,4,0] | 23 |
| QF5 | Larkspur | Multi-asset and factor manager | Factors, trend, priors | [5,4,4,1,8,5,0] | 27 |
| QF6 | Vireo | Volatility and derivatives quant | Estimators, Quant Lab, tails | [3,3,4,2,7,5,1] | 25 |
| QF7 | Corvid | Academic quant methods | Regimes, forecast tests, curricula | [5,2,6,2,8,5,0] | 28 |

Column sums: FALSE-TRUE 26, FALSE-ERROR 20, DESIGN-DEFECT 33, MISSING 16, QUALIFIED 47, CONFIRMED 36, UNVERIFIABLE 2 = 180. `.now` text: "180 items · 26 false trues · 20 false errors".

### D.2 QC cross-examination rows (L666–670) — page-only per-delegation split (totals 332·127·3·10 of 472 in council report L41)
`XK = ['Upheld','Upheld with qualification','Overturned','Unresolved']`

| lab | sub | Upheld | Qualified | Overturned | Unresolved |
|---|---|---|---|---|---|
| PX1 Professors | methods: QF3, QF6, QF7 (+ QF2 timing items) | 79 | 33 | 1 | 1 |
| PX2 Professors | pricing and macro: QF1, QF4, QF5 | 73 | 25 | 0 | 2 |
| EX1 Executives | risk and strategy: QF3, QF4, QF5, QF7 | 94 | 36 | 2 | 5 |
| EX2 Executives | trading and Korea: QF1, QF2, QF6 (+ 17 QF4 items, mostly Korea) | 86 | 33 | 0 | 2 |

### D.3 QC `RES` — twelve resolutions (L746–758; prose version in council report L109 ff.)

| # | topic | resolution (verbatim) | vote | stamp class | outcome |
|---|---|---|---|---|---|
| 1 | Korea vol-target card (R-06 KR) | BUILD-AS-INSURANCE on a formal PASS on long history; cap 1.0 permanent; labelled crisis-clustering insurance. With the conservative selection factor, the formal run is expected to return INSUFFICIENT DATA. | Unanimous; sub-points 2–1 | v-revise | Conditional |
| 2 | US vol-target cards | The 50 bp card stays REJECT, relabelled as a fact about the instrument. A new index-futures card runs in FORWARD-SIM pending a 1926+ settling run and a US sleeve (D5). | Unanimous | v-reject | REJECT / forward-sim |
| 3 | Volatility-estimator default | SMA20 stays acting. COMB (GJR-t + log-HAR on ranges) is the registered challenger behind a staged, counted selection gate. | 2–1 | v-insuff | Challenger |
| 4 | PC-1 → PC-1′ | Tail legs gate (ES95 of 21- and 126-session returns). PC-3 binds. Drawdown is printed, not gated. A do-no-harm cap applies. The package is checked by a placebo acceptance test. | Unanimous; cap 2–1 | v-pass | Build |
| 5 | Deflated-Sharpe trial count | A family trial ledger with N_eff = max(N_clusters, N_equiv). R-03 passes (0.98, borderline); R-04 fails (0.77) and moves to the specification book. | Unanimous core | v-pass | Build |
| 6 | Drawdown ladder | Non-cumulative steps composed by min(), an explicit re-arm, 21-session time-boxing, and a hard stop at −15% of book NAV (D2). | Unanimous; levels 2–1 | v-pass | Build |
| 7 | Staleness | Measured against each source's publication schedule. The failure action depends on the input's role. Risk-model inputs never HALT. | Unanimous | v-pass | Build |
| 8 | R-08, R-11, R-12 | R-08 becomes an execution annotation. The USD/KRW and rates legs are retired as labelled REJECTs (54 and 71 onsets). | Unanimous | v-reject | Retire |
| 9 | Trend axis | A protective-only 10-month trend card for US and other non-Korean sleeves, in FORWARD-SIM. Korean trend stays as context. | Unanimous; scope 2–1 | v-insuff | Forward-sim |
| 10 | Regime engine | No regime module and no regime state, acting or displayed. The jump model stays CONTESTED, with a named settling test. | Unanimous outcome | v-reject | Not built |
| 11 | Episode table | Objective episodes in each market's own data (20% bear markets), extended before 2008. | Unanimous | v-pass | Build |
| 12 | Korea caps, priors, Sep-2026 | Caps on look-through with an active 0.05 single-name cap; MSCI 25/50 template by default (D1). Priors become admissibility filters with equal risk budgets. Sep-2026 is not a Korea episode. | Unanimous | v-pass | Build |

Red lines (QC L360–364): Professors — "No promotion on one path or one crisis. No gate rule chosen after seeing the card it decides. A forward record never validates."; Executives — "No regime-model state, acting or displayed. No decisions on provisional or stale inputs. Risk-model inputs never halt the book. No instrument the desk can't trade at the declared cost and size."; QF — "No REJECT on single-path drawdown. Verdicts are book-specific. Nothing may freeze the book."

### D.4 QC `modules` (JSON) — 34 rows (also in SPEC per-rule headers, e.g. SPEC L197, L925; the page is the only flat list)

| id | change | cls | pri | ms | name |
|---|---|---|---|---|---|
| R-01 | CHANGED | INVARIANT | P0 | M1 | Point-in-time discipline: value_status, session_date, retrieved_at_utc, provisional-row guard, post-close fixtures |
| R-02 | CHANGED | INVARIANT | P0 | M2 | Overlay bounds and composition by min(); recommended-book stack card |
| R-03 | CHANGED | CARD-O | P0 | M4 | Momentum own-vol scaling: indicative-PASS relabel, scale-free target revision, variance-scaled trial |
| R-04 | DEMOTED | CARD-O | P1 | M4 | Daniel–Moskowitz gate: specification book only, A-provisional route closed |
| R-06 | CHANGED | CARD-P | P0 | M7 | Per-market vol target: Korea formal card (BUILD-AS-INSURANCE on PASS); US 50 bp card relabelled; cap 1.0 permanent; dual labels |
| R-07 | CHANGED | INVARIANT | P0 | M5 | Korea caps on look-through with an active single-name cap; drawdown hard stop with explicit re-arm |
| R-08 | DEMOTED | CONVENTION | P1 | M5 | VIX ≥ VIX3M flag demoted to an execution-state annotation with a stated clearing rule |
| R-09 | CHANGED | INVARIANT | P1 | M2 | Hedge-validity state: date-aligned corr63, never-HALT risk-model inputs, display-only fx_hedge_credit |
| R-10 | CHANGED | CONVENTION | P1 | M5 | Event calendar: multi-session gap tags, √n VaR display scaling, BoK decision and press conference as separate events |
| R-11 | RETIRED | CARD-P | P1 | M8 | USD/KRW leg (S1) retired from FORWARD-SIM; REJECT recorded; labelled refusal book only |
| R-12 | RETIRED | CARD-P | P1 | M8 | US rates-stress leg (S2) retired from FORWARD-SIM; REJECT recorded at every timing |
| R-13 | CHANGED | CONTEXT | P1 | M6 | Context log: vintages and first prints, leverage/flow, VRP, live implied-vol snapshots, turbulence |
| R-14 | CHANGED | CARD-O | P2 | M7 | TS-trend sleeve: declared instrument book and diversification claim at cap 1 |
| R-15 | CHANGED | CONVENTION | P0 | M4 | Priors as admissibility filters; equal risk budgets over admissible families; inverse-vol across markets |
| R-16 | CHANGED | CONTEXT | P1 | M9 | Quant Lab: expanding-window fits, FHS/EVT envelope, replay library with regime metadata, range-HAR admitted |
| R-17 | CHANGED | CONVENTION | P2 | M10 | Planned sleeves: crypto 24/7 clock and declared FX instrument |
| R-18 | CHANGED | GOVERNANCE | P2 | M6 | Policy and scale breaks: official-framework trigger now; statistical and BOCPD flags logged only; market-structure break log |
| R-19 | NEW | INVARIANT | P0 | M1 | Data contracts: schedule-aware staleness with role-based failure actions |
| R-20 | NEW | INVARIANT | P0 | M1 | Effective-dated market calendars and regime tags (KRX, NYSE, Fed, SIFMA) |
| R-21 | NEW | GOVERNANCE | P0 | M7 (frozen before the first card run) | CARD-P gate v2: PC-1′ tail legs, PC-2 with CI, binding PC-3, do-no-harm cap, gate-acceptance test |
| R-22 | NEW | GOVERNANCE | P0 | M7 (frozen before the first card run) | Evaluation conventions: objective market-own episodes, excess returns, declared start band, regime lines, post-trough window |
| R-23 | NEW | GOVERNANCE | P0 | M7 (frozen before the first card run) | Step 3: family trial ledger and N_eff = max(N_clusters, N_equiv) |
| R-24 | NEW | GOVERNANCE | P0 | M7 | Statistics and power harness: studentized bootstrap, SE ladder, power/MDE line, PBO on the card claim, Lo-adjusted Sharpe |
| R-25 | NEW | GOVERNANCE | P0 | M8 | Forward-record monitoring and demotion v2: whole-book NAV, calibrated alarms, operational triggers |
| R-26 | NEW | INVARIANT | P0 | M0 | Instrument book, notional and cost realism: tick floor, granularity floor, header fields, execution variants |
| R-27 | NEW | CONVENTION | P2 | M5 | KRX/NYSE simulated fill model: close-auction fill, random end, limit-lock, LP-exempt iNAV check, bar convention |
| R-28 | NEW | CARD-P | P1 | M8 | Trend-axis protective card (US and non-Korean sleeves): monthly SMA10m, 0.5× below trend, FORWARD-SIM |
| R-29 | NEW | CARD-P | P1 | M8 | MACRO-R06-US-FUT: US index-futures vol target (new card), FORWARD-SIM pending a 1926+ settling run |
| R-30 | NEW | GOVERNANCE | P1 | M3 | Volatility-estimator selection gate and forecast-evaluation harness; COMB registered challenger |
| R-31 | NEW | CARD-P | P1 | M7 | Drawdown step-down card: −8% and −12% steps, time-boxed at 21 sessions, specification book until PASS |
| R-32 | CHANGED | GOVERNANCE | P0 | M0 | Card header and artifact schemas v2 (model_card.macro, macro_state, context_log) |
| R-33 | CHANGED | GOVERNANCE | P1 | M0 | DO-NOT-BUILD list v2 |
| R-34 | NEW | GOVERNANCE | P0 | M7 (frozen before the first card run) | Timing-fragility gate: timing profile with a look-ahead positive control on every card |
| R-35 | CHANGED | GOVERNANCE | P1 | M8 | macro_daily workflow gates aligned with v2 (roles, verdict filter, refusal and FORWARD-SIM books) |

(No R-05 row: the page's 34 modules skip R-05; SPEC §5 has R-05 "reversal and quality stay 1.0×" unchanged.)

### D.5 QC `switches` (JSON, 9 rows; md gives only 16.9/30.8/9.75 prose)

| mk | det | sw | src |
|---|---|---|---|
| US | Markov switching (unpenalised) | 16.7 | DLB |
| KOSPI | Markov switching, 2015+ file (the v1.2 figure) | 30.78 | DLB |
| KOSPI | Markov switching, 1996+ file | 9.75 | DLB |
| KOSPI | Jump model, penalty 100 | 0.93 | DLB csv |
| KOSPI | Jump model, penalty 25 | 1.59 | DLB csv |
| KOSPI | Jump model, penalty 50 | 1.17 | DLB csv |
| US | Jump model, penalty 100 | 0.69 | DLB csv |
| US | Jump model, penalty 25 | 2.03 | DLB csv |
| US | Jump model, penalty 50 | 1.25 | DLB csv |

### D.6 QC `mcs` — QLIKE relative to SMA20 (`rel`), `●` = `in90` true (page-only grid; `EST` labels L722: SMA20 "SMA20 (acting)", EWMA94 "EWMA λ 0.94", EWMA97 "EWMA λ 0.97", GARCH_t "GARCH(1,1)-t", GJR_t "GJR-GARCH-t", LHAR_RNG "log-HAR, daily ranges", COMB "COMB (challenger)")

| est | KOSPI 1d | KOSPI 5d | KOSPI 21d | US 1d | US 5d | US 21d |
|---|---|---|---|---|---|---|
| SMA20 | ○ 1.000 (mse ○) | ○ 1.000 (mse ○) | ○ 1.000 | ○ 1.000 | ○ 1.000 | ○ 1.000 |
| EWMA94 | ○ 0.966 | ○ 0.867 | ● 0.749 | ○ 0.965 | ○ 0.870 | ○ 0.814 |
| EWMA97 | ○ 0.976 | ○ 0.895 | ● 0.742 | ○ 0.980 | ○ 0.907 | ○ 0.828 |
| GARCH_t | ○ 0.957 | ● 0.837 | ● 0.683 | ○ 0.949 | ○ 0.809 | ● 0.670 |
| GJR_t | ○ 0.952 | ● 0.841 | ● 0.718 | ○ 0.926 | ● 0.757 | ● 0.652 |
| LHAR_RNG | ● 0.947 | ● 0.818 | ● 0.715 | ○ 0.921 | ● 0.744 | ● 0.695 |
| COMB | ● 0.944 | ● 0.809 | ● 0.691 | ● 0.916 | ● 0.723 | ● 0.642 |

`mse_in90` is true for every cell except SMA20 KOSPI 1d and 5d.

### D.7 QC adversarial rounds `AK=['Blocker','Major','Minor or note']` (L773–777; council report L251–254 gives round 1–2 only partially)
Round 1 "4 × critique" 9/45/34 · Round 2 "4 × critique" 0/19/37 · Round 3 "3 agree, 1 critique" 0/3/24 · Round 4 "4 agree" 0/0/4; `.now` "agreement: 0/4 → 0/4 → 3/4 → 4/4".

### D.8 QC capability gap `A` (L783; council report L195–201 has the same table) — `[area, n, v1.2, v2.0]` on a 0–3 scale
Data layer 4 1.00→2.00 · Validation statistics 6 0.83→2.00 · Risk and sizing 6 0.67→1.67 · Execution and cost realism 6 0.67→1.67 · Volatility and risk models 6 0.83→1.83 · Research methods 5 0.60→1.20 · All 33 capabilities 33 0.76→1.73.

### D.9 QC milestones `MS` (L791; also tasks md L7) — `[ms, description, n]`
M0 "Scaffolding: cost and instrument fields, schemas, do-not-build" 15 · M1 "Data layer: point-in-time store, staleness, calendars" 23 · M2 "Risk layer: min() composition, hedge state" 9 · M3 "Estimator harness and challenger gate" 5 · M4 "Factor sleeves: R-03, R-04, R-15" 7 · M5 "Engine and events: caps, ladder, annotations, fill model" 15 · M6 "Context log and break flags" 6 · M7 "Gate package frozen, then card runs (Korea card here)" 30 · M8 "Forward records, retirements, workflow" 13 · M9 "Quant Lab: FHS/EVT, replay library" 4 · M10 "Deferred sleeves" 2 (= 129).

### D.10 QC owner decisions `OWN` (L797; canonical table SPEC L65–76 — the page defaults match)
D1 "Korea concentration template" → "MSCI 25/50: one name ≤ 22.5% after buffer; names above 4.5% ≤ 45% together" · D2 "Drawdown hard-stop level" → "−15% of book NAV from the high-water mark since the last re-arm" · D3 "Calm-state reversal down-weight (a principle change)" → "Not adopted: principle P3 stands" · D4 "Book-level false-demotion budget" → "At most 10% a year across all statistical triggers" · D5 "Whether, and on which line, to run a US sleeve" → "No US sleeve until decided; the US cards stay in FORWARD-SIM" · D6 "CDaR-guard calibration" → "Frozen now: the lowest-placebo-false-pass rule, used only if a negative control passes".

### D.11 QC `FILES` (L801) — file-role map
`QUANTGEN_MACRO_INTEGRATION.md` "Spec v2.0 for Claude Code: 35 rules, schemas, the frozen gate package, tests and golden values. Start with its Quick start." · `QUANTGEN_V2_CLAUDE_CODE_TASKS.md` "129 tasks from M0 to M10 with acceptance tests and dependencies; the same tasks as JSON." · `QUANTGEN_Quant_Council_Report.md` · `QUANTGEN_MACRO_BACKLOG.md` "Backlog v2.0: the council queue with settling tests, the failure archive, data acquisitions and the data-quality log." · `QUANTGEN macro overlay research.md` · "Council record" (QF papers, cross-examinations, data labs, chairs' rulings, ledger, adversarial-spec rounds — "kept in the research notes", i.e. NOT shipped in this folder).

### D.12 QC "What the review changed" (L386–392) — verbatim bullets
"HALT is per book. Only an acting input can halt its own book. Risk-model, context and forward-sim failures fall back or are logged." · "Schemas are the contract. Every rule output has a field, and every example in the spec validates." · "Clocks are effective-dated. KRX close bounds are 06:00:30Z from June 2015 to July 2016 and 06:30:30Z after, with exchange-specific bounds elsewhere." · "The selection factor is computed, not declared. Every distinct configuration counts, the data cut-off is pinned to the last official closes (KR 2 Oct, US 1 Oct 2026), and the larger factor binds." · "Governance cannot be gamed quietly. Verdicts carry the package hash, forward records are append-only, an operator kill counts against the record, and a redesign is allowed only once."

### D.13 QC evidence captions carrying numbers (L305–337) — page-only phrasings
- c-kvt: static book exposure 0.85; "DL-A's definitive cell: drawdown 12.7 pp better than the static book, tail-exposure ratio 0.68, non-inferiority p 0.052"; "July 2026 carries about half of the episode benefit, and 2016–25 alone is a REJECT"; `.now` "max drawdown −64.7% vs −45.3% (daily)".
- c-kstart: "72 monthly start dates from Feb 1997 to Jan 2003, ETF book, selection factor 1 … positive from every start (3.7 to 12.7 pp), and 71 of 72 starts pass … a counted selection factor above 1.282 turns it into INSUFFICIENT DATA"; `.now` "71 of 72 starts pass at f = 1".
- c-ustart: "44 quarterly start dates from 1990 to 2000. At 50 bp … REJECT from 43 of 44 starts. On index futures it passes from 11, needs revision from 9 and is rejected from 24"; `.now` "futures pass 11/44 · 50 bp pass 0/44".
- c-mcs: "Out-of-sample forecasts from 2001 (KOSPI, 6,342 origins) and 1995 (S&P 500, 7,985 origins), fitted on expanding windows from 1996 and 1990 … cut the vol target's vol-of-vol by 16–24%".
- c-trend: "Monthly, cash at the risk-free rate, 5 bp … drawdown 15.9 pp better than the static book, across 45 onsets … Sharpe gain fails a data-snooping test across 47 trend rules".
- c-switch: "30.8 switches a year came from a Markov-switching model first fitted on two years of KOSPI data".
- Hero `.bottom` (L238–240): "2 Oct 'close' was a mid-session print from a file written at 10:56 KST (official 7,003.74)"; "selection factor 1.26–2.87 against a 1.282 threshold".
- #debate data labs (L285–288): "reproduced all 385 published golden quantities"; "28 tests: 19 replicated, 6 partly replicated, 3 corrected, none failed"; "R-03 passes at 0.98 and R-04 fails at 0.77".

### D.14 ML `nodes` — all 60 (JSON; md lists only the top 8 by focus, research report L181–190; `dest` fields are the 2 Oct spec v1.x routing, see Ambiguities)

| id | cls | fp | fe | ps | es | data | dest | label | key |
|---|---|---|---|---|---|---|---|---|---|
| N-01 | CORE-LINK | 6 | 10 | Strong | Strong | Supports | SPEC §1 P1; §5 R-13 context log | Released macro quantities (IP, payrolls, GDP, exports) lag prices: only timestamped market-priced inputs may act; macro quantities are context | returns->dIP p=2e-8 vs dIP->returns p=0.04; KOSPI leads exports 4-7m (corr 0.52 at k=-5) |
| N-02 | CORE-LINK | 3 | 13 | Strong | Strong | Supports | SPEC §1 P2; §5 R-02 | Overlay is de-risk-only: multipliers in [0.5,1.0], vol-target weights capped at 1.0, 0x only from the fail-closed risk engine; overlay never trades; every multiplier declares active vs total basis | KOSPI VT cap1.5 SR 0.534 vs cap1.0 0.638 (R4); MS 0.5/1 vs 0/1 SR 0.554 vs 0.390 (US) |
| N-03 | CORE-PROHIBITION | 3 | 5 | Refuted | Refuted | Contradicts | SPEC §10; BACKLOG failure archive | Upward multipliers (>1.0) and the prior four-state trend x stress table add value | book -0.07 (share 0.23); mom at 1.425x into Nov-2020 (-12.0%) and 1.50x into Jul-2026 (-10.9%) |
| N-04 | CORE-LINK | 13 | 10 | Strong | Strong | Supports | SPEC §1 P3; §5 R-08 | Implied vol and credit-spread changes add out-of-sample variance information (US, horizons up to 1 month); no stress variable forecasts lower returns. Stress variables size risk only through a fitted forecast and block new entries; they never cut-and-re-add existing exposure | VIX/VIX3M slope -> 21d RV t 7.17 alone, ~4 given current RV, vs -> 21d return t 0.04; no return predictor survives BH-10%; cut-and-re-add -0.088 SR; block-only 0.000 |
| N-05 | CORE-PROHIBITION | 2 | 3 | Refuted | Refuted | Contradicts | SPEC §10; BACKLOG failure archive | Momentum or direction switches driven by external stress flags (VIX-TS -> mom 0x/halved, reversal 1.5x; post-clear 0.5x schedule) add value | VIX-TS mom switch -0.15 (2020-26, share 0.05), -0.19 on top of vol scaling; post-clear schedule -0.158 |
| N-06 | CORE-LINK | 6 | 5 | Strong | Strong | Supports | SPEC §5 R-03 (BUILD NOW) | Own-volatility scaling of cross-sectional momentum is mandatory | Q1b cap2: SR 0.40->0.91; R4 spec cap1.0/12%: 0.40->0.71 (+0.31, share 1.00), MDD -63%->-28% |
| N-07 | CORE-LINK | 5 | 5 | Moderate | Strong | Mixed | SPEC §5 R-04 (BUILD NOW, Tier A-provisional) | Daniel-Moskowitz bear-state gate (24m market return<0 AND 126d market vol in top tercile) as a floored 0.5 add-on on top of vol scaling | JFE T7 dynamic OOS 1.194 vs cvol 1.041 (1934-2013); R4 floor 0.5 adds +0.084 over VS cap1 (share 0.996), ex-2008-09 +0.056 |
| N-08 | CONTESTED | 2 | 1 | Split | Split | Mixed | BACKLOG BL-C01 (exec K2); interim floor 0.5 | D&M gate floor level (0 vs 0.25 vs 0.5) and robustness once 2008-09 is removed | P2 ex-2008-10 spell +0.20->+0.03 vs Q1b ex-crisis +0.11; R4 floor-0.5 add-on ex-2008-09 +0.056 (share 0.97) |
| N-09 | CORE-LINK | 5 | 11 | Strong | Strong | Supports | SPEC §5 R-05 (BUILD NOW) | Reversal and quality stay at 1.0x in every state (no stress up-weight, never cut); reversal entries go through the closing auction | ST_Rev 59.2%/yr at 34.8% vol (SR 1.70) on the true VIX>=VIX3M flag vs 1.8% at 12.3% (SR 0.15); mu/sigma2 4.90 vs 1.20, so 1.0x rests on P2; 1.5x rules -0.05 to -0.20; RMW 1.5x -0.01 |
| N-10 | CONTESTED | 3 | 4 | Opposes (never cut; gross) | Split | Mixed | BACKLOG BL-C02 (exec S5) | Reversal entries should be blocked in fast stress (execution costs) rather than run at 1.0x | gross SR 1.70 vs 0.15 on the true VIX>=VIX3M flag; KOSPI next day after a -5% day +1.71% (n=23, 2015-26) but -0.01% (n=81, 1997-2026); costs unmeasured |
| N-11 | CORE-PROHIBITION | 10 | 5 | Refuted | Refuted | Contradicts | SPEC §10; BACKLOG failure archive | Macro-variable factor/gross gates (curve re-steepening and steepeners, real-rate level or 63d change, credit-triggered factor weights, rates-stress momentum cut, level triggers) add value | curve cut -0.09 (share 0.00); real-rate gate -0.04 (mom SR 0.88 when real rates rose); credit gate -0.05 (2020-26); 10y>5.25% -0.032 |
| N-12 | CORE-LINK | 6 | 5 | Moderate | Strong | Supports | SPEC §1 P6; §8 G3 | Thresholds are set on changes or expanding/trailing percentiles, never on levels calibrated to today; scale breaks need a pre-declared re-anchoring event | 10y>5.25% true on 93.6% of 1990s days, none 2008-25; VKOSPI-type >=30 on 88% of 2026; trailing-3y p90 still 72% of 2026 |
| N-13 | CONTESTED | 4 | 3 | Strong (variance-only) | Split | Mixed | BACKLOG BL-C03 (exec K3); spec: context only | Credit-spread change: variance/entry-block input only (late, mean-free) vs a slow flag that scales existing exposure | BAA +50bp/21d fires after a median 57% of the 12m drawdown; fwd 63d +0.8%; HY OAS on FRED only since 2023-10 |
| N-14 | CORE-LINK | 8 | 9 | Strong | Strong | Mixed | SPEC §5 R-06 (BUILD NOW) | A per-market continuous vol target capped at 1.0 is the primary risk control (Korea SMA20/20%, US SMA20/15%); regime overlays are slow-bear insurance that pay a V-rebound and bull-market tax | R4 KOSPI VT20 cap1 SR 0.641 vs 0.637 (2016-26); Jul-26 -12.2% vs -38.6%; 2016-25 dSR -0.077 (share 0.06); H1-26 +51.7% vs +101.1%; regime-overlay exits lag troughs 46-179 sessions |
| N-15 | CONTESTED | 4 | 3 | Weak (indirect) | Split | Mixed | BACKLOG BL-C04 (exec S4) | The vol estimator should be asymmetric (slow and floored to cut, fast to restore) rather than SMA20 | re-entry 214/121/68/62 sessions (E5 estimator) vs 88/40/29/27 (VT20); KOSPI SMA60 SR 0.550 vs SMA20 0.638 |
| N-16 | CORE-LINK | 3 | 10 | Strong | Strong | Supports | SPEC §1 P4; R-06; R-07 | Korea stress inputs must be local (own vol, concentration, leverage); US macro/VIX/credit states were blind to the Jul-2026 KOSPI crash | 22 Jun-30 Jul 2026 KOSPI -38.6% vs S&P -0.5%, KRW +7.4%, VIX max 20.66, 0 VIX>=VIX3M days, HY +12bp |
| N-17 | CORE-LINK | 3 | 5 | Strong | Strong | Supports | SPEC §5 R-07 (BUILD NOW) | KOSPI is a two-stock memory-semis book: cap the Samsung + SK hynix pair and semis exposure; treat Korea exposure as semis exposure | pair 55.5% of KOSPI cap (22% end-2023); ~65-69% of 2025-26 index-point move; implied ~51% on 2 Oct 2026 (51-54% by anchor) |
| N-18 | CORE-PROHIBITION | 1 | 12 | Refuted | Refuted | Contradicts | SPEC §10; BACKLOG failure archive | Korea gates built from US/global inputs (prior SOX60 x KRW20 gate, SOX trend gate, AI-hardware gate, US stress row on KOSPI, refined KRW gates) add value | prior gate +0.31 with look-ahead -> +0.05 implementable, -0.16 (2024-26); SOX-only -0.22 (2024-26); US stress row on KOSPI -0.15 |
| N-19 | UNTESTED | 3 | 12 | Strong (need); untested | Moderate | Untested | BACKLOG BL-U01 (exec K7, K8) | Korea needs a local leverage/flow/semis-cycle state (margin debt, leveraged-ETF AUM, investor-type flows, DRAM-guide momentum) | single-stock leveraged ETFs listed May-2026; retail +KRW8.54tn on the -9.99% day; DRAM guides +93-98% -> +13-18% (n=1) |
| N-20 | CONTESTED | 4 | 6 | Weak (indirect) | Split | Mixed | BACKLOG BL-C05 (exec S6, K4) | Korea discrete local flags (absolute vs scale-free; -5% day -> 0.5x for 3 sessions; sidecar/CB gross cuts) add value beyond the continuous vol target | time-stop +0.55 in 2026 vs -0.06 in 2016-25 (share 0.004); trailing-3y p90 exceeded on 72% of 2026 days |
| N-21 | CONTESTED | 1 | 2 | Split | Refuted (direction) | Untested | BACKLOG BL-C06 | Foreign/institutional flows still lead KOSPI under the 2026 retail-leverage structure (flow-conditioned weights or direction signal) | H1-2026 foreigners -KRW148.3tn while KOSPI +~101%; Sep-2026 -KRW21.5tn while KRW +12% |
| N-22 | CONTESTED | 4 | 7 | Split | Moderate | Mixed | SPEC §5 R-11 SHADOW (no capital); BACKLOG BL-S01 promotion | USD/KRW 20d > +3% -> Korea gross 0.75x (one-sided, honest publication lag) | R4 0.75x: +0.032 (share 0.967) 2016-26; +0.042 on top of VT20 (0.977); +0.016 with +1 session or Yahoo timing; REJECT on 1997-2026 (54 strict-H.10 onsets) |
| N-23 | CORE-LINK | 4 | 6 | Strong | Strong | Supports | SPEC §10 (rate-differential FX models); R-09/R-11 notes | KRW is a flow/terms-of-trade currency: rate differentials do not forecast it; KOSPI-KRW sign is horizon- and timestamp-dependent; no hard-wired "foreign selling => weak KRW" | USD/KRW monthly R2 0.022 on rate differential (2008-26); Fama b -1.15 post-float; Q3-2026 KRW +12.4% while foreigners sold KRW21.5tn |
| N-24 | ONE-SIDED | 5 | 4 | Weak (indirect) | Moderate | Supports | SPEC §5 R-12 SHADOW (no capital); BACKLOG BL-S02 promotion | US 10y +40bp/20d -> 0.5x on US duration-sensitive gross | R4 +0.038 on BH (0.98), +0.037 on VT15 cap1 (0.97); +0.010 (full) at +1 business day, compliant via the Treasury par-yield channel; -0.000 at strict H.15 +2bd; REJECT at every timing and cost |
| N-25 | CONTESTED | 3 | 11 | Split | Split | Mixed | BACKLOG BL-C07 (exec K1, K5) | Rates/inflation-conditioned de-risk beyond S2: inflation-conditional US-rates input for Korea/Asia; macro-conditioned overlay floor; 2y market-implied repricing | core PCE>=3%: EWMA dSR +0.14 vs +0.05 (CIs include 0); UST10 +25bp KOSPI +0.115 exploratory vs +40bp 12 onsets +0.002; 2y repricing +0.02-0.04 |
| N-26 | CORE-LINK | 6 | 9 | Strong | Moderate | Supports | SPEC §5 R-13 context log | 2026 is a real-yield/term-premium regime: log changes in DFII10, Kim-Wright term premium and MOVE; breakevens as monitor; FOMC-day risk sits in the long end; context and risk attribution only | 2026 YTD 10y +111bp: TIPS +100, BE +11; KW TP 1.02; 5.29% = highest close since 14 May 2002; 30y +11bp on 29 Jul 2026 FOMC (rank 1/86) |
| N-27 | CONTESTED | 4 | 3 | Split | Split | Mixed | BACKLOG BL-C08 (exec K9) | Duration-sensitive tilts under real-rate shocks (long-duration vs value; rates-shock quality tilt; NDX tilt conditional on a rising dollar) | NDX +0.10 (2007-26) but -0.01/-0.04 in 2024-26; RMW 1.5x under rates stress +0.094 (2020-26); lagged HML-dDFII10 t 0.62 ex-2022 |
| N-28 | CORE-LINK | 3 | 2 | Strong | Strong | Supports | SPEC §5 R-09 hedge_state | Stock-bond correlation sign follows inflation: no duration-hedge credit when core PCE >= 3% or the 63d correlation > 0 | pooled corr -0.29 (<2%), +0.21 (>=3%); bonds +6.4bp on worst-5% days 2000-20 vs 0.0bp 2021-26; corr63 +0.53 on 30 Sep 2026 |
| N-29 | CORE-LINK | 4 | 4 | Strong | Strong | Supports | SPEC §5 R-09 hedge_state | The dollar is a conditional haven: classic risk-off = broad USD up AND UST yields down; USD down with equities down is a hedge-failure flag, never an equity de-risk | USD up in 10 of 11 S&P drawdowns; Apr-2025 DXY -3.9%, 10y +28bp, S&P -5.4%; USD-down & eq-down weeks then +7.27%/13w vs +2.84% |
| N-30 | CORE-LINK | 10 | 7 | Strong | Strong | Supports | SPEC §5 R-13 context log; §10 (as gates) | Slow macro models (Sahm, 10y-3m, Estrella-Trubin probit, Taylor-rule residual range, growth x inflation quadrant) are logged priors, never gates | Sahm 0.53 Jul-2024, no recession in 26 months; 534-day inversion; probit 0.744 May-2023; policy 0.4-2.3pp below rules |
| N-31 | CORE-PROHIBITION | 6 | 0 | Refuted | Silent | Contradicts | SPEC §10 (one panel + data); BACKLOG failure archive | Fixed-coefficient textbook relations (Okun, Phillips, sacrifice ratio, M2->CPI) can drive signals | Okun beta -0.407 -> -0.05 (break ~2011); Phillips 2011-25 slope +0.04, OOS RMSE 2.15 vs 1.79; sacrifice 5.5 pp-yrs implied vs -1.57 |
| N-32 | CONTESTED | 9 | 0 | Split | Silent | Mixed | BACKLOG BL-C09; interim log only | Policy-communication states (breakeven credibility gauge, J-K FOMC policy/information classes, "good news is bad news" sign) can drive equity-gross rules | gauge 0.16 in 2022 (Spearman -0.48); INFO_NEG +3.99%/10d (5 of 5); payroll-day corr -0.74 (2017), +0.14 (2022), -0.73 (2026) |
| N-33 | CORE-LINK | 2 | 8 | Strong | Strong | Supports | SPEC §5 R-14 (BUILD NOW as family config) | Time-series trend runs as a diversified vol-scaled sleeve exempt from overlay multipliers; weak per index (KOSPI/KOSDAQ low weight); not fast-crash protection (slow-bear protection with century-long evidence) | 12-equity trend book SR 0.449 at cap 1, corr S&P 0.03 (0.49 / 0.08 at cap 2; 0.34-0.36 in 2013-26); KOSPI SMA10m vs static dSR +0.076, dMDD +4.1pp, daily tail 0.93; 2020 -16.7% vs S&P +16.3% |
| N-34 | CONTESTED | 4 | 8 | Weak (200-DMA data-mined) | Moderate (shadow) | Mixed | BACKLOG BL-C10 (exec S3) | A trend axis with hysteresis (band, confirmation, dwell, own-vol exit) should scale market gross | switches 6.0 -> 3.4 -> 2.45 -> 0.89/yr; silent in Mar-2026 (US) and Jul-2026 (KOSPI min 0.978x 200DMA) |
| N-35 | ONE-SIDED | 3 | 0 | Strong | Silent | Supports | SPEC §5 R-15 config prior (flagged); BACKLOG BL-O01 verification | Regional cross-sectional momentum priors: Japan ~0, US only when vol-scaled, Europe / Asia-Pac ex-Japan / EM strong | French WML 1990-2026 SR: US 0.33, Japan 0.07 (t 0.4), APxJ 0.71, Europe 0.78, EM 0.93; R4 VS cap1 Japan 0.07->0.20 |
| N-36 | UNTESTED | 1 | 5 | Moderate | Weak (indirect) | Untested | SPEC §5 R-15 prior flagged UNVERIFIED; BACKLOG BL-U02 | Korea: 12-1 momentum weak/negative; favour 1-5d and 1-2m reversal and 12-7/residual momentum at low weight | Korean 1m reversal Fama-MacBeth slope -2.950 (t -3.77), not a return; pret(12,7) 0.531%/m, 1999-2021 (literature); no KRX stock data locally |
| N-37 | CORE-LINK | 9 | 12 | Moderate | Strong | Supports | SPEC §5 R-10 (BUILD NOW) | Scheduled events: no swing blackouts; size down rather than black out; short intraday no-new-entry windows; no pre-FOMC long; BoK days quiet; calendar entries carry scheduled/released/cancelled/delayed | FOMC days 2021-26 +0.6 vs +5.3bp at 1.3x \|r\|; pre-FOMC drift 44.5 -> 9.2bp n.s.; BoK days 0.82x \|r\|; Oct-2025 CPI cancelled |
| N-38 | CORE-PROHIBITION | 9 | 8 | Refuted (P1 dissent) | Refuted | Contradicts | SPEC §10; BACKLOG failure archive | 24-hour pre-event blackouts and swing-book blackouts (including KRX quad witching) add value | 24h FOMC blackout swallows the preceding KRX session (FOMC 03:00/04:00 KST); quad witching \|r\| 0.851% vs 0.894% (t -0.38) |
| N-39 | ONE-SIDED | 9 | 12 | Moderate | Opposes | Untested | BACKLOG BL-O02 | Momentum new entries x0.5-0.7 on scheduled decision days | FOMC days \|r\| 97 vs 74bp (1.3x) 2021-26 vs S&P FOMC-day mean +5.5 vs +5.1bp (2015-26) |
| N-40 | CORE-LINK | 11 | 10 | Strong | Strong | Supports | SPEC §5 R-10 open-gap events | US overnight information (SOX, S&P, dUST10, US releases, FOMC at 03-04 KST, hyperscaler earnings) is a KOSPI opening-gap and vol input, not a regime gate | prior US session explains ~15% of KOSPI daily variance jointly (~10% from the S&P alone); SOX(t-1) beta 0.247 overall, 0.559 in 2026; dUST10(t-1) t -3.8; +17.91% on 31 Jul 2026 |
| N-41 | CORE-LINK | 11 | 9 | Moderate (mechanism) | Moderate | Untested | SPEC §5 R-10 (execution-only exception; measure with fill logs) | Korean execution conventions: no new intraday entries 09:00-09:30 KST; daily/reversal entries into the 15:20-15:30 closing auction; KRX regular-session prints only; sidecar/CB order handling | 80.9% of 9-10am VIs in first 30 min; 522 VIs on 4 Mar 2026; reversal +0.93%/m overnight vs -1.05% intraday (US 1993-2013) |
| N-42 | UNTESTED | 2 | 0 | Weak (indirect) | Moderate | Untested | BACKLOG BL-U03 (exec K6) | Anchoring-adjusted macro-surprise \|z\| -> next-open vol forecast and sizing (Korea opening gap) | surprises priced in ~5 ms; consensus ~30% weight on prior print; 7 of 21 US releases drift 30 min pre-release |
| N-43 | CORE-PROHIBITION | 2 | 3 | Refuted | Refuted | Contradicts | SPEC §10; BACKLOG failure archive | A lagged oil-price gate on equity/KOSPI gross (Brent +30%/63d; 20d > +25%) adds value | 22 episodes fwd 63d 2.67% vs 2.66% (p 0.50); 20d gate first fired 6 Mar 2026 after the -12.06% day; -0.05 (share 0.08) |
| N-44 | CORE-LINK | 10 | 5 | Strong | Strong | Supports | SPEC §5 R-10, R-16 | Oil enters the event calendar (weekend geopolitical gaps), the vol estimator and Monte Carlo stress scenarios on a named Brent series | 2026 vs 2022 at +20d: KOSPI -15.5% vs +0.4%, USD/KRW +5.2% vs +2.1%, 10y real +32bp vs -4bp; Dated vs futures gap ~$29 (7 Apr 2026) |
| N-45 | CONTESTED | 3 | 6 | Split | Opposes (20d refuted; 5d untested) | Mixed | BACKLOG BL-C11 | An oil-shock event rule (Brent 5d > +15% or 20d > +30%, real-yield conditional) should scale KOSPI gross | KOSPI -15.5% within 20 days in Mar-2026, then +68% (31 Mar-30 Jun) with oil high; 2022 S&P +7.0% |
| N-46 | CORE-LINK | 4 | 9 | Strong | Strong | Supports | SPEC §4; §5 R-01 | Point-in-time macro hygiene: vintages, calendar-based lags, fail-closed on missing months, named series, closes not intraday prints, survey publication dates | Aug-2026 CPI YoY 3.71% with shift(12) vs 3.35% correct; real-time Sahm 0.53 vs 0.50; benchmarks prelim -818k/-911k (final -598k NSA / -898k SA); 9 Mar 2026 close -5.96% vs -8.11% intraday |
| N-47 | CORE-LINK | 3 | 2 | Strong | Strong | Supports | SPEC §1 P5; §4; §5 R-01 | Cross-time-zone timestamp rule (UTC + publication time; US-session data enter KRX decisions only from the next KRX session) | prior Korea gate +0.31 (look-ahead) -> +0.05; KRW gate +0.17 -> +0.07; same-day KOSPI-KRW corr -0.39/+0.15/-0.30 by timestamp |
| N-48 | CORE-LINK | 7 | 14 | Strong | Strong | Supports | SPEC §5 R-16 | Quant Lab MC/GARCH fits parameters on an expanding (>= 10-year) window that includes 2026, tails by FHS/EVT; one vol module serves both horizons; oil and SEP-band scenarios feed Monte Carlo | KOSPI rv21 > 30% on 88% of 2026 days (mean 56.5%, max 102.6%) vs 8.6-14.5% in 2024-25; EWMA ~ GARCH at 1 day, long-window GARCH better at 5-21 days; SEP band +/-1.4pp (~70%; 90% fan +/-2.2pp) |
| N-49 | CORE-PROHIBITION | 12 | 0 | Refuted | Silent | Contradicts | SPEC §10 (one panel + data); BACKLOG failure archive | Regime-estimation and ML shortcuts (smoothed regime probabilities, unpenalised daily HMM gates, "complexity" macro timing, pre-cutoff LLM backtests) are valid | real-time MS US 16.9 switches/yr, 49% of episodes off the smoothed path (local); 0.5/1 SR 0.554 vs B&H 0.539 net 10bp (0/1 0.390), 0.285 at 50bp; RFF forecasts rho 0.93 with Nagel kernel forecasts |
| N-50 | CORE-LINK | 19 | 13 | Strong | Strong | Supports | SPEC §8 | Validation & governance: overlay dSR is statistically undetectable, so decide on pre-registered, episode-based, drawdown-first tests vs buy-and-hold and same-exposure static books, with trial counting, tiered gates, >=12-month live shadow, kill criteria and pre-declared resets after policy/scale breaks | SE(dSR) vs S 0.061 US / 0.130 KOSPI vol targets (0.02-0.035 add-on legs); +0.05 needs ~150-330 yrs; 21 stress clusters in 12 years (2008-26); all 26 overlay CIs straddle 0 |
| N-51 | CONTESTED | 3 | 9 | Split | Moderate (tiers by event count) | Mixed | BACKLOG BL-C12; interim: report both statistics | Prior-backed effects get a separate non-inferiority tier instead of the uniform multiplicity hurdle | BSC spec rule z 3.84/3.29/2.99 (one-sided hurdles 2.50 / 3.34); D&M z 1.8-2.0, z>1.96 in 0 of 18 ten-year windows; 2016-26 holdout passed 1 of 3 regions (uniform hurdle applies) |
| N-52 | CORE-LINK | 6 | 6 | Strong (carry) / Moderate (intervention) | Moderate | Supports | SPEC §5 R-17 DEFERRED (sleeve not live) | Planned FX sleeve: UIP fails; carry is a crash-prone premium sized like an option seller and de-risked on FX trend + JPY realised vol (not VIX); a confirmed intervention is a trend break with rising vol (FX momentum x0.5 for 20 sessions, stops x1.5; USD/JPY 160-164 zone) | USD/JPY Fama b -1.92 (1991-2007), 0.11 (2008-26); carry -10.6% in 18 days with VIX 12.85-16.36; vol rose in 4 of 5 interventions |
| N-53 | CONTESTED | 0 | 2 | Silent | Split | Mixed | BACKLOG BL-C13 (exec K11) | A yen shock should block new Japanese exporter longs (E3-R3 re-specified) | next 10d -0.23% vs +0.55% (18 episodes) but dSR -0.05 (share 0.17), -0.13 in 2024-26 |
| N-54 | CORE-LINK | 3 | 1 | Strong | Moderate | Supports | SPEC §5 R-17 DEFERRED (sleeve not live) | Planned crypto sleeve: own risk bucket with time-varying equity beta; BTC own trend + vol target + hard gross cap | BTC-NDX weekly corr 0.09 / 0.47-0.50 / 0.22-0.24 on Wednesday weeks, 0.06 / 0.28 / 0.25 on Friday weeks (2015-19 / 2020-22 / 2023-26); BTC -53% while NDX +22%; own 13w trend 1/0.5 +0.03 |
| N-55 | CORE-PROHIBITION | 3 | 1 | Refuted | Refuted | Contradicts | SPEC §10; BACKLOG failure archive | Net-liquidity (WALCL - TGA - RRP) or M2 rules should scale crypto or equity exposure | 1.5x/0.5x rule -0.01 (share 0.50), -0.20 (2023-26); S&P on WALCL t 25.1 in levels vs -0.40 in differences |
| N-56 | CORE-PROHIBITION | 8 | 20 | Refuted | Refuted | Contradicts | SPEC §10; BACKLOG failure archive | Street forecasts, consensus surprises at retail latency, surveys and positioning data work as timing/entry signals, and post-trigger crowding cuts protect momentum | S&P consensus abs error 17.13% (2022-25), corr 0.17; 2026 cuts forecast vs 16 Sep hike; FMS Aug-2026 published after KOSPI -25.4%; Aug-2024 mom -5.9% before trigger, +6.5% after |
| N-57 | CONTESTED | 3 | 8 | Split | Weak (context only) | Untested | BACKLOG BL-C14 | A pre-emptive positioning-based crowding cut that leads own-factor vol by >=5 days adds value | BSC weight already 0.53 (Jul-2026) and 0.31 (Nov-2020); speculative yen shorts ~JPY2tn before Aug-2024 (BIS) |
| N-58 | CORE-PROHIBITION | 0 | 15 | Silent | Refuted | Contradicts | SPEC §10 (one panel + data); BACKLOG failure archive | Calendar and supply-timing effects (quarter-end tilts, KRW seasonality, export-print tilt, expiry-close fade, aggregate issuance, IPO windows, buyback blackouts) time markets | April KRW t -0.64; quarter-end fade t -1.26; expiry next-day continuation corr +0.33; Ritter detrended t -0.3 to -1.4; buyback blackout t -0.26 |
| N-59 | ONE-SIDED | 0 | 8 | Silent | Moderate | Untested | SPEC event_calendar log-only flag; exclusions BACKLOG BL-O03 | Korean supply screens (KOSPI200/MSCI change calendar flag; 60-session long-book exclusion after rights offerings; first 20 sessions after listing excluded from momentum ranks) | IPO 3-yr -24.7% (2011-24 cohorts), lock-ups -1.8%, ABBs -2.55% (US literature via E6); untested on KRX |
| N-60 | CORE-LINK | 14 | 10 | Strong | Strong | Supports | SPEC §13 evidence appendix | Corrected anchor numbers and citations propagate; refuted figures do not | D&M 0.682->1.041->1.194 (JFE T7); Ilmanen value -49%, mom -23% n.s.; KOSPI 9,114.55 / Q3 -19.33%; BoK 3.00%; 10y 5.29% highest close since 14 May 2002 |

Page-only `short` labels for the top list (ML L651): N-50 "Decide overlays on pre-registered, drawdown-first tests with trial counting, tiered gates and forward running"; N-60 "Carry corrected numbers forward; never the refuted ones"; N-04 "Implied vol and credit spreads add variance information; no stress variable forecasts lower returns: they size and block entries only"; N-40 "US overnight data are a KOSPI opening-gap and vol input, never a gate"; N-37 "No swing blackouts around scheduled events; short intraday windows and smaller size"; N-41 "Korean session conventions: no new entries 09:00–09:30, closing-auction timing". Top-6 selection rule: `cls==='CORE-LINK'` sorted by `min(fp,fe)` desc then `fp+fe` desc (L652).

### D.15 ML `EVENTS` (L657–665) — page-only dated event markers
1 `2024-08-05` "Yen carry unwind; Nikkei −12.4%" · 2 `2024-12-03` "Martial law declared in Korea" · 3 `2025-04-02` "US tariff announcement; VIX 52 by 8 Apr" · 4 `2026-02-28` "US and Israeli strikes on Iran" · 5 `2026-06-22` "KOSPI closing peak 9,114.55" · 6 `2026-07-17` "US AI-capex doubts; chip stocks fall 5%+" · 7 `2026-09-16` "Fed hikes to 3.75–4.00%". Seed for the R-10 event calendar's historical `episode`/`event` fixtures (dates only; the SPEC's own episode table at L5126 ff. is canonical).

### D.16 ML `RULES` (L732–743) — overlay-rule bars `[name, series, dSR, share_rule_beats, verdict, word]` (page-only summary of `b1`)
| rule | series | ΔSR | share | verdict |
|---|---|---|---|---|
| Momentum own-volatility scaling | momentum factor | +0.508 | 1.000 | pass "Survives (2× cap; spec caps at 1)" |
| Daniel–Moskowitz bear-market gate | momentum factor | +0.258 | 0.992 | pass "Survives (0× gate; spec floors at 0.5)" |
| Credit-spread gate: momentum 0.5× | momentum factor | +0.050 | 0.937 | revise "Fragile" |
| Momentum 0× when VIX ≥ VIX3M | momentum factor | +0.012 | 0.564 | reject "Fails (−0.15 in 2020–26)" |
| Credit-spread gate: quality 1.5× | profitability factor | −0.008 | 0.372 | reject "Fails" |
| Real-rate gate on momentum (2003+) | momentum factor | −0.040 | 0.101 | reject "Hurts" |
| Reversal 1.5× when VIX ≥ VIX3M | short-term reversal | −0.053 | 0.181 | reject "Hurts" |
| Prior four-state regime table | factor book | −0.073 | 0.233 | reject "Hurts" |
| Curve re-steepening gross cut | factor book | −0.089 | 0.005 | reject "Hurts" |
| Prior four-state table on reversal | short-term reversal | −0.199 | 0.017 | reject "Hurts" |

### D.17 ML `b1` — 37 rows (JSON; page-only; gross, US daily 1990–2026, 1,000 block resamples)
`rule | series | static_sharpe | rule_sharpe | dSR | share_rule_beats | static_maxdd | rule_maxdd`
```
i_BSC_volscale | Mom | 0.399 | 0.907 | 0.508 | 1.0 | -0.633 | -0.28
i_BSC_volscale | BOOK | 1.358 | 1.79 | 0.432 | 1.0 | -0.233 | -0.12
ii_DM_bear_gate | Mom | 0.399 | 0.657 | 0.258 | 0.992 | -0.633 | -0.348
ii_DM_bear_gate | BOOK | 1.358 | 1.615 | 0.257 | 0.993 | -0.233 | -0.12
iii_VIXTS_spliced | Mom | 0.399 | 0.411 | 0.012 | 0.564 | -0.633 | -0.544
iii_VIXTS_spliced | ST_Rev | 1.253 | 1.2 | -0.053 | 0.181 | -0.361 | -0.477
iii_VIXTS_spliced | BOOK | 1.358 | 1.362 | 0.004 | 0.545 | -0.233 | -0.227
iii_VIX30_proxy | Mom | 0.399 | 0.544 | 0.145 | 0.898 | -0.633 | -0.378
iii_VIX30_proxy | ST_Rev | 1.253 | 1.164 | -0.09 | 0.039 | -0.361 | -0.474
iii_VIX30_proxy | BOOK | 1.358 | 1.449 | 0.091 | 0.793 | -0.233 | -0.18
iv_credit_gate | Mom | 0.399 | 0.449 | 0.05 | 0.937 | -0.633 | -0.529
iv_credit_gate | RMW | 0.48 | 0.472 | -0.008 | 0.372 | -0.418 | -0.443
iv_credit_gate | BOOK | 1.358 | 1.413 | 0.055 | 0.933 | -0.233 | -0.216
v_curve_resteep_gross | Mom | 0.399 | 0.382 | -0.018 | 0.283 | -0.633 | -0.586
v_curve_resteep_gross | ST_Rev | 1.253 | 1.195 | -0.059 | 0.033 | -0.361 | -0.328
v_curve_resteep_gross | RMW | 0.48 | 0.422 | -0.057 | 0.055 | -0.418 | -0.408
v_curve_resteep_gross | Mkt-RF | 0.522 | 0.536 | 0.014 | 0.688 | -0.592 | -0.562
v_curve_resteep_gross | BOOK | 1.358 | 1.269 | -0.089 | 0.005 | -0.233 | -0.236
v_curve_resteep_gross_lb252 | Mom | 0.399 | 0.374 | -0.025 | 0.183 | -0.633 | -0.633
v_curve_resteep_gross_lb252 | ST_Rev | 1.253 | 1.214 | -0.04 | 0.034 | -0.361 | -0.328
v_curve_resteep_gross_lb252 | RMW | 0.48 | 0.445 | -0.034 | 0.145 | -0.418 | -0.408
v_curve_resteep_gross_lb252 | Mkt-RF | 0.522 | 0.532 | 0.01 | 0.725 | -0.592 | -0.591
v_curve_resteep_gross_lb252 | BOOK | 1.358 | 1.296 | -0.062 | 0.029 | -0.233 | -0.233
vi_realrate_gate | Mom | 0.105 | 0.065 | -0.04 | 0.101 | -0.633 | -0.609
vi_realrate_gate | BOOK | 0.486 | 0.46 | -0.027 | 0.132 | -0.233 | -0.234
vii_USD_gate_USplacebo | Mom | 0.099 | 0.12 | 0.021 | 0.609 | -0.633 | -0.499
vii_USD_gate_USplacebo | BOOK | 0.5 | 0.55 | 0.049 | 0.761 | -0.233 | -0.192
viii_4state_priordoc | Mom | 0.399 | 0.496 | 0.097 | 0.87 | -0.633 | -0.526
viii_4state_priordoc | ST_Rev | 1.253 | 1.054 | -0.199 | 0.017 | -0.361 | -0.445
viii_4state_priordoc | RMW | 0.48 | 0.524 | 0.045 | 0.872 | -0.418 | -0.42
viii_4state_priordoc | BOOK | 1.358 | 1.285 | -0.073 | 0.233 | -0.233 | -0.236
viiib_4state_derisk_only | Mom | 0.399 | 0.461 | 0.062 | 0.943 | -0.633 | -0.495
viiib_4state_derisk_only | BOOK | 1.358 | 1.459 | 0.101 | 0.994 | -0.233 | -0.193
viiic_4state_credit50bp | Mom | 0.399 | 0.501 | 0.101 | 0.887 | -0.633 | -0.538
viiic_4state_credit50bp | ST_Rev | 1.253 | 1.076 | -0.177 | 0.046 | -0.361 | -0.445
viiic_4state_credit50bp | RMW | 0.48 | 0.524 | 0.045 | 0.872 | -0.418 | -0.42
viiic_4state_credit50bp | BOOK | 1.358 | 1.279 | -0.079 | 0.209 | -0.233 | -0.256
```

### D.18 ML `outperf` — 16 rows (JSON, hidden; R-03/R-04 goldens; values are strings)
```
French Mom daily | US_KIS_50bp x2 legs | R-03 VS vs unscaled | dSR | 0.27284996966111913
… | R-03 VS vs unscaled | p_one_sided_block10 | 0.0005
… | R-03 VS vs unscaled | p_one_sided_blockPW | 0.0
… | R-03 VS vs unscaled | block_PW | 251.0
… | R-03 VS vs unscaled | sharpe_at_2x | 0.6307832741541421
… | R-03 VS vs unscaled | years_positive | 0.7027027027027027
… | R-03 VS vs unscaled | n_years | 37.0
… | R-04 DM on VS | dSR | 0.07238718782305364
… | R-04 DM on VS | p_one_sided_block10 | 0.018
… | R-04 DM on VS | p_one_sided_blockPW | 0.01
… | R-04 DM on VS | block_PW | 229.0
… | R-04 DM on VS | sharpe_at_2x | 0.6913226770369109
… | R-04 DM on VS | years_positive | 0.7297297297297297
… | R-04 DM on VS | n_years | 37.0
French Mom daily | R-04 DM on VS | raw_spell_onsets | 7.0
French Mom daily | R-04 DM on VS | onsets_declustered_126s | 6.0
```

### D.19 ML `protective` — 302 rows (JSON, hidden; v1.2 PC-1…PC-6 checks on 2016–26, not the v2 PC-1′ package). Variants: `R-06 KR VT20 | KRX ETF 3bp`, `R-06 KR VT20 | KRX stock 35bp`, `R-06 US VT15 | US KIS 50bp`, `R-11 KRW on VT20 strict-H.10 | KRX ETF 3bp`, `R-11 KRW on VT20 strict-H.10 | KRX stock 35bp`, `R-11 KRW on VT20 value | KRX stock 35bp`, `R-12 rates on VT15 +2bd | US KIS 50bp`, `R-12 rates on VT15 value | US KIS 50bp`. Metrics (30): `PC1_dMDD_vs_static, PC1_pass, PC2_pass, PC2_tail_exposure_ratio, PC3_PW_block_d, PC3_PW_block_d2, PC3_block_used, PC3_dSR, PC3_lcb10_blockPW, PC3_p_ni_block10, PC3_p_ni_blockPW, PC3_pass, PC4_max_episode_share, PC4_n_positive_episodes, PC4_pass, PC5_n_years, PC5_pass, PC5_years_positive, PC6_pass, PC6_plateau_share, avg_multiplier, dSR_vs_static_point, mdd_off, mdd_on, mdd_static_same_exposure, outperf_p_one_sided_vs_off_block10, sharpe_off, sharpe_on, sharpe_static_same_exposure, years_lagging_static_share` (PC6 rows exist only for the three R-06 variants; `period` `2x` rows carry only the first nine metrics).

Pass matrix at `1x` (1 = pass):

| variant | PC1 | PC2 | PC3 | PC4 | PC5 | PC6 | key values |
|---|---|---|---|---|---|---|---|
| R-06 KR VT20 / ETF 3bp | 1 | 1 | 0 | 0 | 1 | 1 | avg_multiplier 0.9250062551771919; sharpe_on 0.6380531424799194; sharpe_off 0.6372363091964123; mdd_on −0.36848726412771593; mdd_off −0.438978673615093; mdd_static −0.41287549522922073; PC1_dMDD 0.044388231101504805; PC2_tail 0.8179922766410586; PC3_p_ni_block10 0.246; PC3_p_ni_blockPW 0.208; PC3_block_used 101; PC4_max_episode_share 0.5906645617776514; PC5_years_positive 0.7272727272727273 (11 y); PC6_plateau_share 0.625; outperf_p 0.5155 |
| R-06 KR VT20 / stock 35bp | 1 | 1 | 0 | 0 | 1 | 0 | sharpe_on 0.6084981156352368; PC1_dMDD 0.041185356465494816; dSR_vs_static −0.028738193561175462; p_ni_block10 0.3215; PC6_plateau 0.375 |
| R-06 US VT15 / KIS 50bp | 0 | 1 | 0 | 1 | 1 | 0 | avg_multiplier 0.8896508664359063; sharpe_on 0.5052628295658225; sharpe_off 0.5337436880630693; PC1_dMDD 0.0017954230647442282; PC2_tail 0.7938407697343354; p_ni_block10 0.1185; PC4_max_share 0.48925671943774857 (6 episodes); 37 y, 0.7027 positive |
| R-11 KRW strict-H.10 / ETF 3bp | 0 | 0 | 1 | 0 | 1 | — | avg_multiplier 0.9772036474164134; PC1_dMDD 0.0010531592445193194; PC2_tail 1.0000706913615156; PC3_dSR 0.011741102594245767; PC4_max_share 0.7015722999787942 |
| R-11 KRW strict-H.10 / stock 35bp | 0 | 0 | 1 | 0 | 1 | — | PC1_dMDD −0.001612602820596054; PC3_dSR −0.006930913766344027 |
| R-11 KRW value / stock 35bp | 0 | 0 | 1 | 0 | 1 | — | avg_multiplier 0.9775835866261399; PC1_dMDD 0.011265953386393024; PC2_tail 0.9861204348184526 |
| R-12 rates +2bd / KIS 50bp | 0 | 0 | 0 | 0 | 1 | — | avg_multiplier 0.9691832755632582; PC1_dMDD −0.03522850253703658; PC2_tail 0.9939120511599642; PC3_dSR −0.12014626460038325; p_ni_block10 0.823 |
| R-12 rates value / KIS 50bp | 0 | 0 | 0 | 0 | 1 | — | PC1_dMDD −0.007543331229916905; PC2_tail 0.9894550464462424; PC3_dSR −0.07616189492064623; PC4_max_share 0.8137745749143994 |

### D.20 ML `snapshot` — 38 rows (JSON; page renders 17 via the `want` map L686). `variable | latest_date | latest | unit | chg_3m | chg_12m | chg_unit | pctile_vs_history | history_from | history_n`
```
Unemployment rate (UNRATE) | 2026-08-01 | 4.1 | % | -0.2 | -0.2 | pp | 16.856 | 1990-01 | 439
U-6 (U6RATE) | 2026-08-01 | 7.7 | % | -0.4 | -0.4 | pp | 21.611 | 1994-01 | 391
Prime-age LFPR (LNS11300060) | 2026-08-01 | 83.4 | % | -0.5 | -0.3 | pp | 65.034 | 1990-01 | 439
Payrolls 3m avg chg (PAYEMS) | 2026-08-01 | 71.333 | k/mo | -70.333 | 80.0 | k/mo | 24.659 | 1990-01 | 440
JOLTS openings (JTSJOL) | 2026-08-01 | 7079.0 | k | -6.077 | 2.312 | % | 75.243 | 2000-12 | 309
Openings per unemployed (JTSJOL/UNEMPLOY*) | 2026-08-01 | 1.007 | ratio | -0.025 | 0.069 | ratio | 26.923 | 2019-01 | 91
Quits rate (JTSQUR) | 2026-08-01 | 1.9 | % | -0.1 | -0.1 | pp | 33.981 | 2000-12 | 309
Initial claims 4wk avg (ICSA) | 2026-09-26 | 200.0 | k | -24.5 | -36.75 | k | 0.34 | 1990-01 | 441
Avg hourly earnings YoY (CES0500000003) | 2026-08-01 | 3.086 | % | -0.249 | -0.889 | pp | 53.632 | 2007-03 | 234
Sahm real-time (SAHMREALTIME) | 2026-08-01 | -0.07 | pp | -0.17 | -0.2 | pp | 18.793 | 1990-01 | 439
Real GDP growth q/q SAAR (A191RL1Q225SBEA) | 2026-04-01 | 2.2 | % | -0.3 | -1.8 | pp | 36.301 | 1990-01 | 146
CPI YoY (CPIAUCSL) | 2026-08-01 | 3.353 | % | -0.814 | 0.414 | pp | 77.563 | 1990-01 | 439
Core CPI YoY (CPILFESL) | 2026-08-01 | 2.446 | % | -0.377 | -0.666 | pp | 56.606 | 1990-01 | 439
Core PCE YoY (PCEPILFE) | 2026-08-01 | 3.008 | % | -0.154 | 0.156 | pp | 83.523 | 1990-01 | 440
Core PCE 6m annualised | 2026-08-01 | 2.744 | % | -1.113 | 0.097 | pp | 78.977 | 1990-01 | 440
UMich 1y infl. expectations (MICH) | 2026-08-01 | 4.0 | % | -0.8 | -0.8 | pp | 86.25 | 1990-01 | 440
UMich sentiment (UMCSENT) | 2026-08-01 | 51.7 | idx | 6.9 | -6.5 | idx | 1.477 | 1990-01 | 440
Effective fed funds (DFF) | 2026-09-30 | 3.88 | % | 0.25 | -0.21 | pp | 59.07 | 1990-01 | 441
2y UST (DGS2) | 2026-09-30 | 4.88 | % | 0.74 | 1.28 | pp | 73.923 | 1990-01 | 441
10y UST (DGS10) | 2026-09-30 | 5.29 | % | 0.85 | 1.13 | pp | 70.975 | 1990-01 | 441
10y TIPS real (DFII10) | 2026-09-30 | 2.93 | % | 0.73 | 1.13 | pp | 99.474 | 2003-01 | 285
10y breakeven (T10YIE) | 2026-10-01 | 2.36 | % | 0.13 | 0.01 | pp | 71.853 | 2003-01 | 286
5y5y fwd infl. (T5YIFR) | 2026-10-01 | 2.36 | % | 0.16 | 0.05 | pp | 63.55 | 2005-01 | 262
Kim-Wright 10y term premium (THREEFYTP10) | 2026-09-25 | 1.02 | % | 0.321 | 0.513 | pp | 97.893 | 2005-01 | 261
10y-3m (T10Y3M) | 2026-10-01 | 1.07 | pp | 0.44 | 0.96 | pp | 40.158 | 1990-01 | 442
10y-2y (T10Y2Y) | 2026-10-01 | 0.46 | pp | 0.15 | -0.11 | pp | 35.52 | 1990-01 | 442
Baa-10y spread (BAA10Y) | 2026-09-30 | 1.47 | pp | -0.06 | -0.2 | pp | 2.834 | 1990-01 | 441
HY OAS (BAMLH0A0HYM2, 2023-10+) | 2026-09-30 | 3.12 | pp | 0.37 | 0.32 | pp | 55.556 | 2023-10 | 36
VIX (VIXCLS) | 2026-09-30 | 16.34 | idx | -0.11 | 0.06 | idx | 41.837 | 1990-01 | 441
MOVE (^MOVE, 2015+) | 2026-10-01 | 108.125 | idx | 39.565 | 34.625 | idx | 83.451 | 2015-01 | 142
Chicago Fed NFCI | 2026-09-25 | -0.548 | idx | -0.037 | -0.021 | idx | 45.125 | 1990-01 | 441
Broad USD (DTWEXBGS) | 2026-09-25 | 120.33 | idx | -0.6 | -0.176 | % | 84.94 | 2006-01 | 249
USD/JPY (DEXJPUS) | 2026-09-25 | 157.18 | JPY | -2.777 | 4.941 | % | 97.392 | 1990-01 | 441
USD/KRW (DEXKOUS) | 2026-09-25 | 1356.51 | KRW | -11.997 | -3.703 | % | 91.043 | 1990-01 | 441
Brent (DCOILBRENTEU) | 2026-09-29 | 113.96 | $/bbl | 59.184 | 65.159 | % | 96.032 | 1990-01 | 441
Gold (GC=F) | 2026-10-01 | 4202.3 | $/oz | 2.937 | 7.82 | % | 97.452 | 2000-08 | 314
S&P 500 (^GSPC) | 2026-10-01 | 7666.45 | idx | 2.448 | 14.234 | % | 99.688 | 2000-01 | 321
S&P 500 12m return (month-end; latest complete month Sep-2026) | 2026-09-30 | 14.399 | % | -6.462 | -1.67 | pp | 64.887 | 2001-01 | 309
```
Page-rendered subset and display names (L686): UNRATE "Unemployment rate", ICSA "Initial claims, 4-week average", CPIAUCSL "CPI inflation", PCEPILFE "Core PCE inflation", MICH "Household 1-year inflation expectations", DFF "Fed funds, effective", DGS10 "10-year Treasury", DFII10 "10-year real yield", THREEFYTP10 "Term premium, 10-year", BAA10Y "Baa minus 10-year spread", VIXCLS "VIX", DTWEXBGS "Broad dollar index", DEXJPUS "USD/JPY", DEXKOUS "USD/KRW", DCOILBRENTEU "Dated Brent ($/bbl)", GC=F "Gold ($/oz)", UMCSENT "Consumer sentiment".

### D.21 ML `phillips` (JSON) · `haven` (JSON) · `sbbucket` (JSON) — page-only numeric tables
phillips: `1960-1984 −0.39 se 0.105 r2 0.176 n 276` · `1985-2019 −0.053 / 0.059 / 0.024 / 420` · `2020-2026 −0.036 / 0.104 / 0.003 / 80` · `2021-2026 (ex-Covid 2020) 0.567 / 0.376 / 0.062 / 68` · `1960-2026 all −0.185 / 0.064 / 0.074 / 776` (spec: Δ12m core PCE on unemployment gap, HAC SE; the "all" row is excluded from the dot plot, L704).

haven `ep | spx | usd | y10(bp) | gold | krw | sell`:
```
GFC 2007-09 (peak-trough) | -54.6 | 16.7 | -178.0 | 26.8 | 67.8 | False
GFC acute Sep-Nov 2008 | -41.7 | 13.7 | -64.0 | -13.6 | 31.9 | False
Aug-2011 US downgrade/euro | -20.0 | 7.0 | -137.0 | 7.9 | 10.9 | False
Aug-2015 CNY deval | -11.2 | 1.1 | -12.0 | 3.1 | 2.9 | False
Q4-2018 Fed/QT | -19.8 | 2.4 | -33.0 | 5.1 | 0.5 | False
Mar-2020 Covid | -33.9 | 8.0 | -80.0 | -2.5 | 6.4 | False
2022 inflation bear | -25.4 | 11.0 | 228.0 | -6.8 | 19.5 | False
Aug-2024 carry unwind | -8.5 | 0.7 | -39.0 | -0.9 | -1.2 | False
Apr-2025 tariff shock | -18.9 | -0.7 | -27.0 | 1.8 | 2.6 | False
Mar-2026 Iran oil shock | -8.7 | 3.0 | 30.0 | -13.4 | 6.4 | False
Jul-Sep 2026 Asia chip selloff | -3.4 | 0.2 | 11.0 | -1.9 | -3.6 | False
```
(`sell` is `false` on every row even for Apr-2025, which the caption calls the "sell America" break — the flag is unused by the script.)

### D.22 ML Model-failure ledger (L289–306, 13 rows; the research report L108–125 has a sibling table with different column names and some different numbers)
| Model | Works when | Failed when | Why | QUANTGEN use |
|---|---|---|---|---|
| Yield-curve probit | 9 of 13 inversions since 1960 led recessions (median 10 months) | 2022–24: record inversion, 74% probability, no recession | Six-recession sample; term premium distortion | Logged prior only |
| Sahm rule | 9 of 9 recessions caught | Jul 2024 trigger (0.53), no recession | Labor-supply surge; it confirms rather than predicts | Logged prior only |
| Phillips curve / NKPC | 1960–84 (accelerationist slope −0.39) | Flat since 1985; 2021–23 surge; 2023–25 disinflation without slack | Anchored expectations; nonlinearity at high vacancies | Not a signal |
| Okun's law | 1961–2010 (β −0.41) | Break around 2011; 2023–25 | Productivity and labor-force shifts | Not a signal |
| Taylor rule | Describes policy in calm years | 2021–22: funds rate 5–7 pp below the rules | Look-through of supply shocks; r* unobservable | Context range (0.4–2.3 pp below rules now) |
| Expectations hypothesis | Short-rate path drives the 10-year in most cycles | Sep 2024–Jan 2025: 10y +113 bp during 100 bp of cuts | Term premium (+76 bp), fiscal supply | Real yield and term premium as risk inputs |
| UIP | Never at monthly horizons | USD/JPY slope −0.76 vs theory +1; USD/KRW −1.15 | Risk premia; carry crashes | Carry is a crash-prone premium |
| Dollar as safe haven | 10 of 11 equity sell-offs | Apr 2025 "sell America" | US-policy shock instead of a global one | Hedge-validity flag |
| Gold vs real yields | 2006–21 level relation; short-run beta still holds | 2022–26 level break (+568% residual) | Central-bank buying, reserve diversification | Short-run risk input only |
| Stock–bond hedge | Core inflation below 2% | 2022; again from Apr 2026 | Inflation and real-rate shocks hit both | No hedge credit at core PCE ≥3% or positive correlation |
| Term spread as a return forecast | In sample, 1960–89 | Out of sample R² −0.57% from 1980, −1.28% from 2010 | Unstable coefficients | Not a signal |
| Markov-switching regimes (no persistence penalty) | Smoothed, in hindsight | Real time: about 17 switches a year (US) and 31 (KOSPI, with 2-year initial training; about 10 with long training); Sharpe 1.52 smoothed vs 0.39 real time (0/1 switch, net of 10 bp). The half-exposure version earns 0.554 vs 0.539 for buy-and-hold, but 0.285 at 50 bp. | Look-ahead in smoothed probabilities; turnover × cost | Filtered states only; no unpenalised daily HMM gates |
| Jump models (persistence-penalised) | Sharpe 0.68 vs 0.54 (HMM) and 0.48 (buy-and-hold) in the Shu–Yu–Mulvey S&P study (preprint) | Protective outside Korea, but the 200-day band does better and Korea fails; exits lag troughs by 46–179 sessions | Exit lag; penalty learned on overlapping markets | Research item only; no regime engine |

### D.23 ML Indicative verdicts table (L328–338; sibling in research report L286–291 and SPEC §8.9 L5367 — the page wording is the owner-facing one)
| Rule | Card | Evidence at QUANTGEN costs | stamp |
|---|---|---|---|
| Momentum own-vol scaling | Outperformance | ΔSharpe +0.27 vs unscaled at 50 bp per side on both legs, p ≤ 0.001; Sharpe 0.63 at 2× costs; 70% of years positive. Step 3 (multiple testing): deflated ΔSR 0.98 at N_equiv 6.3 and 0.947 at linear N̂ 12.6, just under the 0.95 bar; break-even N ≈ 11.9 | `v-pass` "Pass" + fine "flagged “step 3 borderline”" |
| Daniel–Moskowitz bear gate, floor 0.5 | Add-on to the above | ΔSharpe +0.07, p 0.018. Pooled over four regions the gate has 34 onsets, enough for Tier A, but the add-on fails the multiple-testing step (deflated 0.77) and the out-of-region holdout passed in 1 of 3 regions. It is a floored heuristic inspired by Daniel–Moskowitz, not the published rule. | `v-revise` "Not recommended" |
| Korea 20-day vol target | Protective | Over 1997–2026 at the ETF cost: max drawdown 12.7 pp better than a static book at the same average exposure, with Sharpe non-inferiority (p 0.052), but fragile: July 2026 supplies 49% of the benefit against a 50% limit, and 2016–25 alone is a reject. Under v2 the counted selection factor (1.26–2.87 against a 1.282 limit) makes the expected formal verdict INSUFFICIENT DATA; the PASS holds on the v1.2 checks only (spec §8.9). Over 2016–26 alone: +4.4 pp, ΔSharpe +0.001 (ETF, 3 bp) or −0.029 (stocks, 35 bp), inconclusive. | `v-insuff` "Expected insufficient data (v2)" |
| US 15% vol target | Protective | On US shares at 50 bp, rebalanced daily: drawdown gain vs the same-exposure static book only +0.2 pp, a noisy single-path measure (tail-loss measures favour the target). A futures line at 5 bp is a new card that passes only on a knife edge (11 of 44 start dates). | `v-reject` "Reject (instrument)" |
| USD/KRW leg (20-day rise > 3% → 0.75×) | Protective, forward-sim | 2016–26: drawdown gain −0.2 to +1.1 pp, exposure on the worst 5% of days 0.99–1.00 of average. 1997–2026: −1.3 pp (strict timing) and −1.7 pp (value timing), worst-day exposure 1.004 of average; a reject on 1997–2026 at every timing (54 onsets under strict publication timing) | `v-reject` "Reject" |
| US rates leg (10-year +40 bp in 20 days → 0.5×) | Protective, forward-sim | Max drawdown 3.5 pp worse than the static book under strict publication timing; a reject at every timing and cost, gross included | `v-reject` "Reject" |

Fine print (L339): "Indicative: computed on the research data with QUANTGEN's gate definitions, not a run of QUANTGEN's own gate. The protective card class (drawdown first, Sharpe non-inferiority within 0.10) is defined in the integration spec."

### D.24 ML Debate table (L349–361, 8 rows) — page-only consolidation (the research report's table L159 is "Claim as first circulated / Corrected value / How it was settled", a different table)
1 "How much does momentum crash protection add?" — P3 cited Daniel–Moskowitz as 1.43 vs 0.71 / Use it, but simply / "The chair re-opened the published JFE 2016 paper: 0.682 static, 1.041 with constant vol, 1.194 dynamic. Most of the gain is plain vol scaling."
2 "Does macro add anything at daily horizons?" — P6: no, use the market's own states. P1: macro decides scope (hedges, inflation regime). / Only as risk inputs / "Both: no macro gate on daily equity exposure, but macro decides whether bond and dollar hedges count."
3 "Should stress raise reversal or quality weights?" — P3 proposed 1.5×; withdrew / E1 proposed 1.5×; conceded / "Reversal earns far more in stress (59% a year at 35% volatility vs 2% at 12% on the true VIX ≥ VIX3M flag), so mean-variance would raise its weight, which the no-up-weight bound forbids; every 1.5× rule lowered Sharpe (−0.05 to −0.20). All multipliers now stop at 1.0×."
4 "Black out positions around FOMC and data?" — P3: the announcement premium argues against it / E2/E5: black out / "2015–26 data: FOMC days earned about the same as other days. No swing blackouts; short intraday windows. A decision-day size-down stays a backlog test."
5 "Was the Korea gate real?" — P2 flagged the time-zone look-ahead / E4 defended the semiconductor and won legs / "+0.31 Sharpe became +0.05 once US data were lagged to the next KRX session. Only the won leg survived, and it fails at QUANTGEN's costs."
6 "Do US rates matter for Korea?" — P1: real yields as a Korea driver / E1/E3: rates-stress cuts / "During the July crash the 10-year rose only 17 bp and the won strengthened. Korea inputs must be local."
7 "Can a backtest approve an overlay?" — P2: strict multiple-testing hurdles / E5: 30-event rule; E1: too rigid for 2026 / "Detecting +0.05 Sharpe for a market vol target needs about 150–330 years. Tiered governance: price rules need 30 onsets, macro rules stay bounded and run forward first."
8 "Are Street forecasts or surveys useful?" — Not as predictors / E7: as a priced-in baseline only / "S&P target errors averaged 17%; in 2026 the houses forecast cuts and the Fed hiked. The Aug-2026 survey came out after KOSPI had already fallen 25%."

### D.25 ML Build columns (L371–392) — pre-council (2 Oct) routing with 3 Oct edits; verbatim items
Core links: Point-in-time data ("UTC and publication timestamps, vintages, US data usable only from the next KRX session, missing months fail closed"); Bounded overlays ("Every overlay multiplier in [0.5, 1.0] and every vol-target weight in [0, 1]; nothing above 1.0; zero exposure only from the risk layer or the engine's HALTED state"); Momentum risk state ("Own-vol scaling (cap 1.0); the bear gate (floor 0.5) runs in the specification book only, because it fails the multiple-testing step (0.77)"); Per-market vol target ("Korea 20-day, cap 1.0, Samsung + SK hynix caps. SMA20 as the displayed baseline … spec v2 picks the sizing estimator with a three-stage gate (R-30: calibration, a screen on the 90% QLIKE model confidence set, then the choice at the declared book); long-window GARCH-t and GJR-t already pass the same backtest"); Hedge-validity state ("No bond-hedge credit at core PCE ≥3% or positive 63-day stock–bond correlation"); Events and context ("US nights as KOSPI open-gap inputs; oil to the event calendar and Monte Carlo; Sahm, curve, Taylor and term premium logged, never acting").
Forward-sim / next tests: USD/KRW leg ("20-day rise above 3% → Korea gross 0.75×. Rejected on the 1997–2026 history at every timing … keeps running on paper as a labelled refusal. A timestamped won history is no longer needed to decide it."); US rates leg ("10-year +40 bp in 20 days → US duration-sensitive gross 0.5×. No live feed is needed: Treasury posts each day's par yields by about 6:00 pm ET … via H.15, which posts at 16:15 ET the next business day, only two business days later … keeps running on paper as a labelled refusal."); Korea leverage state (backlog) ("Margin debt, leveraged-ETF assets and investor flows via KIS. Top backlog priority."); Bear-gate holdouts (done) ("passed in 1 of 3 regions, so the Daniel–Moskowitz gate stays in the specification book").
Do not build: "Prior four-state table and every multiplier above 1.0×"; "VIX-term-structure momentum switch — It predicts volatility, not direction."; "Curve, real-rate, credit and oil gates on factor weights or market gross."; "Semiconductor × won Korea gate — Look-ahead artefact."; "Net-liquidity crypto rule, Street forecasts and surveys as signals"; "Smoothed regime probabilities, macro ML "complexity" timing, pre-cutoff LLM backtests, swing blackouts".
Files (L394–398): spec "35 rules (R-01–R-35) … JSON schemas, YAML config, 233 test and golden-value IDs, and a build order M0–M10"; backlog; research report.

### D.26 ML hero / caption numbers worth keeping as a fixture (L214–222, L255–261, L278–285, L317–321, L324)
139 claims / 13 position papers / 7 cross-examinations; 27 core links; 11 prohibitions; 22 backlog. Momentum Sharpe 0.40 → 0.71 (cap 1.0×) → 0.80 (floored gate); MDD −63% → −28% (−21% with gate). KOSPI crash 22 Jun–30 Jul 2026 −38.6% → −12.2% under VT20; H1 +52% vs +101%; 2016–26 Sharpe 0.641 vs 0.637; "July 2026 supplies 59% of its drawdown benefit" (2016–26 window) vs "49% … against a 50% limit" (1997–2026, indicative-verdicts table). Fed cut 175 bp Sep 2024–Dec 2025, hiked 16 Sep 2026 to 3.75–4.00%; 10y 5.29%; KOSPI 3,072 (30 Jun 2025) → 9,114.55 (22 Jun 2026) → −38.6% to 30 Jul; record days −12.06% (4 Mar) and +17.91% (31 Jul); Brent peak $138.21 (7 Apr 2026), Hormuz flows < 10%; USD/KRW ≈ 1,549 (Jun 2026), −12.4% in Q3, foreigners sold ₩21.5tn in Sep; payrolls 3m avg 121.6k (2024) / 9.7k (2025) / 80.4k (Jan–Aug 2026); openings per unemployed 1.36 → 0.87 → 1.01; headline CPI 2.4% → 4.2% (May 2026); Taylor variants 4.3–6.2%; 10y +113 bp while Fed cut 100 bp (term premium +76 bp); 2026 real yields +100 of +111 bp; curve inversion 534 days; probit peak 74% May 2023 (90% band 57–99%); Sahm 0.53 Jul 2024; Okun benchmark −0.405; stock–bond corr −0.29 (<2%) / +0.21 (>3%); gold fit $626 vs $4,187 at 2.93% real; gold −7.6% per +1 pp real yield; SOX beta 0.17 (2015–19) → > 0.5; prior Korea gate +0.31 → +0.05, semis leg −0.22 (2024–26); BTC × net liquidity −0.01 overall, −0.20 (2023–26), BTC −53%.

---

## Ambiguities (conservative reading in each case: display/specification book only, nothing acts, fail closed)

1. **Node routing is stale vs v2.0.** `ML.nodes[].dest` encodes the 2 Oct mapping: N-07 "SPEC §5 R-04 (BUILD NOW, Tier A-provisional)", N-22 "SPEC §5 R-11 SHADOW (no capital)", N-24 "SPEC §5 R-12 SHADOW (no capital)". QC `modules` (3 Oct) has R-04 DEMOTED (spec book only), R-11/R-12 RETIRED (refusal book). The ML figcaption L237 says so in prose ("the Quant Council later retired N-22 and N-24 as REJECTs and made N-14's Korea card a labelled control") but the data is unchanged. Reading: preserve `nodes` verbatim as the 2 Oct record and overlay status from `QC.modules`; never derive a build action from `dest`.
2. **Two different "July 2026 share" numbers.** ML c-kvt caption (L319) "July 2026 supplies 59% of its drawdown benefit" (2016–26 window; `protective` `PC4_max_episode_share 0.5906645617776514`) vs indicative-verdicts table (L331) "49% … against a 50% limit" (1997–2026; council report L73 "0.493") vs council objective-episode rule "0.493 → 0.174" (report L107). Reading: all three are context; PC-4 under v2 uses the objective episode table (R-22), not the page's numbers.
3. **Phillips slope specification differs between page and report.** Page data `1960-1984 slope −0.39` (Δ12m core PCE on the unemployment gap, L281 caption) vs research report L111 "1961–84 slope −0.74" and "1985–2019 −0.18" vs page −0.053. Different regressions; both are N-31 prohibited as signals. Reading: do not encode either as a parameter.
4. **`kstart` 1998-10-01 row is `INSUFFICIENT DATA (inconclusive)` (p 0.103)** while SPEC G-KR-L10 (L5855) says "asserted as PASS or INSUFFICIENT, so the count is 71–72". Reading: a golden on this row must accept either label.
5. **`ustart["futures 5bp"]` last row (2000-11-01, d 6.53, PASS) breaks the 1994-11…2000-08 REJECT run**; the backlog L291 says "every start from 1994-11 to 2000-08 REJECTs" (consistent). No contradiction, but a native bar chart must keep the quarterly spacing (the page draws index positions, not dates, L696–699).
6. **`QC.modules` has 34 rows for R-01…R-35 minus R-05**; the FILES card and ML files card say "35 rules (R-01–R-35)". Reading: R-05 is unchanged in v2.0 (not a module change), so a module-status table must show R-05 as "UNCHANGED" rather than omit it.
7. **`events_all_n = 136`, `protective`, `outperf` are never rendered** (ML script has no reference). They are golden fixtures from the DL-A/R4b harness (v1.2 PC-1…PC-6 checks); the v2 gate is PC-1′ (R-21), so these numbers are not v2 acceptance values. Reading: keep as "v1.2 reference" fixtures only; v2 goldens come from SPEC §9.
8. **`haven[].sell` is `false` for all 11 episodes including "Apr-2025 tariff shock"** although the caption and N-29 call April 2025 the hedge-failure case. The script ignores `sell`. Reading: do not use `sell`; derive the hedge-failure flag from `usd < 0` as the page does (L727).
9. **Macro-tape series are latest-vintage** (ML Limitations L451) and end 2026-10-02; `mkts.kospi` last value 7004.0 is the rounded official 7,003.74. They must not enter the point-in-time store as observations (no `value_status`, no `retrieved_at_utc`).
10. **`ML.snapshot` percentile base differs per row** (`history_from` 1990-01 … 2023-10; HY OAS n = 36). The page colours ≥ 90th red / ≤ 10th blue. Reading: display only; the app's own `pct (1y)` column (`ui/macro_page.py` L95) uses a 1-year window and should not be mixed with these.
11. **Fonts are the only network dependency, but the `<link rel=stylesheet>` is in the body in the extracted copy** (after `<title>`, L8–11) — valid HTML5 in practice; browsers hoist it. No action.
12. **Both pages carry outbound links** (QC 13, ML ~26, including press). Opening the file in the system browser makes those one click away; this is read-only research, no credentials, but the implementer should not add any in-app fetch of them (hermetic tests, no network).
13. **`page.launch_url` with a `file://` URI on Flet desktop is untested here**; `os.startfile` (`ui/runs_page.py` L40) is the proven path on Windows. Reading: use `os.startfile`/`xdg-open` first, `launch_url` as fallback, both wrapped in `try/except`, operator-initiated only.
