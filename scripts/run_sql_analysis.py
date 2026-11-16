"""
Stage 3 DuckDB SQL analysis runner for Portfolio 03.

Loads the two Stage 2 processed CSVs into an in-memory DuckDB connection
(no database file is created), runs the seven SQL queries under sql/, writes
each result to results/<query_name>.csv, and then runs a small set of
validation checks against expected row counts, date coverage, and the
Stage 2 anchor values.

This script performs no analysis of its own beyond what the .sql files
already compute -- it is a thin loader/runner/validator.
"""

from pathlib import Path

import duckdb
import pandas as pd

CATEGORIES_CSV = "data/processed/loan_categories.csv"
BALANCES_CSV = "data/processed/loan_balances_long.csv"
SQL_DIR = Path("sql")
RESULTS_DIR = Path("results")

QUERY_FILES = [
    "01_portfolio_overview_monthly.sql",
    "02_business_sector_exposure_latest.sql",
    "03_business_sector_yoy_monthly.sql",
    "04_business_sector_concentration_monthly.sql",
    "05_consumer_lending_composition_monthly.sql",
    "06_sector_growth_contributions_latest.sql",
    "07_monthly_reconciliation.sql",
]

EXPECTED_ROWS = {
    "01_portfolio_overview_monthly.sql": 62,
    "02_business_sector_exposure_latest.sql": 8,
    "03_business_sector_yoy_monthly.sql": 496,
    "04_business_sector_concentration_monthly.sql": 62,
    "05_consumer_lending_composition_monthly.sql": 310,
    "06_sector_growth_contributions_latest.sql": 8,
    "07_monthly_reconciliation.sql": 62,
}

MIN_DATE = "2021-07-31"
MAX_DATE = "2026-08-31"
ROUNDING_TOLERANCE_MN = 0.2
EPS = 1e-6

# Stage 2 anchor values this stage's SQL results must agree with.
ANCHORS = {
    "total_loans_2021-07-31": 793275.6,
    "total_loans_2026-08-31": 966432.7,
    "latest_yoy_pct_approx": 13.47,
    "top3_concentration_2026-08-31_pct_approx": 76.87,
    "financial_insurance_12m_change": 23150.1,
    "agri_mining_12m_pct_approx": 41.65,
    "others_12m_change": -850.6,
}


def setup_connection():
    """In-memory DuckDB connection with two typed views over the Stage 2 CSVs."""
    con = duckdb.connect(database=":memory:")

    con.execute(f"""
        CREATE OR REPLACE VIEW loan_balances_long AS
        SELECT * FROM read_csv(
            '{BALANCES_CSV}',
            header = true,
            columns = {{
                'period_end': 'DATE',
                'series_id': 'VARCHAR',
                'balance_sgd_mn': 'DOUBLE'
            }}
        )
    """)

    con.execute(f"""
        CREATE OR REPLACE VIEW loan_categories AS
        SELECT * FROM read_csv(
            '{CATEGORIES_CSV}',
            header = true,
            columns = {{
                'series_id': 'VARCHAR',
                'series_name': 'VARCHAR',
                'parent_series_id': 'VARCHAR',
                'indent_level': 'INTEGER',
                'category_role': 'VARCHAR',
                'is_leaf': 'BOOLEAN',
                'row_order': 'INTEGER'
            }}
        )
    """)
    return con


def run_queries(con):
    RESULTS_DIR.mkdir(exist_ok=True)
    results = {}
    print("=== EXECUTING SQL QUERIES ===")
    for fname in QUERY_FILES:
        sql_path = SQL_DIR / fname
        sql_text = sql_path.read_text()
        df = con.execute(sql_text).fetchdf()
        out_name = fname.replace(".sql", ".csv")
        out_path = RESULTS_DIR / out_name
        df.to_csv(out_path, index=False)
        results[fname] = df
        print(f"  {fname}: {len(df)} rows -> {out_path}")
    return results


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}" + (f" -- {detail}" if detail else ""))
    return condition


