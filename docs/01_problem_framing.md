# P1 · Problem Framing

## The business problem
A services marketplace sets a price for each job type / SKU / city. Price is usually tuned to **customer** demand (conversion, AOV). But every price also sets the **partner's** effective earnings per job, which drives partner retention and how much supply shows up — which drives **serviceability**. Optimising one side in isolation produces decisions that look right on a dashboard and lose money in the market (e.g. a price cut that lifts conversion but collapses partner earnings, churns supply, and tanks fulfilment).

**Question the engine answers:** *For each segment, what price band maximises contribution margin subject to (a) a partner-earnings floor and (b) a serviceability constraint — and what is the projected revenue, margin, partner-churn, and serviceability outcome of that choice versus the status quo?*

## Why it matters (the "so what")
A single-sided pricing recommendation is a trap in a two-sided market. The decision-grade output is a **price-band recommendation with both-sides consequences quantified**, so a category/revenue leader can act without discovering the partner-side damage a quarter later.

## Hypotheses to test (track confidence as you go)
- **H1** — Demand elasticity varies enough across segments that uniform pricing leaves margin on the table. *(prior: high)*
- **H2** — There is a partner-earnings threshold below which churn rises non-linearly; ignoring it makes aggressive price cuts value-destructive. *(prior: high — this is the crux)*
- **H3** — The margin-optimal price under a two-sided objective differs materially from the single-sided optimum for at least some segments. *(this difference is the entire point of the project)*
- **H4** — A serviceability constraint binds in high-demand segments, capping how far price can push demand. *(prior: medium-high)*
- **H5** — Demand elasticity is materially higher during promotional periods; a price band set on baseline elasticity will over-shoot demand and breach the partner-earnings floor during promotions. *(prior: high — empirically demonstrated on scanner panel data in Pricing & Demand Analytics, Term 3)*

## The decision it drives
Set / re-set price bands by segment, and flag segments where the current price violates the partner-earnings floor or the serviceability constraint. Output ranks segments by margin upside so a leader knows where to act first.

## Success metrics / KPIs
- **Model quality:** elasticity estimates with confidence intervals; holdout error on demand prediction; sign and magnitude sanity vs. domain priors.
- **Decision quality:** projected contribution-margin uplift from recommended bands vs. status quo; number of segments where the two-sided optimum ≠ single-sided optimum (the headline finding); partner-earnings-floor and serviceability violations avoided.
- **Narrative KPI:** a single "before → recommended" table a leader could take to a pricing review.

## Stakeholders (who this is "for")
Category / Revenue lead (owns the number), Central Pricing/Strategy (owns the model), City Ops (feels the serviceability/partner fallout), Finance (owns margin). The engine is the shared language across them.
