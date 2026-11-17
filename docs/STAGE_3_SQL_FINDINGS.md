# Stage 3: DuckDB SQL Analysis Findings

**Project:** Singapore Banking Loan Portfolio & Sector Exposure Analytics
**Scope:** SQL re-analysis of the Stage 2 processed PRIMARY-dataset CSVs via DuckDB. No new data was introduced; this stage demonstrates the same business questions answered in Stage 2, now in SQL, and cross-checks the results against Stage 2.

## 1. Purpose

Stage 2 answered five business questions in Python/pandas. Stage 3 re-derives the equivalent (and a couple of new) metrics purely in SQL, against the same two processed CSVs, using an in-memory DuckDB connection. The goals are to (a) demonstrate SQL joins, CTEs, conditional aggregation, window functions (`LAG`, `ROW_NUMBER`), and contribution/concentration analysis, and (b) independently confirm that the Stage 2 findings hold up under a different computation path.

## 2. The Seven Queries

| File | What it computes |
|---|---|
| `01_portfolio_overview_monthly.sql` | Total/business/consumer loans per month, business & consumer share of total, MoM and 12-month absolute/percentage change (via `LAG`). |
| `02_business_sector_exposure_latest.sql` | The 8 business sectors at the latest month, balance, share of business total, and rank (`ROW_NUMBER`). |
| `03_business_sector_yoy_monthly.sql` | Per sector, per month: MoM and 12-month change via `LAG(1)`/`LAG(12)` partitioned by sector. |
| `04_business_sector_concentration_monthly.sql` | Per month: top-3 business sectors re-ranked that month, their combined share of the business total. |
| `05_consumer_lending_composition_monthly.sql` | Per month, per consumer category: balance and share of the consumer total. |
| `06_sector_growth_contributions_latest.sql` | Latest 12-month window: each sector's absolute/percentage change and its contribution to the business total's net 12-month change. |
| `07_monthly_reconciliation.sql` | Per month: three hierarchy reconciliation checks (total vs. business+consumer; business total vs. 8 sectors; consumer total vs. 5 categories), with a pass/fail flag. |

## 3. Source Tables and Join Keys

Both tables are loaded as typed DuckDB views directly from the Stage 2 CSVs (no permanent database file):

- `loan_balances_long` (`period_end` DATE, `series_id` VARCHAR, `balance_sgd_mn` DOUBLE): 1,674 rows.
- `loan_categories` (`series_id` VARCHAR, `series_name` VARCHAR, `parent_series_id` VARCHAR, `indent_level` INTEGER, `category_role` VARCHAR, `is_leaf` BOOLEAN, `row_order` INTEGER): 27 rows.

Every query joins the two tables on `series_id`, then filters by `category_role` (`total`, `business_total`, `consumer_total`, `business_sector`, `consumer_category`) to select exactly the intended set of rows. The 11 `business_subsector` rows are never included in any additive calculation, avoiding double-counting.

## 4. Expected vs. Actual Output Dimensions

All seven queries produced exactly the expected row counts, confirmed by `scripts/run_sql_analysis.py` (29/29 validation checks passed):

| Query | Expected rows | Actual rows |
|---|---|---|
| 01 | 62 | 62 |
| 02 | 8 | 8 |
| 03 | 496 | 496 |
| 04 | 62 | 62 |
| 05 | 310 | 310 |
| 06 | 8 | 8 |
| 07 | 62 | 62 |

All `period_end` values across all result sets fall within 2021-07-31–2026-08-31. Query 03 correctly leaves `mom_abs_change_sgd_mn` NULL for each sector's first month, and `yoy_abs_change_sgd_mn` NULL for each sector's first 12 months; these were verified programmatically, not zero-filled.

## 5. Findings

**1. Total loan growth and the business/consumer mix (Query 01).** Total loans to residents rose from **S$793,275.6M** (2021-07-31) to **S$966,432.7M** (2026-08-31). The business share of the total fell from 62.02% to 60.22%; the consumer share rose from 37.98% to 39.78%. The latest 12-month change was **+S$114,706.7M (+13.47%)**, and the latest single month alone (2026-07-31 → 2026-08-31) contributed **+S$27,374.2M (+2.92%)**, a notably large one-month move relative to the rest of the series. This is reported descriptively; the dataset provides no information on what drove it.

**2. Business sector concentration, latest month (Query 02).** At 2026-08-31, Building And Construction (32.82%), Financial And Insurance Activities (26.41%), and General Commerce (17.64%) are the three largest of the 8 business sectors, matching Stage 2 exactly.