def validate(results):
    print("\n=== VALIDATION ===")
    all_ok = []

    # 1. Row counts.
    for fname, expected in EXPECTED_ROWS.items():
        actual = len(results[fname])
        all_ok.append(check(f"{fname}: row count", actual == expected,
                             f"expected {expected}, got {actual}"))

    # 2. Date coverage: every period_end column across every result must be
    #    within [MIN_DATE, MAX_DATE].
    for fname, df in results.items():
        if "period_end" in df.columns:
            dates = df["period_end"].astype(str)
            in_range = dates.between(MIN_DATE, MAX_DATE).all()
            all_ok.append(check(f"{fname}: dates within {MIN_DATE}..{MAX_DATE}", in_range))

    # 3. No hierarchy double-counting: queries that report "sector"/"category"
    #    rows must use exactly 8 business sectors / 5 consumer categories per
    #    period, never the 11 subsectors.
    q02 = results["02_business_sector_exposure_latest.sql"]
    all_ok.append(check("Query 02 uses exactly 8 business sectors", len(q02) == 8))

    q03 = results["03_business_sector_yoy_monthly.sql"]
    all_ok.append(check("Query 03 covers exactly 8 distinct sectors",
                         q03["sector_name"].nunique() == 8))

    q05 = results["05_consumer_lending_composition_monthly.sql"]
    all_ok.append(check("Query 05 covers exactly 5 distinct consumer categories",
                         q05["category_name"].nunique() == 5))

    q06 = results["06_sector_growth_contributions_latest.sql"]
    all_ok.append(check("Query 06 covers exactly 8 distinct sectors",
                         q06["sector_name"].nunique() == 8))

    # 4. Query 03: first month per sector has NULL MoM change; first 12 months
    #    per sector have NULL YoY change (never zero-filled).
    first_month_mom_null = q03.sort_values(["sector_name", "period_end"]).groupby("sector_name").head(1)["mom_abs_change_sgd_mn"].isna().all()
    all_ok.append(check("Query 03: first month per sector has NULL MoM change", first_month_mom_null))

    first_12_yoy_null = q03.sort_values(["sector_name", "period_end"]).groupby("sector_name").head(12)["yoy_abs_change_sgd_mn"].isna().all()
    all_ok.append(check("Query 03: first 12 months per sector have NULL YoY change", first_12_yoy_null))

    # 5. Query 07: all 62 months pass the published-rounding tolerance.
    q07 = results["07_monthly_reconciliation.sql"]
    n_fail = (q07["overall_reconciliation_status"] != "PASS").sum()
    all_ok.append(check("Query 07: all 62 months reconcile within S$0.2M tolerance",
                         n_fail == 0, f"{n_fail} failing month(s)" if n_fail else ""))

    # 6. Anchor values vs Stage 2 findings.
    q01 = results["01_portfolio_overview_monthly.sql"].sort_values("period_end")
    first_row = q01.iloc[0]
    last_row = q01.iloc[-1]

    latest_date_str = pd.Timestamp(last_row["period_end"]).strftime("%Y-%m-%d")
    all_ok.append(check(
        "Anchor: latest date is 2026-08-31",
        latest_date_str == MAX_DATE,
        f"got {latest_date_str}"
    ))
    all_ok.append(check(
        "Anchor: total loans 2021-07-31 = S$793,275.6M",
        abs(first_row["total_loans_sgd_mn"] - ANCHORS["total_loans_2021-07-31"]) < 0.05,
        f"got {first_row['total_loans_sgd_mn']}"
    ))
    all_ok.append(check(
        "Anchor: total loans 2026-08-31 = S$966,432.7M",
        abs(last_row["total_loans_sgd_mn"] - ANCHORS["total_loans_2026-08-31"]) < 0.05,
        f"got {last_row['total_loans_sgd_mn']}"
    ))
    all_ok.append(check(
        "Anchor: latest total-loan YoY growth ~13.47%",
        abs(last_row["total_yoy_pct_change"] - ANCHORS["latest_yoy_pct_approx"]) < 0.05,
        f"got {last_row['total_yoy_pct_change']}"
    ))

    q04 = results["04_business_sector_concentration_monthly.sql"].sort_values("period_end")
    latest_conc = q04.iloc[-1]
    all_ok.append(check(
        "Anchor: top-3 concentration 2026-08-31 ~76.87%",
        abs(latest_conc["top_3_share_pct"] - ANCHORS["top3_concentration_2026-08-31_pct_approx"]) < 0.05,
        f"got {latest_conc['top_3_share_pct']}"
    ))

    q06_by_sector = q06.set_index("sector_name")
    fin_ins = q06_by_sector[q06_by_sector.index.str.contains("Financial And Insurance")].iloc[0]
    all_ok.append(check(
        "Anchor: Financial And Insurance Activities 12m change = +S$23,150.1M",
        abs(fin_ins["abs_change_12m_sgd_mn"] - ANCHORS["financial_insurance_12m_change"]) < 0.05,
        f"got {fin_ins['abs_change_12m_sgd_mn']}"
    ))

    agri = q06_by_sector[q06_by_sector.index.str.contains("Agriculture")].iloc[0]
    all_ok.append(check(
        "Anchor: Agriculture, Mining And Quarrying 12m % growth ~+41.65%",
        abs(agri["pct_change_12m"] - ANCHORS["agri_mining_12m_pct_approx"]) < 0.05,
        f"got {agri['pct_change_12m']}"
    ))

    others = q06_by_sector[q06_by_sector.index.str.contains("Others")].iloc[0]
    all_ok.append(check(
        "Anchor: Others business sector 12m change = -S$850.6M",
        abs(others["abs_change_12m_sgd_mn"] - ANCHORS["others_12m_change"]) < 0.05,
        f"got {others['abs_change_12m_sgd_mn']}"
    ))

    # 7. Query 06 cross-check: sum of sector 12m changes should reconcile with
    #    the business total's own 12m change, within rounding tolerance.
    sector_change_sum = q06["abs_change_12m_sgd_mn"].sum()
    business_total_change = q06["business_total_12m_change_sgd_mn"].iloc[0]
    diff = abs(sector_change_sum - business_total_change)
    all_ok.append(check(
        "Query 06: sum of sector 12m changes reconciles with business total 12m change",
        diff <= ROUNDING_TOLERANCE_MN + EPS,
        f"sector sum = {sector_change_sum:.1f}, business total change = {business_total_change:.1f}, diff = {diff:.4f}"
    ))

    n_pass = sum(all_ok)
    print(f"\n{n_pass}/{len(all_ok)} validation checks passed.")
    if n_pass != len(all_ok):
        raise RuntimeError(
            f"{len(all_ok) - n_pass} validation check(s) FAILED -- see [FAIL] lines above."
        )


def main():
    con = setup_connection()
    results = run_queries(con)
    validate(results)
    print("\nAll SQL queries executed and validated successfully.")


if __name__ == "__main__":
    main()
