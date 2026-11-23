# BigQuery implementation of the SQL analysis

This folder re-implements the project's seven DuckDB SQL queries in GoogleSQL so they run on Google BigQuery, plus a data-validation query and a script that checks the BigQuery output against the existing DuckDB results.

> **Verification status:** all seven analytical queries were run in BigQuery and their exported results match the DuckDB reference results in `results/` (details in [Verification](#verification)).

The BigQuery work is an additional implementation. It does not replace the Python preparation, the DuckDB queries in `sql/`, the reference results in `results/`, or the Power BI dashboard, and it introduces no new analysis or headline figures.

## Why BigQuery was added

DuckDB runs locally on the processed CSVs and is the project's original SQL implementation and reference. BigQuery is a cloud data warehouse. Re-running the same logic there shows that the analysis is not tied to one engine, and checking its output against the DuckDB results gives a cross-platform validation that the SQL logic and the headline figures reproduce. Power BI remains the project's primary dashboard.

## How it differs from DuckDB here

| | DuckDB (`sql/`, `results/`) | BigQuery (`bigquery/`) |
|---|---|---|
| Where it runs | Locally, in memory, via `scripts/run_sql_analysis.py` | Google Cloud, in the BigQuery web console or `bq` CLI |
| Balance type | `DOUBLE` | `NUMERIC` (exact decimal) |
| Table references | Local views over the CSVs | Fully qualified `project.dataset.table` |
| Role | Original implementation and reference results | Re-implementation validated against the reference |

## Google Cloud structure used

The BigQuery sandbox tables are temporary (see [Known limitations](#known-limitations)).

| Item | Value |
|---|---|
| Project ID | `singapore-banking-analytics` |
| Dataset | `banking_analytics` |
| Location | `asia-southeast1` (Singapore) |
| Environment | BigQuery sandbox (no billing) |

Two tables, loaded from this repository's processed CSVs:

**`loan_balances_long`** (from `data/processed/loan_balances_long.csv`, 1,674 rows)

| Column | Type |
|---|---|
| `period_end` | DATE |
| `series_id` | STRING |
| `balance_sgd_mn` | NUMERIC |

**`loan_categories`** (from `data/processed/loan_categories.csv`, 27 rows)

| Column | Type |
|---|---|
| `series_id` | STRING |
| `series_name` | STRING |
| `parent_series_id` | STRING |
| `indent_level` | INTEGER |
| `category_role` | STRING |
| `is_leaf` | BOOLEAN |
| `row_order` | INTEGER |

The balance column must be `NUMERIC`. Query 07 compares exact sums with the documented S$0.2M tolerance and would give wrong results on a floating-point column (see [Implementation differences](#bigquery-specific-implementation-differences)).

## Reproducing this in your own project

You do not need access to the original Google account.

1. Create a Google Cloud project and enable the BigQuery sandbox (no billing needed).
2. Create a dataset named `banking_analytics` in a location of your choice.
3. Load the two CSVs from `data/processed/`:

   **Console:** Create table, source "Upload", format CSV, header rows to skip = 1, and enter the schemas above (balances as `NUMERIC`).

   **`bq` CLI** (from the repository root; replace `YOUR_PROJECT`):
   ```bash
   bq --project_id=YOUR_PROJECT --location=asia-southeast1 load \
     --source_format=CSV --skip_leading_rows=1 --replace \
     banking_analytics.loan_balances_long data/processed/loan_balances_long.csv \
     period_end:DATE,series_id:STRING,balance_sgd_mn:NUMERIC

   bq --project_id=YOUR_PROJECT --location=asia-southeast1 load \
     --source_format=CSV --skip_leading_rows=1 --replace \
     banking_analytics.loan_categories data/processed/loan_categories.csv \
     series_id:STRING,series_name:STRING,parent_series_id:STRING,indent_level:INTEGER,category_role:STRING,is_leaf:BOOLEAN,row_order:INTEGER
   ```
4. The SQL files reference `` `singapore-banking-analytics.banking_analytics.<table>` ``. In a different project, replace `singapore-banking-analytics` with your project ID. Each file uses the two table names only in its first two CTEs (`balances` and `dim`), so there are two lines to change per file.

## Running the queries

Run `sql/00_data_validation.sql` first. Every row of its output should read `PASS`. It checks row counts, unique IDs, month coverage, duplicate month-category pairs, missing values, invalid parent references, unmatched IDs, and the category-role counts the analysis depends on.

Then run the seven analytical queries, `01` to `07`. All are read-only `SELECT` statements over about 1,700 rows, so they stay well inside the free sandbox.

**Console:** open a file, paste it into the query editor, confirm the processing location matches your dataset, and run it. Use **Save results → CSV (local file)** and save the file under the *same name as the SQL file*, with a `.csv` extension, in `bigquery/results/`, for example `bigquery/results/01_portfolio_overview_monthly.csv`.

**`bq` CLI** (from the repository root):
```bash
mkdir -p bigquery/results
for f in bigquery/sql/0[1-7]_*.sql; do
  n=$(basename "$f" .sql)
  bq --project_id=YOUR_PROJECT query --use_legacy_sql=false --format=csv --max_rows=1000 < "$f" > "bigquery/results/$n.csv"
done
```

Only save outputs from queries that have actually run.

## Validating against DuckDB

```bash
python bigquery/scripts/compare_bigquery_to_duckdb.py
```

For each query it first checks that both CSV files are well formed (no duplicate column names, every row has the same number of fields as the header), then the row count, the column names and order, the key columns (same records in the same order), and every other value. It reports each query as `PASS`, `REVIEW`, `FAIL`, or `MISSING`, and it prints the headline values read from the BigQuery exports. `REVIEW` means the only differences are numeric differences of no more than one unit in the last decimal place of a column that shows decimals; these are never counted as a pass and should be inspected by hand. It uses only the Python standard library and never writes to `results/`.

Formatting differences are accepted: trailing zeros, `true` versus `True` in the three Boolean columns of Query 07, and a signed zero (`-0.0` versus `0`). Boolean columns are named explicitly and accept only `true` or `false`; every other column is compared as an exact decimal when both values are numbers (so zero and one are ordinary numbers) and as exact text otherwise. The script rejects any change in row count, column name or order, key column (date or category), row order, missing-value pattern or Boolean value, and it rejects a malformed CSV (a row with too many or too few fields, or a duplicate column name).

A difference should be classified before it is accepted: a formatting or type difference, a rounding-boundary difference, or a real calculation difference. Do not change a tolerance or a definition to make a comparison pass.

## BigQuery-specific implementation differences

- **Table references:** fully qualified and backticked (the project ID contains hyphens), read through two CTEs.
- **Joins:** explicit `ON` clauses instead of `USING`.
- **Conditional aggregation:** `MAX(IF(...))` in place of `MAX(CASE WHEN ...)`. Both are valid GoogleSQL, and `IF` is shorter.
- **`NUMERIC` arithmetic:** percentages are written `(x * 100) / NULLIF(y, 0)`. The exact product is divided once, then rounded, so rounding is applied to an exact decimal rather than a binary float. This is algebraically the same calculation as the DuckDB version. `NUMERIC` division returns a value rounded to nine decimal places, far finer than the two decimals reported.
- **Query 07 tolerance:** the documented S$0.2M tolerance is unchanged. The DuckDB query adds an epsilon of 1e-6 solely to absorb floating-point noise (a true 0.2 summing to 0.2000000000698). With exact `NUMERIC` sums the comparison is `<= NUMERIC '0.2'` and needs no epsilon. In a local test on floating-point data, an exact `0.2` comparison wrongly failed seven months, so a `FLOAT64` balance column would break this check.
- **NULL handling:** unchanged. Windows are partitioned by category and ordered by `period_end`; the first one or twelve months stay `NULL`; the 12-month lookbacks are computed on the full history before any filtering to the latest month.
- **Hierarchy:** only the eight `business_sector` rows and the five `consumer_category` rows are summed; parent totals and the eleven `business_subsector` rows are never added to their parents.

## Verification

Two kinds of evidence are kept separate here.

**1. Query results compared with DuckDB (evidence stored in this repository).** I ran the seven analytical queries in BigQuery and exported each result to `bigquery/results/`. These are real BigQuery outputs, not copies of the DuckDB files. `compare_bigquery_to_duckdb.py` compared each export with the matching file in `results/`:

| Query | Rows | Columns | Result |
|---|---|---|---|
| 01 Portfolio overview, monthly | 62 | 10 | PASS |
| 02 Business sector exposure, latest | 8 | 5 | PASS |
| 03 Business sector 12-month change, monthly | 496 | 9 | PASS |
| 04 Top-three concentration, monthly | 62 | 4 | PASS |
| 05 Consumer lending composition, monthly | 310 | 5 | PASS |
| 06 Sector growth contributions, latest | 8 | 7 | PASS |
| 07 Monthly hierarchy reconciliation | 62 | 8 | PASS |

Every non-key value matched exactly (5,660 values across the seven files), and the key columns (dates and category names) matched in the same row order. The only differences are in how the files are written: BigQuery omits trailing `.0`, writes Booleans as `true` and `false`, and writes zero without a sign. The headline values read from the BigQuery exports are total loans S$966,432.7M (S$966.4B), 13.47% year-on-year growth and 76.87% top-three business sector concentration at August 2026.

The comparison script has its own tests (`bigquery/scripts/test_compare_bigquery_to_duckdb.py`, run with `python -m unittest bigquery/scripts/test_compare_bigquery_to_duckdb.py`). They re-run the real comparison and then deliberately corrupt temporary copies of the exports: changed numbers (including to and from zero), invalid and flipped Boolean values, NULL changes, a missing or extra field, a duplicate column name, reordered columns and rows, wrong dates and categories, missing and extra rows and a missing file. Each corruption is detected, while the formatting differences above are accepted. The real exports and the reference files are never modified.

**Query 07 tolerance.** All 62 months return `PASS` and all 186 component checks are within tolerance. I recomputed the three differences for every month from the source CSVs in exact decimal arithmetic: they agree with the BigQuery export, and the largest absolute difference is S$0.2M. Fourteen component differences are exactly S$0.2M, on the threshold itself, so they pass only because the comparison is inclusive and exact (`<= NUMERIC '0.2'`, with no floating-point noise). This also confirms that the balance column behaves as exact `NUMERIC`.

**2. Data validation (reported, not stored).** I ran `sql/00_data_validation.sql` in BigQuery and all 23 checks returned `PASS`. The output of that run is not saved in this repository, so this result rests on my own run; anyone reproducing the project can run the same file against their own tables.

**Local logic check before the BigQuery run.** The SQL files were also parsed with a BigQuery-dialect parser, transpiled to DuckDB and run with fixed-point balances; this matched the DuckDB results and passed all 23 validation checks. It was a development check only, not BigQuery execution.

## Known limitations

- **Temporary tables:** BigQuery sandbox tables expire automatically (after 60 days by default), so the cloud tables in `singapore-banking-analytics.banking_analytics` will not exist permanently. The durable record is in this repository: the processed CSVs in `data/processed/`, the SQL in `bigquery/sql/`, the load commands above, the exported results in `bigquery/results/` and the comparison script. Recreating the tables takes only a few minutes.
- **Single dataset:** the analysis covers the one MAS lending dataset, July 2021 to August 2026, as described in the main README.
- **Manual execution:** the queries were run by hand in the BigQuery console; there is no scheduled or automated BigQuery pipeline.
- **Validation output not stored:** the result of `00_data_validation.sql` is reported but not saved in the repository.
- **Same descriptive scope:** concentration and contribution are balance-composition statistics, not credit-risk measures.

## Files

```
bigquery/
  README.md                              this guide
  sql/00_data_validation.sql             integrity checks on the two tables
  sql/01 ... 07_*.sql                    GoogleSQL ports of the seven DuckDB queries
  scripts/compare_bigquery_to_duckdb.py  compares BigQuery exports with results/
  scripts/test_compare_bigquery_to_duckdb.py  tests for the comparison script
  results/                               BigQuery exports of queries 01-07 (real BigQuery output)
```
