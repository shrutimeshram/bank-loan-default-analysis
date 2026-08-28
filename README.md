# Bank Loan Default & Credit Risk Analysis

SQL and Python analysis of a consumer lending portfolio — portfolio KPIs, month-on-month
trends, and a cohort breakdown of where credit risk actually concentrates.

## Dataset

Any of the standard public lending datasets work here. This was built against the
**LendingClub-style loan book** (~38,000 funded applications) available on Kaggle:

- [Bank Loan Dataset](https://www.kaggle.com/datasets/bhavikjikadara/bank-loan)
- or the larger [LendingClub Loan Data](https://www.kaggle.com/datasets/wordsforthewise/lending-club)

Place the CSV in `data/loans.csv`. It is not committed here.

Expected columns (rename in `loan_analysis.py` if yours differ):

| Column | Meaning |
|---|---|
| `loan_amount` | funded amount |
| `total_payment` | amount received back |
| `int_rate` | interest rate |
| `dti` | debt-to-income ratio |
| `grade` / `sub_grade` | internal credit grade |
| `purpose` | stated loan purpose |
| `home_ownership` | RENT / OWN / MORTGAGE |
| `emp_length` | employment length |
| `loan_status` | Fully Paid / Charged Off / Current |
| `issue_date` | origination date |

## What it answers

**Portfolio KPIs** — total applications, funded amount, amount received, average interest
rate, average DTI, split by good loans (Fully Paid / Current) vs bad loans (Charged Off).

**Month-on-month movement** — MTD vs PMTD for each KPI using window functions, so the
direction of travel is visible rather than just the level.

**Where the risk sits** — default rate by grade, purpose, home ownership, employment length,
and DTI band, so lending policy can be targeted rather than blanket-tightened.

## Layout

```
sql/
  01_portfolio_kpis.sql      -- headline metrics, good vs bad loan split
  02_mtd_trends.sql          -- month-on-month movement via window functions
  03_risk_cohorts.sql        -- default rate by grade / purpose / DTI band
loan_analysis.py             -- same analysis in pandas, plus charts
```

The SQL is written for MySQL 8+ / PostgreSQL (CTEs and window functions).
`loan_analysis.py` reproduces it in pandas so the repo runs without a database.

## Running it

```bash
pip install -r requirements.txt
python loan_analysis.py --data data/loans.csv
```

Charts and a KPI summary are written to `outputs/`.

## Results

Fill in once you have run it against your copy of the data:

| Metric | Value |
|---|---|
| Total funded amount | |
| Total amount received | |
| Overall default rate | |
| Average interest rate | |
| Average DTI | |
| Highest-risk grade band | |
