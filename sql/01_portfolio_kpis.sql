-- =============================================================
-- 01 - Portfolio KPIs
-- Headline lending metrics, and the good-loan / bad-loan split.
-- =============================================================

-- A loan is "bad" once it is charged off; Fully Paid and Current are "good".
-- Defining this once in a CTE keeps every downstream metric consistent.
WITH classified AS (
    SELECT
        id,
        loan_amount,
        total_payment,
        int_rate,
        dti,
        grade,
        purpose,
        home_ownership,
        emp_length,
        issue_date,
        loan_status,
        CASE
            WHEN loan_status = 'Charged Off' THEN 'Bad'
            ELSE 'Good'
        END AS loan_quality
    FROM bank_loan
)

-- ---------- Headline portfolio numbers ----------
SELECT
    COUNT(*)                                        AS total_applications,
    SUM(loan_amount)                                AS total_funded_amount,
    SUM(total_payment)                              AS total_amount_received,
    ROUND(AVG(int_rate) * 100, 2)                   AS avg_interest_rate_pct,
    ROUND(AVG(dti) * 100, 2)                        AS avg_dti_pct,
    ROUND(
        100.0 * SUM(CASE WHEN loan_quality = 'Bad' THEN 1 ELSE 0 END) / COUNT(*),
        2
    )                                               AS default_rate_pct
FROM classified;


-- ---------- Good vs bad loan breakdown ----------
WITH classified AS (
    SELECT
        loan_amount,
        total_payment,
        int_rate,
        dti,
        CASE WHEN loan_status = 'Charged Off' THEN 'Bad' ELSE 'Good' END AS loan_quality
    FROM bank_loan
)
SELECT
    loan_quality,
    COUNT(*)                                        AS applications,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_portfolio,
    SUM(loan_amount)                                AS funded_amount,
    SUM(total_payment)                              AS amount_received,
    -- Recovery ratio: how much of what we lent came back
    ROUND(100.0 * SUM(total_payment) / NULLIF(SUM(loan_amount), 0), 2) AS recovery_pct,
    ROUND(AVG(int_rate) * 100, 2)                   AS avg_interest_rate_pct,
    ROUND(AVG(dti) * 100, 2)                        AS avg_dti_pct
FROM classified
GROUP BY loan_quality
ORDER BY loan_quality;
