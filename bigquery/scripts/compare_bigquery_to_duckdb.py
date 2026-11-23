"""
Compare BigQuery query exports against the DuckDB reference results.

Reads the seven CSVs exported from BigQuery (default: bigquery/results/) and
compares each one with the matching reference file in results/ (the DuckDB
outputs). It only reads files: nothing is written, and nothing in results/ is
changed.

For every query it checks:
  1. that both files are well-formed CSV (no duplicate column names, and every
     row has exactly as many fields as the header),
  2. the row count,
  3. the column names and their order,
  4. the key columns (same records, same order),
  5. every other value.

How values are compared:
  - Boolean columns are named explicitly (BOOLEAN_COLUMNS below). Only the
    words true/false are accepted, in any capitalisation ("True" equals
    "true"). Anything else in a Boolean column is a mismatch.
  - Every other column is compared as an exact Decimal when both values are
    numbers (so "0.0" equals "0" and "-0.0" equals "0", but 0 never equals
    34.32), and as exact text otherwise (dates, category names, PASS/FAIL).
  - An empty field is NULL. NULL equals only NULL.

Each value is classified as:
  - exact: identical after the normalisation above;
  - rounding: a numeric difference no larger than one unit in the last decimal
    place the reference file shows for that column (only for columns that show
    at least one decimal place; whole-number columns must match exactly).
    This is flagged for manual review and is never counted as a pass;
  - mismatch: anything else.

A query is PASS only if every value is exact. It is REVIEW if there are
rounding differences but no mismatches, and FAIL if anything else differs.

Usage (from the repository root):
    python bigquery/scripts/compare_bigquery_to_duckdb.py
    python bigquery/scripts/compare_bigquery_to_duckdb.py --bq-dir path/to/exports

Requires only the Python standard library.
"""

import argparse
import csv
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

# (file stem, key columns, expected rows)
QUERIES = [
    ("01_portfolio_overview_monthly", ["period_end"], 62),
    ("02_business_sector_exposure_latest", ["sector_name"], 8),
    ("03_business_sector_yoy_monthly", ["period_end", "sector_name"], 496),
    ("04_business_sector_concentration_monthly", ["period_end"], 62),
    ("05_consumer_lending_composition_monthly", ["period_end", "category_name"], 310),
    ("06_sector_growth_contributions_latest", ["sector_name"], 8),
    ("07_monthly_reconciliation", ["period_end"], 62),
]

# The only Boolean columns in the seven outputs.
BOOLEAN_COLUMNS = {
    "07_monthly_reconciliation": {
        "total_check_within_tolerance",
        "business_check_within_tolerance",
        "consumer_check_within_tolerance",
    },
}

EXACT = "exact"
ROUNDING = "rounding"
MISMATCH = "mismatch"


class CsvFormatError(Exception):
    """Raised when a CSV file is malformed."""


