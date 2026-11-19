"""
Stage 2 cleaning script for Portfolio 03.

Reads the official PRIMARY dataset (Commercial Banks: Loans And Advances To
Residents By Industry, data.gov.sg dataset d_af0415517a3a3a94b3b74039934ef976)
and reshapes it into two simple, analysis-ready CSVs:

  - data/processed/loan_categories.csv  (one row per DataSeries / category)
  - data/processed/loan_balances_long.csv (one row per category x month)

The hierarchy in the source file is encoded only by leading-whitespace
indentation in the "DataSeries" column (0 / 4 / 8 / 12 spaces). This script
parses that indentation into explicit parent_series_id links using a stack
that walks the rows top-to-bottom, so it does not depend on fixed hardcoded
row positions (row N is never assumed to mean a specific category). It does
depend on the source file's own ordering convention: each row's parent must
appear somewhere above it before any of its children (standard pre-order tree
layout), which holds for this dataset as published.

All reported figures are END-OF-PERIOD STOCK BALANCES in S$ million. They
are never summed across months, and subtotal rows are never added to their
own children.
"""

import csv
import re
from datetime import date
from calendar import monthrange

import pandas as pd

RAW_PATH = "data/raw/loans_advances_by_industry_d_af0415517a3a3a94b3b74039934ef976.csv"
CATEGORIES_OUT = "data/processed/loan_categories.csv"
BALANCES_OUT = "data/processed/loan_balances_long.csv"

EXPECTED_SERIES = 27
EXPECTED_MONTHS = 62
EXPECTED_OBS = EXPECTED_SERIES * EXPECTED_MONTHS
ROUNDING_TOLERANCE_MN = 0.2  # S$ million, per Stage 1 published-rounding findings
FLOAT_EPSILON = 1e-6  # absorbs binary float64 summation noise, not a data tolerance

MONTH_ABBR_TO_NUM = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


def slugify(label):
    """Deterministic, human-readable id derived only from the category label."""
    s = label.strip().lower()
    s = s.replace("&", "and")
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def month_col_to_period_end(col):
    """'2026Aug' -> date(2026, 8, 31) (last calendar day of the month)."""
    year = int(col[:4])
    mon = MONTH_ABBR_TO_NUM[col[4:]]
    last_day = monthrange(year, mon)[1]
    return date(year, mon, last_day)


def load_raw():
    with open(RAW_PATH, newline="") as f:
        rows = list(csv.reader(f))
    header, data_rows = rows[0], rows[1:]
    month_cols = header[1:]
    return header, month_cols, data_rows


def build_category_dimension(data_rows):
    """Parse indentation into series_id / parent_series_id / role / is_leaf."""
    raw_labels = [row[0] for row in data_rows]
    indent_levels = [len(lbl) - len(lbl.lstrip(" ")) for lbl in raw_labels]
    series_names = [lbl.strip() for lbl in raw_labels]
    series_ids = [slugify(name) for name in series_names]

    if len(set(series_ids)) != len(series_ids):
        raise ValueError("Duplicate series_id generated from DataSeries labels; check source file.")

    # Parent assignment via indentation stack (pre-order tree traversal).
    parent_ids = []
    role_by_id = {}
    stack = []  # (indent_level, series_id)
    for name, sid, indent in zip(series_names, series_ids, indent_levels):
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent_id = stack[-1][1] if stack else None
        parent_ids.append(parent_id)

        if indent == 0:
            role = "total"
        elif indent == 4:
            if name.startswith("Loans To Businesses"):
                role = "business_total"
            elif name.startswith("Consumer Loans"):
                role = "consumer_total"
            else:
                role = "other"
        elif indent == 8:
            parent_role = role_by_id.get(parent_id)
            if parent_role == "business_total":
                role = "business_sector"
            elif parent_role == "consumer_total":
                role = "consumer_category"
            else:
                role = "other"
        elif indent == 12:
            role = "business_subsector"
        else:
            role = "other"

        role_by_id[sid] = role
        stack.append((indent, sid))

    parent_id_set = {p for p in parent_ids if p is not None}
    is_leaf = [sid not in parent_id_set for sid in series_ids]

    categories = pd.DataFrame({
        "series_id": series_ids,
        "series_name": series_names,
        "parent_series_id": parent_ids,
        "indent_level": indent_levels,
        "category_role": [role_by_id[sid] for sid in series_ids],
        "is_leaf": is_leaf,
        "row_order": range(len(series_ids)),
    })
    return categories


