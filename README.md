# Two-Sided Pricing & Elasticity Decision Engine

**Status: complete.** All data is synthetic (calibrated on a public proxy); results are model outputs, not production impact.

## The answer

> **Reprice 10 marketplace segments as shown below: +7.1% modelled contribution, ₹5.46M → ₹5.85M a year, using only price moves the data can support. A demand-only approach delivers +3.2%. The difference, ₹0.21M a year, comes from one segment: Delhi cleaning.**

| | | |
|---|---|---|
| **+7.1%** | **₹0.21M / yr** | **64% → 92%** |
| modelled annual contribution vs today, inside the observed price range | value of pricing both sides vs pricing demand alone | Delhi cleaning peak-week fulfilment: demand-only price vs two-sided price |

**The question.** For each city × job segment, which price maximises contribution *subject to* a partner-earnings floor and a peak-week fulfilment target, and what happens to conversion, partner churn and fulfilment compared with today?

**Why two-sided.** Price sets two things at once: what customers see (conversion) and what partners earn (churn, and therefore supply, and therefore fulfilment). A demand-only optimiser cuts Delhi cleaning to 0.80× today's price, lifts demand about 60%, then cannot serve it. It promises ₹0.95M and delivers ₹0.67M.

![Scenario comparison](figures/05_scenario_comparison.png)

**So what.** Pricing to the capacity edge beats chasing demand. The demand-only line looks best on a demand dashboard (₹6.08M promised) and delivers ₹5.64M, because the promised demand exceeds partner capacity.

---

## Where the difference comes from: Delhi cleaning

![Delhi cleaning frontier](figures/03_delhi_cleaning_frontier.png)

**So what.** Below about 0.91× today's price, extra demand outruns partner capacity: fulfilment drops under the 90% target, and realised contribution falls even as the demand-only view keeps rising. The two-sided optimum (0.915×, −8.5%) sits at the edge of capacity: still a real discount, but one the partner base can serve.

## What to do

![Recommended moves](figures/04_recommended_moves.png)

| | Move now (inside observed range) | Then |
|---|---|---|
| **Cut**: Delhi cleaning, Delhi and Hyderabad salon at home, Hyderabad pest control | −8.5% to −20% | none: these optima are already inside the data |
| **Raise**: plumbing, appliance repair, Delhi pest control, Hyderabad cleaning | +5% | **test** larger rises up to +25% (extrapolation) |

**So what.** Four segments (plumbing and appliance repair, both cities) pay partners below the ₹220-a-job reference wage today, with 28–39% modelled annual churn. For them a price rise is a win-win, not a trade-off. Appliance repair clears the floor at +5%; plumbing needs about +19%, which the data cannot vouch for, so it needs a staged test.

![Partner response](figures/02_partner_response.png)

The full recommendation table, with per-segment churn, fulfilment and contribution, is in the **[decision memo](docs/DECISION_MEMO.md)**.

## How much to trust it

![Elasticity recovery](figures/01_elasticity_recovery.png)

- **Demand model.** A per-segment logit on ln(relative price) recovers 9 of 10 true sensitivities inside its 95% interval (mean absolute error 0.21). It beats gradient boosting on a 13-week holdout (log-loss 0.6574 vs 0.6599), so interpretability is not costing accuracy. A placebo test finds no promotion-specific effect, correctly, since the generator has none.
- **Stable direction.** With each segment's price sensitivity redrawn from its own uncertainty, every recommended move keeps its direction in at least 99% of 400 draws.

![Sensitivity](figures/06_sensitivity.png)

- **Assumption-sensitive.** The Delhi cleaning price ranges from −17% to +3% as bookable partner capacity moves ±30%, because price is the rationing device when capacity is tight. The portfolio gain barely moves (+6% to +8%). Capacity is the least-observed input and the first thing to validate.

## What this does not show

- **Partner response is calibrated, not estimated.** The churn curve and the ₹220 threshold are built into the synthetic partner data. Real churn would have to be measured before acting on the partner side.
- **The demand sensitivities are a plausible range, not a measured elasticity.** The spread of true β values was calibrated from a price-volume association in UCI Online Retail II, where unit price reflects buyer type and order size (shown in the promotion project's first figure). Read them as realistic magnitudes for a synthetic world.
- **Cost inputs are assumptions:** non-partner variable cost 10% of base price, ₹3,000 to replace a partner, 85% peak utilisation in the busiest segment, 90% fulfilment target, 65% partner take rate.
- **Extrapolation.** Observed relative prices span about 0.71–1.05× base. The full-band gain (+13.4%) needs price tests, not trust.
- **No cross-price or promotion effects.** The data has none, so cannibalisation and promotional elasticity are handled in the promotion project, on real retail data.
- **No causal identification.** These are conversion-response estimates from randomised-price synthetic leads, not a claim about any real marketplace.

## Try it

```bash
pip install -r requirements.txt
python data/generate.py              # rebuild the synthetic data (downloads the ~44 MB UCI proxy once)
python analysis/run_analysis.py      # fit, optimise, write outputs/, figures/, docs/DECISION_MEMO.md
streamlit run app/streamlit_app.py   # price-band explorer: move the assumptions, watch the answer change
```

Every number in the figures and the memo is computed by `analysis/run_analysis.py`, not typed.

```
src/          elasticity.py (demand model) · economics.py (two-sided engine, optimiser) · viz.py · data generators
analysis/     run_analysis.py
app/          streamlit_app.py
data/         generate.py · processed/ (committed) · generation_report.md
outputs/      CSVs behind every chart · summary.json
figures/      the six charts above
docs/         DECISION_MEMO.md · method spec · problem framing
notebooks/    00_data_generation_and_proxy.ipynb (how the synthetic data is built)
```

**Author:** Akash Sood · ISB AMPBA · [portfolio](https://akash-sood97.github.io) · [GitHub](https://github.com/akash-sood97)

*Data: demand calibrated on [UCI Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii) (CC BY 4.0); everything else simulated.*
