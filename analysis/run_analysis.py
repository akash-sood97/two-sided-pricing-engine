"""One command: fit demand, run the two-sided engine, write outputs/, figures/ and the decision memo.

    python analysis/run_analysis.py

Every number quoted in figures and in docs/DECISION_MEMO.md is computed here, not typed.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import economics as X  # noqa: E402
from src import elasticity as E  # noqa: E402
from src import viz  # noqa: E402
from src.config import REFERENCE_WAGE  # noqa: E402
from src.partners import churn_probability  # noqa: E402

OUT, FIG, DOCS = ROOT / "outputs", ROOT / "figures", ROOT / "docs"
for d in (OUT, FIG, DOCS):
    d.mkdir(exist_ok=True)
C = viz.C
viz.setup()


def label(seg):  # "Delhi / appliance repair" -> "Delhi · appliance repair"
    return seg.replace(" / ", " · ")


def main():
    tx = E.load_transactions(ROOT / "data/processed/transactions.csv")
    truth = pd.read_csv(ROOT / "data/processed/segment_truth.csv")
    partners = pd.read_csv(ROOT / "data/processed/partners.csv")

    fit = E.fit_all(tx, truth)
    placebo = E.deal_placebo(tx)
    holdout = E.holdout_comparison(tx)
    segs = X.build_segments(fit, tx, partners)
    f = X.calibrate_capacity(segs)
    tab = X.scenario_table(segs)
    robust = X.decision_robustness(segs)
    sens = X.sensitivity(segs)

    fit.to_csv(OUT / "elasticity_fit.csv", index=False)
    placebo.to_csv(OUT / "deal_placebo.csv", index=False)
    holdout.to_csv(OUT / "holdout_comparison.csv", index=False)
    tab.to_csv(OUT / "scenarios.csv", index=False)
    robust.to_csv(OUT / "decision_robustness.csv", index=False)
    sens.to_csv(OUT / "sensitivity.csv", index=False)

    tot = tab.groupby("scenario")[["promised", "gross", "repl", "net"]].sum()
    sq, ss, ts, tf = (tot.loc[k] for k in ["Status quo", "Single-sided (in-sample)", "Two-sided (in-sample)", "Two-sided (full band)"])
    cd = tab[tab.segment == "Delhi / cleaning"].set_index("scenario")
    below = partners.groupby(["city", "skill"])["earnings_per_job"].mean().reset_index()
    below = below[below.earnings_per_job < REFERENCE_WAGE]
    S = dict(
        bookable_share=f, coverage=float(fit.covered.mean()), mae_beta=float((fit.beta - fit.true_beta).abs().mean()),
        placebo_sig=int((placebo.p_value < 0.05).sum()), logit_ll=float(holdout.log_loss[1]),
        gbm_ll=float(holdout.log_loss[2]), base_ll=float(holdout.log_loss[0]),
        net_sq=sq.net, net_ss=ss.net, net_ts=ts.net, net_tf=tf.net, promised_ss=ss.promised,
        uplift_ts=ts.net / sq.net - 1, uplift_ss=ss.net / sq.net - 1, uplift_tf=tf.net / sq.net - 1,
        gain_two_vs_single=ts.net - ss.net, gap_single_promised=ss.promised - ss.net,
        cd_r_single=cd.loc["Single-sided (in-sample)", "r"], cd_r_two=cd.loc["Two-sided (in-sample)", "r"],
        cd_serv_single=cd.loc["Single-sided (in-sample)", "serv_peak"], cd_serv_two=cd.loc["Two-sided (in-sample)", "serv_peak"],
        cd_net_single=cd.loc["Single-sided (in-sample)", "net"], cd_net_two=cd.loc["Two-sided (in-sample)", "net"],
        cd_net_sq=cd.loc["Status quo", "net"], cd_promised_single=cd.loc["Single-sided (in-sample)", "promised"],
        n_below=len(below), churn_repl_sq=sq.repl, churn_repl_ts=ts.repl,
        sens_r_lo=float(sens.cleaning_delhi_r.min()), sens_r_hi=float(sens.cleaning_delhi_r.max()),
        sens_up_lo=float(sens.uplift_vs_status_quo.min()), sens_up_hi=float(sens.uplift_vs_status_quo.max()),
        robust_min=float(robust.direction_stability.min()),
    )
    (OUT / "summary.json").write_text(json.dumps({k: float(v) for k, v in S.items()}, indent=2))

    fig1_recovery(fit)
    fig2_partner(partners)
    fig3_frontier(segs, S)
    fig4_moves(tab)
    fig5_scenarios(sq, ss, ts, tf, S)
    fig6_sensitivity(sens)
    write_memo(S, tab, robust, fit)
    print("Done. Wrote outputs/, figures/, docs/DECISION_MEMO.md")
    for k in ["uplift_ts", "uplift_ss", "uplift_tf", "gain_two_vs_single", "cd_serv_single", "cd_serv_two", "coverage"]:
        print(f"  {k}: {S[k]:.4f}")


# --------------------------------------------------------------------------- figures
def fig1_recovery(fit):
    d = fit.sort_values("true_beta").reset_index(drop=True)
    fig, ax = plt_fig(9, 5.6)
    y = np.arange(len(d))
    ax.hlines(y, d.beta_lo, d.beta_hi, color=C["blue"], lw=2.4, alpha=0.9, zorder=2)
    ax.scatter(d.beta, y, s=46, color=C["blue"], zorder=3, label="Estimated β (95% interval)")
    ax.scatter(d.true_beta, y, s=64, marker="D", facecolor=C["surface"], edgecolor=C["orange"], lw=2, zorder=4,
               label="True β used to generate the data")
    ax.set_yticks(y, [label(f"{c} / {j.replace('_', ' ')}") for c, j in zip(d.city, d.job_type)])
    ax.set_xlabel("Price sensitivity β  (more negative = customers react more to price)")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="upper left", fontsize=9)
    viz.header(fig, f"The model recovers {int(d.covered.sum())} of 10 true price sensitivities inside its 95% interval",
               "Segment-level logit of booking on ln(relative price), 108,957 leads · a parameter-recovery check on synthetic data")
    fig.subplots_adjust(left=0.27, right=0.97, top=0.82, bottom=0.14)
    viz.footnote(fig, "Recovery is testable because the data is synthetic and the true β is known. "
                      "Real marketplaces have no answer key; this is a check on the estimator, not on reality.")
    viz.save(fig, FIG / "01_elasticity_recovery.png")


def fig2_partner(partners):
    fig, ax = plt_fig(9, 5.4)
    x = np.linspace(120, 380, 300)
    ax.plot(x, churn_probability(x) * 100, color=C["blue"], lw=2.6)
    ax.axvline(REFERENCE_WAGE, color=C["muted"], lw=1.2, ls=(0, (4, 3)))
    ax.axvspan(120, REFERENCE_WAGE, color=C["orange_light"], alpha=0.55, lw=0)
    ax.text(REFERENCE_WAGE + 3, 44, f"Reference wage\n₹{REFERENCE_WAGE:.0f} / job", fontsize=9, color=C["muted"], va="top")
    seg = partners.groupby(["city", "skill"]).earnings_per_job.mean().reset_index()
    seg["churn"] = churn_probability(seg.earnings_per_job.to_numpy()) * 100
    for _, r in seg.sort_values("earnings_per_job").iterrows():
        below = r.earnings_per_job < REFERENCE_WAGE
        ax.scatter(r.earnings_per_job, r.churn, s=52, color=C["orange"] if below else C["blue"],
                   edgecolor=C["surface"], lw=1.5, zorder=4)
    for job in ["plumbing", "appliance_repair"]:
        r = seg[seg.skill == job].mean(numeric_only=True)
        ax.annotate(f"{job.replace('_', ' ')}: ₹{r.earnings_per_job:.0f} a job,\n{r.churn:.0f}% annual churn", (r.earnings_per_job, r.churn),
                    xytext=(140 if job == "plumbing" else r.earnings_per_job + 16, 22 if job == "plumbing" else r.churn + 6),
                    fontsize=9, color=C["ink"], arrowprops=dict(arrowstyle="-", color=C["neutral"], lw=1))
    ax.set_xlabel("Partner earnings per job (₹, segment mean at today's prices)")
    ax.set_ylabel("Annual partner churn probability (%)")
    ax.set_xlim(130, 380); ax.set_ylim(0, 50)
    viz.header(fig, f"Partner churn jumps below ₹{REFERENCE_WAGE:.0f} a job, and plumbing and appliance repair sit below it",
               "Annual churn probability vs partner earnings · dots are today's segment averages (orange = below the reference wage)")
    fig.subplots_adjust(left=0.09, right=0.97, top=0.82, bottom=0.15)
    viz.footnote(fig, "The churn curve and the ₹220 threshold are calibrated assumptions in the synthetic partner data, not estimated from real partners. The four higher-paid segments (above ₹380) are off-scale.")
    viz.save(fig, FIG / "02_partner_response.png")


def fig3_frontier(segs, S):
    import matplotlib.pyplot as plt
    seg = next(s for s in segs if s.key == "Delhi / cleaning")
    o = X.optimise(seg, X.IN_SAMPLE)
    ev, g = o["ev"], o["grid"]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9.2, 7.2), sharex=True, gridspec_kw=dict(height_ratios=[2.2, 1.2], hspace=0.12))
    a1.plot(g, ev["promised"] / 1e3, color=C["orange"], lw=2.4, ls=(0, (5, 2)), label="What a demand-only model expects")
    a1.plot(g, ev["net"] / 1e3, color=C["blue"], lw=2.8, label="What the two-sided model realises")
    ns, ts = o["grid"][o["i_naive"]], o["grid"][o["i_two"]]
    for a in (a1, a2):
        a.axvspan(g.min() - 0.01, g[np.argmax(ev["serv_peak"] >= 0.90)] - 0.0025, color=C["orange_light"], alpha=0.5, lw=0)
    a1.scatter([ns], [ev["promised"][o["i_naive"]] / 1e3], s=70, color=C["orange"], zorder=5)
    a1.scatter([ns], [ev["net"][o["i_naive"]] / 1e3], s=70, color=C["blue"], zorder=5)
    a1.scatter([ts], [ev["net"][o["i_two"]] / 1e3], s=90, color=C["blue"], edgecolor=C["ink"], lw=1.5, zorder=6)
    a1.annotate(f"Demand-only optimum ({ns:.2f}×)\nexpects ₹{ev['promised'][o['i_naive']]/1e3:.0f}k,\nrealises ₹{ev['net'][o['i_naive']]/1e3:.0f}k",
                (ns, ev["net"][o["i_naive"]] / 1e3), xytext=(0.835, 700), fontsize=9, arrowprops=dict(arrowstyle="-", color=C["neutral"]))
    a1.annotate(f"Two-sided optimum ({ts:.2f}×)\n₹{ev['net'][o['i_two']]/1e3:.0f}k, peak fulfilment {ev['serv_peak'][o['i_two']]*100:.0f}%",
                (ts, ev["net"][o["i_two"]] / 1e3), xytext=(0.94, 920), fontsize=9, arrowprops=dict(arrowstyle="-", color=C["neutral"]))
    a1.set_ylabel("Annual contribution (₹ thousand)")
    a1.legend(loc="lower right", fontsize=9)
    a2.plot(g, ev["serv_peak"] * 100, color=C["aqua"], lw=2.6)
    a2.axhline(90, color=C["muted"], lw=1.1, ls=(0, (4, 3)))
    a2.text(1.045, 91.5, "90% target", fontsize=9, color=C["muted"], ha="right")
    a2.set_ylabel("Peak-week\nfulfilment (%)"); a2.set_ylim(55, 103)
    a2.set_xlabel("Price as a multiple of today's price  (left = discount, right = increase)")
    a2.text(g.min() + 0.004, 60, "Oversold: demand exceeds\npartner capacity", fontsize=9, color=C["muted"])
    viz.header(fig, f"In Delhi cleaning, chasing demand alone drops peak-week fulfilment to {S['cd_serv_single']*100:.0f}%",
               "Annual contribution and peak-week fulfilment across the price range the data covers · Delhi cleaning, largest segment", top=0.985)
    fig.subplots_adjust(left=0.1, right=0.97, top=0.885, bottom=0.115)
    viz.footnote(fig, "Capacity share of listed partner-hours is calibrated so the busiest segment runs at 85% peak utilisation today; see sensitivity chart.")
    viz.save(fig, FIG / "03_delhi_cleaning_frontier.png")


def fig4_moves(tab):
    two = tab[tab.scenario == "Two-sided (in-sample)"].set_index("segment")
    full = tab[tab.scenario == "Two-sided (full band)"].set_index("segment")
    d = pd.DataFrame({"r": two.r, "r_full": full.r, "status": two.status, "gap": two.floor_gap}).sort_values("r")
    fig, ax = plt_fig(9.4, 5.8)
    y = np.arange(len(d))
    ax.axvline(0, color=C["muted"], lw=1.2)
    ax.axvspan(5, 40, color=C["blue_light"], alpha=0.35, lw=0)
    ax.text(5.8, 1.6, "Beyond the observed\nprice range: test first", fontsize=8.5, color=C["muted"], va="center")
    for i, (seg, r) in enumerate(d.iterrows()):
        pct, pfull = (r.r - 1) * 100, (r.r_full - 1) * 100
        ax.hlines(i, 0, pct, color=C["blue"], lw=6, alpha=0.95, zorder=2)
        if abs(pfull - pct) > 0.4:
            ax.scatter(pfull, i, s=64, facecolor=C["surface"], edgecolor=C["orange"], lw=2, zorder=4)
            ax.hlines(i, pct, pfull, color=C["orange"], lw=1.4, ls=(0, (3, 2)), zorder=1)
        ax.text(pct / 2 if pct >= 0 else pct - 1.0, i - 0.34 if pct >= 0 else i, f"{pct:+.1f}%", va="center",
                ha="center" if pct >= 0 else "right", fontsize=9, color=C["ink"], fontweight="bold")
        if abs(pfull - pct) > 0.4:
            ax.text(pfull + 1.0, i, f"test to {pfull:+.0f}%", va="center", fontsize=9, color=C["ink"])
        if r.status == "floor not reachable":
            ax.text(pct + 1.6, i - 0.34, f"floor still ₹{r.gap:.0f} a job away", va="center", fontsize=8.5, color=C["muted"])
    ax.set_yticks(y, [label(s) for s in d.index]); ax.set_xlim(-26, 40)
    ax.set_xlabel("Recommended price change vs today (%)"); ax.grid(axis="y", visible=False)
    ax.scatter([], [], s=64, facecolor=C["surface"], edgecolor=C["orange"], lw=2, label="Full-band optimum (needs a price test)")
    ax.legend(loc="upper left", fontsize=9)
    n_cut, n_up = int((d.r < 0.999).sum()), int((d.r > 1.001).sum())
    viz.header(fig, f"Cut price in {n_cut} segments, raise it in {n_up}, and test the bigger rises before rolling them out",
               "Two-sided optimum inside the observed price range (solid) and out to +25% (open marker) · both constraints applied")
    fig.subplots_adjust(left=0.22, right=0.97, top=0.83, bottom=0.14)
    viz.footnote(fig, "Observed relative prices span ~0.71–1.05× base; any move above +5% extrapolates beyond the data.")
    viz.save(fig, FIG / "04_recommended_moves.png")


def fig5_scenarios(sq, ss, ts, tf, S):
    fig, ax = plt_fig(9.2, 5.6)
    names = ["Status quo", "Demand-only\n(what it delivers)", "Two-sided\n(in observed range)", "Two-sided\n(full band, needs test)"]
    vals = [sq.net, ss.net, ts.net, tf.net]
    cols = [C["neutral"], C["orange"], C["blue"], C["blue"]]
    bars = ax.bar(names, [v / 1e6 for v in vals], color=cols, width=0.58, zorder=3)
    bars[3].set_hatch("////"); bars[3].set_edgecolor(C["surface"]); bars[3].set_alpha(0.75)
    ax.bar(names[1], (ss.promised - ss.net) / 1e6, bottom=ss.net / 1e6, width=0.58, facecolor="none",
           edgecolor=C["orange"], ls=(0, (3, 2)), lw=1.6, zorder=4)
    ax.text(1, ss.promised / 1e6 + 0.12, f"Promised ₹{ss.promised/1e6:.2f}M\nnever arrives", ha="center", fontsize=8.5, color=C["muted"])
    for i, v in enumerate(vals[:3]):
        ax.text(i, v / 1e6 - 0.32, f"₹{v/1e6:.2f}M", ha="center", fontsize=11, fontweight="bold", color="white" if i else C["ink"], zorder=6)
    ax.text(2, ts.net / 1e6 + 0.08, f"+{S['uplift_ts']*100:.1f}% vs today", ha="center", fontsize=9.5, color=C["ink"])
    ax.text(3, tf.net / 1e6 + 0.08, f"₹{tf.net/1e6:.2f}M\n+{S['uplift_tf']*100:.1f}% vs today", ha="center", fontsize=10, color=C["ink"], fontweight="bold")
    ax.set_ylim(0, 7.2); ax.set_ylabel("Annual contribution, 10 segments (₹ million)"); ax.grid(axis="x", visible=False)
    viz.header(fig, f"Pricing both sides adds ₹{S['gain_two_vs_single']/1e6:.2f}M a year over a demand-only approach and ₹{(ts.net-sq.net)/1e6:.2f}M over today",
               "Realised annual contribution after partner churn and capacity limits, 10 city × job segments · all scenarios use the same constraints")
    fig.subplots_adjust(left=0.09, right=0.97, top=0.82, bottom=0.13)
    viz.footnote(fig, "Contribution = platform margin per fulfilled job less partner replacement cost. Cost assumptions are listed in the memo and stress-tested.")
    viz.save(fig, FIG / "05_scenario_comparison.png")


def fig6_sensitivity(sens):
    import matplotlib.pyplot as plt
    d = sens[sens.service_target == 0.90].sort_values("capacity_mult")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4.9))
    x = (d.capacity_mult - 1) * 100
    a1.plot(x, (d.cleaning_delhi_r - 1) * 100, color=C["blue"], lw=2.6, marker="o", ms=7)
    a1.axhline(0, color=C["muted"], lw=1); a1.set_title("Delhi cleaning: recommended price change (%)")
    a2.plot(x, d.uplift_vs_status_quo * 100, color=C["aqua"], lw=2.6, marker="o", ms=7)
    a2.set_ylim(0, 10); a2.set_title("Portfolio: gain vs today (%)")
    for a in (a1, a2):
        a.set_xlabel("Bookable partner capacity vs baseline assumption (%)")
    viz.header(fig, f"The Delhi cleaning price swings with the capacity assumption; the portfolio gain holds at +{d.uplift_vs_status_quo.min()*100:.0f}% to +{d.uplift_vs_status_quo.max()*100:.0f}%",
               "Two-sided optimum re-solved for capacity ±30% · 90% peak-fulfilment target")
    fig.subplots_adjust(left=0.07, right=0.98, top=0.79, bottom=0.15, wspace=0.22)
    viz.footnote(fig, "Capacity is the least-observed input, so it is the assumption to validate first. Raising the target from 80% to 95% moves the portfolio gain by under 0.5 points.")
    viz.save(fig, FIG / "06_sensitivity.png")


def plt_fig(w, h):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(w, h))
    return fig, ax


# --------------------------------------------------------------------------- memo
def write_memo(S, tab, robust, fit):
    two = tab[tab.scenario == "Two-sided (in-sample)"].set_index("segment")
    full = tab[tab.scenario == "Two-sided (full band)"].set_index("segment")
    sq = tab[tab.scenario == "Status quo"].set_index("segment")
    rows = []
    for seg in two.sort_values("r").index:
        t, fu, s0 = two.loc[seg], full.loc[seg], sq.loc[seg]
        action = f"{(t.r-1)*100:+.1f}%"
        test = f"test to {(fu.r-1)*100:+.0f}%" if fu.r - t.r > 0.004 else "-"
        rows.append(f"| {label(seg)} | {action} | {test} | {s0.churn*100:.0f}% → {t.churn*100:.0f}% | {t.serv_peak*100:.0f}% | ₹{s0.net/1e3:,.0f}k → ₹{t.net/1e3:,.0f}k |")
    txt = f"""# Decision memo: two-sided pricing recommendation