def build_long_balances(month_cols, data_rows, categories):
    period_ends = [month_col_to_period_end(c).isoformat() for c in month_cols]
    records = []
    for sid, row in zip(categories["series_id"], data_rows):
        values = row[1:]
        for period_end, raw_val in zip(period_ends, values):
            records.append((period_end, sid, float(raw_val)))
    long_df = pd.DataFrame(records, columns=["period_end", "series_id", "balance_sgd_mn"])
    long_df = long_df.sort_values(["series_id", "period_end"]).reset_index(drop=True)
    return long_df


def reconcile(long_df, categories, child_role, parent_role, label):
    """Sum children of a given role under each parent and compare to the parent's own balance."""
    cat_by_id = categories.set_index("series_id")
    children = categories[categories["category_role"] == child_role]
    wide = long_df.pivot(index="period_end", columns="series_id", values="balance_sgd_mn")

    max_abs_diff = 0.0
    max_month = None
    checked_parents = sorted(children["parent_series_id"].dropna().unique())
    for parent_id in checked_parents:
        if cat_by_id.loc[parent_id, "category_role"] != parent_role:
            continue
        child_ids = children.loc[children["parent_series_id"] == parent_id, "series_id"]
        child_sum = wide[child_ids].sum(axis=1)
        diff = (wide[parent_id] - child_sum).abs()
        m = diff.max()
        if m > max_abs_diff:
            max_abs_diff = m
            max_month = diff.idxmax()
    passed = max_abs_diff <= ROUNDING_TOLERANCE_MN + FLOAT_EPSILON
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {label}: max |diff| = {max_abs_diff:.4f} (at {max_month}), tolerance = {ROUNDING_TOLERANCE_MN}")
    return passed


