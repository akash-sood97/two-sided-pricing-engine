"""CLI entrypoint: rebuild the P1 synthetic/anchored dataset from scratch.

Usage:
    python data/generate.py

Writes data/processed/{transactions,partners,capacity,segment_truth}.csv and a
data/generation_report.md sanity-check summary.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import capacity, partners, proxy, transactions  # noqa: E402
from src.config import REFERENCE_WAGE  # noqa: E402

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORT_PATH = PROJECT_ROOT / "data" / "generation_report.md"


def main():
    print("Calibrating on UCI Online Retail II proxy...")
    calibration = proxy.calibrate()
    elasticity_dist = calibration["elasticity"]
    seasonality = calibration["seasonality"]
    print(
        f"  Elasticity distribution: mean={elasticity_dist['mean']:.3f} "
        f"std={elasticity_dist['std']:.3f} (n={elasticity_dist['n']} products)"
    )

    print("Simulating partners...")
    partners_df = partners.simulate_partners()

    print("Simulating capacity...")
    capacity_df = capacity.simulate_capacity(partners_df)

    print("Simulating transactions...")
    transactions_df = transactions.simulate_transactions(elasticity_dist, seasonality)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    transactions_df.to_csv(PROCESSED_DIR / "transactions.csv", index=False)
    partners_df.to_csv(PROCESSED_DIR / "partners.csv", index=False)
    capacity_df.to_csv(PROCESSED_DIR / "capacity.csv", index=False)
    transactions_df.attrs["segment_truth"].to_csv(PROCESSED_DIR / "segment_truth.csv", index=False)

    write_report(elasticity_dist, transactions_df, partners_df, capacity_df)
    print(f"Done. Data written to {PROCESSED_DIR}, report at {REPORT_PATH}")


def write_report(elasticity_dist, transactions_df, partners_df, capacity_df):
    lines = ["# P1 Data Generation Report", ""]

    lines.append("## Row counts")
    lines.append(f"- transactions: {len(transactions_df):,}")
    lines.append(f"- partners: {len(partners_df):,}")
    lines.append(f"- capacity: {len(capacity_df):,}")
    lines.append("")

    lines.append("## NaN check (required columns)")
    required = {
        "transactions": ["date", "city", "job_type", "list_price", "discount", "booked", "gmv", "units"],
        "partners": [
            "partner_id",
            "city",
            "skill",
            "tenure_months",
            "jobs_done",
            "earnings_per_job",
            "active_flag",
            "churn_flag",
        ],
        "capacity": ["city", "job_type", "week", "available_partner_hours"],
    }
    dfs = {"transactions": transactions_df, "partners": partners_df, "capacity": capacity_df}
    for name, cols in required.items():
        n_nan = int(dfs[name][cols].isna().sum().sum())
        lines.append(f"- {name}: {n_nan} NaNs across required columns")
    lines.append("")

    lines.append("## Elasticity calibration (proxy: UCI Online Retail II)")
    lines.append(
        f"- mean={elasticity_dist['mean']:.3f}, std={elasticity_dist['std']:.3f}, "
        f"n_products={elasticity_dist['n']}"
    )
    lines.append("- Segment elasticities drawn from this distribution are clipped to [-4.0, -0.2] (always negative).")
    lines.append("")

    lines.append("## Churn hazard kink check")
    below = partners_df[partners_df["earnings_per_job"] < REFERENCE_WAGE]["churn_probability"]
    above = partners_df[partners_df["earnings_per_job"] >= REFERENCE_WAGE]["churn_probability"]
    lines.append(f"- Reference wage: {REFERENCE_WAGE}")
    lines.append(
        f"- Mean churn probability below reference wage (n={len(below)}): {below.mean():.3f}"
        if len(below)
        else "- No partners below reference wage in this run."
    )
    lines.append(
        f"- Mean churn probability at/above reference wage (n={len(above)}): {above.mean():.3f}"
        if len(above)
        else "- No partners at/above reference wage in this run."
    )
    lines.append("")

    lines.append("## Conversion sanity")
    lines.append(f"- Overall booking rate: {transactions_df['booked'].mean():.3f}")
    lines.append("- Booking rate by segment:")
    by_segment = transactions_df.groupby(["city", "job_type"])["booked"].mean().round(3)
    for (city, job_type), rate in by_segment.items():
        lines.append(f"  - {city} / {job_type}: {rate}")

    REPORT_PATH.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
