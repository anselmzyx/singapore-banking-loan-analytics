# Stage 1: Data Inspection Report

**Project:** Singapore Banking Loan Portfolio & Sector Exposure Analytics
**Retrieval date:** 2026-11-09
**Status:** Setup and raw inspection only. No cleaning, EDA, SQL, or dashboard work performed.

## 1. Dataset Inventory

| | Primary | Supporting |
|---|---|---|
| Name | Commercial Banks: Loans And Advances To Residents By Industry (End Of Period), Monthly | Commercial Banks: Assets And Liabilities (End Of Period), Monthly |
| Dataset ID | `d_af0415517a3a3a94b3b74039934ef976` | `d_f357c61441e2850ca4eae05813ebd37b` |
| Catalog page | https://data.gov.sg/datasets/d_af0415517a3a3a94b3b74039934ef976/view | https://data.gov.sg/datasets/d_f357c61441e2850ca4eae05813ebd37b/view |
| Published by | Singapore Dept. of Statistics (data steward); source data from Monetary Authority of Singapore (MAS) | Same |
| Adapted from | https://tablebuilder.singstat.gov.sg/table/TS/M701091 | https://tablebuilder.singstat.gov.sg/table/TS/M701131 |
| Retrieval method | Official data.gov.sg v1 Dataset API (`initiate-download` → presigned S3 CSV URL) | Same |
| Local file | `data/raw/loans_advances_by_industry_d_af0415517a3a3a94b3b74039934ef976.csv` | `data/raw/assets_liabilities_d_f357c61441e2850ca4eae05813ebd37b.csv` |
| File size | 15,319 bytes | 21,361 bytes |
| SHA-256 | `d1976fd2ab77f1f382044a5a5246292d7c3aa236bf6bb74f0f1b8bb19f53490b` | `c6eee9207eab9bf3ff6c2083ded2b9fbfce790e513075a9a4bd17a74f37ed3a5` |
| Source format | Original CSV (not a JSON fallback) | Original CSV (not a JSON fallback) |
| Dataset `lastUpdatedAt` (per API metadata) | 2026-10-14 | 2026-10-14 |

**Licence:** Not returned as an explicit field by the dataset metadata API. data.gov.sg's site-wide Terms of Service govern reuse; no per-dataset licence string was present in the retrieved metadata, so none is asserted here beyond what the catalog pages state.

Both files were downloaded unchanged via data.gov.sg's documented `initiate-download`/poll flow (`GET https://api-open.data.gov.sg/v1/public/api/datasets/{datasetId}/initiate-download`, which returned a presigned S3 URL serving the dataset's original CSV export directly; no manual poll step was needed since the file was generated immediately). Raw files are to be treated as immutable for all later stages.

## 2. Dimensions and Coverage

| | Primary | Supporting |
|---|---|---|
| Rows (DataSeries) | **27** | **35** |
| Columns | 1 label column + **62 monthly columns** | 1 label column + **62 monthly columns** |
| Coverage | Jul 2021 – Aug 2026 (62 consecutive months) | Jul 2021 – Aug 2026 (62 consecutive months, identical month set) |
| Catalog claim (~27 series / 62 periods / 35 series) | **Confirmed** | **Confirmed** |

Both datasets' month-column sets are **identical** (same 62 labels, `2021Jul`…`2026Aug`), so time alignment between the two files is not a concern.

## 3. Units and Measure Type

- All numeric cells in both files are denominated in **Million Dollars** (SGD), per column metadata.
- Every reported figure is an **end-of-period stock balance**, that is, the outstanding balance on the last day of each month, not a flow (new originations) or a rate. Values must not be summed across months as if they were period flows.
- No non-numeric placeholders, blanks, or text markers (e.g. `-`, `n.a.`, `..`) were found in any of the 62 month columns across either file; both datasets are fully populated with numeric values for every DataSeries × month cell (no missing observations).
- No duplicate `DataSeries` labels were found in either file.

## 4. Category Hierarchy

Both CSVs encode a parent/child hierarchy via **leading whitespace indentation** in the `DataSeries` label (not a separate column). This must be respected when aggregating: summing a parent row together with its own children will double-count.

### Primary (Loans & Advances by Industry): 27 rows, 4 indentation levels (0, 4, 8, 12 spaces)

```
Total Loans And Advances Including Bills Financing                     (indent 0: grand total)
  Loans To Businesses - Total                                          (indent 4)
    Agriculture, Mining And Quarrying - Total                         (indent 8)
      Agriculture And Fishing / Mining And Quarrying                  (indent 12)
    Manufacturing                                                      (indent 8, leaf)
    Building And Construction - Total → Construction / Real Property  (indent 8 → 12)
    General Commerce - Total → Wholesale / Retail / Accommodation&Food (indent 8 → 12)
    Transport, Storage And Communication - Total → Transport&Storage / Info&Comms (indent 8 → 12)
    Financial And Insurance Activities                                 (indent 8, leaf)
    Professional/Scientific/Technical/Admin Support Services           (indent 8, leaf)
    Others - Total → Electricity Gas Water / Other Industries          (indent 8 → 12)
  Consumer Loans - Total                                                (indent 4)
    Housing And Bridging Loans / Car Loans / Credit Cards /
    Share Financing / Others                                            (indent 8, leaves)
```

