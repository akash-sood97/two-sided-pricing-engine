> **Scope note (read first).** This is the original method spec. What the delivered project builds: the per-segment logit demand model, a partner-response curve, the serviceability constraint, the constrained optimiser, scenario simulation and a sensitivity/robustness analysis (`docs/DECISION_MEMO.md`). **Cross-price elasticity and promotional elasticity are not tested here**, because the synthetic generator contains neither effect; they are delivered in the promotion & cannibalisation project on real retail data. The bundle-menu and no-price-history (WTP) sections below were **not built**.

# P1 · Data & Method

## Data strategy (confidentiality-safe)
This project uses **no real marketplace data**. It builds a **seeded synthetic dataset** whose structure mirrors a home-services marketplace, with demand-side elasticity and seasonality calibrated on a **public proxy** (UCI Online Retail II) and the partner side simulated on top. Parameters that are assumptions (reference wage, churn-hazard shape) are labelled as such.

**Synthetic schema (generate with a seeded Python script — include the generator in the repo so the work is reproducible):**
- `transactions`: date, city, job_type/SKU, list_price, discount, booked (0/1), gmv, units.
- `partners`: partner_id, city, skill, tenure, jobs_done, earnings_per_job, active_flag, churn_flag.
- `capacity`: city × job_type × week → available partner-hours (drives serviceability).

**Named public proxies (pick one for the demand side, cite it):** UCI *Online Retail II* (price/quantity for elasticity), *Instacart* orders (basket/segment behaviour), *Olist* Brazilian e-commerce (multi-category, price + delivery), NYC-TLC trips (demand intensity by zone/time). Use the proxy to make elasticity estimation defensible, then layer the simulated partner economics.

## Features
- **Demand side:** price, relative price vs. segment mean, discount depth, seasonality/day-of-week, city, segment; log-price and log-quantity for elasticity; **price of substitute/competing job types in the same city** (for cross-elasticity); a **promotion/deal flag** and its interaction with log-price.
- **Partner side:** effective earnings per job at a given price, earnings vs. a reference wage, utilisation, tenure cohort; a churn-hazard input as a function of earnings.
- **Serviceability:** demand at a price ÷ available capacity → fulfilment probability.

