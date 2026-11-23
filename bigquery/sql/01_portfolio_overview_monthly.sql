-- Query 01: Portfolio overview, monthly
--
-- One row per month (62 rows total). Pulls the three reported totals (overall,
-- business, consumer) via conditional aggregation, then uses LAG() to compute
-- month-over-month and 12-month changes. Balances are never summed across
-- months -- only compared period-to-period via LAG(). The first month has a
-- NULL 1-month lag and the first 12 months have a NULL 12-month lag; these
-- stay NULL.
--
-- BigQuery port of sql/01_portfolio_overview_monthly.sql.
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
with_lags AS (
    SELECT
        period_end,
        total_loans_sgd_mn,
        business_total_sgd_mn,
        consumer_total_sgd_mn,
        LAG(total_loans_sgd_mn, 1)  OVER (ORDER BY period_end) AS total_prev_month_sgd_mn,
        LAG(total_loans_sgd_mn, 12) OVER (ORDER BY period_end) AS total_prev_12m_sgd_mn
    FROM totals
)
SELECT
    period_end,
    total_loans_sgd_mn,
    business_total_sgd_mn,
    consumer_total_sgd_mn,
    ROUND(business_total_sgd_mn * 100 / NULLIF(total_loans_sgd_mn, 0), 2) AS business_share_of_total_pct,
    ROUND(consumer_total_sgd_mn * 100 / NULLIF(total_loans_sgd_mn, 0), 2) AS consumer_share_of_total_pct,
    ROUND(total_loans_sgd_mn - total_prev_month_sgd_mn, 1) AS total_mom_abs_change_sgd_mn,
    ROUND((total_loans_sgd_mn - total_prev_month_sgd_mn) * 100 / NULLIF(total_prev_month_sgd_mn, 0), 2) AS total_mom_pct_change,
    ROUND(total_loans_sgd_mn - total_prev_12m_sgd_mn, 1) AS total_yoy_abs_change_sgd_mn,
    ROUND((total_loans_sgd_mn - total_prev_12m_sgd_mn) * 100 / NULLIF(total_prev_12m_sgd_mn, 0), 2) AS total_yoy_pct_change
FROM with_lags
ORDER BY period_end;