**August 2026 spot check:** `Loans To Businesses - Total + Consumer Loans - Total = Total Loans` exactly (diff = 0.0), and each group's "Total" row equals the sum of its immediate children within ±S$0.1M.

**Full 62-month check (Jul 2021–Aug 2026), max absolute residual per additive group:**

| Parent total | Max |diff| across 62 months | Month of max |
|---|---|---|
| Total Loans = Loans To Businesses Total + Consumer Loans Total | S$0.1M | 2023Mar |
| Loans To Businesses Total = sum of 8 sub-sector rows | **S$0.2M** | 2025Dec |
| Consumer Loans Total = sum of 5 consumer sub-rows | **S$0.2M** | 2021Jul |
| Agriculture/Mining Total = Agri&Fishing + Mining&Quarrying | S$0.1M | 2026Jan |
| Building&Construction Total = Construction + Real Property | S$0.1M | 2026May |
| General Commerce Total = Wholesale + Retail + Accommodation&Food | S$0.1M | 2026Mar |
| Transport/Storage/Comms Total = Transport&Storage + Info&Comms | S$0.1M | 2026Aug |
| Others Total = Electricity/Gas/Water + Other Industries | S$0.1M | 2025Jul |

All residuals are consistent with the dataset's published 1-decimal-place (S$0.1M) rounding: individual month-end balances are each rounded before publication, so sums of 2–8 rounded components can differ from an independently rounded total by up to roughly half a rounding unit per component. These are **not data errors** and should be treated as expected rounding noise, not evidence against the hierarchy. **Subtotal and total rows must not be added to their own children in any analysis.**

### Supporting (Assets & Liabilities): 35 rows, two parallel hierarchies plus one orphan memo row

```
Total Assets                                                            (indent 0)
  Cash And Balances → Of Which: Cash And Balances With MAS              (indent 4 → 8)
  Loans And Advances Incl. Bills Financing - Total                      (indent 4)
    Of Which: Trade Finance / Resident / Non-Resident /
    Bills Discounted (Payable In / Outside Singapore)                   (indent 8, leaves: overlapping "of which" breakdowns)
  Securities And Equities Issued By Private Entities - Total            (indent 4)
    Debt Securities (In/Outside SG) / Equity Investments (In/Outside SG) (indent 8)
  Debt Securities By Government Related Entities - Total                (indent 4)
    Govt of SG / Public Sector Entities / Other Governments             (indent 8)
  Amounts Receivable From Banks - Total → In/Outside Singapore          (indent 4 → 8)
  Other Assets → Of Which: Loans To SPVs For Covered Bond Issuances     (indent 4 → 8)

Assets - Securities And Equities                                        (indent 0: MEMO ROW, see below)

Total Liabilities                                                       (indent 0)
  Capital And Reserves                                                  (indent 4, leaf)
  Deposits And Balances Of Non-Bank Customers - Total                   (indent 4)
    Demand / Fixed / Savings / Other Deposits                           (indent 8)
  Amounts Payable To Banks - Total → In/Outside Singapore               (indent 4 → 8)
  Other Liabilities                                                     (indent 4, leaf)
```

Verified for 2026Aug:
- `Total Assets` = exact sum of its 6 indent-4 children (diff = 0.0).
- `Total Liabilities` = exact sum of its 4 indent-4 children (diff = 0.0).
- **Balance-sheet identity holds exactly:** `Total Assets = Total Liabilities` (both 4,072,085.2 for 2026Aug).
- The row **"Assets - Securities And Equities"** (index 23) sits at indent 0 between the asset and liability blocks but is **not** part of either total's child set. It was found to equal `Securities And Equities Issued By Private Entities - Total + Debt Securities By Government Related Entities - Total` (869,565.8 ≈ 274,801.5 + 594,764.2, within rounding). **This is a cross-cutting memo/summary row, not an independent total: including it alongside the main hierarchy in any sum would double-count securities exposure.**
- The "Loans And Advances" block's "of which" rows (Trade Finance, Resident, Non-Resident, Bills Discounted In/Outside SG) are **not mutually exclusive categorisations at the same level**. Trade Finance is a cross-cutting "of which" memo rather than a sibling to Resident/Non-Resident. This sub-hierarchy should be treated cautiously; it was not used in this project's primary calculations.

## 5. Reporting Changes and Historical Comparability

Both datasets' footnotes state: *"Data have been revised from July 2021 following changes to the MAS Notices 610 and 1003. The previous series have been discontinued and can be found on the MAS Website."*

