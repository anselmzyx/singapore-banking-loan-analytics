# Stage 2: Cleaning, Validation, and EDA Findings

**Project:** Singapore Banking Loan Portfolio & Sector Exposure Analytics
**Scope:** PRIMARY dataset only (`d_af0415517a3a3a94b3b74039934ef976`, Commercial Banks: Loans And Advances To Residents By Industry). The Supporting dataset was not used or modified in this stage.

## 1. Summary of Transformations

`scripts/clean_data.py` reads the raw CSV and performs a single reshape, with no value edits:

1. Parses each `DataSeries` row's **leading-whitespace indentation** (0/4/8/12 spaces) into an explicit parent/child tree via a stack-based pass (not by hardcoded row positions), producing a `parent_series_id` link for every row.
2. Derives a **stable `series_id`** for each of the 27 categories as a slug of its own label text (not dependent on row order).
3. Classifies each category into a `category_role`: `total`, `business_total`, `consumer_total`, `business_sector` (the 8 top-level business categories, whether or not they have children), `business_subsector` (the 11 finer rows beneath 5 of those sectors), or `consumer_category` (the 5 consumer categories).
4. Converts each `YYYYMon` month column (e.g. `2026Aug`) into an ISO month-end date (e.g. `2026-08-31`).
5. Melts the 62 month columns into long format: one row per (category, month).
6. Writes `data/processed/loan_categories.csv` (the dimension table) and `data/processed/loan_balances_long.csv` (the fact table), then runs 12 validation checks before reporting success.

No values were rounded, imputed, or otherwise altered. Balances in the processed output are the same floats parsed directly from the raw CSV cells (confirmed by validation check 12, below).

## 2. Processed Data Dimensions and Column Definitions

### `data/processed/loan_categories.csv`: 27 rows (one per category)

| Column | Type | Description |
|---|---|---|
| `series_id` | string | Stable id derived from the category's own label (slug) |
| `series_name` | string | Original DataSeries label, whitespace-stripped, otherwise unchanged |
| `parent_series_id` | string / null | `series_id` of the immediate parent in the hierarchy; null for the root total |
| `indent_level` | int | Original leading-whitespace indent (0, 4, 8, or 12) |
| `category_role` | string | One of: `total`, `business_total`, `consumer_total`, `business_sector`, `business_subsector`, `consumer_category` |
| `is_leaf` | bool | True if no other row has this category as its parent |
| `row_order` | int | 0-based position in the original raw CSV (preserves source ordering for display) |

### `data/processed/loan_balances_long.csv`: 1,674 rows (27 series × 62 months)

| Column | Type | Description |
|---|---|---|
| `period_end` | date (ISO) | Month-end date the balance is reported as of |
| `series_id` | string | Foreign key into `loan_categories.csv` |
| `balance_sgd_mn` | float | End-of-period stock balance, S$ million, exactly as published |

## 3. Validation Results

All 12 checks are implemented directly in `scripts/clean_data.py` and run automatically on every execution. **12 / 12 passed** on the current raw file.

| # | Check | Result |
|---|---|---|
| 1 | Exactly 1,674 long-format observations | PASS: 1,674 |
| 2 | Exactly 27 unique series | PASS: 27 |
| 3 | Exactly 62 consecutive months | PASS: 2021-07-31 to 2026-08-31 |
| 4 | No duplicate (period_end, series_id) keys | PASS: 0 duplicates |
| 5 | No missing / non-numeric balances | PASS: 0 missing, numeric dtype confirmed |
| 6 | No unexpected negative balances | PASS: 0 negative values |
| 7 | All `series_id` in the fact table reference valid dimension entries | PASS: 0 unmatched |
| 8 | All `parent_series_id` values reference valid dimension entries | PASS: 0 unmatched |
| 9 | Business sector totals reconcile to the business lending total | PASS: max abs diff S$0.2M (2025-12-31), tolerance S$0.2M |
| 10 | Consumer categories reconcile to the consumer lending total | PASS: max abs diff S$0.2M (2021-07-31), tolerance S$0.2M |
| 11 | Business + consumer totals reconcile to the overall total | PASS: max abs diff S$0.1M (2022-03-31), tolerance S$0.2M |
| 12 | Cleaned values match their original source cells exactly | PASS: max abs diff 0.0 |

Checks 9–11 use a **S$0.2M rounding tolerance**, consistent with the maximum parent-child residuals independently measured across all 62 months in `docs/STAGE_1_DATA_INSPECTION.md` Section 4 (the source publishes each figure already rounded to 1 decimal place, so sums of several rounded components can differ from an independently rounded total by a small amount, which is expected and not a data defect).

## 4. Five Evidence-Backed Findings

All balances are **end-of-period stocks** (S$ million); none of the figures below represent newly originated loans, and none imply anything about credit quality, default risk, or profitability.

