-- Query 01: Portfolio overview, monthly
--
-- One row per month (62 rows total). Pulls the three reported totals (overall,
-- business, consumer) via conditional aggregation, then uses LAG() to compute
-- month-over-month and 12-month changes. Balances are never summed across
-- months -- only compared period-to-period via LAG().

WITH totals AS (
    SELECT
        b.period_end,
        MAX(CASE WHEN c.category_role = 'total'          THEN b.balance_sgd_mn END) AS total_loans_sgd_mn,
        MAX(CASE WHEN c.category_role = 'business_total'  THEN b.balance_sgd_mn END) AS business_total_sgd_mn,
        MAX(CASE WHEN c.category_role = 'consumer_total'  THEN b.balance_sgd_mn END) AS consumer_total_sgd_mn
    FROM loan_balances_long b
    JOIN loan_categories c USING (series_id)
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
    ROUND(business_total_sgd_mn / NULLIF(total_loans_sgd_mn, 0) * 100, 2) AS business_share_of_total_pct,
    ROUND(consumer_total_sgd_mn / NULLIF(total_loans_sgd_mn, 0) * 100, 2) AS consumer_share_of_total_pct,
    ROUND(total_loans_sgd_mn - total_prev_month_sgd_mn, 1) AS total_mom_abs_change_sgd_mn,
    ROUND((total_loans_sgd_mn - total_prev_month_sgd_mn) / NULLIF(total_prev_month_sgd_mn, 0) * 100, 2) AS total_mom_pct_change,
    ROUND(total_loans_sgd_mn - total_prev_12m_sgd_mn, 1) AS total_yoy_abs_change_sgd_mn,
    ROUND((total_loans_sgd_mn - total_prev_12m_sgd_mn) / NULLIF(total_prev_12m_sgd_mn, 0) * 100, 2) AS total_yoy_pct_change
FROM with_lags
ORDER BY period_end;