def run_validation(long_df, categories, data_rows, month_cols):
    print("\n=== VALIDATION ===")
    results = []

    # 1. Exactly 1,674 long-format observations.
    ok = len(long_df) == EXPECTED_OBS
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] 1. Observation count: {len(long_df)} (expected {EXPECTED_OBS})")

    # 2. Exactly 27 unique series.
    n_series = categories["series_id"].nunique()
    ok = n_series == EXPECTED_SERIES
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] 2. Unique series: {n_series} (expected {EXPECTED_SERIES})")

    # 3. Exactly 62 consecutive months.
    periods = pd.to_datetime(sorted(long_df["period_end"].unique()))
    expected_periods = pd.date_range(start=periods[0], periods=EXPECTED_MONTHS, freq="ME")
    ok = len(periods) == EXPECTED_MONTHS and list(periods) == list(expected_periods)
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] 3. Consecutive months: {len(periods)} found, "
          f"{periods.min().date()} to {periods.max().date()}")

    # 4. No duplicate (period_end, series_id) keys.
    dup_count = long_df.duplicated(subset=["period_end", "series_id"]).sum()
    ok = dup_count == 0
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] 4. Duplicate keys: {dup_count}")

    # 5. No missing or nonnumeric balances.
    missing = long_df["balance_sgd_mn"].isna().sum()
    is_numeric = pd.api.types.is_numeric_dtype(long_df["balance_sgd_mn"])
    ok = missing == 0 and is_numeric
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] 5. Missing/non-numeric balances: {missing} missing, numeric dtype={is_numeric}")

    # 6. No unexpected negative balances.
    neg_count = (long_df["balance_sgd_mn"] < 0).sum()
    ok = neg_count == 0
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] 6. Negative balances: {neg_count}")

    # 7. All series_id in long format reference valid dimension entries.
    valid_ids = set(categories["series_id"])
    orphan_ids = set(long_df["series_id"]) - valid_ids
    ok = len(orphan_ids) == 0
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] 7. Long-format series_id validity: {len(orphan_ids)} unmatched")

    # 8. All parent_series_id reference valid dimension entries.
    non_null_parents = categories["parent_series_id"].dropna()
    bad_parents = set(non_null_parents) - valid_ids
    ok = len(bad_parents) == 0
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] 8. Parent id validity: {len(bad_parents)} unmatched")

    # 9. Business sector totals reconcile to business lending total within tolerance.
    ok = reconcile(long_df, categories, "business_sector", "business_total",
                    "9. Business sectors sum to business total")
    results.append(ok)

    # 10. Consumer categories reconcile to consumer lending total within tolerance.
    ok = reconcile(long_df, categories, "consumer_category", "consumer_total",
                    "10. Consumer categories sum to consumer total")
    results.append(ok)

    # 11. Business + consumer totals reconcile to overall total within tolerance.
    wide = long_df.pivot(index="period_end", columns="series_id", values="balance_sgd_mn")
    total_id = categories.loc[categories["category_role"] == "total", "series_id"].iloc[0]
    biz_id = categories.loc[categories["category_role"] == "business_total", "series_id"].iloc[0]
    cons_id = categories.loc[categories["category_role"] == "consumer_total", "series_id"].iloc[0]
    diff = (wide[total_id] - (wide[biz_id] + wide[cons_id])).abs()
    ok = diff.max() <= ROUNDING_TOLERANCE_MN + FLOAT_EPSILON
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] 11. Business + consumer = total: max |diff| = {diff.max():.4f} "
          f"(at {diff.idxmax()}), tolerance = {ROUNDING_TOLERANCE_MN}")

    # 12. Cleaned numerical observations match their original source cells exactly.
    orig_wide = pd.DataFrame(
        {sid: [float(v) for v in row[1:]] for sid, row in zip(categories["series_id"], data_rows)},
        index=[month_col_to_period_end(c).isoformat() for c in month_cols],
    )
    orig_wide.index.name = "period_end"
    reshaped_wide = long_df.pivot(index="period_end", columns="series_id", values="balance_sgd_mn")
    orig_wide = orig_wide.reindex(index=reshaped_wide.index, columns=reshaped_wide.columns)
    max_cell_diff = (orig_wide - reshaped_wide).abs().max().max()
    ok = max_cell_diff == 0
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] 12. Reshape integrity vs raw source cells: max |diff| = {max_cell_diff}")

    n_pass = sum(results)
    print(f"\n{n_pass}/{len(results)} validation checks passed.")
    if n_pass != len(results):
        raise RuntimeError(
            f"{len(results) - n_pass} validation check(s) FAILED, see [FAIL] lines above. "
            "Processed output was written but must not be used until this is resolved."
        )
    return results


def main():
    header, month_cols, data_rows = load_raw()
    print(f"Loaded raw file: {RAW_PATH}")
    print(f"  {len(data_rows)} DataSeries rows, {len(month_cols)} month columns")

    categories = build_category_dimension(data_rows)
    long_df = build_long_balances(month_cols, data_rows, categories)

    categories.to_csv(CATEGORIES_OUT, index=False)
    long_df.to_csv(BALANCES_OUT, index=False)
    print(f"\nWrote {CATEGORIES_OUT} ({len(categories)} rows)")
    print(f"Wrote {BALANCES_OUT} ({len(long_df)} rows)")

    print("\nCategory role counts:")
    print(categories["category_role"].value_counts().to_string())

    run_validation(long_df, categories, data_rows, month_cols)


if __name__ == "__main__":
    main()
