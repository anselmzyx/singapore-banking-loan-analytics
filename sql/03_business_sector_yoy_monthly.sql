-- Query 03: Business sector month-over-month and 12-month change, all months
--
-- All 8 business_sector categories across all 62 months (496 rows). Uses
-- LAG(1) and LAG(12), each PARTITIONed BY sector (series_id) and ordered by
-- period_end, so lags never leak across sectors. The first month per sector
-- has NULL for the 1-month lag, and the first 12 months per sector have NULL
-- for the 12-month lag -- these are left as NULL, not replaced with zero.
-- Percentage changes use NULLIF to avoid division by zero.

WITH sector_balances AS (
    SELECT
        b.period_end,
        c.series_id,
        c.series_name AS sector_name,
        b.balance_sgd_mn
    FROM loan_balances_long b
    JOIN loan_categories c USING (series_id)
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
    ROUND((balance_sgd_mn - prev_month_balance_sgd_mn) / NULLIF(prev_month_balance_sgd_mn, 0) * 100, 2) AS mom_pct_change,
    balance_12m_earlier_sgd_mn,
    ROUND(balance_sgd_mn - balance_12m_earlier_sgd_mn, 1) AS yoy_abs_change_sgd_mn,
    ROUND((balance_sgd_mn - balance_12m_earlier_sgd_mn) / NULLIF(balance_12m_earlier_sgd_mn, 0) * 100, 2) AS yoy_pct_change
FROM with_lags
ORDER BY sector_name, period_end;
