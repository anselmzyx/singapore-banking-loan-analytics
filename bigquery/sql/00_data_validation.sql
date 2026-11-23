-- BigQuery validation 00: integrity checks on the two imported tables
--
-- One row per check: check_name, expected, actual, status (PASS / FAIL).
-- Run this first. If any row says FAIL, do not trust the analytical queries.
-- Tables: loan_balances_long (fact, one row per month x category) and
--         loan_categories (dimension, one row per category).
-- Expected values come from the repository's processed CSVs
-- (data/processed/); they are the documented Stage 2 figures.

WITH balances AS (
    SELECT period_end, series_id, balance_sgd_mn
    FROM `singapore-banking-analytics.banking_analytics.loan_balances_long`
),
dim AS (
    SELECT series_id, series_name, parent_series_id, indent_level, category_role, is_leaf, row_order
    FROM `singapore-banking-analytics.banking_analytics.loan_categories`
),
per_month AS (
    SELECT period_end, COUNT(*) AS rows_in_month
    FROM balances
    GROUP BY period_end
),
dupes AS (
    SELECT period_end, series_id
    FROM balances
    GROUP BY period_end, series_id
    HAVING COUNT(*) > 1
),
role_counts AS (
    SELECT category_role, COUNT(*) AS n
    FROM dim
    GROUP BY category_role
),
checks AS (
    -- 1. Row counts
    SELECT 1 AS check_order, 'fact rows' AS check_name, '1674' AS expected,
           CAST(COUNT(*) AS STRING) AS actual FROM balances
    UNION ALL
    SELECT 2, 'dimension rows', '27', CAST(COUNT(*) AS STRING) FROM dim
    -- 2. Unique category IDs
    UNION ALL
    SELECT 3, 'distinct category ids in dimension', '27',
           CAST(COUNT(DISTINCT series_id) AS STRING) FROM dim
    UNION ALL
    SELECT 4, 'distinct category ids in fact', '27',
           CAST(COUNT(DISTINCT series_id) AS STRING) FROM balances
    -- 3. Month coverage
    UNION ALL
    SELECT 5, 'distinct months', '62', CAST(COUNT(DISTINCT period_end) AS STRING) FROM balances
    UNION ALL
    SELECT 6, 'first month', '2021-07-31', CAST(MIN(period_end) AS STRING) FROM balances
    UNION ALL
    SELECT 7, 'last month', '2026-08-31', CAST(MAX(period_end) AS STRING) FROM balances
    UNION ALL
    SELECT 8, 'months that are not a calendar month-end', '0',
           CAST(COUNTIF(period_end != LAST_DAY(period_end)) AS STRING) FROM per_month
    UNION ALL
    SELECT 9, 'months without exactly 27 category rows', '0',
           CAST(COUNTIF(rows_in_month != 27) AS STRING) FROM per_month
    -- 4. Duplicate month-category combinations
    UNION ALL
    SELECT 10, 'duplicate month-category combinations', '0', CAST(COUNT(*) AS STRING) FROM dupes
    -- 5. Missing values
    UNION ALL
    SELECT 11, 'fact rows with a missing period_end, series_id or balance', '0',
           CAST(COUNTIF(period_end IS NULL OR series_id IS NULL OR balance_sgd_mn IS NULL) AS STRING)
    FROM balances
    UNION ALL
    SELECT 12, 'dimension rows with a missing id, name, role or is_leaf flag', '0',
           CAST(COUNTIF(series_id IS NULL OR series_name IS NULL OR category_role IS NULL OR is_leaf IS NULL) AS STRING)
    FROM dim
    -- 6. Invalid parent-category references (the single root has no parent)
    UNION ALL
    SELECT 13, 'categories whose parent id does not exist', '0',
           CAST(COUNT(*) AS STRING)
    FROM dim d
    WHERE NULLIF(d.parent_series_id, '') IS NOT NULL
      AND NOT EXISTS (SELECT 1 FROM dim p WHERE p.series_id = d.parent_series_id)
    UNION ALL
    SELECT 14, 'root categories (no parent)', '1',
           CAST(COUNTIF(NULLIF(parent_series_id, '') IS NULL) AS STRING) FROM dim
    -- 7. Unmatched category IDs (both directions of the join)
    UNION ALL
    SELECT 15, 'fact rows with no matching category', '0',
           CAST(COUNT(*) AS STRING)
    FROM balances b
    LEFT JOIN dim d ON d.series_id = b.series_id
    WHERE d.series_id IS NULL
    UNION ALL
    SELECT 16, 'categories with no fact rows', '0',
           CAST(COUNT(*) AS STRING)
    FROM dim d
    LEFT JOIN (SELECT DISTINCT series_id FROM balances) f ON f.series_id = d.series_id
    WHERE f.series_id IS NULL
    -- 8. Category-role counts (the hierarchy the analysis depends on)
    UNION ALL
    SELECT 17, 'role: total', '1', CAST(IFNULL(MAX(IF(category_role = 'total', n, NULL)), 0) AS STRING) FROM role_counts
    UNION ALL
    SELECT 18, 'role: business_total', '1', CAST(IFNULL(MAX(IF(category_role = 'business_total', n, NULL)), 0) AS STRING) FROM role_counts
    UNION ALL
    SELECT 19, 'role: consumer_total', '1', CAST(IFNULL(MAX(IF(category_role = 'consumer_total', n, NULL)), 0) AS STRING) FROM role_counts
    UNION ALL
    SELECT 20, 'role: business_sector (top-level sectors)', '8', CAST(IFNULL(MAX(IF(category_role = 'business_sector', n, NULL)), 0) AS STRING) FROM role_counts
    UNION ALL
    SELECT 21, 'role: business_subsector (excluded from additive totals)', '11', CAST(IFNULL(MAX(IF(category_role = 'business_subsector', n, NULL)), 0) AS STRING) FROM role_counts
    UNION ALL
    SELECT 22, 'role: consumer_category', '5', CAST(IFNULL(MAX(IF(category_role = 'consumer_category', n, NULL)), 0) AS STRING) FROM role_counts
    UNION ALL
    SELECT 23, 'dimension rows with any other role', '0',
           CAST(COUNTIF(category_role NOT IN ('total', 'business_total', 'consumer_total',
                                              'business_sector', 'business_subsector', 'consumer_category')) AS STRING)
    FROM dim
)
SELECT
    check_order,
    check_name,
    expected,
    actual,
    IF(expected = actual, 'PASS', 'FAIL') AS status
FROM checks
ORDER BY check_order;
