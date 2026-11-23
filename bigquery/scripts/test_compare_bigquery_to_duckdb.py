"""
Tests for compare_bigquery_to_duckdb.py.

Run from the repository root:
    python -m unittest bigquery/scripts/test_compare_bigquery_to_duckdb.py -v

The real BigQuery exports (bigquery/results/) and the DuckDB reference files
(results/) are only ever read. Every deliberate corruption is applied to a
temporary copy of the exports that is deleted afterwards.
"""

import csv
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compare_bigquery_to_duckdb as cmp  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
BQ_DIR = REPO / "bigquery" / "results"
REF_DIR = REPO / "results"

Q01 = "01_portfolio_overview_monthly"
Q02 = "02_business_sector_exposure_latest"
Q03 = "03_business_sector_yoy_monthly"
Q06 = "06_sector_growth_contributions_latest"
Q07 = "07_monthly_reconciliation"
KEYS = {s: k for s, k, _ in cmp.QUERIES}
ROWS = {s: n for s, _, n in cmp.QUERIES}


class ClassifyTests(unittest.TestCase):
    def test_numbers_that_differ_are_never_exact(self):
        self.assertEqual(cmp.classify("34.32", "0", 2), cmp.MISMATCH)
        self.assertEqual(cmp.classify("0.2", "0", 1), cmp.MISMATCH)
        self.assertEqual(cmp.classify("0", "999", 0), cmp.MISMATCH)
        self.assertEqual(cmp.classify("1", "0", 0), cmp.MISMATCH)
        self.assertEqual(cmp.classify("0", "1", 0), cmp.MISMATCH)
        self.assertEqual(cmp.classify("1", "2", 0), cmp.MISMATCH)  # whole-number column: no tolerance

    def test_non_numeric_text_never_matches_a_number(self):
        self.assertEqual(cmp.classify("0", "nonsense", 0), cmp.MISMATCH)
        self.assertEqual(cmp.classify("12.5", "nan", 1), cmp.MISMATCH)
        self.assertEqual(cmp.classify("12.5", "inf", 1), cmp.MISMATCH)

    def test_boolean_columns(self):
        self.assertEqual(cmp.classify("True", "true", 0, is_boolean=True), cmp.EXACT)
        self.assertEqual(cmp.classify("False", "FALSE", 0, is_boolean=True), cmp.EXACT)
        self.assertEqual(cmp.classify("true", "false", 0, is_boolean=True), cmp.MISMATCH)
        self.assertEqual(cmp.classify("false", "nonsense", 0, is_boolean=True), cmp.MISMATCH)
        self.assertEqual(cmp.classify("true", "1", 0, is_boolean=True), cmp.MISMATCH)
        self.assertEqual(cmp.classify("false", "0", 0, is_boolean=True), cmp.MISMATCH)

    def test_formatting_only_differences_are_exact(self):
        self.assertEqual(cmp.classify("0.0", "0", 1), cmp.EXACT)
        self.assertEqual(cmp.classify("-0.0", "0", 1), cmp.EXACT)
        self.assertEqual(cmp.classify("793275.6", "793275.600000000", 1), cmp.EXACT)
        self.assertEqual(cmp.classify("PASS", "PASS", 0), cmp.EXACT)
        self.assertEqual(cmp.classify("PASS", "FAIL", 0), cmp.MISMATCH)

    def test_null_handling(self):
        self.assertEqual(cmp.classify("", "", 1), cmp.EXACT)
        self.assertEqual(cmp.classify("", "0", 1), cmp.MISMATCH)
        self.assertEqual(cmp.classify("0", "", 1), cmp.MISMATCH)
        self.assertEqual(cmp.classify("", "false", 0, is_boolean=True), cmp.MISMATCH)

    def test_rounding_threshold_is_review_not_pass(self):
        self.assertEqual(cmp.classify("13.47", "13.48", 2), cmp.ROUNDING)
        self.assertEqual(cmp.classify("966432.7", "966432.8", 1), cmp.ROUNDING)
        self.assertEqual(cmp.classify("13.47", "13.49", 2), cmp.MISMATCH)


