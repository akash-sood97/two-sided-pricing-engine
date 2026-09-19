"""Price-band explorer: move the assumptions, watch the two-sided recommendation change.

    streamlit run app/streamlit_app.py
"""
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import economics as X  # noqa: E402
from src import elasticity as E  # noqa: E402

st.set_page_config(page_title="Two-sided price-band explorer", layout="wide")


@st.cache_data
def load():
    tx = E.load_transactions(ROOT / "data/processed/transactions.csv")
    truth = pd.read_csv(ROOT / "data/processed/segment_truth.csv")
    partners = pd.read_csv(ROOT / "data/processed/partners.csv")
    return E.fit_all(tx, truth), tx, partners


fit, tx, partners = load()
st.title("Two-sided price-band explorer")
st.caption("Synthetic data. Demand is estimated; partner response and cost inputs are labelled assumptions.")

with st.sidebar:
    st.header("Assumptions")
    cap = st.slider("Bookable partner capacity vs baseline", 0.6, 1.4, 1.0, 0.05)
    target = st.slider("Peak-week fulfilment target", 0.70, 0.99, 0.90, 0.01)
    floor = st.slider("Partner earnings floor (₹/job)", 150, 300, 220, 5)
    repl = st.slider("Cost to replace a partner (₹)", 0, 10000, 3000, 250)
    hi = st.slider("Highest price multiple allowed", 1.05, 1.25, 1.05, 0.05,
                   help="The data only covers up to 1.05×. Anything above is extrapolation.")

segs = X.build_segments(fit, tx, partners)
X.calibrate_capacity(segs)
for s in segs:
    s.bookable_share *= cap
a_ = replace(X.A, service_target=target, earnings_floor=float(floor), replacement_cost=float(repl), band=(0.80, hi))

tab = X.scenario_table(segs, a_)
two = tab[tab.scenario == "Two-sided (in-sample)"] if hi <= 1.05 else tab[tab.scenario == "Two-sided (full band)"]
sq = tab[tab.scenario == "Status quo"]
ss = tab[tab.scenario == "Single-sided (in-sample)"]

c1, c2, c3 = st.columns(3)
c1.metric("Two-sided contribution / yr", f"₹{two.net.sum()/1e6:.2f}M", f"{(two.net.sum()/sq.net.sum()-1)*100:+.1f}% vs today")
c2.metric("Demand-only, as delivered", f"₹{ss.net.sum()/1e6:.2f}M", f"{(ss.net.sum()/sq.net.sum()-1)*100:+.1f}% vs today")
c3.metric("Value of pricing both sides", f"₹{(two.net.sum()-ss.net.sum())/1e3:,.0f}k / yr")

st.subheader("Recommended price move by segment")
show = two[["segment", "r", "conversion", "earn", "churn", "serv_peak", "net", "status"]].copy()
show["move"] = ((show.r - 1) * 100).round(1)
show = show.rename(columns={"conversion": "conversion", "earn": "partner ₹/job", "churn": "churn", "serv_peak": "peak fulfilment",
                            "net": "contribution ₹/yr"})
st.dataframe(show[["segment", "move", "conversion", "partner ₹/job", "churn", "peak fulfilment", "contribution ₹/yr", "status"]]
             .style.format({"move": "{:+.1f}%", "conversion": "{:.1%}", "partner ₹/job": "{:.0f}", "churn": "{:.0%}",
                            "peak fulfilment": "{:.0%}", "contribution ₹/yr": "{:,.0f}"}), width="stretch", hide_index=True)

st.subheader("Contribution vs price for one segment")
choice = st.selectbox("Segment", [s.key for s in segs], index=1)
seg = next(s for s in segs if s.key == choice)
o = X.optimise(seg, a_)
chart = pd.DataFrame({"price multiple": o["grid"], "demand-only view": o["ev"]["promised"] / 1e3,
                      "realised (two-sided)": o["ev"]["net"] / 1e3}).set_index("price multiple")
st.line_chart(chart, y_label="₹ thousand / year")
st.caption(f"Peak-week fulfilment at the recommended price: {o['ev']['serv_peak'][o['i_two']]:.0%} · status: {o['status']}")