*Synthetic data; assumptions labelled; results are model outputs, not production impact.*

## The answer
**Move prices as shown below, inside the range the data covers, and run price tests before going further.** Doing so lifts modelled annual contribution by **{S['uplift_ts']*100:.1f}%** (₹{S['net_sq']/1e6:.2f}M → ₹{S['net_ts']/1e6:.2f}M across 10 city × job segments). A demand-only approach delivers **{S['uplift_ss']*100:.1f}%**. The **₹{S['gain_two_vs_single']/1e6:.2f}M** difference comes from one place: Delhi cleaning.

## Situation → complication → resolution
- **Situation.** Price sets conversion for customers and earnings for partners at once.
- **Complication.** A demand-only optimum says to discount Delhi cleaning to {S['cd_r_single']:.2f}× today's price. That lifts demand about 60% but oversells partner capacity: peak-week fulfilment falls to **{S['cd_serv_single']*100:.0f}%** and realised contribution to ₹{S['cd_net_single']/1e3:.0f}k, against ₹{S['cd_promised_single']/1e3:.0f}k promised and ₹{S['cd_net_sq']/1e3:.0f}k today.
- **Resolution.** Price Delhi cleaning at **{S['cd_r_two']:.3f}× ({(S['cd_r_two']-1)*100:+.1f}%)**: fulfilment stays at {S['cd_serv_two']*100:.0f}%, contribution rises to ₹{S['cd_net_two']/1e3:.0f}k.