def read_csv(path):
    """Read a CSV into (header, rows-as-dicts), rejecting malformed input."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            raise CsvFormatError(f"{path.name}: file is empty") from None
        if any(h.strip() == "" for h in header):
            raise CsvFormatError(f"{path.name}: header contains an empty column name")
        duplicates = sorted({h for h in header if header.count(h) > 1})
        if duplicates:
            raise CsvFormatError(f"{path.name}: duplicate column name(s) {duplicates}")
        rows = []
        for row in reader:
            if len(row) != len(header):
                raise CsvFormatError(
                    f"{path.name}: line {reader.line_num} has {len(row)} fields, "
                    f"expected {len(header)}"
                )
            rows.append(dict(zip(header, row)))
    return header, rows


def parse_bool(value):
    """Return True/False for 'true'/'false' (any case), else None."""
    v = value.strip().lower()
    if v == "true":
        return True
    if v == "false":
        return False
    return None


def parse_decimal(value):
    """Return a finite Decimal, or None if the text is not a finite number."""
    v = value.strip()
    if v == "":
        return None
    try:
        d = Decimal(v)
    except InvalidOperation:
        return None
    return d if d.is_finite() else None


def decimals_of(value):
    v = value.strip()
    return len(v.split(".")[1]) if "." in v else 0


def classify(ref_val, bq_val, ref_decimals, is_boolean=False):
    """Return 'exact', 'rounding' or 'mismatch' for one pair of cell values."""
    r, b = ref_val.strip(), bq_val.strip()

    # NULL equals only NULL.
    if r == "" or b == "":
        return EXACT if r == b else MISMATCH

    if is_boolean:
        rb, bb = parse_bool(r), parse_bool(b)
        if rb is None or bb is None:
            return MISMATCH  # not a valid Boolean in a Boolean column
        return EXACT if rb == bb else MISMATCH

    rd, bd = parse_decimal(r), parse_decimal(b)
    if rd is not None and bd is not None:
        if rd == bd:
            return EXACT
        if ref_decimals >= 1 and abs(rd - bd) <= Decimal(1).scaleb(-ref_decimals):
            return ROUNDING
        return MISMATCH

    # At least one side is not a number: compare as exact text.
    return EXACT if r == b else MISMATCH


def compare_query(stem, keys, expected_rows, bq_dir, ref_dir):
    ref_path, bq_path = ref_dir / f"{stem}.csv", bq_dir / f"{stem}.csv"
    if not bq_path.exists():
        return "MISSING", [f"no export found at {bq_path}"]
    try:
        ref_header, ref_rows = read_csv(ref_path)
        bq_header, bq_rows = read_csv(bq_path)
    except CsvFormatError as e:
        return "FAIL", [f"malformed CSV: {e}"]
    problems, notes = [], []

    if len(bq_rows) != expected_rows:
        problems.append(f"row count {len(bq_rows)} != expected {expected_rows}")
    if len(bq_rows) != len(ref_rows):
        problems.append(f"row count {len(bq_rows)} != reference {len(ref_rows)}")
    if bq_header != ref_header:
        problems.append(f"column names or order differ: BigQuery {bq_header} vs reference {ref_header}")
        return "FAIL", problems

    ref_keys = [tuple(r[k] for k in keys) for r in ref_rows]
    bq_keys = [tuple(r[k] for k in keys) for r in bq_rows]
    if ref_keys != bq_keys:
        problems.append("key columns differ (different records or different row order)")
        return "FAIL", problems

    bool_cols = BOOLEAN_COLUMNS.get(stem, set())
    ref_dec = {c: max((decimals_of(r[c]) for r in ref_rows), default=0) for c in ref_header}
    counts = {EXACT: 0, ROUNDING: 0, MISMATCH: 0}
    for rr, br, key in zip(ref_rows, bq_rows, ref_keys):
        for c in ref_header:
            if c in keys:
                continue
            outcome = classify(rr[c], br[c], ref_dec[c], is_boolean=(c in bool_cols))
            counts[outcome] += 1
            if outcome != EXACT and len(notes) < 10:
                notes.append(f"{outcome}: key={key} column={c} reference={rr[c]!r} bigquery={br[c]!r}")
    if counts[MISMATCH]:
        problems.append(f"{counts[MISMATCH]} value mismatches")
    status = "FAIL" if problems else ("REVIEW" if counts[ROUNDING] else "PASS")
    summary = (f"{counts[EXACT]} exact, {counts[ROUNDING]} rounding differences, "
               f"{counts[MISMATCH]} mismatches")
    return status, problems + [summary] + notes


def headline_values(bq_dir):
    """Read the headline figures from the BigQuery exports (not from the reference)."""
    out = {}
    try:
        _, rows = read_csv(bq_dir / "01_portfolio_overview_monthly.csv")
        last = rows[-1]
        out["latest month"] = last["period_end"]
        out["total loans (S$M)"] = last["total_loans_sgd_mn"]
        out["total loans (S$B)"] = str(Decimal(last["total_loans_sgd_mn"]) / 1000)
        out["total YoY growth (%)"] = last["total_yoy_pct_change"]
    except Exception as e:  # noqa: BLE001
        out["query 01 headline"] = f"unavailable ({e})"
    try:
        _, rows = read_csv(bq_dir / "04_business_sector_concentration_monthly.csv")
        out["top-3 concentration (%)"] = rows[-1]["top_3_share_pct"]
    except Exception as e:  # noqa: BLE001
        out["query 04 headline"] = f"unavailable ({e})"
    return out


def main():
    repo = Path(__file__).resolve().parents[2]
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--bq-dir", type=Path, default=repo / "bigquery" / "results")
    p.add_argument("--ref-dir", type=Path, default=repo / "results")
    args = p.parse_args()

    overall = []
    for stem, keys, n in QUERIES:
        status, lines = compare_query(stem, keys, n, args.bq_dir, args.ref_dir)
        overall.append(status)
        print(f"[{status}] {stem}")
        for line in lines:
            print(f"        {line}")

    print("\nHeadline values read from the BigQuery exports:")
    for k, v in headline_values(args.bq_dir).items():
        print(f"  {k}: {v}")

    if all(s == "PASS" for s in overall):
        print("\nRESULT: all seven BigQuery exports match the DuckDB reference results.")
        return 0
    print("\nRESULT: not fully verified - see the lines above "
          "(MISSING = not exported yet, REVIEW = rounding differences to inspect, FAIL = real difference).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
