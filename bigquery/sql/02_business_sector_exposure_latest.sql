-- Query 02: Business sector exposure, latest month
--
-- Exactly the 8 top-level business_sector categories at the latest reported
-- month (8 rows). Shares use the reported business_total as the denominator.
-- Ranked by outstanding balance with ROW_NUMBER(); ties broken deterministically
-- by series_id.
--
-- BigQuery port of sql/02_business_sector_exposure_latest.sql.
-- GoogleSQL differences from the DuckDB original:
--   * Tables are fully qualified (project.dataset.table, in backticks) and read
--     through the two CTEs `balances` and `dim`; JOINs use explicit ON clauses.
--   * balance_sgd_mn is NUMERIC (exact decimal), not DOUBLE. Percentages are
--     computed as (x * 100) / NULLIF(y, 0), so the exact product is divided
--     once and ROUND(..., 2) is applied to an exact decimal.
--   * Calculations, filters, partitions, ordering and output columns are
--     otherwise unchanged from the DuckDB query.
WITH balances AS (
    SELECT period_end, series_id, balance_sgd_mn
    FROM `singapore-banking-analytics.banking_analytics.loan_balances_long`
),
dim AS (
    SELECT series_id, series_name, parent_series_id, indent_level, category_role, is_leaf, row_order
    FROM `singapore-banking-analytics.banking_analytics.loan_categories`
),
latest AS (
    SELECT MAX(period_end) AS period_end FROM balances
),
business_total AS (
    SELECT b.period_end, b.balance_sgd_mn AS business_total_sgd_mn
    FROM balances b
    JOIN dim c ON c.series_id = b.series_id
    WHERE c.category_role = 'business_total'
),
sectors AS (
    SELECT
        b.period_end,
        c.series_id,
        c.series_name AS sector_name,
        b.balance_sgd_mn
    FROM balances b
    JOIN dim c ON c.series_id = b.series_id
    WHERE c.category_role = 'business_sector'
)
SELECT
    s.period_end,
    s.sector_name,
    s.balance_sgd_mn,
    ROUND(s.balance_sgd_mn * 100 / NULLIF(t.business_total_sgd_mn, 0), 2) AS share_of_business_total_pct,
    ROW_NUMBER() OVER (ORDER BY s.balance_sgd_mn DESC, s.series_id) AS sector_rank
FROM sectors s
JOIN business_total t ON t.period_end = s.period_end
JOIN latest l ON l.period_end = s.period_end
ORDER BY sector_rank;