class RealExportTests(unittest.TestCase):
    def test_real_exports_all_pass(self):
        for stem, keys, n in cmp.QUERIES:
            with self.subTest(query=stem):
                status, lines = cmp.compare_query(stem, keys, n, BQ_DIR, REF_DIR)
                self.assertEqual(status, "PASS", lines)
                self.assertIn("0 rounding differences, 0 mismatches", " ".join(lines))


class MutationTests(unittest.TestCase):
    """Each test corrupts a temporary copy of the real exports."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for f in BQ_DIR.glob("*.csv"):
            shutil.copy(f, self.tmp / f.name)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # helpers --------------------------------------------------------------
    def edit(self, stem, fn):
        path = self.tmp / f"{stem}.csv"
        with open(path, newline="") as f:
            rows = list(csv.reader(f))
        fn(rows)
        with open(path, "w", newline="") as f:
            csv.writer(f).writerows(rows)

    def status(self, stem):
        return cmp.compare_query(stem, KEYS[stem], ROWS[stem], self.tmp, REF_DIR)[0]

    def find(self, rows, col, value):
        i = rows[0].index(col)
        for r in rows[1:]:
            if r[i] == value:
                return r, i
        raise AssertionError(f"{value!r} not found in {col}")

    # numeric ----------------------------------------------------------------
    def test_34_32_to_0_fails(self):
        def f(rows):
            r, i = self.find(rows, "contribution_to_business_change_pct", "34.32"); r[i] = "0"
        self.edit(Q06, f)
        self.assertEqual(self.status(Q06), "FAIL")

    def test_0_2_to_0_fails(self):
        def f(rows):
            r, i = self.find(rows, "diff_business_total_vs_8_sectors_sgd_mn", "-0.2"); r[i] = "0"
        self.edit(Q07, f)
        self.assertEqual(self.status(Q07), "FAIL")

    def test_0_to_999_fails(self):
        def f(rows):
            i = rows[0].index("diff_total_vs_business_plus_consumer_sgd_mn")
            r = next(r for r in rows[1:] if r[i] == "0"); r[i] = "999"
        self.edit(Q07, f)
        self.assertEqual(self.status(Q07), "FAIL")

    def test_whole_number_rank_changed_fails(self):
        def f(rows):
            i = rows[0].index("sector_rank"); rows[1][i] = "2"
        self.edit(Q02, f)
        self.assertEqual(self.status(Q02), "FAIL")

    def test_small_difference_within_rounding_threshold_is_review(self):
        def f(rows):
            i = rows[0].index("total_yoy_pct_change"); rows[-1][i] = "13.48"  # reference 13.47
        self.edit(Q01, f)
        self.assertEqual(self.status(Q01), "REVIEW")

    def test_rounding_difference_plus_real_mismatch_fails(self):
        def f(rows):
            i = rows[0].index("total_yoy_pct_change"); rows[-1][i] = "13.48"
            j = rows[0].index("total_loans_sgd_mn"); rows[-1][j] = "966433.9"
        self.edit(Q01, f)
        self.assertEqual(self.status(Q01), "FAIL")

    # Boolean ------------------------------------------------------------------
    def test_invalid_boolean_text_fails(self):
        def f(rows):
            i = rows[0].index("total_check_within_tolerance"); rows[1][i] = "nonsense"
        self.edit(Q07, f)
        self.assertEqual(self.status(Q07), "FAIL")

    def test_true_to_false_fails(self):
        def f(rows):
            i = rows[0].index("business_check_within_tolerance"); rows[1][i] = "false"
        self.edit(Q07, f)
        self.assertEqual(self.status(Q07), "FAIL")

    def test_boolean_capitalisation_is_accepted(self):
        def f(rows):
            for name in ("total_check_within_tolerance", "business_check_within_tolerance", "consumer_check_within_tolerance"):
                i = rows[0].index(name)
                for r in rows[1:]:
                    r[i] = r[i].capitalize()  # true -> True
        self.edit(Q07, f)
        self.assertEqual(self.status(Q07), "PASS")

    def test_numeric_0_1_in_boolean_column_fails(self):
        def f(rows):
            i = rows[0].index("total_check_within_tolerance"); rows[1][i] = "1"
        self.edit(Q07, f)
        self.assertEqual(self.status(Q07), "FAIL")

    # formatting -----------------------------------------------------------------
    def test_trailing_zero_and_signed_zero_are_accepted(self):
        def f(rows):
            i = rows[0].index("diff_total_vs_business_plus_consumer_sgd_mn")
            for r in rows[1:]:
                if r[i] == "0":
                    r[i] = "-0.0"
            j = rows[0].index("diff_business_total_vs_8_sectors_sgd_mn")
            for r in rows[1:]:
                if r[j] == "0.1":
                    r[j] = "0.10000"
        self.edit(Q07, f)
        self.assertEqual(self.status(Q07), "PASS")

    def test_numeric_0_0_written_as_0_is_accepted(self):
        def f(rows):
            r = rows[1]; i = rows[0].index("diff_total_vs_business_plus_consumer_sgd_mn")
            r[i] = "0.0" if r[i] == "0" else r[i]
        self.edit(Q07, f)
        self.assertEqual(self.status(Q07), "PASS")

    # NULL handling --------------------------------------------------------------
    def test_null_replaced_by_value_or_value_blanked_fails(self):
        def f(rows):
            i = rows[0].index("prev_month_balance_sgd_mn"); rows[1][i] = "0"  # was empty (first month)
        self.edit(Q03, f)
        self.assertEqual(self.status(Q03), "FAIL")

        def g(rows):
            i = rows[0].index("balance_sgd_mn"); rows[5][i] = ""
        self.edit(Q03, g)
        self.assertEqual(self.status(Q03), "FAIL")

    # structure ------------------------------------------------------------------
    def test_missing_field_fails(self):
        self.edit(Q01, lambda rows: rows[3].pop())
        self.assertEqual(self.status(Q01), "FAIL")

    def test_extra_field_fails(self):
        self.edit(Q01, lambda rows: rows[3].append("extra"))
        self.assertEqual(self.status(Q01), "FAIL")

    def test_duplicate_column_header_fails(self):
        def f(rows):
            rows[0][2] = rows[0][1]
        self.edit(Q01, f)
        status, lines = cmp.compare_query(Q01, KEYS[Q01], ROWS[Q01], self.tmp, REF_DIR)
        self.assertEqual(status, "FAIL")
        self.assertIn("duplicate column", " ".join(lines))

    def test_reordered_columns_fail(self):
        def f(rows):
            for r in rows:
                r[1], r[2] = r[2], r[1]
        self.edit(Q01, f)
        self.assertEqual(self.status(Q01), "FAIL")

    def test_renamed_column_fails(self):
        def f(rows):
            rows[0][3] = "consumer_total"
        self.edit(Q01, f)
        self.assertEqual(self.status(Q01), "FAIL")

    def test_reordered_rows_fail(self):
        self.edit(Q03, lambda rows: rows.__setitem__(slice(2, 4), [rows[3], rows[2]]))
        self.assertEqual(self.status(Q03), "FAIL")

    def test_wrong_date_or_category_fails(self):
        def f(rows):
            rows[5][0] = "2021-12-30"
        self.edit(Q01, f)
        self.assertEqual(self.status(Q01), "FAIL")

        def g(rows):
            i = rows[0].index("sector_name"); rows[2][i] += "X"
        self.edit(Q02, g)
        self.assertEqual(self.status(Q02), "FAIL")

    def test_missing_and_extra_rows(self):
        self.edit(Q01, lambda rows: rows.pop())
        self.assertEqual(self.status(Q01), "FAIL")
        self.edit(Q07, lambda rows: rows.append(rows[-1]))
        self.assertEqual(self.status(Q07), "FAIL")

    def test_missing_file_is_reported(self):
        (self.tmp / f"{Q02}.csv").unlink()
        self.assertEqual(self.status(Q02), "MISSING")


class ReadOnlyTests(unittest.TestCase):
    def test_real_files_unchanged_by_a_comparison(self):
        before = {p: p.read_bytes() for p in list(BQ_DIR.glob("*.csv")) + list(REF_DIR.glob("*.csv"))}
        for stem, keys, n in cmp.QUERIES:
            cmp.compare_query(stem, keys, n, BQ_DIR, REF_DIR)
        for p, data in before.items():
            self.assertEqual(p.read_bytes(), data)


if __name__ == "__main__":
    unittest.main()
