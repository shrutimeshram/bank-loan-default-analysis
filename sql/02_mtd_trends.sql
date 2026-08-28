-- =============================================================
-- 02 - Month-on-month movement (MTD vs PMTD)
-- Uses window functions so each month carries its own prior-month
-- comparison, rather than needing a self-join per metric.
-- =============================================================

WITH monthly AS (
    SELECT
        DATE_FORMAT(issue_date, '%Y-%m-01')  AS month_start,
        COUNT(*)                             AS applications,
        SUM(loan_amount)                     AS funded_amount,
        SUM(total_payment)                   AS amount_received,
        AVG(int_rate)                        AS avg_int_rate,
        AVG(dti)                             AS avg_dti,
        SUM(CASE WHEN loan_status = 'Charged Off' THEN 1 ELSE 0 END) AS bad_loans
    FROM bank_loan
    GROUP BY DATE_FORMAT(issue_date, '%Y-%m-01')
),

with_prior AS (
    SELECT
        month_start,
        applications,
        funded_amount,
        amount_received,
        bad_loans,
        ROUND(avg_int_rate * 100, 2) AS avg_int_rate_pct,
        ROUND(avg_dti * 100, 2)      AS avg_dti_pct,
        -- PMTD: previous month's value, carried onto the same row
        LAG(applications)    OVER (ORDER BY month_start) AS pmtd_applications,
        LAG(funded_amount)   OVER (ORDER BY month_start) AS pmtd_funded_amount,
        LAG(amount_received) OVER (ORDER BY month_start) AS pmtd_amount_received,
        -- Running total across the whole book
        SUM(funded_amount)   OVER (ORDER BY month_start
                                   ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                                                          AS cumulative_funded
    FROM monthly
)

SELECT
    month_start,
    applications,
    funded_amount,
    amount_received,
    cumulative_funded,
    avg_int_rate_pct,
    avg_dti_pct,
    ROUND(100.0 * bad_loans / NULLIF(applications, 0), 2) AS default_rate_pct,
    -- Month-on-month growth, guarded against a divide-by-zero on the first row
    ROUND(
        100.0 * (funded_amount - pmtd_funded_amount) / NULLIF(pmtd_funded_amount, 0),
        2
    ) AS funded_mom_growth_pct,
    ROUND(
        100.0 * (applications - pmtd_applications) / NULLIF(pmtd_applications, 0),
        2
    ) AS applications_mom_growth_pct
FROM with_prior
ORDER BY month_start;
