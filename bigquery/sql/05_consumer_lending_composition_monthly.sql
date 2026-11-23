-- Query 05: Consumer lending composition, monthly
--
-- Exactly the 5 consumer_category rows, across all 62 months (310 rows).
-- Shares use the reported consumer_total as the denominator; the consumer
-- total itself is not included as a sixth "category" row.
--
-- BigQuery port of sql/05_consumer_lending_composition_monthly.sql.
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
consumer_total AS (
    SELECT b.period_end, b.balance_sgd_mn AS consumer_total_sgd_mn
    FROM balances b
    JOIN dim c ON c.series_id = b.series_id
    WHERE c.category_role = 'consumer_total'
),
categories AS (
    SELECT
        b.period_end,
        c.series_name AS category_name,
        b.balance_sgd_mn
    FROM balances b
    JOIN dim c ON c.series_id = b.series_id
    WHERE c.category_role = 'consumer_category'
)
SELECT
    cat.period_end,
    cat.category_name,
    cat.balance_sgd_mn,
    ct.consumer_total_sgd_mn,
    ROUND(cat.balance_sgd_mn * 100 / NULLIF(ct.consumer_total_sgd_mn, 0), 2) AS share_of_consumer_total_pct
FROM categories cat
JOIN consumer_total ct ON ct.period_end = cat.period_end
ORDER BY cat.period_end, cat.category_name;
