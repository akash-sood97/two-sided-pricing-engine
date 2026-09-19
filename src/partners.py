"""Simulate the partners table: earnings-per-job and a churn probability
with a non-linear kink below the reference wage. 03_execution_plan.md's
risk mitigation explicitly calls for a genuine earnings-threshold
non-linearity (not a smooth curve) so the two-sided finding in later weeks
is non-obvious rather than baked in by construction.
"""
import numpy as np
import pandas as pd

from src.config import (
    CITIES,
    JOB_TYPES,
    N_PARTNERS_PER_CITY_JOBTYPE,
    REFERENCE_WAGE,
    RNG,
    TAKE_RATE,
    TENURE_MAX_MONTHS,
)


def churn_probability(earnings_per_job, base_rate: float = 0.03, max_extra: float = 0.45, k: float = 0.04):
    """Base attrition + a logistic hazard in (reference_wage - earnings):
    flat near base_rate above the floor, accelerating sharply below it."""
    gap = REFERENCE_WAGE - np.asarray(earnings_per_job, dtype=float)
    extra = max_extra / (1.0 + np.exp(-k * gap))
    return np.clip(base_rate + extra, 0.0, 0.95)


def simulate_partners() -> pd.DataFrame:
    rows = []
    partner_id = 0
    for city in CITIES:
        for job_type, meta in JOB_TYPES.items():
            for _ in range(N_PARTNERS_PER_CITY_JOBTYPE):
                partner_id += 1
                tenure = int(RNG.integers(1, TENURE_MAX_MONTHS + 1))
                jobs_done = int(RNG.poisson(lam=tenure * 8))
                price = meta["base_price"] * RNG.uniform(0.85, 1.05)
                earnings_per_job = price * TAKE_RATE
                churn_p = float(churn_probability(earnings_per_job))
                churn_flag = int(RNG.random() < churn_p)
                rows.append(
                    {
                        "partner_id": f"P{partner_id:05d}",
                        "city": city,
                        "skill": job_type,
                        "tenure_months": tenure,
                        "jobs_done": jobs_done,
                        "earnings_per_job": round(earnings_per_job, 2),
                        "churn_probability": round(churn_p, 4),
                        "churn_flag": churn_flag,
                        "active_flag": 0 if churn_flag else 1,
                    }
                )
    return pd.DataFrame(rows)
