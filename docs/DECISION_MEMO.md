# Decision memo: two-sided pricing recommendation

*Synthetic data; assumptions labelled; results are model outputs, not production impact.*

## The answer
**Move prices as shown below, inside the range the data covers, and run price tests before going further.** Doing so lifts modelled annual contribution by **7.1%** (₹5.46M → ₹5.85M across 10 city × job segments). A demand-only approach delivers **3.2%**. The **₹0.21M** difference comes from one place: Delhi cleaning.

## Situation → complication → resolution
- **Situation.** Price sets conversion for customers and earnings for partners at once.
- **Complication.** A demand-only optimum says to discount Delhi cleaning to 0.80× today's price. That lifts demand about 60% but oversells partner capacity: peak-week fulfilment falls to **64%** and realised contribution to ₹667k, against ₹952k promised and ₹815k today.
- **Resolution.** Price Delhi cleaning at **0.915× (-8.5%)**: fulfilment stays at 92%, contribution rises to ₹880k.

## Recommended moves
| Segment | Move now | Then | Partner churn | Peak fulfilment | Contribution / yr |
|---|---|---|---|---|---|
| Hyderabad · salon at home | -20.0% | - | 3% → 3% | 100% | ₹969k → ₹1,135k |
| Hyderabad · pest control | -16.0% | - | 3% → 3% | 100% | ₹380k → ₹397k |
| Delhi · salon at home | -15.0% | - | 3% → 3% | 100% | ₹1,244k → ₹1,286k |
| Delhi · cleaning | -8.5% | - | 5% → 7% | 92% | ₹815k → ₹880k |
| Delhi · appliance repair | +5.0% | test to +25% | 28% → 24% | 100% | ₹326k → ₹347k |
| Delhi · pest control | +5.0% | test to +25% | 3% → 3% | 100% | ₹490k → ₹505k |
| Delhi · plumbing | +5.0% | test to +25% | 39% → 36% | 100% | ₹212k → ₹234k |
| Hyderabad · appliance repair | +5.0% | test to +25% | 28% → 24% | 100% | ₹248k → ₹266k |
| Hyderabad · cleaning | +5.0% | test to +25% | 4% → 4% | 100% | ₹631k → ₹642k |
| Hyderabad · plumbing | +5.0% | test to +25% | 39% → 36% | 100% | ₹145k → ₹155k |

*"Move now" is inside the observed price range (~0.71–1.05× base). "Then" is the full-band optimum (up to +25%), which extrapolates beyond the data and needs a price test first.*

## Interpretation
1. **Where two-sided pricing matters is a capacity question, not a wage question.** The partner-earnings floor does not change any segment's optimum here because most demand is inelastic enough that price rises are already optimal. Capacity is what separates the two approaches.
2. **4 segments sit below the ₹220 earnings reference wage today** (plumbing, appliance repair in both cities), with 28-39% modelled annual churn. For them, raising price is a win-win: better partner economics and higher margin. Appliance repair clears the floor at +5%; plumbing needs about +19%, which is outside the observed range, so it needs a test.
3. **The recommendation is stable.** Re-solving with each segment's price sensitivity redrawn from its own uncertainty leaves the direction of every move unchanged in at least 99% of draws.
4. **The Delhi cleaning price is assumption-sensitive.** It ranges from -17% to +3% as bookable capacity moves ±30%, because price is the rationing device when capacity is tight. The portfolio gain barely moves (6% to 8%).

## Trade-offs and what this does not show
- **Demand response is estimated; partner response is calibrated, not estimated.** The churn curve and the ₹220 threshold are built into the synthetic partner data. Real churn must be measured before acting on the partner side.
- **Cost inputs are assumptions:** non-partner variable cost 10% of base price, ₹3,000 to replace a partner, 85% peak utilisation in the busiest segment, 90% fulfilment target.
- **The full-band gain (+13.4%) is extrapolation.** Treat it as a hypothesis for a price test.
- **No cross-price or promotion effects** are in this dataset (the generator has none), so cannibalisation and promotional elasticity are handled in the promotion project on real retail data.

## Next step
Run a staged price test in the six "raise" segments (+5% now, then +10%, +15%) with partner-earnings and fulfilment guardrails, and measure partner churn directly.