**1. Total outstanding loans to residents grew over the period, with the business/consumer mix shifting toward consumer lending.** Total loans rose from **S$793,275.6M** (2021-07-31) to **S$966,432.7M** (2026-08-31), a stock increase of **S$173,157.1M**. Over the same window, the business-lending share of the total fell from **62.02% to 60.22%** (−1.80 percentage points), while the consumer-lending share rose from **37.98% to 39.78%** (+1.80 percentage points). The most recent 12 months alone (2025-08-31 → 2026-08-31) accounted for a **S$114,706.7M (+13.47%)** increase in the total, a larger single-year increase than in several earlier years of the series, based on the trend visible in `figures/01_total_business_consumer_trends.png`.

**2. Business lending is concentrated in a small number of sectors.** At 2026-08-31, of the 8 mutually exclusive top-level business sectors, **Building And Construction** was the largest at **S$191,010.6M (32.82% of business lending)**, followed by **Financial And Insurance Activities** at **S$153,736.2M (26.41%)** and **General Commerce** at **S$102,648.4M (17.64%)**. These three sectors alone account for **76.87%** of business lending; the remaining five sectors together hold the other ~23%.

**3. Over the latest 12-month period, Financial And Insurance Activities grew the most in absolute terms, while Agriculture, Mining And Quarrying grew the most in percentage terms, and Others was the only sector to shrink.** Comparing 2025-08-31 to 2026-08-31: Financial And Insurance Activities increased by **+S$23,150.1M (+17.73%)**; Agriculture, Mining And Quarrying increased by **+41.65% (+S$1,378.2M)** off the smallest base (S$3,309.3M → S$4,687.5M), the largest percentage move of any sector; Others was the only sector with a balance decline, **−S$850.6M (−2.74%)**.

**4. Business-sector lending concentration (top-3 sector share) was essentially flat over the full window, though it moved within a narrow range intra-period.** The combined share of the three largest business sectors was **76.79%** at 2021-07-31 and **76.87%** at 2026-08-31, a change of only **+0.07 percentage points** end-to-end. Across all 62 months the measure ranged from **76.56% to 79.93%**, meaning concentration fluctuated modestly within the period but did not show a sustained directional trend toward higher or lower concentration. This is a descriptive balance-composition measure only, not a risk or default-probability metric.

**5. Consumer lending remains dominated by housing and bridging loans, though their share has declined slightly, while credit cards grew from a small base.** Housing And Bridging Loans fell from **69.26% to 66.74%** of consumer lending (−2.52 percentage points) between 2021-07-31 and 2026-08-31. The "Others" consumer category rose from **24.21% to 25.71%** (+1.50 points), and Credit Cards rose from **3.37% to 4.67%** (+1.30 points, a roughly 38% relative increase in its share). Car Loans stayed nearly flat (2.78% → 2.69%), and Share Financing, already the smallest category, shrank from **0.38% to 0.19%** of consumer lending.

## 5. Analytical Limitations

- **Stocks, not flows.** All balances are end-of-period snapshots. Balance increases are not newly originated loan volumes, and balances must never be summed across months.
- **Hierarchy, not 27 independent sectors.** The 27 series form a 4-level tree (totals → business/consumer totals → 8 business sectors / 5 consumer categories → 11 business subsectors). Any aggregate analysis must use the correct level and must not add a parent total to its own children.
- **Rounding noise, not error.** Published figures are rounded to 1 decimal place; parent-child sums can differ from the reported total by up to ~S$0.2M. This is expected and was characterized in Stage 1 and re-validated here; it is not evidence of a data quality problem.
- **Reporting basis starts Jul 2021.** The current MAS/SingStat reporting methodology (per MAS Notices 610/1003) only covers Jul 2021 onward; this analysis does not and should not be extended backward with the discontinued pre-2021 series.
- **No causal claims.** Observed trends (e.g. the recent acceleration in total loan growth, or sector-level changes) are descriptive. This dataset contains no information on interest rates, monetary policy, or macroeconomic drivers, so no causal attribution is made or should be inferred.
- **No credit-risk or performance claims.** The dataset reports outstanding balances only. It contains no information on defaults, non-performing loans, profitability, or credit quality, and the concentration measure in Finding 4 is a balance-composition statistic, not a risk measure.
- **Sector definitions are the official dataset's own.** Industry categories follow the Singapore Standard Industrial Classification as adopted by SingStat/MAS in this dataset; no alternative classification was applied.
- **Single-source analysis.** Per project scope, only the Primary dataset was used for these findings; the Supporting (Assets & Liabilities) dataset was not merged in, consistent with the Stage 1 recommendation.

## 6. Tables and Calculations Suitable for Stage 3 (DuckDB SQL)

**Tables:**
- `loan_categories`: category dimension (27 rows), hierarchy, roles, leaf flags.
- `loan_balances_long`: balance fact table (1,674 rows), one row per category × month.

**Calculations expected to carry forward:**
- Business vs. consumer share of total loans, by month (Finding 1).
- Business sector ranking and share-of-business-total, by month (Finding 2).
- Month-over-month and 12-month (YoY) absolute/percentage change, by series (Finding 3).
- Top-3 business sector concentration share, by month (Finding 4).
- Consumer category share-of-consumer-total, by month (Finding 5).

All of the above should continue to use the dataset's own reported parent totals as denominators, respect the 4-level hierarchy (never summing a subtotal with its children), and apply the same ~S$0.2M published-rounding tolerance documented above when reconciling totals.
