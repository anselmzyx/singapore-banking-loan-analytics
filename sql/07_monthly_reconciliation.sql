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
-- A tiny epsilon (1e-6) is added to the S$0.2M published-rounding tolerance
-- to absorb ordinary binary floating-point summation noise (e.g. a true
-- 0.2 landing as 0.2000000000698 after SUM()) -- not a data tolerance.

WITH totals AS (
    SELECT
        b.period_end,
        MAX(CASE WHEN c.category_role = 'total'         THEN b.balance_sgd_mn END) AS total_loans_sgd_mn,
        MAX(CASE WHEN c.category_role = 'business_total' THEN b.balance_sgd_mn END) AS business_total_sgd_mn,
        MAX(CASE WHEN c.category_role = 'consumer_total' THEN b.balance_sgd_mn END) AS consumer_total_sgd_mn
    FROM loan_balances_long b
    JOIN loan_categories c USING (series_id)
    WHERE c.category_role IN ('total', 'business_total', 'consumer_total')
    GROUP BY b.period_end
),
sector_sum AS (
    SELECT b.period_end, SUM(b.balance_sgd_mn) AS business_sector_sum_sgd_mn
    FROM loan_balances_long b
    JOIN loan_categories c USING (series_id)
    WHERE c.category_role = 'business_sector'
    GROUP BY b.period_end
),
category_sum AS (
    SELECT b.period_end, SUM(b.balance_sgd_mn) AS consumer_category_sum_sgd_mn
    FROM loan_balances_long b
    JOIN loan_categories c USING (series_id)
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
    (ABS(diff_total_vs_business_plus_consumer_sgd_mn) <= 0.2000001) AS total_check_within_tolerance,
    (ABS(diff_business_total_vs_8_sectors_sgd_mn) <= 0.2000001) AS business_check_within_tolerance,
    (ABS(diff_consumer_total_vs_5_categories_sgd_mn) <= 0.2000001) AS consumer_check_within_tolerance,
    CASE
        WHEN ABS(diff_total_vs_business_plus_consumer_sgd_mn) <= 0.2000001
         AND ABS(diff_business_total_vs_8_sectors_sgd_mn) <= 0.2000001
         AND ABS(diff_consumer_total_vs_5_categories_sgd_mn) <= 0.2000001
        THEN 'PASS'
        ELSE 'FAIL'
    END AS overall_reconciliation_status
FROM diffs
ORDER BY period_end;
