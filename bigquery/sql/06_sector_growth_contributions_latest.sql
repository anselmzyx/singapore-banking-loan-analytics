-- Query 06: Business sector growth contributions, latest 12-month period
--
-- One row per business sector (8 rows), covering the most recent 12-month
-- window available in the data. "Contribution" = this sector's own 12-month
-- absolute change, as a percentage of the business lending total's own
-- 12-month absolute change:
--
--     contribution_pct = sector_12m_abs_change / business_total_12m_abs_change * 100
--
-- This represents each sector's share of the NET business-lending stock
-- change over the period -- it is not a share of gross growth. Because
-- sectors can move in opposite directions, contributions can be negative
-- (a sector that shrank while the total grew) or exceed 100% (a sector grew
-- by more than the net total change, offset by declines elsewhere).
-- NULLIF guards the case where the business total's 12-month change is zero.
--
-- LAG(12) is computed over each series' full 62-month history first, then
-- filtered down to the latest period -- not computed on a pre-filtered
-- single-row partition, which would always return NULL.
--
-- BigQuery port of sql/06_sector_growth_contributions_latest.sql.
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
sector_series AS (
    SELECT
        b.period_end,
        c.series_id,
        c.series_name AS sector_name,
        b.balance_sgd_mn,
        LAG(b.balance_sgd_mn, 12) OVER (PARTITION BY c.series_id ORDER BY b.period_end) AS balance_12m_earlier_sgd_mn
    FROM balances b
    JOIN dim c ON c.series_id = b.series_id
    WHERE c.category_role = 'business_sector'
),
latest AS (
    SELECT MAX(period_end) AS period_end FROM balances
),
latest_sectors AS (
    SELECT s.period_end, s.series_id, s.sector_name, s.balance_sgd_mn, s.balance_12m_earlier_sgd_mn
    FROM sector_series s
    JOIN latest l ON l.period_end = s.period_end
),
business_total_series AS (
    SELECT
        b.period_end,
        b.balance_sgd_mn,
        LAG(b.balance_sgd_mn, 12) OVER (ORDER BY b.period_end) AS balance_12m_earlier_sgd_mn
    FROM balances b
    JOIN dim c ON c.series_id = b.series_id
    WHERE c.category_role = 'business_total'
),
business_total_change AS (
    SELECT
        bts.period_end,
        bts.balance_sgd_mn - bts.balance_12m_earlier_sgd_mn AS business_total_12m_change_sgd_mn
    FROM business_total_series bts
    JOIN latest l ON l.period_end = bts.period_end
)
SELECT
    ls.sector_name,
    ROUND(ls.balance_sgd_mn, 1) AS latest_balance_sgd_mn,
    ROUND(ls.balance_12m_earlier_sgd_mn, 1) AS balance_12m_earlier_sgd_mn,
    ROUND(ls.balance_sgd_mn - ls.balance_12m_earlier_sgd_mn, 1) AS abs_change_12m_sgd_mn,
    ROUND((ls.balance_sgd_mn - ls.balance_12m_earlier_sgd_mn) * 100 / NULLIF(ls.balance_12m_earlier_sgd_mn, 0), 2) AS pct_change_12m,
    ROUND(btc.business_total_12m_change_sgd_mn, 1) AS business_total_12m_change_sgd_mn,
    ROUND((ls.balance_sgd_mn - ls.balance_12m_earlier_sgd_mn) * 100 / NULLIF(btc.business_total_12m_change_sgd_mn, 0), 2) AS contribution_to_business_change_pct
FROM latest_sectors ls
CROSS JOIN business_total_change btc
ORDER BY contribution_to_business_change_pct DESC;
