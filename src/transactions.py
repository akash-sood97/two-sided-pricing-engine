"""Synthesize the transactions table. Segment-level elasticities are drawn
from the distribution calibrated on the UCI Online Retail II proxy
(src/proxy.py) — the "anchor demand-side on a public proxy, then simulate
the marketplace on top" strategy from 02_data_and_method.md.
"""
import numpy as np
import pandas as pd

from src.config import CITIES, JOB_TYPES, N_WEEKS, RNG, START_DATE

CITY_DEMAND_FACTOR = {"Delhi": 1.3, "Hyderabad": 1.0}
JOB_TYPE_DAILY_LEADS = {
    "cleaning": 40,
    "appliance_repair": 25,
    "salon_at_home": 30,
    "plumbing": 20,
    "pest_control": 15,
}
BASE_CONVERSION = 0.35  # booking rate at relative_price == 1.0, before elasticity effect


def _logit(p):
    return np.log(p / (1 - p))


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def simulate_transactions(elasticity_dist: dict, seasonality: pd.Series) -> pd.DataFrame:
    dates = pd.date_range(START_DATE, periods=N_WEEKS * 7, freq="D")
    chunks = []
    truth = []  # true segment betas, kept for the Week 2 parameter-recovery check

    for city in CITIES:
        for job_type, meta in JOB_TYPES.items():
            base_price = meta["base_price"]
            elasticity = float(np.clip(RNG.normal(elasticity_dist["mean"], elasticity_dist["std"]), -4.0, -0.2))
            truth.append({"city": city, "job_type": job_type, "true_beta": round(elasticity, 6)})
            lam_base = JOB_TYPE_DAILY_LEADS[job_type] * CITY_DEMAND_FACTOR[city]

            for day in dates:
                season_mult = float(seasonality.get(day.dayofweek, 1.0))
                n_leads = int(RNG.poisson(lam_base * season_mult))
                if n_leads == 0:
                    continue

                discount_applied = RNG.random(n_leads) < 0.3
                discount = np.where(discount_applied, RNG.uniform(0.05, 0.25, n_leads), 0.0)
                list_price = base_price * RNG.uniform(0.95, 1.05, n_leads)
                effective_price = list_price * (1 - discount)
                relative_price = effective_price / base_price

                log_odds = _logit(BASE_CONVERSION) + elasticity * np.log(relative_price)
                booking_prob = _sigmoid(log_odds)
                booked = (RNG.random(n_leads) < booking_prob).astype(int)
                gmv = effective_price * booked

                chunks.append(
                    pd.DataFrame(
                        {
                            "date": day,
                            "city": city,
                            "job_type": job_type,
                            "list_price": np.round(list_price, 2),
                            "discount": np.round(discount, 3),
                            "booked": booked,
                            "gmv": np.round(gmv, 2),
                            "units": 1,
                        }
                    )
                )

    out = pd.concat(chunks, ignore_index=True)
    out.attrs["segment_truth"] = pd.DataFrame(truth)
    return out
