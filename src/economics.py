"""Weeks 3-4: the two-sided economics engine and the optimiser.

Chain, for a price multiplier r applied to a segment's base price:

    price -> conversion (fitted logit)          -> booking demand
    price -> partner earnings -> churn hazard   -> active partners -> capacity
    demand vs capacity                          -> serviceability, fulfilled bookings
    fulfilled bookings x margin per job         -> contribution
    churned partners x replacement cost         -> partner-side cost

Everything below the demand model is a labelled ASSUMPTION (ASSUMPTIONS), not an
estimate from data, and is stress-tested in the sensitivity analysis.
"""
from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

from src.config import AVG_WEEKLY_HOURS_PER_ACTIVE_PARTNER, JOB_TYPES, REFERENCE_WAGE, TAKE_RATE
from src.partners import churn_probability


@dataclass(frozen=True)
class Assumptions:
    take_rate: float = TAKE_RATE                 # partner share of the net price (from the generator)
    var_cost_pct: float = 0.10                   # non-partner variable cost per job, % of base price
    replacement_cost: float = 3000.0             # INR to recruit + onboard one replacement partner
    earnings_floor: float = REFERENCE_WAGE       # INR/job; segment-mean partner earnings must stay >= this
    service_target: float = 0.90                 # peak-week fulfilment must stay >= this
    peak_util_target: float = 0.85               # calibrates bookable-hours share (see calibrate_capacity)
    band: tuple = (0.80, 1.25)                   # price multiplier limits (governance guardrail)
    hours_per_partner: float = AVG_WEEKLY_HOURS_PER_ACTIVE_PARTNER


A = Assumptions()
SUPPORT = (0.71, 1.05)   # relative-price range actually observed (list +/-5%, discounts 0-25%)
IN_SAMPLE = Assumptions(band=(0.80, SUPPORT[1]))
GRID = np.round(np.arange(0.80, 1.2501, 0.005), 3)


@dataclass
class Segment:
    city: str
    job_type: str
    a: float                 # fitted intercept
    beta: float              # fitted logit-price coefficient
    se: float
    leads_week: np.ndarray   # 52 weekly leads (observed)
    earn0: np.ndarray        # partners' status-quo earnings per job
    hours_job: float
    base_price: float
    bookable_share: float = 1.0  # f, set by calibrate_capacity

    @property
    def key(self):
        return f"{self.city} / {self.job_type.replace('_', ' ')}"


def build_segments(fit: pd.DataFrame, tx: pd.DataFrame, partners: pd.DataFrame) -> list:
    tx = tx.copy()
    tx["week"] = tx["date"].dt.to_period("W-SUN")
    segs = []
    for _, row in fit.iterrows():
        sub = tx[(tx["city"] == row.city) & (tx["job_type"] == row.job_type)]
        wk = sub.groupby("week").size().to_numpy(dtype=float)
        earn = partners[(partners["city"] == row.city) & (partners["skill"] == row.job_type)]["earnings_per_job"].to_numpy()
        segs.append(Segment(row.city, row.job_type, row.a, min(row.beta, 0.0), row.se, wk, earn,
                            JOB_TYPES[row.job_type]["hours_per_job"], JOB_TYPES[row.job_type]["base_price"]))
    return segs


def evaluate(seg: Segment, r, beta=None, a_=A) -> dict:
    """Vectorised over a price-multiplier array r. Returns per-r arrays (annual INR)."""
    r = np.atleast_1d(np.asarray(r, dtype=float))
    b = seg.beta if beta is None else beta
    p = 1.0 / (1.0 + np.exp(-(seg.a + b * np.log(r))))                     # conversion
    earn_mean = seg.earn0.mean() * r                                       # mean partner earnings/job
    churn = churn_probability(seg.earn0[None, :] * r[:, None]).mean(axis=1)  # annual churn probability
    n = len(seg.earn0)
    active = n * (1.0 - churn)
    cap_jobs = active * a_.hours_per_partner * seg.bookable_share / seg.hours_job   # jobs/week
    demand_w = seg.leads_week[None, :] * p[:, None]                        # (R, weeks)
    fulfilled_w = np.minimum(demand_w, cap_jobs[:, None])
    peak = np.argmax(seg.leads_week)
    serv_peak = fulfilled_w[:, peak] / demand_w[:, peak]
    demand_yr, fulfilled_yr = demand_w.sum(1), fulfilled_w.sum(1)
    margin_job = (1 - a_.take_rate) * seg.base_price * r - a_.var_cost_pct * seg.base_price
    repl = n * churn * a_.replacement_cost
    return dict(r=r, price=seg.base_price * r, conversion=p, earn=earn_mean, churn=churn, active=active,
                demand=demand_yr, fulfilled=fulfilled_yr, serv_peak=serv_peak,
                serv_annual=fulfilled_yr / demand_yr, margin_job=margin_job,
                promised=demand_yr * margin_job,                     # what a demand-only model expects
                gross=fulfilled_yr * margin_job, repl=repl,
                net=fulfilled_yr * margin_job - repl)                # realised two-sided contribution


def calibrate_capacity(segs: list, a_=A) -> float:
    """Pick one bookable-hours share f so the busiest segment runs at peak_util_target
    at today's price. f is an assumption (listed partner-hours are not all bookable)."""
    need = []
    for s in segs:
        s.bookable_share = 1.0
        ev = evaluate(s, [1.0], a_=a_)
        peak_jobs = s.leads_week.max() * ev["conversion"][0]
        hours_needed = peak_jobs * s.hours_job
        listed = ev["active"][0] * a_.hours_per_partner
        need.append(hours_needed / listed)
    f = max(need) / a_.peak_util_target
    for s in segs:
        s.bookable_share = f
    return f


