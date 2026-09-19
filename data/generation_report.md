# P1 Data Generation Report

## Row counts
- transactions: 108,957
- partners: 400
- capacity: 520

## NaN check (required columns)
- transactions: 0 NaNs across required columns
- partners: 0 NaNs across required columns
- capacity: 0 NaNs across required columns

## Elasticity calibration (proxy: UCI Online Retail II)
- mean=-2.116, std=2.161, n_products=277
- Segment elasticities drawn from this distribution are clipped to [-4.0, -0.2] (always negative).

## Churn hazard kink check
- Reference wage: 220.0
- Mean churn probability below reference wage (n=134): 0.358
- Mean churn probability at/above reference wage (n=266): 0.052

## Conversion sanity
- Overall booking rate: 0.378
- Booking rate by segment:
  - Delhi / appliance_repair: 0.356
  - Delhi / cleaning: 0.398
  - Delhi / pest_control: 0.369
  - Delhi / plumbing: 0.36
  - Delhi / salon_at_home: 0.386
  - Hyderabad / appliance_repair: 0.368
  - Hyderabad / cleaning: 0.368
  - Hyderabad / pest_control: 0.384
  - Hyderabad / plumbing: 0.365
  - Hyderabad / salon_at_home: 0.403