-- Query 04: Business sector concentration, monthly
--
-- One row per month (62 rows). For each month independently, ranks the 8
-- business_sector categories by outstanding balance with ROW_NUMBER()
-- (ties broken deterministically by series_id), takes the top 3 for THAT
-- month -- not a fixed set of 3 sectors -- sums their balances, and divides
-- by the reported business_total for that month.
--
-- This is a concentration-of-outstanding-balances measure only. It says
-- nothing about default probability or credit risk.
--
-- BigQuery port of sql/04_business_sector_concentration_monthly.sql.
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
sectors AS (
    SELECT
        b.period_end,
        c.series_id,
        c.series_name AS sector_name,
        b.balance_sgd_mn
    FROM balances b
    JOIN dim c ON c.series_id = b.series_id
    WHERE c.category_role = 'business_sector'
),
ranked AS (
    SELECT
        period_end,
        series_id,
        sector_name,
        balance_sgd_mn,
        ROW_NUMBER() OVER (PARTITION BY period_end ORDER BY balance_sgd_mn DESC, series_id) AS sector_rank
    FROM sectors
),
top3 AS (
    SELECT period_end, SUM(balance_sgd_mn) AS top_3_sector_balance_sgd_mn
    FROM ranked
    WHERE sector_rank <= 3
    GROUP BY period_end
),
business_total AS (
    SELECT b.period_end, b.balance_sgd_mn AS business_total_sgd_mn
    FROM balances b
    JOIN dim c ON c.series_id = b.series_id
    WHERE c.category_role = 'business_total'
)
SELECT
    t.period_end,
    ROUND(t.top_3_sector_balance_sgd_mn, 1) AS top_3_sector_balance_sgd_mn,
    ROUND(bt.business_total_sgd_mn, 1) AS business_total_sgd_mn,
    ROUND(t.top_3_sector_balance_sgd_mn * 100 / NULLIF(bt.business_total_sgd_mn, 0), 2) AS top_3_share_pct
FROM top3 t
JOIN business_total bt ON bt.period_end = t.period_end
ORDER BY t.period_end;
