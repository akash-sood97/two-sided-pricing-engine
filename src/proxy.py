"""Anchor P1's demand side on a named public proxy: UCI Online Retail II.

We don't reuse the proxy's rows directly — it's retail, our schema is
services bookings — we use it to *calibrate* a realistic price-elasticity
distribution and a seasonality curve, then simulate the marketplace
transactions table on top of those calibration inputs (transactions.py).
This is what 02_data_and_method.md means by "anchor the customer-demand
side on a public proxy."
"""
import io
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import statsmodels.api as sm

from src.config import RNG

UCI_URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
RAW_XLSX = RAW_DIR / "online_retail_II.xlsx"


def download_proxy(force: bool = False) -> Path:
    """Download and cache the UCI Online Retail II workbook. Skips the
    download if already cached at data/raw/online_retail_II.xlsx."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if RAW_XLSX.exists() and not force:
        return RAW_XLSX

    resp = requests.get(UCI_URL, timeout=120)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        xlsx_names = [n for n in zf.namelist() if n.lower().endswith(".xlsx")]
        if not xlsx_names:
            raise RuntimeError("UCI Online Retail II zip did not contain an .xlsx file")
        with zf.open(xlsx_names[0]) as src, open(RAW_XLSX, "wb") as dst:
            dst.write(src.read())
    return RAW_XLSX


def load_proxy(path: Path) -> pd.DataFrame:
    """Load and clean the two-sheet UCI workbook into one transaction table."""
    sheets = pd.read_excel(path, sheet_name=None)
    df = pd.concat(sheets.values(), ignore_index=True)
    df.columns = [c.strip().replace(" ", "_") for c in df.columns]
    df = df[~df["Invoice"].astype(str).str.startswith("C")]
    df = df[(df["Quantity"] > 0) & (df["Price"] > 0)]
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    return df


def fit_elasticity_distribution(df: pd.DataFrame, min_weeks: int = 8, top_n: int = 300) -> dict:
    """Fit log(qty) ~ log(price) OLS per product on weekly aggregates; return
    the (mean, std) of the negative price elasticities across products with
    enough weekly price variation to fit."""
    d = df.copy()
    d["week"] = d["InvoiceDate"].dt.to_period("W").dt.start_time
    top_products = d["StockCode"].value_counts().head(top_n).index
    d = d[d["StockCode"].isin(top_products)]

    weekly = (
        d.groupby(["StockCode", "week"])
        .agg(qty=("Quantity", "sum"), price=("Price", "mean"))
        .reset_index()
    )
    weekly = weekly[(weekly["qty"] > 0) & (weekly["price"] > 0)]

    elasticities = []
    for _, g in weekly.groupby("StockCode"):
        if g["week"].nunique() < min_weeks or g["price"].nunique() < 3:
            continue
        x = sm.add_constant(np.log(g["price"].values))
        y = np.log(g["qty"].values)
        try:
            beta = sm.OLS(y, x).fit().params[1]
        except Exception:
            continue
        if np.isfinite(beta) and beta < 0:
            elasticities.append(beta)

    elasticities = np.array(elasticities)
    if len(elasticities) < 5:
        raise RuntimeError("Too few UCI products with a fittable negative elasticity")
    return {"mean": float(elasticities.mean()), "std": float(elasticities.std()), "n": int(len(elasticities))}


def fit_seasonality(df: pd.DataFrame) -> pd.Series:
    """Day-of-week volume multiplier (mean-normalised to 1.0) from the proxy."""
    d = df.copy()
    d["dow"] = d["InvoiceDate"].dt.dayofweek
    weekly_vol = d.groupby("dow")["Quantity"].sum()
    return (weekly_vol / weekly_vol.mean()).reindex(range(7)).fillna(1.0)


def sample_segment_elasticities(dist: dict, n: int) -> np.ndarray:
    """Draw n segment-level elasticities from the calibrated distribution,
    clipped to a plausible negative range."""
    draws = RNG.normal(dist["mean"], dist["std"], size=n)
    return np.clip(draws, -4.0, -0.2)


def calibrate(force_download: bool = False) -> dict:
    """End-to-end: download (if needed) -> load -> fit. Returns the
    elasticity distribution and the seasonality multiplier series."""
    path = download_proxy(force=force_download)
    df = load_proxy(path)
    return {
        "elasticity": fit_elasticity_distribution(df),
        "seasonality": fit_seasonality(df),
    }