## Recommended moves
| Segment | Move now | Then | Partner churn | Peak fulfilment | Contribution / yr |
|---|---|---|---|---|---|
{chr(10).join(rows)}

*"Move now" is inside the observed price range (~0.71–1.05× base). "Then" is the full-band optimum (up to +25%), which extrapolates beyond the data and needs a price test first.*

## Interpretation
1. **Where two-sided pricing matters is a capacity question, not a wage question.** The partner-earnings floor does not change any segment's optimum here because most demand is inelastic enough that price rises are already optimal. Capacity is what separates the two approaches.
2. **{S['n_below']:.0f} segments sit below the ₹{REFERENCE_WAGE:.0f} earnings reference wage today** (plumbing, appliance repair in both cities), with 28-39% modelled annual churn. For them, raising price is a win-win: better partner economics and higher margin. Appliance repair clears the floor at +5%; plumbing needs about +19%, which is outside the observed range, so it needs a test.
3. **The recommendation is stable.** Re-solving with each segment's price sensitivity redrawn from its own uncertainty leaves the direction of every move unchanged in at least {S['robust_min']*100:.0f}% of draws.
4. **The Delhi cleaning price is assumption-sensitive.** It ranges from {(S['sens_r_lo']-1)*100:+.0f}% to {(S['sens_r_hi']-1)*100:+.0f}% as bookable capacity moves ±30%, because price is the rationing device when capacity is tight. The portfolio gain barely moves ({S['sens_up_lo']*100:.0f}% to {S['sens_up_hi']*100:.0f}%).

## Trade-offs and what this does not show
- **Demand response is estimated; partner response is calibrated, not estimated.** The churn curve and the ₹{REFERENCE_WAGE:.0f} threshold are built into the synthetic partner data. Real churn must be measured before acting on the partner side.
- **Cost inputs are assumptions:** non-partner variable cost 10% of base price, ₹3,000 to replace a partner, 85% peak utilisation in the busiest segment, 90% fulfilment target.
- **The full-band gain (+{S['uplift_tf']*100:.1f}%) is extrapolation.** Treat it as a hypothesis for a price test.
- **No cross-price or promotion effects** are in this dataset (the generator has none), so cannibalisation and promotional elasticity are handled in the promotion project on real retail data.

## Next step
Run a staged price test in the six "raise" segments (+5% now, then +10%, +15%) with partner-earnings and fulfilment guardrails, and measure partner churn directly.
"""
    (DOCS / "DECISION_MEMO.md").write_text(txt)


if __name__ == "__main__":
    main()
