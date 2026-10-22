"""2-3 page PDF comparing the 2026-10-07 run (out/) with the 2026-10-12 KRX run (out_krx/).

    python -m paper_live.compare_pdf OUT.pdf      (wording comes from compare_text.json)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle  # noqa: E402

HERE = Path(__file__).resolve().parent
RUNS = {"Oct 7 (US/UK/FICC)": HERE / "out", "Oct 12 (KOSPI/FICC)": HERE / "out_krx"}
ACCTS = ["QG-TREND", "QG-TACTICAL", "QG-CORE", "LAZYOWEN-CAL", "LAZYOWEN-NAIVE"]
COL = {"QG-TREND": "#2a78d6", "LAZYOWEN-NAIVE": "#eb6834", "QG-CORE": "#1baf7a", "LAZYOWEN-CAL": "#eda100",
       "QG-TACTICAL": "#e87ba4", "EW_ALL_BH": "#8a949e"}
INK, MUTED, RULE = colors.HexColor("#13202b"), colors.HexColor("#5b6773"), colors.HexColor("#d9dfe5")

pdfmetrics.registerFont(TTFont("UI", r"C:\Windows\Fonts\segoeui.ttf"))
pdfmetrics.registerFont(TTFont("UIB", r"C:\Windows\Fonts\segoeuib.ttf"))
pdfmetrics.registerFont(TTFont("MONO", r"C:\Windows\Fonts\consola.ttf"))
from reportlab.pdfbase.pdfmetrics import registerFontFamily  # noqa: E402
registerFontFamily("UI", normal="UI", bold="UIB", italic="UI", boldItalic="UIB")
plt.rcParams.update({"font.family": "Segoe UI", "font.size": 8.5, "axes.edgecolor": "#c3c2b7", "axes.labelcolor": "#4a5865",
                     "xtick.color": "#4a5865", "ytick.color": "#4a5865", "axes.spines.top": False, "axes.spines.right": False})

S = dict(
    h1=ParagraphStyle("h1", fontName="UIB", fontSize=17, leading=21, textColor=INK, spaceAfter=4),
    sub=ParagraphStyle("sub", fontName="UI", fontSize=8.5, leading=11, textColor=MUTED, spaceAfter=8),
    h2=ParagraphStyle("h2", fontName="UIB", fontSize=11.5, leading=15, textColor=INK, spaceBefore=8, spaceAfter=4),
    p=ParagraphStyle("p", fontName="UI", fontSize=9, leading=12.6, textColor=INK, spaceAfter=5),
    li=ParagraphStyle("li", fontName="UI", fontSize=9, leading=12.4, textColor=INK, leftIndent=10, bulletIndent=0, spaceAfter=3),
    cell=ParagraphStyle("cell", fontName="UI", fontSize=7.8, leading=9.8, textColor=INK),
    cellb=ParagraphStyle("cellb", fontName="UIB", fontSize=7.8, leading=9.8, textColor=INK),
    note=ParagraphStyle("note", fontName="UI", fontSize=7.4, leading=9.6, textColor=MUTED, spaceAfter=4),
)


def usd(v, d=2):
    return ("+" if v > 0.0005 else "-" if v < -0.0005 else "±") + f"${abs(v):.{d}f}"


AN_DIR = os.environ.get("ANALYSIS_DIR", "analysis")   # analysis_v2: the corrected analysis of 2026-10-20


def load(d: Path):
    an = json.loads((d / AN_DIR / "summary.json").read_text())
    rs = json.loads((d / "replay" / "summary.json").read_text())
    gp = d / "grid" / "summary.json"
    gs = json.loads(gp.read_text()) if gp.exists() else None
    paths = json.loads((d / AN_DIR / "equity_paths.json").read_text())
    t = d / AN_DIR / "trades.csv"
    tr = pd.read_csv(t) if t.exists() and t.stat().st_size > 5 else pd.DataFrame()
    return dict(an=an, rs=rs, gs=gs, paths=paths, tr=tr)


def table(rows, widths, head=1, bold_first_col=False):
    data = [[Paragraph(str(c), S["cellb"] if (i < head or (bold_first_col and j == 0)) else S["cell"]) for j, c in enumerate(r)]
            for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=head)
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, head - 1), 0.8, INK), ("LINEBELOW", (0, head), (-1, -1), 0.3, RULE),
                           ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5), ("LEFTPADDING", (0, 0), (-1, -1), 3)]))
    return t


def equity_fig(runs, path):
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 2.6), sharey=True)
    for ax, (label, r) in zip(axes, runs.items()):
        for n in ACCTS + ["EW_ALL_BH"]:
            p = r["paths"].get(n, [])
            if not p:
                continue
            t = pd.to_datetime([x[0] for x in p], utc=True).tz_convert("Asia/Seoul")
            v = [x[1] - 500 for x in p]
            ax.plot(t, v, color=COL[n], lw=1.6 if n != "EW_ALL_BH" else 1.1, ls="--" if n == "EW_ALL_BH" else "-",
                    label=("EW basket (no costs)" if n == "EW_ALL_BH" else n))
        ax.axhline(0, color="#4a5865", lw=0.6, ls=":")
        ax.set_title(label, fontsize=9, loc="left", color="#13202b")
        ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%H:%M", tz="Asia/Seoul"))
        ax.grid(axis="y", color="#e8ecf0", lw=0.6)
    axes[0].set_ylabel("P&L vs $500 start (USD)")
    axes[1].legend(fontsize=6.8, frameon=False, loc="lower left", ncol=2)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def bars_fig(runs, path):
    import numpy as np
    fig, ax = plt.subplots(figsize=(7.4, 2.3))
    x = np.arange(len(ACCTS))
    w = 0.38
    for i, (label, r) in enumerate(runs.items()):
        net = [r["an"]["accounts"][a]["net_pnl"] for a in ACCTS]
        gross = [r["an"]["accounts"][a]["gross_pnl_closed"] for a in ACCTS]
        xs = x + (i - 0.5) * w
        ax.bar(xs, net, w * 0.92, color=[COL[a] for a in ACCTS], alpha=1.0 if i else 0.45, edgecolor="none",
               label=f"{label}: net")
        ax.scatter(xs, gross, marker="_", s=180, color="#13202b", zorder=3, label=f"gross before costs" if i else None)
        for xx, v in zip(xs, net):
            ax.text(xx, v + (0.25 if v >= 0 else -0.25), usd(v), ha="center", va="bottom" if v >= 0 else "top", fontsize=6.6, color="#4a5865")
    ax.axhline(0, color="#4a5865", lw=0.6)
    ax.set_xticks(x, ACCTS, fontsize=7.5)
    ax.set_ylabel("USD per $500 account")
    ax.set_title("Net P&L per account: faded bar = Oct 7, solid bar = Oct 12, black tick = gross before costs", loc="left", fontsize=8, color="#13202b")
    lo = min(r["an"]["accounts"][a]["net_pnl"] for r in runs.values() for a in ACCTS)
    ax.set_ylim(min(lo * 1.22, -1), 1.2)
    ax.grid(axis="y", color="#e8ecf0", lw=0.6)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def main(out_pdf: str):
    runs = {k: load(v) for k, v in RUNS.items()}
    txt = json.loads((HERE / "compare_text.json").read_text(encoding="utf-8"))
    tmp = HERE / "out_krx" / AN_DIR
    equity_fig(runs, tmp / "cmp_equity.png")
    bars_fig(runs, tmp / "cmp_bars.png")
    (r1, a), (r2, b) = list(runs.items())

    story = [Paragraph(txt["title"], S["h1"]), Paragraph(txt["subtitle"], S["sub"])]
    for para in txt["summary"]:
        story.append(Paragraph(para, S["p"]))
    if txt.get("errata"):
        story.append(Paragraph(txt.get("errataTitle", "Corrections"), S["h2"]))
        story.append(Paragraph(txt.get("errataIntro", ""), S["note"]))
        for h, body in txt["errata"]:
            story.append(Paragraph(f"<b>{h}</b> {body}", S["li"], bulletText="•"))
    story.append(Paragraph("Results side by side", S["h2"]))
    rows = [["Account", "Net Oct 7", "Net Oct 12", "Gross Oct 7 → Oct 12", "Costs Oct 7 → Oct 12", "Trades", "Replay mean / session (Oct 7 → Oct 12)"]]
    for n in ACCTS:
        x, y = a["an"]["accounts"][n], b["an"]["accounts"][n]
        rows.append([n, usd(x["net_pnl"]), usd(y["net_pnl"]), f'{usd(x["gross_pnl_closed"])} → {usd(y["gross_pnl_closed"])}',
                     f'${x["costs"]:.2f} → ${y["costs"]:.2f}', f'{x["closed_trades"]} → {y["closed_trades"]}',
                     f'{usd(a["rs"]["accounts"][n]["all"]["mean"])} → {usd(b["rs"]["accounts"][n]["all"]["mean"])}'])
    tot = lambda r, k: sum(r["an"]["accounts"][n][k] for n in ACCTS)  # noqa: E731
    rows.append(["All five ($2,500)", usd(tot(a, "net_pnl")), usd(tot(b, "net_pnl")),
                 f'{usd(tot(a, "gross_pnl_closed"))} → {usd(tot(b, "gross_pnl_closed"))}',
                 f'${tot(a, "costs"):.2f} → ${tot(b, "costs"):.2f}', f'{tot(a, "closed_trades")} → {tot(b, "closed_trades")}', ""])
    rows.append(["Equal-weight basket, buy-and-hold", usd(a["an"]["benchmarks"]["EW_ALL_BH_ret"] * 500),
                 usd(b["an"]["benchmarks"]["EW_ALL_BH_ret"] * 500), "no costs", "", "", ""])
    story.append(table(rows, [34 * mm, 19 * mm, 19 * mm, 30 * mm, 26 * mm, 16 * mm, 38 * mm], bold_first_col=True))
    story.append(Paragraph("What changed in the setup", S["h2"]))
    story.append(table([["", r1, r2]] + txt["setup"], [34 * mm, 72 * mm, 76 * mm], bold_first_col=True))

    story += [PageBreak(), Paragraph("How the two sessions moved", S["h2"]),
              Image(str(tmp / "cmp_equity.png"), width=182 * mm, height=64 * mm),
              Paragraph(txt["equity_note"], S["note"]),
              Image(str(tmp / "cmp_bars.png"), width=182 * mm, height=56.5 * mm),
              Paragraph("Differences that matter", S["h2"])]
    for h, body in txt["differences"]:
        story.append(Paragraph(f"<b>{h}</b> {body}", S["li"], bulletText="•"))

    story += [PageBreak(), Paragraph("Tonight in context: replay of the same rules", S["h2"]),
              Paragraph(txt["replay_intro"], S["p"])]
    rows = [["Account", "Oct 7 replay (49 sessions)", "Oct 12 replay", "Oct 7 live pct.", "Oct 12 live pct."]]
    for n in ACCTS:
        ra, rb = a["rs"]["accounts"][n]["all"], b["rs"]["accounts"][n]["all"]
        rows.append([n, f'{usd(ra["mean"])} ± {ra["sd"] or 0:.2f}, {ra["trades_per_day"]:.1f} trades, loss days {100 * (1 - ra["win_days"] - ra["flat_days"]):.0f}%',
                     f'{usd(rb["mean"])} ± {rb["sd"] or 0:.2f}, {rb["trades_per_day"]:.1f} trades, loss days {100 * (1 - rb["win_days"] - rb["flat_days"]):.0f}%',
                     f'{a["an"].get("replay_percentile", {}).get(n, 0):.0f}', f'{b["an"].get("replay_percentile", {}).get(n, 0):.0f}'])
    story.append(table(rows, [32 * mm, 58 * mm, 58 * mm, 17 * mm, 17 * mm], bold_first_col=True))
    story.append(Paragraph(f'Oct 12 replay: {b["rs"]["n_days"]} KRX sessions ({b["rs"]["first"]} to {b["rs"]["last"]}), same 10:20–15:20 KST window, '
                           'KRX bars delayed 20 minutes as live. "Live pct." is the share of replayed sessions that did worse than the live result, ties counted as half.', S["note"]))
    story.append(Paragraph("What the second run confirms, and what it changes", S["h2"]))
    for h, body in txt["lessons"]:
        story.append(Paragraph(f"<b>{h}</b> {body}", S["li"], bulletText="•"))
    oc = b["an"].get("outcomes")
    if oc:                                # from the analysis, not typed by hand
        story.append(Paragraph("Which trades worked, which hurt, and the worst asset (Oct 12)", S["h2"]))
        rows = [["", "Account", "Instrument", "Net", "Gross", "Cost", "Hold"]]
        for label, key in (("Best", "best_trades"), ("Worst", "worst_trades")):
            for t in oc[key][:3]:
                rows.append([label, t["account"], f'{t["name"]} ({t["traded"]})' if t["traded"] != t["key"] else t["name"],
                             usd(t["pnl_net"]), usd(t["pnl_gross"]), f'${t["cost"]:.2f}', f'{t["hold_min"]:.0f} min'])
        story.append(table(rows, [14 * mm, 30 * mm, 56 * mm, 18 * mm, 18 * mm, 16 * mm, 18 * mm], bold_first_col=True))
        w, w1 = oc["worst_assets_all_accounts"][0], (a["an"].get("outcomes") or {}).get("worst_assets_all_accounts", [None])[0]
        rk = (oc.get("riskiest_trades") or [None])[0]
        line = (f'Worst asset across all accounts: {w["name"]}, {usd(w["net"])} over {w["trades"]} trades, '
                f'${w["cost"]:.2f} of it costs'
                + (f' (Oct 7: {w1["name"]}, {usd(w1["net"])} over {w1["trades"]} trades)' if w1 else "") + ". ")
        if rk:
            line += (f'Riskiest trade by adverse excursion: {rk["account"]} {rk["name"]}, down ${abs(rk["mae_usd"]):.2f} at '
                     f'its worst, closed at {usd(rk["pnl_net"])}. ')
        if oc.get("cost_share_of_losses") is not None:
            line += f"Costs were {oc['cost_share_of_losses']:.0%} of what the losing trades lost."
        story.append(Paragraph(line, S["note"]))
    story.append(Paragraph("Limits", S["h2"]))
    story.append(Paragraph(txt["limits"], S["p"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(txt["footer"], S["note"]))

    def deco(canv, doc):
        canv.saveState()
        canv.setFont("UI", 7)
        canv.setFillColor(MUTED)
        canv.drawString(15 * mm, 9 * mm, "QUANTGEN paper_live · second live paper session · paper trading only, not investment advice")
        canv.drawRightString(195 * mm, 9 * mm, f"{doc.page}")
        canv.restoreState()

    SimpleDocTemplate(out_pdf, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=13 * mm, bottomMargin=15 * mm,
                      title="QUANTGEN second live paper session", author="QUANTGEN paper_live").build(story, onFirstPage=deco, onLaterPages=deco)
    print("wrote", out_pdf)


if __name__ == "__main__":
    main(sys.argv[1])
