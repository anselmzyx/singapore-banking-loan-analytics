-- Query 07: Monthly hierarchy reconciliation
--
-- One row per month (62 rows). Independently re-checks the three additive
-- relationships in the category hierarchy for every month:
--   1. total_loans            vs  business_total + consumer_total
--   2. business_total         vs  SUM of exactly the 8 business_sector rows
--   3. consumer_total         vs  SUM of exactly the 5 consumer_category rows
--
-- Subsectors (the 11 business_subsector rows) are intentionally excluded
-- from check 2 -- they are grandchildren of business_total, already folded
-- into their parent sector's own reported balance, and including them would
-- double-count.
--
-- Tolerance: the documented S$0.2M published-rounding tolerance, unchanged.
-- The DuckDB original added an epsilon of 1e-6 only to absorb binary
-- floating-point summation noise (a true 0.2 summing to 0.2000000000698).
-- BigQuery NUMERIC sums are exact, so the comparison here uses exactly
-- NUMERIC '0.2' and needs no epsilon; the tolerance itself is not widened.
--
-- BigQuery port of sql/07_monthly_reconciliation.sql.
-- GoogleSQL differences from the DuckDB original:
--   * Tables are fully qualified (project.dataset.table, in backticks) and read
--     through the two CTEs `balances` and `dim`; JOINs use explicit ON clauses.
--   * balance_sgd_mn is NUMERIC (exact decimal), not DOUBLE. This query
--     calculates no percentages: the three reconciliation differences are exact
--     NUMERIC subtractions and sums, rounded to 4 decimal places for display,
--     and each tolerance flag compares the exact difference with NUMERIC '0.2'
--     (see the tolerance note above).
--   * Calculations, filters, ordering and output columns are otherwise
--     unchanged from the DuckDB query.
WITH balances AS (
    SELECT period_end, series_id, balance_sgd_mn
    FROM `singapore-banking-analytics.banking_analytics.loan_balances_long`
),
dim AS (
    SELECT series_id, series_name, parent_series_id, indent_level, category_role, is_leaf, row_order
    FROM `singapore-banking-analytics.banking_analytics.loan_categories`
),
totals AS (
    SELECT
        b.period_end,
        MAX(IF(c.category_role = 'total',          b.balance_sgd_mn, NULL)) AS total_loans_sgd_mn,
        MAX(IF(c.category_role = 'business_total', b.balance_sgd_mn, NULL)) AS business_total_sgd_mn,
        MAX(IF(c.category_role = 'consumer_total', b.balance_sgd_mn, NULL)) AS consumer_total_sgd_mn
    FROM balances b
    JOIN dim c ON c.series_id = b.series_id
    WHERE c.category_role IN ('total', 'business_total', 'consumer_total')
    GROUP BY b.period_end
),
sector_sum AS (
    SELECT b.period_end, SUM(b.balance_sgd_mn) AS business_sector_sum_sgd_mn
    FROM balances b
    JOIN dim c ON c.series_id = b.series_id
    WHERE c.category_role = 'business_sector'
    GROUP BY b.period_end
),
category_sum AS (
    SELECT b.period_end, SUM(b.balance_sgd_mn) AS consumer_category_sum_sgd_mn
    FROM balances b
    JOIN dim c ON c.series_id = b.series_id
    WHERE c.category_role = 'consumer_category'
    GROUP BY b.period_end
),
diffs AS (
    SELECT
        t.period_end,
        t.total_loans_sgd_mn - (t.business_total_sgd_mn + t.consumer_total_sgd_mn) AS diff_total_vs_business_plus_consumer_sgd_mn,
        t.business_total_sgd_mn - ss.business_sector_sum_sgd_mn AS diff_business_total_vs_8_sectors_sgd_mn,
        t.consumer_total_sgd_mn - cs.consumer_category_sum_sgd_mn AS diff_consumer_total_vs_5_categories_sgd_mn
    FROM totals t
    JOIN sector_sum ss ON ss.period_end = t.period_end
    JOIN category_sum cs ON cs.period_end = t.period_end
)
SELECT
    period_end,
    ROUND(diff_total_vs_business_plus_consumer_sgd_mn, 4) AS diff_total_vs_business_plus_consumer_sgd_mn,
    ROUND(diff_business_total_vs_8_sectors_sgd_mn, 4) AS diff_business_total_vs_8_sectors_sgd_mn,
    ROUND(diff_consumer_total_vs_5_categories_sgd_mn, 4) AS diff_consumer_total_vs_5_categories_sgd_mn,
    (ABS(diff_total_vs_business_plus_consumer_sgd_mn) <= NUMERIC '0.2') AS total_check_within_tolerance,
    (ABS(diff_business_total_vs_8_sectors_sgd_mn) <= NUMERIC '0.2') AS business_check_within_tolerance,
    (ABS(diff_consumer_total_vs_5_categories_sgd_mn) <= NUMERIC '0.2') AS consumer_check_within_tolerance,
    CASE
        WHEN ABS(diff_total_vs_business_plus_consumer_sgd_mn) <= NUMERIC '0.2'
         AND ABS(diff_business_total_vs_8_sectors_sgd_mn) <= NUMERIC '0.2'
         AND ABS(diff_consumer_total_vs_5_categories_sgd_mn) <= NUMERIC '0.2'
        THEN 'PASS'
        ELSE 'FAIL'
    END AS overall_reconciliation_status
FROM diffs
ORDER BY period_end;