**3. Latest 12-month sector moves (Query 03 / Query 06).** Financial And Insurance Activities had the largest absolute 12-month increase (**+S$23,150.1M, +17.73%**); Agriculture, Mining And Quarrying had the largest percentage increase (**+41.65%**, off a small base); Others was the only sector to decline (**−S$850.6M, −2.74%**). All three match the Stage 2 findings exactly.

**4. Top-3 concentration is essentially flat, within a narrow range (Query 04).** Top-3 business sector concentration was 76.79% at 2021-07-31 and 76.87% at 2026-08-31, a change of +0.07 percentage points. Across all 62 months it ranged from **76.56% (2026-01-31) to 79.93% (2023-08-31)**. This matches the Stage 2 result exactly, now re-selecting the top 3 sectors independently for every month via `ROW_NUMBER()` rather than a fixed set of 3. It is a balance-composition measure, not a credit-risk measure.

**5. Consumer composition remains housing-dominated (Query 05).** Housing And Bridging Loans represents the largest consumer category throughout, 69.26% (2021-07-31) down to 66.74% (2026-08-31) of consumer lending, consistent with Stage 2.

**6. Growth contribution analysis (Query 06, new in Stage 3).** Over the latest 12 months, the business lending total grew by **+S$67,446.4M**. Decomposing this by sector: Financial And Insurance Activities contributed the largest share of that net growth (**34.32%**), followed by General Commerce (23.38%) and Building And Construction (17.49%). Others, the only shrinking sector, contributed **−1.26%**: it partially offset growth elsewhere rather than adding to it. The eight sector contributions sum to **99.99%** of the net change (a Query 06 cross-check confirmed the sector-change sum of S$67,446.3M reconciles with the business total's own S$67,446.4M change, within the S$0.1M rounding tolerance). The small gap from 100% is published-rounding noise, not a calculation error. This confirms that while most sectors grew in the latest year, growth was concentrated in a few sectors and one sector actively worked against the trend.

**7. Hierarchy reconciliation holds for all 62 months (Query 07).** Every month's three additive checks (total = business + consumer; business total = sum of 8 sectors; consumer total = sum of 5 categories) passed within the documented S$0.2M published-rounding tolerance, confirmed independently in SQL, consistent with the Python-based validation in Stage 2 and the manual checks in Stage 1.

## 6. Cross-Checks with Stage 2

Every anchor value specified for this stage was independently reproduced by SQL and matched the Stage 2 (pandas-based) results to the data's own 0.1M reporting precision: total loans at both endpoints, the latest YoY growth rate, the latest top-3 concentration share, and all three Query 06 sector-change anchors (Financial And Insurance, Agriculture/Mining/Quarrying, Others). No discrepancies were found between the SQL and pandas computation paths.

## 7. Financial Interpretation Limitations

- All balances are end-of-period **stocks**; changes describe balance movements, not loan origination volumes, and are never summed across months.
- Shares always use the dataset's own reported parent total as the denominator (business/consumer total, or the overall total), never an ad hoc sum of siblings.
- The concentration measure (Query 04) and the contribution measure (Query 06) are descriptive balance-composition statistics. Neither measures default probability, credit risk, or portfolio quality, and neither should be read as one.
- No causal claims are made about interest rates, monetary policy, or macroeconomic conditions, including for the large single-month move noted in Finding 1, because this dataset contains no information to support such claims.
- Sector definitions are exactly as published in the official dataset (Singapore Standard Industrial Classification, as adopted by SingStat/MAS).
- This analysis uses the PRIMARY dataset only, consistent with the Stage 1 recommendation; the Supporting dataset was not used or modified.

## 8. New Insight From the Growth-Contribution Analysis

Stage 2 established which sectors grew the most in absolute and percentage terms. Query 06 adds a view Stage 2 did not compute: **what share of the business portfolio's net growth each sector is responsible for.** This reframes Finding 3: Financial And Insurance Activities is not just the largest absolute mover, it accounts for roughly a third of the entire business-lending total's net 12-month increase, while the only declining sector (Others) is shown to be a small drag rather than a meaningful offset. Because contributions are computed relative to a net change, they are not directly comparable to the share-of-total figures in Finding 2 (a reminder captured in the query's own in-file comments), but they usefully decompose "the business total grew by S$67.4B" into which sectors actually drove that figure.
