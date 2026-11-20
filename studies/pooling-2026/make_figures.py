"""Figures for the study write-up (static PNG, light surface), from results/results.json.

    python studies/pooling-2026/make_figures.py

fig1_refused_by_target.png  share of R0-comparable pairs the pooling check refuses, per
                            target (one series; EGFR named in bold)
fig2_egfr_reasons.png       EGFR: refused pairs by the first named condition
fig3_egfr_shift.png         EGFR: shift in pooled potency, averaging across types (R1)
                            vs the largest valid class, with the 0.3 and 1.0 lines

Colours: the reference palette's categorical slot 1 (#2a78d6) for the single series,
text inks #0b0b0b / #52514e, surface #fcfcfb; recessive grid. A table of every number
plotted is in results/RESULTS.md.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
SERIES, INK, INK2, SURF, GRID = "#2a78d6", "#0b0b0b", "#52514e", "#fcfcfb", "#e4e3df"

NAMES = {
    "CHEMBL203": "EGFR", "CHEMBL1862": "ABL1", "CHEMBL1871": "Androgen receptor",
    "CHEMBL2034": "Glucocorticoid receptor", "CHEMBL2047": "FXR", "CHEMBL204": "Thrombin",
    "CHEMBL2147": "PIM1", "CHEMBL214": "5-HT1A", "CHEMBL218": "CB1",
    "CHEMBL219": "Dopamine D4", "CHEMBL228": "SERT", "CHEMBL231": "Histamine H1",
    "CHEMBL233": "Mu opioid", "CHEMBL234": "Dopamine D3", "CHEMBL235": "PPARγ",
    "CHEMBL236": "Delta opioid", "CHEMBL237": "Kappa opioid", "CHEMBL238": "DAT",
    "CHEMBL239": "PPARα", "CHEMBL244": "Factor Xa", "CHEMBL262": "GSK-3β",
    "CHEMBL264": "Histamine H3", "CHEMBL2835": "JAK1", "CHEMBL287": "Sigma-1",
    "CHEMBL2971": "JAK2", "CHEMBL3979": "PPARδ", "CHEMBL4005": "PIK3CA",
    "CHEMBL4203": "CLK4", "CHEMBL4616": "Ghrelin receptor", "CHEMBL4792": "Orexin-2"}


def style(ax):
    ax.set_facecolor(SURF)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9, length=0)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def fig1(res):
    per = [(r["target"], r["M1"]["refused_share_of_paired"]) for r in res["per_target"]
           if r["M1"]["refused_share_of_paired"] is not None]
    per.sort(key=lambda x: x[1])
    fig, ax = plt.subplots(figsize=(7.2, 0.26 * len(per) + 1.4), dpi=150, facecolor=SURF)
    style(ax)
    ys = range(len(per))
    ax.barh(ys, [100 * v for _, v in per], height=0.62, color=SERIES, edgecolor=SURF,
            linewidth=1)
    ax.set_yticks(list(ys))
    labels = [f"{NAMES.get(t, t)} ({t})" for t, _ in per]
    ax.set_yticklabels(labels)
    for lab, (t, _) in zip(ax.get_yticklabels(), per, strict=True):
        if t == "CHEMBL203":
            lab.set_fontweight("bold")
            lab.set_color(INK)
    for y, (_, v) in zip(ys, per, strict=True):
        ax.text(100 * v + 0.6, y, f"{100 * v:.0f}%", va="center", fontsize=8, color=INK2)
    ax.set_xlabel("Pairs refused by the pooling check (% of pairs unit conversion treats "
                  "as comparable)", color=INK2, fontsize=9)
    ax.set_title("Same molecule, same target, same unit: how often the assay conditions "
                 "differ", loc="left", color=INK, fontsize=11)
    fig.tight_layout()
    fig.savefig(RES / "fig1_refused_by_target.png", facecolor=SURF)
    plt.close(fig)


def fig2(res):
    egfr = next(r for r in res["per_target"] if r["target"] == "CHEMBL203")
    reasons = list(egfr["M1"]["refused_by_first_reason"].items())[:8][::-1]
    fig, ax = plt.subplots(figsize=(7.2, 0.34 * len(reasons) + 1.3), dpi=150, facecolor=SURF)
    style(ax)
    ys = range(len(reasons))
    ax.barh(ys, [v for _, v in reasons], height=0.62, color=SERIES, edgecolor=SURF,
            linewidth=1)
    ax.set_yticks(list(ys))
    ax.set_yticklabels([k for k, _ in reasons], fontsize=9)
    mx = max(v for _, v in reasons)
    for y, (_, v) in zip(ys, reasons, strict=True):
        ax.text(v + mx * 0.01, y, f"{v:,}", va="center", fontsize=8, color=INK2)
    ax.set_xlabel("Refused pairs of EGFR records (first named reason)", color=INK2, fontsize=9)
    ax.set_title("EGFR: why pairs may not be pooled", loc="left", color=INK, fontsize=11)
    fig.tight_layout()
    fig.savefig(RES / "fig2_egfr_reasons.png", facecolor=SURF)
    plt.close(fig)


def fig3(shifts: list):
    if not shifts:
        return
    fig, ax = plt.subplots(figsize=(7.2, 3.4), dpi=150, facecolor=SURF)
    style(ax)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.xaxis.grid(False)
    top = max(3.0, math.ceil(max(shifts) * 2) / 2)
    bins = [i * 0.1 for i in range(int(top * 10) + 1)]
    ax.hist([min(s, top) for s in shifts], bins=bins, color=SERIES, edgecolor=SURF,
            linewidth=1)
    ytop = ax.get_ylim()[1]
    for x, lab, h in ((0.3, "0.3 log units", 0.95), (1.0, "1 log unit", 0.82)):
        ax.axvline(x, color=INK2, linewidth=1, linestyle=(0, (3, 3)))
        ax.text(x + 0.04, ytop * h, lab, color=INK2, fontsize=8,
                bbox={"facecolor": SURF, "edgecolor": "none", "pad": 1})
    ax.set_xlabel("|average across types (R1) − pooled value of the largest valid class| "
                  "(log units)", color=INK2, fontsize=9)
    ax.set_ylabel("Molecules", color=INK2, fontsize=9)
    ax.set_title("EGFR: how much the pooled potency moves", loc="left", color=INK,
                 fontsize=11)
    fig.tight_layout()
    fig.savefig(RES / "fig3_egfr_shift.png", facecolor=SURF)
    plt.close(fig)


def main():
    res = json.loads((RES / "results.json").read_text(encoding="utf-8"))
    fig1(res)
    fig2(res)
    sh = RES / "egfr_shifts.json"
    fig3(json.loads(sh.read_text()) if sh.is_file() else [])
    print("figures written")


if __name__ == "__main__":
    main()
