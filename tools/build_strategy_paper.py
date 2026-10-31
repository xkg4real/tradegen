#!/usr/bin/env python3
"""Build the bilingual research paper from one completed, frozen study.

No strategy evaluation, selection, network access or account operation occurs.
Requires local numpy/pandas/matplotlib and XeLaTeX with Noto CJK fonts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
STUDY = Path("docs/research/2026-10-31-strategy-lab")
FAMILIES = {
    "tsmom": ("시계열 모멘텀", "Time-series momentum", 27),
    "sma": ("단일 이동평균", "Moving average", 27),
    "crossover": ("이동평균 교차", "MA crossover", 40),
    "donchian": ("이전 범위 돌파", "Close breakout", 15),
    "zscore_reversion": ("가격 표준점수 반전", "Z-score reversion", 30),
    "rsi_reversion": ("RSI 반전", "RSI reversion", 30),
    "lowvol_trend": ("저변동성 추세", "Low-volatility trend", 27),
    "drawdown_reversion": ("고점 하락 후 반전", "Drawdown reversion", 27),
}
SELECTED_COLOR = "#12606c"
BENCH_COLOR = "#c97b34"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tex(value):
    replacements = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
                    "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
                    "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(replacements.get(c, c) for c in str(value))


def number(value, digits=2, scale=1):
    if value is None or not np.isfinite(value):
        return "--"
    return f"{value * scale:,.{digits}f}"


def pct(value, digits=1):
    return number(value, digits, 100) + (r"\%" if value is not None else "")


def pval(value):
    if value is not None and 0 < value < .0001:
        return "$<0.0001$"
    return number(value, 4)


def table(caption, headers, rows, *, alignment=None, note="", size=r"\small"):
    alignment = alignment or ("l" + "r" * (len(headers) - 1))
    lines = [r"\begin{table}[htbp]\centering", size, r"\setlength{\tabcolsep}{4pt}",
             r"\caption{" + caption + "}", r"\begin{tabular}{" + alignment + "}", r"\toprule",
             " & ".join(headers) + r" \\", r"\midrule"]
    lines += [" & ".join(map(str, row)) + r" \\" for row in rows]
    lines += [r"\bottomrule", r"\end{tabular}"]
    if note:
        lines += [r"\par\smallskip\begin{minipage}{\linewidth}\footnotesize " + note + r"\end{minipage}"]
    return "\n".join(lines + [r"\end{table}"])


def validate_inputs(summary, protocol, manifest, candidates, daily, results):
    if summary["mode"] != "retrospective_exploratory_internal_holdout":
        raise ValueError("Unexpected study mode")
    if summary["production_status"] != "NOT_VALIDATED_FOR_PRODUCTION":
        raise ValueError("Unexpected production interpretation")
    for key, path in (("protocol_sha256", ROOT / "research_lab/protocol.json"),
                      ("data_manifest_sha256", ROOT / "research_lab/data_manifest.json"),
                      ("catalogue_sha256", ROOT / "research_lab/catalogue.json"),
                      ("selection_registry_sha256", results / "selection_registry.json")):
        if summary[key] != digest(path):
            raise ValueError("Input fingerprint mismatch: " + key)
    if list(protocol["assets"]) != list(manifest["selection"]):
        # JSON key order is not a scientific constraint.
        if set(protocol["assets"]) != set(manifest["selection"]):
            raise ValueError("Declared asset sets differ")
    if len(candidates) != summary["evaluated_asset_configurations"]:
        raise ValueError("Incomplete candidate supplement")
    if candidates.duplicated(["asset", "candidate_id"]).any():
        raise ValueError("Duplicate candidate rows")
    if set(summary["assets"]) != set(protocol["assets"]):
        raise ValueError("Summary asset set differs")
    for asset in protocol["assets"]:
        result = summary["assets"][asset]
        selected = result["selected"]
        rows = daily[daily.asset == asset]
        if selected is None:
            if len(rows):
                raise ValueError("Daily trace exists for absent selection")
            continue
        if set(rows.candidate_id) != {selected["candidate_id"]}:
            raise ValueError("Daily trace selection mismatch")
        hold = rows[rows.split == "holdout"]
        if len(hold) != result["holdout"]["n"] or hold.date.duplicated().any():
            raise ValueError("Daily trace count mismatch")
        total = np.prod(1 + hold.net_return.to_numpy()) - 1
        if not np.isclose(total, result["holdout"]["total_return"], atol=1e-10, rtol=1e-10):
            raise ValueError("Daily trace and reported return disagree")


def draw_figures(summary, assets, candidates, daily, output, scratch):
    for variable, directory in (("MPLCONFIGDIR", "matplotlib"), ("XDG_CACHE_HOME", "xdg_cache_home")):
        cache = scratch / directory
        cache.mkdir(parents=True, exist_ok=True)
        os.environ[variable] = str(cache)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8,
                        "axes.spines.top": False, "axes.spines.right": False,
                        "axes.grid": True, "grid.alpha": .17, "pdf.fonttype": 42,
                        "figure.facecolor": "white", "savefig.facecolor": "white"})
    for kind, filename in (("wealth", "selected_wealth.pdf"), ("drawdown", "selected_drawdowns.pdf")):
        fig, axs = plt.subplots(4, 2, figsize=(7, 8.5), constrained_layout=True)
        for ax, asset in zip(axs.flat, assets):
            result = summary["assets"][asset]
            rows = daily[(daily.asset == asset) & (daily.split == "holdout")].sort_values("date")
            ax.set_title(f"{asset} ({result['currency']})", loc="left", weight="bold")
            if rows.empty:
                ax.set_axis_off()
                bh = result.get("holdout_benchmark", {})
                metric = bh.get("cagr" if kind == "wealth" else "max_drawdown")
                label = "CAGR" if kind == "wealth" else "MDD"
                value = "unavailable" if metric is None else f"{metric * 100:.1f}%"
                ax.text(.04, .55, f"No eligible validation selection\nResearch fallback: cash (return = 0)\nCosted buy-and-hold {label}: {value}",
                        fontsize=8, linespacing=1.7, transform=ax.transAxes)
                continue
            dates = pd.to_datetime(rows.date)
            for column, label, color in (("net_return", "Frozen selection", SELECTED_COLOR),
                                          ("benchmark_return", "Costed buy-and-hold", BENCH_COLOR)):
                wealth = np.r_[1., np.cumprod(1 + rows[column].to_numpy())]
                y = wealth[1:] if kind == "wealth" else 100 * (wealth / np.maximum.accumulate(wealth) - 1)[1:]
                ax.plot(dates, y, label=label, color=color, lw=1.15)
            ax.xaxis.set_major_locator(mdates.YearLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
            ax.set_ylabel("Wealth (initial = 1)" if kind == "wealth" else "Drawdown (%)")
        axs.flat[0].legend(loc="best", fontsize=6.4, frameon=False)
        fig.savefig(output / filename, metadata={"Title": kind + ": frozen retrospective selections"})
        plt.close(fig)
    fig, axs = plt.subplots(4, 2, figsize=(7, 8.5), constrained_layout=True)
    for ax, asset in zip(axs.flat, assets):
        rows = candidates[candidates.asset == asset]
        finite = np.isfinite(rows.validation_sharpe) & np.isfinite(rows.holdout_sharpe)
        ax.scatter(rows.loc[finite, "validation_sharpe"], rows.loc[finite, "holdout_sharpe"],
                   c=SELECTED_COLOR, alpha=.14, s=4, linewidths=0, rasterized=True)
        selected = summary["assets"][asset]["selected"]
        if selected:
            chosen = rows[rows.candidate_id == selected["candidate_id"]].iloc[0]
            ax.scatter([chosen.validation_sharpe], [chosen.holdout_sharpe], marker="*", s=70,
                       color=BENCH_COLOR, edgecolors="black", linewidths=.5, zorder=5)
        ax.axhline(0, color="gray", lw=.6)
        ax.axvline(0, color="gray", lw=.6)
        ax.set(xlabel="Validation net Sharpe (2021–22)", ylabel="Internal holdout net Sharpe")
        ax.set_title(f"{asset} · {int(finite.sum()):,} finite pairs", loc="left", fontsize=8)
    fig.savefig(output / "selection_transfer.pdf", dpi=200)
    plt.close(fig)
    fig, axs = plt.subplots(4, 2, figsize=(7, 8.5), constrained_layout=True)
    for ax, asset in zip(axs.flat, assets):
        result = summary["assets"][asset]
        ax.set_title(asset, loc="left", weight="bold")
        if result["selected"] is None:
            ax.set_axis_off()
            ax.text(.04, .55, "No eligible validation selection\nNo selected-strategy stress run", fontsize=8,
                    linespacing=1.7, transform=ax.transAxes)
            continue
        vals = [result["holdout"]["cagr"]] + [result["stress"][k]["cagr"] for k in ("cost_2x", "cost_3x", "lag_2")]
        ax.bar(["Base", "2× cost", "3× cost", "Lag 2"], np.array(vals) * 100,
               color=[SELECTED_COLOR, "#518b93", "#85b1b6", BENCH_COLOR], width=.65)
        ax.axhline(0, color="gray", lw=.7)
        ax.set_ylabel("Internal holdout CAGR (%)")
    fig.savefig(output / "cost_stress.pdf")
    plt.close(fig)


def make_sections(summary, protocol, manifest, candidates, bibliography):
    assets = protocol["assets"]
    results = summary["assets"]
    selected = [a for a in assets if results[a]["selected"] is not None]
    promising = [a for a in selected if results[a]["research_label"] == "promising_exploratory"]
    positive = [a for a in selected if results[a]["holdout"]["mean_daily"] > 0]
    val_sig = [a for a in assets if results[a]["validation_holm_p"] <= .05]
    hold_sig = [a for a in selected if results[a]["holdout_holm_p"] <= .05]
    configurations = summary["evaluated_asset_configurations"]
    s = {}
    s["ABSTRACT_EN"] = (
        f"We evaluate {configurations:,} asset--configuration pairs across eight economic rule families and eight "
        "asset price series. A frozen protocol uses 2021--2022 for selection and 2023--September 2026 "
        "for an internal holdout, with next-close execution, fee-inclusive self-financing ledgers, "
        "and a costed buy-and-hold benchmark. Centered joint block-bootstrap maximum-mean tests and "
        f"Holm correction address the declared search multiplicity. The selection rule retains {len(selected)} asset-level "
        f"candidates; {len(positive)} have positive internal-holdout mean returns. {len(val_sig)} asset-level validation "
        f"omnibus tests and {len(hold_sig)} selected-versus-benchmark holdout tests meet the adjusted 5\\% threshold; "
        f"{len(promising)} candidates satisfy all preregistered exploratory conditions. "
        "These counts distinguish positive absolute performance from benchmark-relative evidence. "
        "Because the historical caches were previously inspected, the results are retrospective diagnostics, "
        "not independent confirmation. Close-only fractional-capital simulations do not validate executable "
        "limit fills, realized account profit, principal protection, or production deployment.")
    s["ABSTRACT_KO"] = (
        f"여덟 경제적 규칙군과 여덟 가격 시계열에서 {configurations:,}개 자산·설정 조합을 평가하였다. "
        "2021--2022년을 선택 구간으로, 2023년부터 2026년 9월까지를 회고적 내부 이후 구간으로 고정하였다. "
        "다음 종가 실행, 비용 포함 자기금융 장부, 비용 차감 단순 보유와의 비교, 공동 블록 재표본화와 Holm 보정을 적용하였다. "
        f"선택된 {len(selected)}개 중 이후 구간 평균수익이 양수인 것은 {len(positive)}개이다. "
        f"보정 5\\% 수준에서 검증 전체 집합은 {len(val_sig)}개 자산, 고정 선택의 이후 구간 벤치마크 우위는 {len(hold_sig)}개 자산이며, "
        f"사전 명시한 탐색 조건을 모두 만족한 것은 {len(promising)}개이다. "
        "이미 사용한 가격 캐시와 소수 수량·종가 모형이라는 한계 때문에 이 결과를 독립 확인이나 실거래 승인으로 해석하지 않는다.")
    s["DATA_PARAGRAPH"] = (
        "자료 목록의 46개 파일 중 사전에 정한 여덟 시계열만 사용하였다. 미국 ETF 네 개, 한국 지수 ETF 한 개, "
        "원화 비트코인 및 USDT 표시 비트코인·이더리움이 포함된다. 종가와 날짜 이외의 호가·체결·거래량 정보는 없다. "
        "고정 마감일은 2026-09-24이며 한국 ETF의 마지막 관측은 2026-09-23이다. 모든 선택 캐시는 2026-09-27의 "
        "이전 자산 확장 연구에 이미 사용되었다. 2026-10-31 작성 시점의 실시간 가격 또는 최신 계좌 상태를 조회한 자료가 아니다.")
    s["DATA_TABLE"] = table("선택 자료와 표시 통화", ["자산", "통화", "최초 일자", "최종 일자", "사용 행 수"],
        [[tex(a), manifest["selection"][a]["currency"], manifest["selection"][a]["start"],
          manifest["selection"][a]["end"], f"{manifest['selection'][a]['rows']:,}"] for a in assets], alignment="llccr",
        note="사용 행 수는 고정 마감일 이후 행을 제거한 뒤, 공통 500봉 준비 구간을 제거하기 전이다. 전체 파일·선택 행의 지문은 데이터 매니페스트에 보관한다.")
    s["SPLIT_TABLE"] = table("자산별 실제 평가 행 수", ["자산", "2020년까지", "2021--2022", "2023년 이후"],
        [[tex(a)] + [f"{results[a]['phases'][p]['n']:,}" for p in ("train", "validation", "holdout")] for a in assets],
        note="각 시계열 최초 500봉은 신호 준비에 사용하고 평가에서 제외하였다. 최소 행 기준은 각각 500/365/365이다.")
    s["SPLIT_PARAGRAPH"] = (
        "학습이라고 표시한 2020년까지의 구간은 규칙 진단 구간이며 추정형 모형을 적합하거나 그 성적으로 후보를 고르지 않는다. "
        "모든 규칙과 매개변수는 수익 평가 전 코드·카탈로그·프로토콜과 함께 고정되었다. "
        "2021-01-01--2022-12-31에 선택을 끝내고 선택 레지스트리를 저장한 뒤 2023-01-01--2026-09-24를 평가하였다.")
    family_rows = []
    for key, (ko, _, raw) in FAMILIES.items():
        family_rows.append([ko, str(raw), str(raw * 12)])
    s["FAMILY_TABLE"] = table("경제적 가설군과 자산당 탐색 크기", ["규칙군", "기본 규칙", "실행 변형 포함"], family_rows + [["합계", "223", "2,676"]])
    s["UNIVERSE_PARAGRAPH"] = (
        "223개 기본 규칙에 1·5·21봉 재조정, 목표 비중 상한 0.5·1.0, 변동성 목표 없음·연 15\\%를 교차하여 "
        "자산당 2,676개를 만든다. 변동성 목표가 있으면 과거 20봉의 연환산 변동성으로 목표 비중을 정하고 상한을 적용한다. "
        f"선언한 자산·설정은 {summary['declared_asset_configurations']:,}개이며 실제 평가한 수는 {configurations:,}개이다. "
        "이는 서로 독립적인 전략 2만여 개를 발견했다는 뜻이 아니다. 매개변수 전체와 후보 ID는 카탈로그와 전체 결과 CSV에 기록한다.")
    s["COST_TABLE"] = table("거래비용 가정: 거래 명목액 대비 편도 bp", ["자산군", "기본", "2배", "3배"],
        [["미국 ETF", "50", "100", "150"], ["한국 지수 ETF", "3", "6", "9"], ["암호자산", "10", "20", "30"]],
        note="1 bp = 0.01\\%. 기존 연구 비용 하한에서 고정한 모형 가정이며 현재 중개사 요율표가 아니다.")
    s["RESULTS_OVERVIEW"] = (
        f"총 {configurations:,}개 조합이 결과 CSV에 기록되었고 자산별 {len(selected)}개 선택을 고정하였다. "
        f"검증 구간 전체 후보 검정에서 Holm 보정 5\\% 수준을 통과한 자산은 {len(val_sig)}개, "
        f"고정 선택의 이후 구간 단순 보유 대비 평균수익 검정을 통과한 자산은 {len(hold_sig)}개이다. "
        f"다섯 탐색 조건을 모두 만족한 선택은 {len(promising)}개이며, 어떤 경우에도 실거래 인증을 부여하지 않는다.")
    infrows, cirows, perfrows, stressrows, blockrows = [], [], [], [], []
    for a in assets:
        r = results[a]
        d = r.get("holdout_inference", {})
        family = r.get("validation_family_test", {})
        infrows.append([tex(a), pval(family.get("primary", {}).get("p_value")), pval(r["validation_holm_p"]),
                        pval(d.get("mean_diff_p_value")), pval(r["holdout_holm_p"]),
                        "충족" if a in promising else "미충족"])
        sensitivity = family.get("sensitivity", {})
        blockrows.append([tex(a), pval(sensitivity.get("5", {}).get("p_value")),
                          pval(family.get("primary", {}).get("p_value")),
                          pval(sensitivity.get("60", {}).get("p_value")),
                          str(r.get("eligible_validation_candidates", "--")),
                          str(r.get("distinct_validation_return_paths", "--"))])
        ci = d.get("mean_diff_ci")
        hac = d.get("market_model", {})
        cirows.append([tex(a), number(d.get("mean_diff"), 2, 10000),
                       "[" + ", ".join(number(x, 2, 10000) for x in ci) + "]" if ci else "--",
                       number(hac.get("alpha_daily"), 2, 10000),
                       r"$\le10^{-300}$" if hac.get("p_value_is_upper_bound") else pval(hac.get("alpha_p_one_sided"))])
        h, bh = r.get("holdout", {}), r.get("holdout_benchmark", {})
        perfrows.append([tex(a), pct(h.get("cagr")), pct(bh.get("cagr")), number(h.get("sharpe")),
                         pct(h.get("max_drawdown")), pct(h.get("avg_exposure")), str(h.get("completed_trades", "--"))])
        stressrows.append([tex(a), pct(h.get("cagr"))] + [pct(r.get("stress", {}).get(k, {}).get("cagr")) for k in ("cost_2x", "cost_3x", "lag_2")])
    s["INFERENCE_TABLE"] = table("사전 고정 추론과 탐색 조건", ["자산", "검증 원시 $p$", "검증 Holm", "이후 원시 $p$", "이후 Holm", "전체 조건"], infrows,
        note="검증은 전체 후보 집합의 최대 평균 초과수익 검정이다. 이후 구간은 고정 선택의 단순 보유 대비 평균 차이 검정이다. 결측 검정은 Holm 계열에서 1로 처리한다.", size=r"\footnotesize")
    s["INFERENCE_TABLE"] += "\n" + table("이후 구간 초과수익과 시장모형 진단", ["자산", "일평균 차이 bp", "차이 95\\% CI", "HAC $\\alpha$ bp/일", "진단 $p$"], cirows,
        note="차이는 선택 수익률에서 비용 차감 단순 보유 수익률을 뺀 값이다. 신뢰구간은 다중성 보정 전 개별 쌍별 블록 부트스트랩 구간이다. HAC 절편 검정은 진단용 원시 단측 p이며 본 연구의 통과 조건이 아니다.", size=r"\footnotesize")
    s["INFERENCE_TABLE"] += "\n" + table("검증 블록 길이 민감도와 선택 가능한 후보", ["자산", "$p$: 5봉", "$p$: 20봉", "$p$: 60봉", "자격 후보 수", "서로 다른 경로"], blockrows,
        note="민감도는 원시 전체 집합 p값이며 기본 20봉은 1,999회, 5·60봉은 999회 재표본화하였다. 서로 다른 검증 수익률 경로의 수가 독립 가설의 수를 뜻하지는 않는다. 자격 후보는 양의 평균수익·20회 왕복·유효 SR 조건을 만족한 수이다.", size=r"\footnotesize")
    s["PERFORMANCE_TABLE"] = table("고정 선택의 이후 구간 성과", ["자산", "CAGR", "보유 CAGR", "Sharpe", "MDD", "평균 노출", "왕복 수"], perfrows,
        note="CAGR와 MDD는 비용 차감 평가수익률 기반이며 자산 고유 통화이다. 평균 노출은 가격 이동 전 보유 비중의 평균이다. 세후 실현 순이익과 같지 않다.", size=r"\footnotesize")
    s["PERFORMANCE_TABLE"] += "\n" + table("고정 선택의 비용·시차 스트레스 CAGR", ["자산", "기본", "2배 비용", "3배 비용", "2봉 시차"], stressrows, size=r"\footnotesize")
    family_diagnostics = []
    for key, (ko, _, _) in FAMILIES.items():
        rows = candidates[candidates.family == key]
        family_diagnostics.append([ko, f"{len(rows):,}", number(rows.validation_sharpe.median()),
                                   number(rows.holdout_sharpe.median()), pct(float((rows.holdout_mean_daily > 0).mean()))])
    s["PERFORMANCE_TABLE"] += "\n" + table("전체 후보의 규칙군별 사후 진단", ["규칙군", "조합 수", "검증 SR 중앙값", "이후 SR 중앙값", "이후 양수 비율"], family_diagnostics,
        note="여덟 자산·설정 행의 분포이다. SR 결측은 중앙값에서 제외하고 양수 비율은 비용 차감 평균수익을 기준으로 한다. 이 표는 포트폴리오 합산, 독립 복제 수, 검정 결과가 아니며 이후 성적으로 재선택하지 않는다.", size=r"\footnotesize")
    interpretation = []
    if selected:
        best = max(selected, key=lambda a: results[a]["holdout"]["cagr"])
        r = results[best]
        interpretation.append(
            f"고정 선택 중 이후 구간 CAGR가 가장 높은 것은 {tex(best)}의 {pct(r['holdout']['cagr'])}이다. "
            f"같은 자산 단순 보유의 CAGR는 {pct(r['holdout_benchmark']['cagr'])}이고, "
            f"평균 초과수익의 Holm 보정 $p$값은 {pval(r['holdout_holm_p'])}이다. "
            "이 순위는 결과를 설명하는 사후 순위이며 이 자산으로 재선택하거나 투자 비중을 바꾸는 규칙이 아니다.")
        underperformers = [a for a in selected if results[a]["holdout"]["cagr"] < results[a]["holdout_benchmark"]["cagr"]]
        compound_positive = [a for a in selected if results[a]["holdout"]["cagr"] > 0]
        interpretation.append(
            f"선택 {len(selected)}개 중 양의 복리 성장을 기록한 것은 {len(compound_positive)}개이며, "
            f"같은 자산의 비용 차감 단순 보유보다 CAGR가 낮은 선택은 {len(underperformers)}개이다. "
            "양의 수익률과 벤치마크 대비 우위의 구분이 이 표본에서도 중요하다.")
    no_eligible = [a for a in assets if results[a]["status"] == "no_eligible_validation_candidate"]
    if no_eligible:
        interpretation.append(
            ", ".join(tex(a) for a in no_eligible) + "는 검증 구간 자격 후보가 없어 선택하지 않았다. "
            "이는 해당 자산이 거래 불가능하다는 뜻이 아니라 이번 양의 평균수익·최소 왕복 수·유효 샤프비율 조건에 맞는 후보가 없었다는 뜻이다. "
            "최소 거래 횟수 조건은 느리게 보유하는 규칙보다 빈번히 진입·청산하는 규칙에 유리할 수 있다. "
            "따라서 선택 후보의 실패를 모든 장기 추세 가설의 반증으로 일반화하지 않는다.")
    if not promising:
        interpretation.append("어느 선택도 선언한 다섯 조건을 모두 만족하지 않았다. 양의 절대수익이 있는 경우에도 이를 벤치마크 우위나 새 전략의 확인 성공으로 바꾸어 표현하지 않는다. 통계적 비유의는 시장 예측이 원천적으로 불가능하다는 증명도 아니다.")
    else:
        interpretation.append("탐색 조건을 모두 만족한 자산은 " + ", ".join(tex(a) for a in promising) + "이다. 이 표지는 이번 사전 고정 기준에만 해당하며, 재사용된 역사에서의 결과라는 이유로 전향적 확인을 대체하지 못한다.")
    inconsistent_sign = [a for a in selected if results[a]["holdout"]["mean_daily"] > 0 and results[a]["holdout"]["cagr"] <= 0]
    for a in inconsistent_sign:
        h = results[a]["holdout"]
        interpretation.append(
            f"{tex(a)}는 특히 산술 평균과 복리 성장을 구별해야 한다. 이후 구간 일평균 수익률은 {number(h['mean_daily'], 3, 10000)} bp로 양수이나, "
            f"CAGR는 {pct(h['cagr'])}, 누적 수익률은 {pct(h['total_return'])}이다. "
            "수익률이 변동하면 양의 산술 평균이 양의 복리 성장이나 최종 이익을 보장하지 않는다. "
            "따라서 탐색 조건의 양의 평균수익 여부를 실제 자산 증가라는 표현으로 바꾸지 않고 두 지표를 함께 제시한다.")
    if results.get("ETH_USDT", {}).get("selected"):
        r = results["ETH_USDT"]
        h, bh = r["holdout"], r["holdout_benchmark"]
        interpretation.append(
            f"ETH\\_USDT의 선택은 평균 노출 {pct(h['avg_exposure'])}에서 CAGR {pct(h['cagr'])}, "
            f"MDD {pct(h['max_drawdown'])}를 기록하였다. 단순 보유의 CAGR {pct(bh['cagr'])}, "
            f"MDD {pct(bh['max_drawdown'])}와 비교하면 위험과 수익을 함께 줄인 경로이다. "
            f"3배 비용에서는 CAGR가 {pct(r['stress']['cost_3x']['cagr'])}이나 추가 한 봉 지연에서는 {pct(r['stress']['lag_2']['cagr'])}로 변한다. "
            "이 후보의 관측 스트레스에서는 비용 증액보다 실행 시차 변경의 영향이 더 컸다. "
            "이 예는 제한된 노출의 낙폭 감소와 방향 예측의 우위를 구별하고, 정해진 종가 시차에 대한 민감도를 함께 읽어야 함을 보여준다.")
    raw_sensitivity = []
    for a in assets:
        family_test = results[a].get("validation_family_test", {})
        primary = family_test.get("primary", {}).get("p_value", 1)
        for block, values in family_test.get("sensitivity", {}).items():
            if values["p_value"] < .05 <= primary:
                raw_sensitivity.append(f"{tex(a)} {block}봉에서 {pval(values['p_value'])}")
    if raw_sensitivity:
        interpretation.append("블록 길이를 바꾸면 원시 $p$값이 0.05 아래로 내려가는 사례도 있다(" + ", ".join(raw_sensitivity)
            + "). 하지만 선언한 기본 20봉 검정과 자산 간 보정 결과를 대신하지 않는다. 유리한 블록 길이를 사후에 택하면 추가 탐색을 숨기게 되므로 이 사례를 통과로 재분류하지 않았다.")
    basket = summary.get("usd_basket", {})
    if basket.get("status") == "descriptive_only":
        h, bh = basket["selected_metrics"], basket["buy_hold_metrics"]
        interpretation.append(
            f"USD ETF 네 자산을 최초에 1/4씩 나눈 선택 슬리브의 기술적 합산 CAGR는 {pct(h['cagr'])}, "
            f"MDD는 {pct(h['max_drawdown'])}이다. 같은 방식의 단순 보유 합산 CAGR는 {pct(bh['cagr'])}, "
            f"MDD는 {pct(bh['max_drawdown'])}이다. 슬리브 사이의 자금 재배분은 하지 않으며 선택이 없는 슬리브는 현금이다. "
            "이 보조 그림자 포트폴리오는 추가 가설 검정을 거치지 않았고, 다른 통화를 섞은 계좌 손익이 아니다.")
        if h["annual_vol"] < bh["annual_vol"] and h["max_drawdown"] < bh["max_drawdown"]:
            interpretation.append("이 합산에서는 연환산 변동성이 낮아졌는데도 관측 최대 낙폭은 오히려 더 컸다. 변동성은 전체 경로의 산포, 최대 낙폭은 특정 고점 이후 누적 하락이므로 두 위험 지표가 항상 같은 순위를 줄 이유는 없다. 낮은 노출이나 변동성만으로 실제 경로의 보호 성과를 대신할 수 없다.")
    s["RESULTS_INTERPRETATION"] = "\n\n".join(interpretation)
    changed = [a for a in selected if results[a]["stress"]["cost_2x"]["mean_daily"] <= 0 < results[a]["holdout"]["mean_daily"]]
    lowerdd = [a for a in selected if results[a]["holdout"]["max_drawdown"] > results[a]["holdout_benchmark"]["max_drawdown"]]
    val_sr = [results[a]["validation"]["sharpe"] for a in selected]
    hold_sr = [results[a]["holdout"]["sharpe"] for a in selected]
    s["DISCUSSION"] = (
        f"선택된 후보의 검증 샤프비율 중앙값은 {number(float(np.median(val_sr)) if val_sr else None)}이고 "
        f"이후 구간 중앙값은 {number(float(np.median([x for x in hold_sr if x is not None])) if any(x is not None for x in hold_sr) else None)}이다. "
        "서로 다른 시장 상태·표본 길이·사후 선택이 함께 영향을 주므로 이 차이를 순수한 과최적화 효과라고 식별할 수 없다. "
        "그림의 전체 후보 구름은 선택 구간의 성적이 다음 구간에 얼마나 불안정하게 전달되는지를 보여주는 진단이다.\n\n"
        f"선택 {len(selected)}개 중 단순 보유보다 관측 최대 낙폭이 작았던 것은 {len(lowerdd)}개이다. "
        "그 차이는 노출 축소의 대가와 함께 읽어야 하며 낮은 낙폭 자체가 예측 알파는 아니다. "
        f"기본 비용에서 평균수익이 양수였으나 2배 비용에서 비양수로 바뀐 선택은 {len(changed)}개이다. "
        "그 밖에도 비용은 연속적으로 누적되므로 이 이분법만으로 비용 민감도가 없다고 결론내릴 수 없다. "
        "추가 지연 실험은 시간 정렬의 취약성을 확인하지만 실제 거래소의 미체결·지연 분포를 추정한 것은 아니다.")
    if all(results.get(a, {}).get("selected") for a in ("BTC_KRW", "BTC_USDT", "ETH_USDT")):
        choices = [results[a]["selected"] for a in ("BTC_KRW", "BTC_USDT", "ETH_USDT")]
        if all(c["family"] == "sma" and dict(c["parameters"]) == {"band": .01, "lookback": 5}
               and c["rebalance_bars"] == 5 for c in choices):
            s["DISCUSSION"] += (
                "\n\n암호자산 세 선택은 모두 5봉 이동평균·1\\% 진입 여유·5봉 재조정이라는 방향 규칙을 공유한다. "
                "그러나 비중 상한과 변동성 조절 정책이 다르며, 표시 통화와 시장의 일자 경계도 다르다. "
                "따라서 원화 비트코인 선택과 USDT 비트코인 선택의 수익 차이를 거래소 우위, 환율 예측력 또는 통화 자체의 효과로 식별할 수 없다. "
                "이를 묻는 후속 실험은 동일 노출 정책·동일 시점·환율 환산을 별도로 고정해야 한다.")
    s["CONCLUSION"] = (
        f"{configurations:,}개 자산·설정 조합을 동일한 선언 절차로 평가한 결과, 사전 고정 탐색 조건을 모두 만족한 선택은 {len(promising)}개였다. "
        "이 연구의 기여는 많은 후보를 좋은 순서로 나열한 데 있지 않고, 경제적 가설과 매개변수 변형을 구별하고 "
        "비용·시차·선택편향·자료 재사용을 같은 평가 안에 드러낸 데 있다. "
        "후속 결정은 공개된 후보·설정과 실패 조건을 유지한 채 새로운 자료와 실거래 규격을 이용해 확인해야 한다. "
        "이번 결과만으로 자동주문을 활성화하거나 실현 이익·원금 보호를 보장할 근거는 없다.")
    s["REPRODUCIBILITY"] = (
        "계산 전 고정 커밋: \\path{" + summary["freeze_commit"] + "}.\\par\n"
        "프로토콜 SHA256: \\path{" + summary["protocol_sha256"] + "}.\\par\n"
        "자료 매니페스트 SHA256: \\path{" + summary["data_manifest_sha256"] + "}.\\par\n"
        "선택 레지스트리 SHA256: \\path{" + summary["selection_registry_sha256"] + "}.\\par\n"
        "상대 경로 \\path{docs/research/2026-10-31-strategy-lab/results/}에 "
        "\\texttt{summary.json}, \\texttt{run\\_manifest.json}, \\texttt{selection\\_registry.json}, "
        "\\texttt{candidates\\_all.csv}, \\texttt{selected\\_daily.csv}와 USD 슬리브 보조 자료를 보관한다. "
        "보고서 빌드는 \\path{tools/build_strategy_paper.py}로 수행한다. "
        "결과 파일과 생성기의 지문은 \\texttt{paper/build\\_manifest.json}에 기록한다.")
    selected_lines = [r"\small\begin{longtable}{p{.16\linewidth}p{.76\linewidth}}",
                      r"\caption{자산별 고정 후보와 설정}\\\toprule 자산 & 선택 내용 \\\midrule\endfirsthead",
                      r"\toprule 자산 & 선택 내용 \\\midrule\endhead"]
    for a in assets:
        choice = results[a]["selected"]
        if choice is None:
            body = "선택 없음: " + tex(results[a]["status"])
        else:
            pars = ", ".join(f"{key}={value}" for key, value in dict(choice["parameters"]).items())
            vol = "없음" if choice["volatility_target"] is None else pct(choice["volatility_target"])
            body = (r"\path{" + choice["candidate_id"] + "}\\newline " + tex(pars) + r"\newline "
                    f"재조정 {choice['rebalance_bars']}봉; 목표 상한 {choice['target_cap']}; 변동성 목표 {vol}")
        selected_lines.append(tex(a) + " & " + body + r" \\[6pt]")
    s["SELECTED_TABLE"] = "\n".join(selected_lines + [r"\bottomrule\end{longtable}\normalsize"])
    references = []
    for ref in bibliography["references"]:
        references.append(r"\bibitem{" + ref["id"] + "} " + tex(ref["authors"]) + f" ({ref['year']}). "
            + tex(ref["title"]) + ". \\emph{" + tex(ref["journal"]) + "}, " + tex(ref["volume"])
            + ", " + tex(ref["pages"]) + ". DOI: \\url{https://doi.org/" + ref["doi"] + "}.")
    s["BIBLIOGRAPHY"] = "\n\n".join(references)
    return s


def build(results, output, artifact, scratch):
    results, output, scratch = results.resolve(), output.resolve(), scratch.resolve()
    required = [results / name for name in ("summary.json", "candidates_all.csv", "selected_daily.csv", "run_manifest.json", "selection_registry.json")]
    for path in required:
        if not path.is_file() or path.is_symlink():
            raise ValueError("Completed study input missing or linked: " + str(path))
    summary = json.loads(required[0].read_text())
    protocol_path = ROOT / "research_lab/protocol.json"
    manifest_path = ROOT / "research_lab/data_manifest.json"
    protocol = json.loads(protocol_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    candidates = pd.read_csv(results / "candidates_all.csv")
    daily = pd.read_csv(results / "selected_daily.csv")
    source = ROOT / STUDY / "paper"
    bibpath, templatepath = source / "bibliography.json", source / "manuscript.tex.in"
    bibliography = json.loads(bibpath.read_text())
    validate_inputs(summary, protocol, manifest, candidates, daily, results)
    output.mkdir(parents=True, exist_ok=True)
    scratch.mkdir(parents=True, exist_ok=True)
    draw_figures(summary, protocol["assets"], candidates, daily, output / "figures", scratch)
    sections = make_sections(summary, protocol, manifest, candidates, bibliography)
    manuscript = templatepath.read_text()
    for key, value in sections.items():
        manuscript = manuscript.replace("@@" + key + "@@", value)
    if re.search(r"@@[A-Z_]+@@", manuscript):
        raise ValueError("Unfilled manuscript placeholder")
    texpath = output / "TRADEGEN_Strategy_Research.tex"
    texpath.write_text(manuscript, encoding="utf-8")
    env = os.environ.copy()
    for variable in ("TEXMFVAR", "TEXMFCONFIG", "XDG_CACHE_HOME"):
        path = scratch / variable.lower()
        path.mkdir(parents=True, exist_ok=True)
        env[variable] = str(path)
    command = ["xelatex", "-no-shell-escape", "-halt-on-error", "-interaction=nonstopmode",
               "-output-directory=" + str(scratch), texpath.name]
    for pass_number in (1, 2):
        run = subprocess.run(command, cwd=output, env=env, capture_output=True, text=True)
        (scratch / f"xelatex-pass-{pass_number}.txt").write_text(run.stdout + run.stderr)
        if run.returncode:
            raise RuntimeError("XeLaTeX failed; see " + str(scratch / f"xelatex-pass-{pass_number}.txt"))
    pdf = output / "TRADEGEN_Strategy_Research.pdf"
    shutil.copyfile(scratch / pdf.name, pdf)
    artifact.parent.mkdir(parents=True, exist_ok=True)
    if artifact.resolve() != pdf.resolve():
        shutil.copyfile(pdf, artifact)
    inputs = required + [protocol_path, manifest_path, bibpath, templatepath, Path(__file__).resolve()]
    inputs += [p for p in (results / "usd_basket_daily.csv", ROOT / "research_lab/catalogue.json") if p.exists()]
    provenance = {
        "schema_version": 1, "study_id": summary["study_id"], "freeze_commit": summary["freeze_commit"],
        "report_status": "retrospective_exploratory_not_peer_reviewed_not_production_validation",
        "build_command": "python tools/build_strategy_paper.py",
        "rendering": "XeLaTeX; shell escape disabled; Noto Serif/Sans CJK KR; matplotlib",
        "inputs_sha256": {str(p.relative_to(ROOT)): digest(p) for p in inputs},
        "outputs_sha256": {str(p.relative_to(output)): digest(p) for p in [texpath, pdf] + sorted((output / "figures").glob("*.pdf"))},
        "recomputes_strategy_or_inference": False,
    }
    (output / "build_manifest.json").write_text(json.dumps(provenance, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"pdf": str(pdf), "artifact": str(artifact), "sha256": digest(pdf),
                      "candidate_rows": len(candidates), "figures": 4}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=ROOT / STUDY / "results")
    parser.add_argument("--output", type=Path, default=ROOT / STUDY / "paper")
    parser.add_argument("--artifact", type=Path, default=Path("/workspace/tradegen-session/artifacts/TRADEGEN_Strategy_Research.pdf"))
    parser.add_argument("--scratch", type=Path, default=Path("/workspace/tradegen-session/paper-build"))
    args = parser.parse_args()
    build(args.results, args.output, args.artifact, args.scratch)