## Method (build in this order)
1. **Elasticity estimation — own-price, cross-price, and promotional.** Log-log demand regression per segment (statsmodels) for interpretable elasticities *and* an ML price-response model (gradient boosting) for non-linear/threshold effects. Compare — interpretability vs. accuracy is itself a talking point.

   **Cross-price elasticity (from Pricing & Demand Analytics, Term 3).** Job types compete for the same customer wallet and the same partner hours — discounting deep cleaning pulls demand from regular cleaning, and may pull partners away from plumbing. Extend the log-log spec:
   ```
   log Q_x = β₀ + β₁·log P_x + β₂·log P_y + ...
   β₁ = own-price elasticity      (always negative)
   β₂ = cross-price elasticity    (positive for substitutes)
   ```
   Produce a **cross-elasticity matrix** across job types per city (the Coke/Pepsi template: elasticities are *asymmetric* — check which job type's customers are more price-sensitive to the other's price, not just the sign). Add a decision test to Validation below: show at least one pair where the naive own-elasticity recommendation reverses once cannibalisation is priced in.

   **Promotional elasticity (H5).** Elasticity is not constant — it shifts under promotion (PDA's scanner-panel result: −2.91 no-deal vs. −4.33 with a deal). Add a `log P × deal_flag` interaction term to the log-log spec and report the deal-period elasticity separately. This matters operationally: an elasticity estimated only from normal weeks *understates* promotional response, so a promotion sized on baseline elasticity overshoots demand and breaches the partner-earnings floor harder than the model predicted — directly testing H5 in `01_problem_framing.md`.

2. **Partner-response model.** Map price → partner earnings → churn hazard (calibrated logistic/hazard curve). This is the two-sided step most projects skip.
3. **Serviceability model.** Demand(price) vs. capacity → fulfilment %; encode as a constraint. **Sparsity check:** the transaction table is dense at city × job_type, but the moment you model at segment × week × price band, cells thin out fast (ASA's comparable UrbanMart grid was 96% zeros). If the modelling grain produces >50% zero cells, switch from OLS on logged quantity to a **two-stage hurdle structure** — logistic for any-demand × Poisson for volume given demand — and check for over-dispersion (variance > mean → negative binomial instead of Poisson). Also build the complete city × job_type × week grid *before* aggregating transactions, or zero-demand cells silently disappear and the model over-forecasts.
4. **Constrained optimisation.** Maximise expected contribution margin over price bands **subject to** partner-earnings floor and serviceability ≥ target (SciPy `minimize` / PuLP for the linearised version). Grid-search fallback for transparency.
5. **Bundle / price-discrimination layer.** Add a bundle menu to the pricing model — single visit, multi-visit pack, subscription, annual plan — a natural second-degree price-discrimination structure (a menu of choices with customer self-selection; you don't need to know who the customer is, only offer options that sort them). Run the same per-unit revenue optimisation across the menu: `price × cumulative % willing to pay`, following the Springfield Nor'easters pattern where the revenue-optimal per-ticket price fell monotonically with commitment size ($10 single → $8 5-pack → $6–8 half-season → $6 full-season). A bundle changes the partner side too — guaranteed repeat visits mean predictable partner earnings, which raises the earnings floor without raising unit price, a two-sided move a single-sided model can't represent. **Flat-optimum caveat:** when two price points score within a few cents of each other, choose on strategy (anchoring against the single-visit price), not on the decimal — say so explicitly in the memo.
6. **Scenario simulation.** For each segment, simulate status-quo vs. recommended vs. single-sided-naïve price; report revenue, margin, partner churn, serviceability for each.

## Appendix method — pricing with no price history 
For a brand-new job type with zero historical price variation, elasticity regression has nothing to fit. Use **WTP-based expected-revenue optimisation** (the Springfield Nor'easters method): survey willingness-to-pay → build the cumulative WTP curve → maximise `price × cumulative %`:
```
cumulative WTP at $10 = everyone willing at $10 and above
expected revenue = price × cumulative %
$8 × 93% = $7.44 | $10 × 80% = $8.00 ← max | $12 × 49% = $5.88 | $14 × 22% = $3.08
```
Survey instrument: four blocks — **D**emographics, **Q**uality **P**erception, **P**urchase **L**ikelihood, **WTP** — one design rule: every question must contribute to the pricing decision, or drop it. Demographics either reveal segment differences worth pricing on, or confirm none exist and become control variables. This is the answer to "how would you price a brand-new service category with no data?" — elasticity can't answer that; this can. Name it in `04_deliverables.md` as a section of the decision memo.

## Validation
- Back-test demand model on a holdout; report error and elasticity CIs.
- **Sanity/decision test:** show at least one segment where the two-sided optimum diverges from the single-sided optimum and explain the mechanism (this is the proof the two-sided framing matters). Add the cross-elasticity reversal case from the cross-price elasticity layer alongside it.
- Sensitivity: vary the earnings-floor and serviceability targets; show how the recommendation moves (robustness a reviewer will probe).
- **Diagnostics section (from Advanced Statistical Analysis, Term 3).** Residuals vs. fitted (heteroscedasticity is near-certain in price data), Q–Q, **Cook's distance**, VIF (log-price + log-quantity + segment dummies will produce real collinearity — check it). Use **AIC**, not R², as the stopping rule when comparing specifications. Pick the baseline category (largest segment) for city/job_type dummies and state why — the choice changes every coefficient's wording but no fitted value, which is worth saying because it pre-empts a common reviewer challenge. Run **Breusch–Pagan** (`lmtest::bptest()`, H₀ = constant variance) rather than eyeballing the residual plot — price data is almost always heteroscedastic, and the honest framing is that this makes standard errors unreliable, not coefficients biased.
- **Outlier policy.** Investigate extreme bookings, don't delete them automatically (ASA's explicit instruction) — deleting makes the elasticity estimate look cleaner than the market is. Report sensitivity to their inclusion and flag which are valid-but-rare business situations.

## Tools
Python (pandas, numpy, statsmodels, scikit-learn, scipy/pulp, matplotlib), SQL for the query layer, Tableau **or** a small Streamlit app for the interactive price-band explorer.

---