def optimise(seg: Segment, a_=A, beta=None, grid=GRID) -> dict:
    lo, hi = a_.band
    g = grid[(grid >= lo - 1e-9) & (grid <= hi + 1e-9)]
    ev = evaluate(seg, g, beta=beta, a_=a_)
    i_naive = int(np.argmax(ev["promised"]))                               # single-sided: demand only
    feas = (ev["earn"] >= a_.earnings_floor) & (ev["serv_peak"] >= a_.service_target)
    floor_gap = 0.0
    if feas.any():
        idx = np.where(feas)[0]
        i_two = int(idx[np.argmax(ev["net"][idx])])
        status = "feasible"
    else:
        # earnings floor unreachable inside this price range: keep serviceability, maximise net,
        # and report how far the best point sits below the floor
        svc = np.where(ev["serv_peak"] >= a_.service_target)[0]
        idx = svc if len(svc) else np.arange(len(g))
        i_two = int(idx[np.argmax(ev["net"][idx])])
        status = "floor not reachable" if ev["earn"][i_two] < a_.earnings_floor else "serviceability not reachable"
        floor_gap = max(a_.earnings_floor - ev["earn"][i_two], 0.0)
    # which constraint stops the single-sided optimum from being feasible?
    bind = []
    if ev["earn"][i_naive] < a_.earnings_floor:
        bind.append("partner-earnings floor")
    if ev["serv_peak"][i_naive] < a_.service_target:
        bind.append("serviceability")
    return dict(grid=g, ev=ev, i_naive=i_naive, i_two=i_two, status=status, binds=bind, floor_gap=floor_gap)


def scenario_table(segs: list, a_=A) -> pd.DataFrame:
    """Four scenarios per segment. 'in-sample' restricts the two-sided optimum to the price
    range the data actually covers; anything above SUPPORT[1] is extrapolation and needs a test."""
    rows = []
    for s in segs:
        o = optimise(s, a_)
        oi = optimise(s, replace(a_, band=(a_.band[0], min(a_.band[1], SUPPORT[1]))))
        ev, iq = o["ev"], int(np.argmin(np.abs(o["grid"] - 1.0)))
        picks = [("Status quo", ev, iq, o), ("Single-sided (in-sample)", oi["ev"], oi["i_naive"], oi),
                 ("Two-sided (in-sample)", oi["ev"], oi["i_two"], oi), ("Two-sided (full band)", ev, o["i_two"], o)]
        for name, e, i, oo in picks:
            rows.append(dict(segment=s.key, city=s.city, job_type=s.job_type, scenario=name, r=e["r"][i],
                             price=e["price"][i], conversion=e["conversion"][i], earn=e["earn"][i],
                             churn=e["churn"][i], serv_peak=e["serv_peak"][i], serv_annual=e["serv_annual"][i],
                             demand=e["demand"][i], fulfilled=e["fulfilled"][i], promised=e["promised"][i],
                             gross=e["gross"][i], repl=e["repl"][i], net=e["net"][i],
                             extrapolated=bool(e["r"][i] > SUPPORT[1] + 1e-9),
                             status=oo["status"] if name.startswith("Two") else "", floor_gap=oo["floor_gap"] if name.startswith("Two") else 0.0,
                             binds="; ".join(oi["binds"]) if name.startswith("Single") else ""))
    return pd.DataFrame(rows)


def decision_robustness(segs: list, a_=A, draws: int = 400, seed: int = 7) -> pd.DataFrame:
    """Re-solve the two-sided optimum with beta drawn from its sampling distribution.
    Reports how stable the recommendation is (share of draws with the same direction)."""
    rng = np.random.default_rng(seed)
    rows = []
    for s in segs:
        a_ = replace(a_, band=(a_.band[0], min(a_.band[1], SUPPORT[1])))
        base = optimise(s, a_)
        r_star = base["grid"][base["i_two"]]
        rs = []
        for b in np.minimum(rng.normal(s.beta, s.se, draws), 0.0):
            o = optimise(s, a_, beta=b)
            rs.append(o["grid"][o["i_two"]])
        rs = np.array(rs)
        direction = np.sign(r_star - 1.0)
        same = (np.sign(rs - 1.0) == direction) if direction != 0 else (np.abs(rs - 1.0) < 0.03)
        rows.append(dict(segment=s.key, r_star=r_star, r_p10=np.percentile(rs, 10), r_p90=np.percentile(rs, 90),
                         direction_stability=same.mean()))
    return pd.DataFrame(rows)


def sensitivity(segs: list, a_=A) -> pd.DataFrame:
    """Portfolio net contribution and two-sided price for the tightest segment under alternative assumptions."""
    rows = []
    f0 = segs[0].bookable_share
    for fmult in [0.7, 0.85, 1.0, 1.15, 1.3]:
        for tgt in [0.80, 0.85, 0.90, 0.95]:
            for s in segs:
                s.bookable_share = f0 * fmult
            a2 = replace(a_, service_target=tgt)
            tab = scenario_table(segs, a2)
            two = tab[tab.scenario == "Two-sided (in-sample)"]
            sq = tab[tab.scenario == "Status quo"]
            cd = two[two.segment == "Delhi / cleaning"].iloc[0]
            rows.append(dict(capacity_mult=fmult, service_target=tgt, cleaning_delhi_r=cd.r,
                             portfolio_net=two.net.sum(), uplift_vs_status_quo=two.net.sum() / sq.net.sum() - 1,
                             unreachable_segments=int((two.status != "feasible").sum())))
    for s in segs:
        s.bookable_share = f0
    return pd.DataFrame(rows)
