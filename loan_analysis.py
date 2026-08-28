"""
Bank Loan Default & Credit Risk Analysis

Reproduces the SQL in sql/ using pandas, so the repo runs without a database.

Usage:
    python loan_analysis.py --data data/loans.csv
"""

import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OUTPUT_DIR = "outputs"

# Rename here if your copy of the dataset uses different headers.
COLUMN_ALIASES = {
    "loan_amnt": "loan_amount",
    "funded_amnt": "loan_amount",
    "total_pymnt": "total_payment",
    "interest_rate": "int_rate",
    "issue_d": "issue_date",
}

BAD_STATUSES = {"Charged Off", "Default", "Late (31-120 days)"}


def load(path):
    df = pd.read_csv(path, low_memory=False)
    df = df.rename(columns={k: v for k, v in COLUMN_ALIASES.items() if k in df.columns})
    print(f"Loaded {len(df):,} loans, {df.shape[1]} columns")

    required = ["loan_amount", "loan_status"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise SystemExit(
            f"Missing required column(s): {missing}\n"
            f"Available: {list(df.columns)[:25]}\n"
            "Add a mapping to COLUMN_ALIASES at the top of this file."
        )

    # int_rate sometimes arrives as '13.5%' text
    if "int_rate" in df.columns and df["int_rate"].dtype == object:
        df["int_rate"] = (
            df["int_rate"].astype(str).str.rstrip("%").replace("nan", np.nan).astype(float)
        )
        if df["int_rate"].max() > 1:
            df["int_rate"] = df["int_rate"] / 100

    if "dti" in df.columns and df["dti"].max() > 1:
        df["dti"] = df["dti"] / 100

    df["is_bad"] = df["loan_status"].isin(BAD_STATUSES).astype(int)
    return df


def portfolio_kpis(df):
    print("\n=== Portfolio KPIs ===")
    kpis = {
        "total_applications": len(df),
        "total_funded_amount": df["loan_amount"].sum(),
        "default_rate_pct": round(df["is_bad"].mean() * 100, 2),
    }
    if "total_payment" in df.columns:
        kpis["total_amount_received"] = df["total_payment"].sum()
        kpis["recovery_pct"] = round(
            100 * df["total_payment"].sum() / df["loan_amount"].sum(), 2
        )
    if "int_rate" in df.columns:
        kpis["avg_interest_rate_pct"] = round(df["int_rate"].mean() * 100, 2)
    if "dti" in df.columns:
        kpis["avg_dti_pct"] = round(df["dti"].mean() * 100, 2)

    for k, v in kpis.items():
        print(f"  {k:>24}: {v:,}" if isinstance(v, (int, float)) else f"  {k:>24}: {v}")

    # Good vs bad split
    split = (
        df.assign(quality=np.where(df["is_bad"] == 1, "Bad", "Good"))
        .groupby("quality")
        .agg(
            applications=("loan_amount", "size"),
            funded_amount=("loan_amount", "sum"),
        )
    )
    split["pct_of_portfolio"] = (
        100 * split["applications"] / split["applications"].sum()
    ).round(2)
    print("\n=== Good vs bad loans ===")
    print(split.to_string())

    pd.Series(kpis).to_csv(f"{OUTPUT_DIR}/portfolio_kpis.csv", header=["value"])
    return kpis


def risk_cohorts(df):
    """Default rate per cohort, benchmarked against the portfolio average."""
    portfolio_avg = df["is_bad"].mean()
    print(f"\n=== Risk cohorts (portfolio average = {portfolio_avg:.2%}) ===")

    frames = []
    for col in ["grade", "purpose", "home_ownership", "emp_length"]:
        if col not in df.columns:
            continue
        g = (
            df.groupby(col)
            .agg(loans=("is_bad", "size"), default_rate=("is_bad", "mean"))
            .query("loans >= 50")  # thin cohorts are noise
        )
        g["risk_multiple"] = (g["default_rate"] / portfolio_avg).round(2)
        g["default_rate_pct"] = (g["default_rate"] * 100).round(2)
        g = g.drop(columns=["default_rate"]).sort_values(
            "default_rate_pct", ascending=False
        )
        g.insert(0, "cohort_type", col)
        g.index.name = "cohort_value"
        print(f"\n-- {col} --")
        print(g.to_string())
        frames.append(g.reset_index())

    # DTI banding
    if "dti" in df.columns:
        bands = pd.cut(
            df["dti"],
            bins=[-np.inf, 0.10, 0.15, 0.20, 0.25, np.inf],
            labels=["<10%", "10-15%", "15-20%", "20-25%", "25%+"],
        )
        g = (
            df.groupby(bands, observed=True)
            .agg(loans=("is_bad", "size"), default_rate=("is_bad", "mean"))
            .query("loans >= 50")
        )
        g["risk_multiple"] = (g["default_rate"] / portfolio_avg).round(2)
        g["default_rate_pct"] = (g["default_rate"] * 100).round(2)
        g = g.drop(columns=["default_rate"])
        g.insert(0, "cohort_type", "dti_band")
        g.index.name = "cohort_value"
        print("\n-- dti_band --")
        print(g.to_string())
        frames.append(g.reset_index())

        fig, ax = plt.subplots(figsize=(7, 4))
        g["default_rate_pct"].plot.bar(ax=ax, color="#4C72B0")
        ax.axhline(
            portfolio_avg * 100,
            color="crimson",
            linestyle="--",
            label=f"portfolio avg ({portfolio_avg:.1%})",
        )
        ax.set_ylabel("Default rate (%)")
        ax.set_xlabel("Debt-to-income band")
        ax.set_title("Default rate by DTI band")
        ax.legend()
        fig.tight_layout()
        fig.savefig(f"{OUTPUT_DIR}/default_by_dti.png", dpi=150)

    if frames:
        pd.concat(frames, ignore_index=True).to_csv(
            f"{OUTPUT_DIR}/risk_cohorts.csv", index=False
        )


def monthly_trend(df):
    if "issue_date" not in df.columns:
        print("\nNo issue_date column - skipping monthly trend")
        return

    d = df.copy()
    d["issue_date"] = pd.to_datetime(d["issue_date"], errors="coerce")
    d = d.dropna(subset=["issue_date"])
    if d.empty:
        return

    monthly = (
        d.set_index("issue_date")
        .resample("MS")
        .agg(applications=("loan_amount", "size"),
             funded_amount=("loan_amount", "sum"),
             default_rate=("is_bad", "mean"))
    )
    # PMTD comparison, mirroring the LAG() in 02_mtd_trends.sql
    monthly["pmtd_funded"] = monthly["funded_amount"].shift(1)
    monthly["funded_mom_growth_pct"] = (
        100
        * (monthly["funded_amount"] - monthly["pmtd_funded"])
        / monthly["pmtd_funded"]
    ).round(2)
    monthly["cumulative_funded"] = monthly["funded_amount"].cumsum()
    monthly["default_rate_pct"] = (monthly["default_rate"] * 100).round(2)

    print("\n=== Monthly trend (tail) ===")
    print(
        monthly[["applications", "funded_amount", "funded_mom_growth_pct",
                 "default_rate_pct"]].tail(12).to_string()
    )
    monthly.to_csv(f"{OUTPUT_DIR}/monthly_trend.csv")

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(monthly.index, monthly["funded_amount"], marker="o", markersize=3)
    ax.set_ylabel("Funded amount")
    ax.set_title("Funded amount by month")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(f"{OUTPUT_DIR}/funded_by_month.png", dpi=150)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/loans.csv")
    args = parser.parse_args()

    if not os.path.exists(args.data):
        raise SystemExit(
            f"Dataset not found at {args.data}\n"
            "See the README for where to download a loan book CSV."
        )

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df = load(args.data)
    portfolio_kpis(df)
    risk_cohorts(df)
    monthly_trend(df)
    print(f"\nArtifacts written to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
