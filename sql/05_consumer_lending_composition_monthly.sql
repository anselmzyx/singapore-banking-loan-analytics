-- Query 05: Consumer lending composition, monthly
--
-- Exactly the 5 consumer_category rows, across all 62 months (310 rows).
-- Shares use the reported consumer_total as the denominator; the consumer
-- total itself is not included as a sixth "category" row.

WITH consumer_total AS (
    SELECT b.period_end, b.balance_sgd_mn AS consumer_total_sgd_mn
    FROM loan_balances_long b
    JOIN loan_categories c USING (series_id)
    WHERE c.category_role = 'consumer_total'
),
categories AS (
    SELECT
        b.period_end,
        c.series_name AS category_name,
        b.balance_sgd_mn
    FROM loan_balances_long b
    JOIN loan_categories c USING (series_id)
    WHERE c.category_role = 'consumer_category'
)
SELECT
    cat.period_end,
    cat.category_name,
    cat.balance_sgd_mn,
    ct.consumer_total_sgd_mn,
    ROUND(cat.balance_sgd_mn / NULLIF(ct.consumer_total_sgd_mn, 0) * 100, 2) AS share_of_consumer_total_pct
FROM categories cat
JOIN consumer_total ct ON ct.period_end = cat.period_end
ORDER BY cat.period_end, cat.category_name;
