-- Query 02: Business sector exposure, latest month
--
-- Exactly the 8 top-level business_sector categories at the latest reported
-- month (8 rows). Shares use the reported business_total as the denominator.
-- Ranked by outstanding balance with ROW_NUMBER(); ties broken deterministically
-- by series_id.

WITH latest AS (
    SELECT MAX(period_end) AS period_end FROM loan_balances_long
),
business_total AS (
    SELECT b.period_end, b.balance_sgd_mn AS business_total_sgd_mn
    FROM loan_balances_long b
    JOIN loan_categories c USING (series_id)
    WHERE c.category_role = 'business_total'
),
sectors AS (
    SELECT
        b.period_end,
        c.series_id,
        c.series_name AS sector_name,
        b.balance_sgd_mn
    FROM loan_balances_long b
    JOIN loan_categories c USING (series_id)
    WHERE c.category_role = 'business_sector'
)
SELECT
    s.period_end,
    s.sector_name,
    s.balance_sgd_mn,
    ROUND(s.balance_sgd_mn / NULLIF(t.business_total_sgd_mn, 0) * 100, 2) AS share_of_business_total_pct,
    ROW_NUMBER() OVER (ORDER BY s.balance_sgd_mn DESC, s.series_id) AS sector_rank
FROM sectors s
JOIN business_total t ON t.period_end = s.period_end
JOIN latest l ON l.period_end = s.period_end
ORDER BY sector_rank;