- This matches the observed coverage start of **July 2021** exactly, confirming the current CSV exports contain **only the post-revision series**, with no silent concatenation of the discontinued pre-2021 series.
- No other in-sample reporting breaks or methodology changes were identified within the 62-month window; all cells are numeric and populated throughout.
- **Implication for later stages:** the ~62-month window is a hard lower bound for historical analysis using this reporting basis. Do not attempt to extend the time series backward using the discontinued MAS series without separately validating definitional comparability; this project does not do so.

## 6. Cross-Source Comparability (Primary vs. Supporting)

The two datasets share identical month coverage (62/62 months, Jul 2021–Aug 2026). An initial single-row comparison (Primary `Total Loans` vs. Supporting's `Loans And Advances - Resident` sub-row alone) shows an apparent ~S$19.8B gap for 2026Aug. That gap is **fully explained** once the Supporting dataset's resident-bills component is included, and is not evidence that the two datasets are unreconcilable.

**Reconciliation check:** `Primary Total Loans And Advances Including Bills Financing = Supporting "Loans And Advances - Resident" + Supporting "Bills Discounted Or Purchased - Payable In Singapore"`

| 2026Aug (S$M) | Value |
|---|---|
| Supporting: `Loans And Advances - Resident` | 946,656.2 |
| Supporting: `Bills Discounted Or Purchased - Payable In Singapore` | 19,776.5 |
| Sum | 966,432.7 |
| Primary: `Total Loans And Advances Including Bills Financing` | 966,432.7 |
| Difference | 0.0 |

This reconciliation was independently re-derived from the raw CSVs using exact `Decimal` arithmetic (not floating-point) and checked across **all 62 months**, not just 2026Aug:
- **Maximum absolute difference across all 62 months: S$0.1M.**
- **43 of 62 months reconcile exactly (diff = 0.0); the remaining 19 months differ by ±S$0.1M**, consistent with the datasets' published 1-decimal-place rounding and not indicative of a definitional break.
- The 19 non-exact months: 2021Sep, 2021Nov, 2021Dec, 2022Jul, 2022Aug, 2022Sep, 2022Oct, 2023Jan, 2023Mar, 2023May, 2023Nov, 2023Dec, 2024Jan, 2024Feb, 2024May, 2024Nov, 2024Dec, 2025Apr, 2026Jul.

**Interpretation:** this establishes a **numerical reconciliation** between the Primary total and a specific two-row combination from the Supporting dataset. It is not proof that the two datasets' underlying definitions, reporting populations, or methodologies are completely identical in every respect (e.g., the Supporting dataset's broader "Loans And Advances Including Bills Financing - Total" of 1,521,912.8 for 2026Aug also includes non-resident loans and bills payable outside Singapore, which fall outside the Primary dataset's resident-lending scope and are correctly excluded from this reconciliation). The reconciliation shows the two datasets are **consistent with each other** where their scopes overlap; it does not establish that every row or total in the Supporting dataset maps onto the Primary dataset.

**Conclusion: the two datasets are numerically consistent where they overlap, but this project still does not merge them or compute ongoing cross-source ratios.** The reconciliation above is a one-time structural validation, not an analysis deliverable. The Supporting dataset continues to be retained only for contextual/inspection purposes, per the original task scope.

## 7. Recommendation: Can the Primary Dataset Alone Support the Project?

**Yes.** The Primary dataset (27 series, 62 months, fully populated, internally consistent, single well-documented reporting basis since Jul 2021) is sufficient on its own to support at least five substantive business questions, e.g.:

1. Which business sectors hold the largest share of bank loan exposure, and how has that composition shifted since Jul 2021?
2. How has consumer lending (housing/bridging, cars, credit cards) evolved in share relative to total consumer loans?
3. Which sectors show the fastest/slowest month-over-month or year-over-year growth in outstanding loan balances?
4. How concentrated is bank lending across industries (e.g. concentration/HHI-style measures) and has concentration risk increased or decreased?
5. What is the relative balance between business lending and consumer lending over time, and how did it move around notable periods (e.g. interest-rate cycles) within the 2021–2026 window?

All five are answerable using stock-balance comparisons, shares-of-total, and growth rates **within** the Primary dataset's own hierarchy. None require merging with the Supporting dataset or reconstructing pre-2021 history.

## 8. Blockers

**None identified.** Both datasets downloaded successfully as original, complete CSVs with verified dimensions matching the public catalog's stated counts; no missing observations, no fabricated/truncated data, and the key structural risks (subtotal double-counting, the orphan "Assets - Securities And Equities" memo row, and the published 1-decimal rounding noise affecting some additive subtotals) are documented above for later stages to respect. The Primary and Supporting datasets reconcile numerically where their scopes overlap (Section 6), but this project still treats them as separate sources and does not merge them.
