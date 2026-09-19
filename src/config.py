"""Shared constants and the single seeded RNG for the P1 data generator.

Every src/ module imports RNG from here rather than creating its own, so a
full run of `python data/generate.py` is reproducible end to end as long as
the call order in generate.py stays fixed.
"""
import numpy as np

SEED = 42
RNG = np.random.default_rng(SEED)

CITIES = ["Delhi", "Hyderabad"]

# Synthetic home-services categories with a plausible base list price (INR)
# and average job duration (hours, used for the capacity table).
JOB_TYPES = {
    "cleaning": {"base_price": 499, "hours_per_job": 2.0},
    "appliance_repair": {"base_price": 349, "hours_per_job": 1.0},
    "salon_at_home": {"base_price": 999, "hours_per_job": 1.5},
    "plumbing": {"base_price": 299, "hours_per_job": 1.0},
    "pest_control": {"base_price": 799, "hours_per_job": 2.0},
}

START_DATE = "2024-01-01"
N_WEEKS = 52

# Partner economics
TAKE_RATE = 0.65  # partner's share of list price (net of discount) per job
REFERENCE_WAGE = 220.0  # INR/job earnings floor below which churn hazard kinks up
AVG_WEEKLY_HOURS_PER_ACTIVE_PARTNER = 30.0

# Partner population
N_PARTNERS_PER_CITY_JOBTYPE = 40
TENURE_MAX_MONTHS = 36
