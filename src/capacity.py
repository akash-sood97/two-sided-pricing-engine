"""Simulate the capacity table: city x job_type x week -> available
partner-hours, derived from the active partner population. This is the
input the serviceability constraint (Week 3) divides demand by.
"""
import pandas as pd

from src.config import AVG_WEEKLY_HOURS_PER_ACTIVE_PARTNER, CITIES, JOB_TYPES, N_WEEKS, RNG, START_DATE


def simulate_capacity(partners: pd.DataFrame) -> pd.DataFrame:
    weeks = pd.date_range(START_DATE, periods=N_WEEKS, freq="W-MON")
    active = partners[partners["active_flag"] == 1]

    rows = []
    for city in CITIES:
        for job_type in JOB_TYPES:
            n_active = len(active[(active["city"] == city) & (active["skill"] == job_type)])
            for week in weeks:
                utilisation_noise = float(RNG.uniform(0.85, 1.1))
                hours = n_active * AVG_WEEKLY_HOURS_PER_ACTIVE_PARTNER * utilisation_noise
                rows.append(
                    {
                        "city": city,
                        "job_type": job_type,
                        "week": week,
                        "available_partner_hours": round(hours, 1),
                    }
                )
    return pd.DataFrame(rows)
