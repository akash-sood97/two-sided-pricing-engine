"""Week 2, step 1: price response by segment.

Bookings are binary conversions of leads, so the price response is a logit,
not a log-log volume regression:

    logit P(book) = a + beta * ln(relative_price),   relative_price = net price / base price

beta is a *logit-price* coefficient. The point elasticity of the booking
probability is  beta * (1 - p)  and is reported separately.
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import log_loss

from src.config import JOB_TYPES

SEGMENTS = None  # filled lazily; (city, job_type) pairs present in the data


def load_transactions(path="data/processed/transactions.csv") -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    df["base_price"] = df["job_type"].map(lambda j: JOB_TYPES[j]["base_price"])
    df["net_price"] = df["list_price"] * (1 - df["discount"])
    df["rel_price"] = df["net_price"] / df["base_price"]
    df["ln_rel"] = np.log(df["rel_price"])
    df["deal"] = (df["discount"] > 0).astype(int)
    return df


def fit_segment(seg: pd.DataFrame):
    X = sm.add_constant(seg[["ln_rel"]])
    return sm.Logit(seg["booked"], X).fit(disp=0)


def fit_all(df: pd.DataFrame, truth: pd.DataFrame) -> pd.DataFrame:
    """One logit per city x job_type; compare with the generator's true beta."""
    rows = []
    for (city, job), seg in df.groupby(["city", "job_type"]):
        m = fit_segment(seg)
        lo, hi = m.conf_int().loc["ln_rel"]
        a, b = m.params["const"], m.params["ln_rel"]
        p0 = 1 / (1 + np.exp(-a))  # conversion at the base price
        rows.append(
            dict(city=city, job_type=job, n_leads=len(seg), a=a, beta=b, beta_lo=lo, beta_hi=hi,
                 se=m.bse["ln_rel"], p_base=p0, point_elasticity=b * (1 - p0))
        )
    out = pd.DataFrame(rows).merge(truth, on=["city", "job_type"])
    out["covered"] = (out["true_beta"] >= out["beta_lo"]) & (out["true_beta"] <= out["beta_hi"])
    return out


def deal_placebo(df: pd.DataFrame) -> pd.DataFrame:
    """Does a deal flag shift the price response beyond the price itself?
    The generator applies a single price response, so this should be ~0.
    A significant result here would mean a specification error, not a finding."""
    rows = []
    for (city, job), seg in df.groupby(["city", "job_type"]):
        X = seg[["ln_rel", "deal"]].copy()
        X["ln_rel_x_deal"] = X["ln_rel"] * X["deal"]
        m = sm.Logit(seg["booked"], sm.add_constant(X)).fit(disp=0)
        rows.append(dict(city=city, job_type=job, interaction=m.params["ln_rel_x_deal"],
                         p_value=m.pvalues["ln_rel_x_deal"]))
    return pd.DataFrame(rows)


def holdout_comparison(df: pd.DataFrame) -> pd.DataFrame:
    """Time-based holdout (last 13 weeks): interpretable logit vs gradient boosting."""
    cut = df["date"].max() - pd.Timedelta(weeks=13)
    tr, te = df[df["date"] <= cut], df[df["date"] > cut]
    feats = ["ln_rel", "discount", "base_price"]
    rows = []
    ll_logit, ll_gbm, ll_base, n = 0.0, 0.0, 0.0, 0
    for (city, job), seg_tr in tr.groupby(["city", "job_type"]):
        seg_te = te[(te["city"] == city) & (te["job_type"] == job)]
        m = fit_segment(seg_tr)
        p_l = m.predict(sm.add_constant(seg_te[["ln_rel"]], has_constant="add"))
        ll_logit += log_loss(seg_te["booked"], p_l, labels=[0, 1]) * len(seg_te)
        g = HistGradientBoostingClassifier(max_depth=3, max_iter=150, learning_rate=0.05, random_state=0)
        g.fit(seg_tr[feats], seg_tr["booked"])
        ll_gbm += log_loss(seg_te["booked"], g.predict_proba(seg_te[feats])[:, 1], labels=[0, 1]) * len(seg_te)
        ll_base += log_loss(seg_te["booked"], np.full(len(seg_te), seg_tr["booked"].mean()), labels=[0, 1]) * len(seg_te)
        n += len(seg_te)
    return pd.DataFrame(
        [dict(model="Segment-mean baseline (no price)", log_loss=ll_base / n),
         dict(model="Logit on ln(price), per segment", log_loss=ll_logit / n),
         dict(model="Gradient boosting (price, discount, base)", log_loss=ll_gbm / n)]
    )
