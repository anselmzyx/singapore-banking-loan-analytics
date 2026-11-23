-- Query 03: Business sector month-over-month and 12-month change, all months
--
-- All 8 business_sector categories across all 62 months (496 rows). Uses
-- LAG(1) and LAG(12), each PARTITIONed BY sector (series_id) and ordered by
-- period_end, so lags never leak across sectors. The first month per sector
-- has NULL for the 1-month lag, and the first 12 months per sector have NULL
-- for the 12-month lag -- these are left as NULL, not replaced with zero.
-- Percentage changes use NULLIF to avoid division by zero.
--
-- BigQuery port of sql/03_business_sector_yoy_monthly.sql.
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
sector_balances AS (
    SELECT
        b.period_end,
        c.series_id,
        c.series_name AS sector_name,
        b.balance_sgd_mn
    FROM balances b
    JOIN dim c ON c.series_id = b.series_id
    WHERE c.category_role = 'business_sector'
),
with_lags AS (
    SELECT
        period_end,
        sector_name,
        series_id,
        balance_sgd_mn,
        LAG(balance_sgd_mn, 1)  OVER (PARTITION BY series_id ORDER BY period_end) AS prev_month_balance_sgd_mn,
        LAG(balance_sgd_mn, 12) OVER (PARTITION BY series_id ORDER BY period_end) AS balance_12m_earlier_sgd_mn
    FROM sector_balances
)
SELECT
    period_end,
    sector_name,
    balance_sgd_mn,
    prev_month_balance_sgd_mn,
    ROUND(balance_sgd_mn - prev_month_balance_sgd_mn, 1) AS mom_abs_change_sgd_mn,
    ROUND((balance_sgd_mn - prev_month_balance_sgd_mn) * 100 / NULLIF(prev_month_balance_sgd_mn, 0), 2) AS mom_pct_change,
    balance_12m_earlier_sgd_mn,
    ROUND(balance_sgd_mn - balance_12m_earlier_sgd_mn, 1) AS yoy_abs_change_sgd_mn,
    ROUND((balance_sgd_mn - balance_12m_earlier_sgd_mn) * 100 / NULLIF(balance_12m_earlier_sgd_mn, 0), 2) AS yoy_pct_change
FROM with_lags
ORDER BY sector_name, period_end;
