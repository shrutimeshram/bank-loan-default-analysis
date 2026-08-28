-- =============================================================
-- 03 - Where the credit risk actually sits
-- Default rate by grade, purpose, home ownership, employment
-- length and DTI band, each benchmarked against the portfolio
-- average so outliers are obvious.
-- =============================================================

-- Portfolio-wide default rate, reused as the benchmark in every cohort below.
WITH portfolio AS (
    SELECT
        AVG(CASE WHEN loan_status = 'Charged Off' THEN 1.0 ELSE 0.0 END) AS avg_default_rate
    FROM bank_loan
),

by_grade AS (
    SELECT
        grade                                                            AS cohort_value,
        'grade'                                                          AS cohort_type,
        COUNT(*)                                                         AS loans,
        SUM(loan_amount)                                                 AS funded_amount,
        AVG(CASE WHEN loan_status = 'Charged Off' THEN 1.0 ELSE 0.0 END) AS default_rate
    FROM bank_loan
    GROUP BY grade
),

by_purpose AS (
    SELECT
        purpose, 'purpose', COUNT(*), SUM(loan_amount),
        AVG(CASE WHEN loan_status = 'Charged Off' THEN 1.0 ELSE 0.0 END)
    FROM bank_loan
    GROUP BY purpose
),

by_home AS (
    SELECT
        home_ownership, 'home_ownership', COUNT(*), SUM(loan_amount),
        AVG(CASE WHEN loan_status = 'Charged Off' THEN 1.0 ELSE 0.0 END)
    FROM bank_loan
    GROUP BY home_ownership
),

by_dti_band AS (
    SELECT
        CASE
            WHEN dti < 0.10 THEN 'DTI < 10%'
            WHEN dti < 0.15 THEN 'DTI 10-15%'
            WHEN dti < 0.20 THEN 'DTI 15-20%'
            WHEN dti < 0.25 THEN 'DTI 20-25%'
            ELSE                 'DTI 25%+'
        END,
        'dti_band', COUNT(*), SUM(loan_amount),
        AVG(CASE WHEN loan_status = 'Charged Off' THEN 1.0 ELSE 0.0 END)
    FROM bank_loan
    GROUP BY 1
),

combined AS (
    SELECT * FROM by_grade
    UNION ALL SELECT * FROM by_purpose
    UNION ALL SELECT * FROM by_home
    UNION ALL SELECT * FROM by_dti_band
)

SELECT
    c.cohort_type,
    c.cohort_value,
    c.loans,
    c.funded_amount,
    ROUND(c.default_rate * 100, 2)                          AS default_rate_pct,
    ROUND(p.avg_default_rate * 100, 2)                      AS portfolio_avg_pct,
    -- How many times the portfolio average this cohort defaults at
    ROUND(c.default_rate / NULLIF(p.avg_default_rate, 0), 2) AS risk_multiple,
    RANK() OVER (
        PARTITION BY c.cohort_type ORDER BY c.default_rate DESC
    )                                                        AS risk_rank_in_group
FROM combined c
CROSS JOIN portfolio p
-- Ignore thin cohorts: a 3-loan bucket at 100% default is noise, not signal.
WHERE c.loans >= 50
ORDER BY c.cohort_type, c.default_rate DESC;
