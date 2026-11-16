# Power BI Build Guide — Singapore Banking Loan Portfolio & Sector Exposure

**Status:** Model design, DAX measures, and dashboard specification only. **No PBIX has been created and no dashboard has been built.** This guide is for manual construction in Power BI Desktop after independent review. DAX formulas below have been checked for logical correctness against the approved Stage 2/3 outputs using Python, but **have not been executed inside Power BI** — final validation must happen there (see Section 5).

---

## 1. Data Model

### 1.1 Tables and files

| Power BI table name | Source file | Role |
|---|---|---|
| `FactLoans` | `data/processed/loan_balances_long.csv` (imported directly, unchanged) | Fact table |
| `DimCategory` | `powerbi/dim_category.csv` | Category dimension |
| `DimMonth` | `powerbi/dim_month.csv` | Month dimension |

### 1.2 Column data types

**FactLoans**
| Column | Power BI type |
|---|---|
| `period_end` | Date |
| `series_id` | Text |
| `balance_sgd_mn` | Decimal number |

**DimCategory**
| Column | Power BI type |
|---|---|
| `series_id` | Text |
| `series_name` | Text |
| `parent_series_id` | Text |
| `indent_level` | Whole number |
| `category_role` | Text |
| `is_leaf` | True/False |
| `row_order` | Whole number |
| `display_name` | Text |

**DimMonth**
| Column | Power BI type |
|---|---|
| `period_end` | Date |
| `year` | Whole number |
| `month_number` | Whole number |
| `month_name` | Text |
| `year_month` | Text |
| `year_month_sort` | Whole number |
| `month_index` | Whole number |

### 1.3 Relationships

Exactly two relationships, both **one-to-many, single direction (dimension → fact), Active**:

1. `DimMonth[period_end]` (1) → `FactLoans[period_end]` (*)
2. `DimCategory[series_id]` (1) → `FactLoans[series_id]` (*)

No other relationships exist. **Bidirectional / many-to-many filtering is not needed**: every report visual filters FROM the two dimensions INTO the fact table (slicers and axes are always built from `DimMonth`/`DimCategory` fields), and no measure needs a fact-table selection to filter back into a dimension. Turning on bidirectional filtering here would only add ambiguity risk (e.g. a selected category appearing to filter the month dimension) with no analytical benefit.

### 1.4 Columns to hide from Report view

**Build order matters here: do this step LAST, after Pages 1 and 2 are fully built (Section 4, steps 6–7), not as part of initial model setup.** Several of the columns below — most importantly `DimMonth[period_end]` — are needed directly on visuals (it is the X-axis field for the historical line charts: Page 1 visual 4 and Page 2 visual 5). If hidden too early, it will not be draggable onto those visuals from the field list. Keep every column visible while constructing visuals; only hide the technical/non-report-facing ones once both pages are finished and validated (Section 4, step 8).

Once both pages are built, hide these from Report view (they remain usable inside DAX and for the `Sort by Column` settings in 1.6 regardless of visibility):

- `DimCategory`: `series_id`, `parent_series_id`, `series_name`, `row_order`, `indent_level` (keep `display_name` and `category_role` visible — `category_role` is useful for building/debugging visuals even though end users will mostly use pre-built measures).
- `DimMonth`: `year_month_sort`, `month_index` (needed only for DAX and sort-by-column, never dragged onto a visual directly). **Do not hide `period_end`** — it stays visible permanently, since it is the axis field for the two historical line charts; only `year_month_sort` and `month_index` are truly report-invisible technical columns.
- `FactLoans`: hide the whole table from Report view except where needed for troubleshooting — all analysis should go through measures, not raw `balance_sgd_mn` drags.

### 1.5 Slicer fields

- `DimMonth[year]` — single-select or multi-select slicer for year.
- `DimMonth[year_month]` — slicer or dropdown for a specific month (sorted chronologically, see 1.6).
- `DimCategory[category_role]` — useful as a page-level filter to constrain a visual to `business_sector` or `consumer_category` only (prevents accidentally mixing subsector rows into a sector-level chart).
- `DimCategory[display_name]` — for sector/category selection within Page 2 visuals.

**Incompatible Year + Year-Month combinations:** `year` and `year_month` are two independent slicers on the same `DimMonth` table. If a user selects a `year` value and then a `year_month` value that belongs to a *different* year (e.g. `year = 2022` plus `year_month = 2023-05`), the two filters intersect to zero rows of `DimMonth` — every measure on the page will show blank, not an error, and not a misleading zero. This is expected Power BI slicer behavior, not a model defect. If every visual on a page suddenly goes blank, check for this first: clear one of the two slicers (or use the slicer's "Clear selection" icon) so the `year` and `year_month` selections refer to the same period again.

### 1.6 Sorting `year_month` chronologically

`year_month` (e.g. `"2021-07"`) happens to sort correctly alphabetically, but set this explicitly anyway so the behavior isn't accidental: select the `DimMonth[year_month]` column → **Column tools → Sort by Column → `year_month_sort`**. Do the same for `DimMonth[month_name]` → **Sort by Column → `month_number`** (so month name slicers/legends read January…December, not alphabetically).

### 1.7 `DimMonth` is a Period table, not a Date table

`DimMonth` has exactly 62 rows — one per reported month-end — not one row per calendar day. **Do not mark it as a Date table** (Power BI's Model view → table → "Mark as date table" option), and **do not use time-intelligence functions that assume a contiguous daily calendar** (`SAMEPERIODLASTYEAR`, `DATEADD`, `PREVIOUSMONTH`, `TOTALYTD`, etc.) against it — these silently assume every day exists, which this table does not, and would produce wrong or blank results in ways that are easy to miss.

Instead, every time-comparison measure in this guide uses the explicit `DimMonth[month_index]` (1…62, one per row, already in strict chronological order) to look up "the previous row" or "the row 12 periods back" via `CALCULATE` + `REMOVEFILTERS(DimMonth)` + an exact `month_index` match. This is simple, always correct for this specific monthly grain, and transparent to audit.

**Also disable Power BI's automatic date/time tables** for this file: *File → Options and settings → Options → Data Load → uncheck "Auto date/time" (both Global and Current File)*. Auto date/time would otherwise silently generate hidden calendar hierarchies behind `period_end` in both `FactLoans` and `DimMonth`, which is unnecessary here (we already have `DimMonth`) and can make the relationship/field list confusing.

---

## 2. DAX Measures

All measures below are the single authoritative version — no conflicting duplicates exist elsewhere in this project. Create them in a dedicated **measures table** (e.g. a small disconnected table named `_Measures`) or directly inside `FactLoans`, whichever the builder prefers; grouping by the headings below (as Display Folders) is recommended.

### 2.0 Helper measures

```DAX
Current Month Index =
MAX ( DimMonth[month_index] )
```

```DAX
Prev Month Period End =
VAR CurrentIndex = [Current Month Index]
RETURN
CALCULATE (
    MAX ( DimMonth[period_end] ),
    REMOVEFILTERS ( DimMonth ),
    DimMonth[month_index] = CurrentIndex - 1
)
```

```DAX
Prev 12M Period End =
VAR CurrentIndex = [Current Month Index]
RETURN
CALCULATE (
    MAX ( DimMonth[period_end] ),
    REMOVEFILTERS ( DimMonth ),
    DimMonth[month_index] = CurrentIndex - 12
)
```

`Prev Month Period End` / `Prev 12M Period End` return **BLANK** whenever `CurrentIndex - 1` or `CurrentIndex - 12` falls outside 1…62 (e.g. the first month, or the first 12 months) — there is no row to find, so `CALCULATE(MAX(...))` over an empty filtered table returns BLANK automatically. Nothing needs to zero-fill this; downstream measures check `ISBLANK(...)` explicitly where it matters.

### 2.1 CORE

**1. Outstanding Balance at Selected Month (S$M)**
```DAX
Outstanding Balance at Selected Month (S$M) =
VAR SelectedPeriodEnd = MAX ( DimMonth[period_end] )
RETURN
CALCULATE (
    SUM ( FactLoans[balance_sgd_mn] ),
    FactLoans[period_end] = SelectedPeriodEnd
)
```
This is the foundational pattern every other balance measure below specializes: pin to the single latest `period_end` visible in the current context (so a Year filter never causes 12 months to be summed together), then let whatever `DimCategory` filter is already in context apply. **Used directly only where the surrounding visual already guarantees an unambiguous, non-additive category selection** (e.g. one row per leaf category in a table). For anything that must be safe regardless of category selection, use measures 2–4 instead.

**2. Total Loans (S$M)**
```DAX
Total Loans (S$M) =
VAR SelectedPeriodEnd = MAX ( DimMonth[period_end] )
RETURN
CALCULATE (
    SUM ( FactLoans[balance_sgd_mn] ),
    REMOVEFILTERS ( DimCategory ),
    DimCategory[category_role] = "total",
    FactLoans[period_end] = SelectedPeriodEnd
)
```

**3. Business Loans (S$M)**
```DAX
Business Loans (S$M) =
VAR SelectedPeriodEnd = MAX ( DimMonth[period_end] )
RETURN
CALCULATE (
    SUM ( FactLoans[balance_sgd_mn] ),
    REMOVEFILTERS ( DimCategory ),
    DimCategory[category_role] = "business_total",
    FactLoans[period_end] = SelectedPeriodEnd
)
```

**4. Consumer Loans (S$M)**
```DAX
Consumer Loans (S$M) =
VAR SelectedPeriodEnd = MAX ( DimMonth[period_end] )
RETURN
CALCULATE (
    SUM ( FactLoans[balance_sgd_mn] ),
    REMOVEFILTERS ( DimCategory ),
    DimCategory[category_role] = "consumer_total",
    FactLoans[period_end] = SelectedPeriodEnd
)
```

Measures 2–4 deliberately `REMOVEFILTERS(DimCategory)` before re-applying their own `category_role` filter — so even if a report page also has a sector slicer selected, these three KPIs always show the true reported total/business/consumer figures, never a value scoped down to whatever sector happens to be selected elsewhere.

**5. Business Share (%)**
```DAX
Business Share (%) =
DIVIDE ( [Business Loans (S$M)], [Total Loans (S$M)] )
```

**6. Consumer Share (%)**
```DAX
Consumer Share (%) =
DIVIDE ( [Consumer Loans (S$M)], [Total Loans (S$M)] )
```

### 2.2 GROWTH

**7. Total Loans Previous Month (S$M)**
```DAX
Total Loans Previous Month (S$M) =
VAR PriorPeriodEnd = [Prev Month Period End]
RETURN
IF (
    ISBLANK ( PriorPeriodEnd ),
    BLANK (),
    CALCULATE (
        [Total Loans (S$M)],
        REMOVEFILTERS ( DimMonth ),
        DimMonth[period_end] = PriorPeriodEnd
    )
)
```

**8. Total MoM Growth (%)**
```DAX
Total MoM Growth (%) =
DIVIDE (
    [Total Loans (S$M)] - [Total Loans Previous Month (S$M)],
    [Total Loans Previous Month (S$M)]
)
```

**9. Total Loans 12M Ago (S$M)**
```DAX
Total Loans 12M Ago (S$M) =
VAR PriorPeriodEnd = [Prev 12M Period End]
RETURN
IF (
    ISBLANK ( PriorPeriodEnd ),
    BLANK (),
    CALCULATE (
        [Total Loans (S$M)],
        REMOVEFILTERS ( DimMonth ),
        DimMonth[period_end] = PriorPeriodEnd
    )
)
```

**10. Total YoY Growth (%)**
```DAX
Total YoY Growth (%) =
DIVIDE (
    [Total Loans (S$M)] - [Total Loans 12M Ago (S$M)],
    [Total Loans 12M Ago (S$M)]
)
```

`DIVIDE()` returns BLANK whenever the denominator is BLANK or 0 — so measures 8 and 10 are automatically BLANK for the first month / first 12 months, with no risk of a false zero.

### 2.3 SECTOR ANALYSIS

**11. Business Sector Balance (S$M)**
```DAX
Business Sector Balance (S$M) =
VAR SelectedPeriodEnd = MAX ( DimMonth[period_end] )
RETURN
CALCULATE (
    SUM ( FactLoans[balance_sgd_mn] ),
    FactLoans[period_end] = SelectedPeriodEnd,
    DimCategory[category_role] = "business_sector"
)
```
Unlike measures 2–4, this one does **not** `REMOVEFILTERS(DimCategory)` — it is meant to work together with whatever sector selection a visual already provides (axis, legend, slicer), while the `category_role = "business_sector"` filter acts as a safety net: if a subsector's `display_name` is ever accidentally dropped onto a "sector" visual, this measure returns BLANK for that row instead of silently including an 11-subsector double-count.

**12. Business Sector Share (%)**
```DAX
Business Sector Share (%) =
DIVIDE ( [Business Sector Balance (S$M)], [Business Loans (S$M)] )
```
The denominator is measure 3 (`Business Loans (S$M)`), which always forces the full reported `business_total` regardless of any sector selection — so this share's denominator never shrinks when one sector is selected (per the data model requirement).

**13. Business Sector Balance 12M Ago (S$M)**
```DAX
Business Sector Balance 12M Ago (S$M) =
VAR PriorPeriodEnd = [Prev 12M Period End]
RETURN
IF (
    ISBLANK ( PriorPeriodEnd ),
    BLANK (),
    CALCULATE (
        [Business Sector Balance (S$M)],
        REMOVEFILTERS ( DimMonth ),
        DimMonth[period_end] = PriorPeriodEnd
    )
)
```

**14. Business Sector YoY Change (S$M)**
```DAX
Business Sector YoY Change (S$M) =
IF (
    ISBLANK ( [Business Sector Balance 12M Ago (S$M)] ),
    BLANK (),
    [Business Sector Balance (S$M)] - [Business Sector Balance 12M Ago (S$M)]
)
```
The explicit `ISBLANK` guard matters here: in DAX, `X - BLANK()` evaluates to `X`, not BLANK — without the guard, a sector with no 12-months-ago value would show a "change" equal to its own current balance instead of correctly showing no value.

**15. Business Sector YoY Growth (%)**
```DAX
Business Sector YoY Growth (%) =
DIVIDE ( [Business Sector YoY Change (S$M)], [Business Sector Balance 12M Ago (S$M)] )
```

### 2.4 CONCENTRATION AND CONTRIBUTION

**16. Top-3 Business Sector Concentration (%)**
```DAX
Top-3 Business Sector Concentration (%) =
VAR SelectedPeriodEnd = MAX ( DimMonth[period_end] )
VAR SectorTable =
    CALCULATETABLE (
        ADDCOLUMNS (
            VALUES ( DimCategory[series_id] ),
            "@Balance",
                CALCULATE (
                    SUM ( FactLoans[balance_sgd_mn] ),
                    FactLoans[period_end] = SelectedPeriodEnd
                )
        ),
        REMOVEFILTERS ( DimCategory ),
        DimCategory[category_role] = "business_sector"
    )
VAR Top3Sum =
    SUMX (
        TOPN ( 3, SectorTable, [@Balance], DESC, DimCategory[series_id], ASC ),
        [@Balance]
    )
RETURN
DIVIDE ( Top3Sum, [Business Loans (S$M)] )
```
This re-ranks **all 8** business sectors independently at `SelectedPeriodEnd` every time it is evaluated (`REMOVEFILTERS(DimCategory)` first, so it is never affected by an existing sector selection elsewhere on the page), takes the 3 largest that month (`TOPN`, with `DimCategory[series_id]` as a secondary deterministic tie-break), and divides by the true `business_total` (measure 3). It never assumes the same 3 sectors stay on top.

**17. Business Loans 12M Ago (S$M)**
```DAX
Business Loans 12M Ago (S$M) =
VAR PriorPeriodEnd = [Prev 12M Period End]
RETURN
IF (
    ISBLANK ( PriorPeriodEnd ),
    BLANK (),
    CALCULATE (
        [Business Loans (S$M)],
        REMOVEFILTERS ( DimMonth ),
        DimMonth[period_end] = PriorPeriodEnd
    )
)
```

**18. Business Loans YoY Change (S$M)**
```DAX
Business Loans YoY Change (S$M) =
IF (
    ISBLANK ( [Business Loans 12M Ago (S$M)] ),
    BLANK (),
    [Business Loans (S$M)] - [Business Loans 12M Ago (S$M)]
)
```

**19. Business Sector Contribution to Business Growth (%)**
```DAX
Business Sector Contribution to Business Growth (%) =
DIVIDE ( [Business Sector YoY Change (S$M)], [Business Loans YoY Change (S$M)] )
```
This is the sector's share of the **net** 12-month change in business lending — not a share of gross growth, not originations, and not a profitability measure. `DIVIDE` permits (and this measure is expected to sometimes show) **negative values** (a sector shrinking while the total grows) **or values over 100%** (a sector grew by more than the net total change because another sector offset it). Both are legitimate, expected outputs — not errors.

### 2.5 CONSUMER ANALYSIS

**20. Consumer Category Balance (S$M)**
```DAX
Consumer Category Balance (S$M) =
VAR SelectedPeriodEnd = MAX ( DimMonth[period_end] )
RETURN
CALCULATE (
    SUM ( FactLoans[balance_sgd_mn] ),
    FactLoans[period_end] = SelectedPeriodEnd,
    DimCategory[category_role] = "consumer_category"
)
```

**21. Consumer Category Share (%)**
```DAX
Consumer Category Share (%) =
DIVIDE ( [Consumer Category Balance (S$M)], [Consumer Loans (S$M)] )
```

### 2.6 Formatting

| Measure type | Format |
|---|---|
| All `(S$M)` measures | Custom format `"S$"#,##0.0` — values are **already in S$ million** from the source data. Do **not** apply Power BI's built-in thousands/millions dynamic scaling (e.g. a `,,` suffix) on top of this, or figures will be divided by a further 1,000,000. |
| All `(%)` measures | Built-in **Percentage** format, 1–2 decimal places (e.g. `0.0%`). All percentage DAX above uses `DIVIDE()` returning a raw ratio (e.g. `0.6022`) — **never multiply by 100 in the DAX** when the field format is already Percentage, or the display will read `6022.0%`. |
| `DimMonth[year_month]` / `month_name` on axes | Text, sorted per Section 1.6 — reads as `"2021-07"` or `"July"`, not a raw date-time. |

**Display units — a separate Power BI setting from the measure's Format String, and the most common way this gets silently wrong.** Every `(S$M)` measure's underlying value is already in S$ million (e.g. `966432.7` means S$966,432.7 million). Power BI visuals (cards, chart axes, data labels) have their own independent **Display units** property — separate from the measure's custom format string above — that defaults to "Auto" and can silently re-scale a value that's already in millions by applying *another* round of Thousands/Millions/Billions scaling on top of it.

- For every card, chart axis, and data label showing an `(S$M)` measure: open **Format visual → [Callout value / Y-axis / Data labels] → Display units**, and set it explicitly to **None**. Do not leave it on "Auto."
- Label every visual title or subtitle that shows a balance with the unit explicitly, e.g. *"Total Outstanding Loans (S$ million)"* — do not rely on the axis or the measure name alone to convey the unit.
- Percentage measures are unaffected by Display units (they are not scaled the same way), but double-check each one is set to the Percentage format type (Section above), not a Decimal/General number that happens to look similar.

---

## 3. Two-Page Dashboard Specification

Short sector/category labels throughout use `DimCategory[display_name]`, never the raw `series_name`. No visual sums balances across months — every trend chart places `DimMonth[period_end]` (or `year_month`) on an axis so each point independently shows that month's measure value; no visual aggregates `balance_sgd_mn` over a date range.

### Page 1 — Banking Loan Portfolio Overview

| # | Visual | Fields / Measures | Axis / Legend | Filters required | Sort | Business question |
|---|---|---|---|---|---|---|
| 1 | Card | `Total Loans (S$M)` | — | None (whole-portfolio KPI) | — | What is the total outstanding loan book right now (or at the selected period)? |
| 2 | Card | `Total YoY Growth (%)` | — | None | — | How fast is the total loan book growing over the latest available 12 months? |
| 3 | Card x2 (or one multi-row card) | `Business Share (%)`, `Consumer Share (%)` | — | None | — | What is the business-vs-consumer split of the portfolio? |
| 4 | Line chart | `Total Loans (S$M)`, `Business Loans (S$M)`, `Consumer Loans (S$M)` | X: `DimMonth[period_end]`; Legend: the 3 measures | None (full 62-month history by default) | X axis chronological (sort by `period_end`) | How have total, business, and consumer lending evolved since Jul 2021? |
| 5 | 100% stacked column chart | `Business Loans (S$M)`, `Consumer Loans (S$M)` | X: `DimMonth[year]`; Legend: measure | None required (see interaction note below) | Chronological (`year` is already numeric/ascending) | How has the business/consumer composition shifted year over year since the start of the series? |
| 6 | Bar chart | `Consumer Category Balance (S$M)` or `Consumer Category Share (%)` | Y: `DimCategory[display_name]`; filtered to `category_role = "consumer_category"` | `DimCategory[category_role] = "consumer_category"` | Descending by balance | What does consumer lending consist of (housing, cards, car loans, etc.)? |

**Visual 5 detail — composition by year, without summing balances across months.** Placing `DimMonth[year]` on the X-axis groups the chart into one column per calendar year (2021–2026). Within each year-column's filter context, `Business Loans (S$M)` and `Consumer Loans (S$M)` already evaluate `MAX(DimMonth[period_end])` **within that year only** — i.e. the *last reported month-end in that specific year* — before pinning `FactLoans[period_end]` to exactly that one date (Section 2.1). No DAX change is required: the existing measures are already "latest month in current filter context," and `year` is just a coarser filter context than a single month. Each column therefore shows one month's balance, never a 12-month sum.

Concretely, each year's column uses:
- **2021:** Dec 2021 (last reported month that year — reporting itself only starts Jul 2021, so 2021 is a **partial-coverage year** even though its *displayed* balance is the normal December month-end).
- **2022–2025:** Dec of each year (complete calendar years, normal December month-end).
- **2026:** Aug 2026 (the latest month available as of this dataset's extract — 2026 is a **partial-coverage year** with no Sep–Dec data yet).

This partial-coverage note must appear directly on the visual (e.g. a subtitle or text box: *"2021 reflects Jul–Dec only; 2026 reflects Jan–Aug only — all other years are complete calendar years."*) so a viewer does not read 2021 or 2026 as full-year figures.

**Slicer interaction for visual 5:** because this chart's entire purpose is a full 2021–2026 comparison, it should **ignore** both page slicers rather than be filtered by them. Set **Edit interactions** (select the `DimMonth[year]` slicer → Format → Edit interactions) → visual 5 → **None**, and repeat for the `DimMonth[year_month]` slicer → visual 5 → **None**. Without this, selecting a single `year_month` value anywhere on the page would collapse `DimMonth` to one row and make every other year's column disappear from visual 5 (since a year with no remaining rows has no `MAX(period_end)` to evaluate) — breaking the full-history comparison the chart exists to show. With the interaction disabled, visual 5 always shows all 6 years regardless of what the slicers are doing to the KPI cards and line chart elsewhere on the page.

**Slicers on Page 1:** `DimMonth[year]` and `DimMonth[year_month]`, placed at the top of the page. Selecting a year or month updates the 4 KPI cards (filtering them to that period's latest available month) and the line chart's visible range; visual 5 is explicitly excluded from both slicers per the interaction note above so it always shows the full 2021–2026 comparison.

### Page 2 — Business Sector Exposure & Growth

| # | Visual | Fields / Measures | Axis / Legend | Filters required | Sort | Business question |
|---|---|---|---|---|---|---|
| 1 | Card | `Business Loans (S$M)` | — | None | — | What is the total outstanding business loan book? |
| 2 | Bar chart (horizontal) | `Business Sector Balance (S$M)` | Y: `DimCategory[display_name]` | `DimCategory[category_role] = "business_sector"` | Descending by balance | Which sectors carry the largest exposure right now? |
| 3 | Bar or donut chart | `Business Sector Share (%)` | Y/Legend: `DimCategory[display_name]` | `DimCategory[category_role] = "business_sector"` | Descending by share | What proportion of business lending does each sector represent? |
| 4 | Bar chart (horizontal, diverging) | `Business Sector YoY Change (S$M)` and/or `Business Sector YoY Growth (%)` (two similar visuals, or one with a measure-swap) | Y: `DimCategory[display_name]`; X: 0-centered | `DimCategory[category_role] = "business_sector"` | Descending by change | Which sectors grew or shrank the most over the latest 12 months, in absolute and % terms? |
| 5 | Line chart | `Top-3 Business Sector Concentration (%)` | X: `DimMonth[period_end]` | None (full history) | Chronological | Has business-lending concentration in the top 3 sectors increased or decreased over time? |
| 6 | Bar chart (horizontal, diverging) | `Business Sector Contribution to Business Growth (%)` | Y: `DimCategory[display_name]`; X: 0-centered, allow >100%/<0% | `DimCategory[category_role] = "business_sector"` | Descending by contribution | Which sectors are actually driving (or dragging on) the net change in business lending over the latest 12 months? |

**Slicers on Page 2:** `DimMonth[year_month]` (to re-point visuals 1–4 and 6 at a different "latest" month if desired) and optionally `DimCategory[display_name]` as a sector highlighter. Visual 5 (the concentration trend) is intended to stay unfiltered by month so its full trend remains visible even while other visuals are focused on one period — a page-level interaction note should be set so the `year_month` slicer does not filter visual 5 (**Edit interactions → set visual 5 to "None"** for that slicer).

---

## 4. Manual Build Steps

1. **Import the three CSVs.** Power BI Desktop → Get Data → Text/CSV → import, in this order: `data/processed/loan_balances_long.csv` (name the table `FactLoans`), `powerbi/dim_category.csv` (name it `DimCategory`), `powerbi/dim_month.csv` (name it `DimMonth`).
2. **Check data types** against the tables in Section 1.2 for every column, in Power Query before loading (fix any column Power BI auto-detected incorrectly, especially `period_end` as Date, not Date/Time, and `is_leaf` as True/False).
3. **Create the two relationships** in Model view: drag `DimMonth[period_end]` to `FactLoans[period_end]`, and `DimCategory[series_id]` to `FactLoans[series_id]`. Confirm both show as 1:* with a single arrow (dimension → fact) in the relationship properties, and both are Active.
4. **Set sort fields**: set `Sort by Column` for `year_month` → `year_month_sort` and `month_name` → `month_number` (Section 1.6); confirm "Mark as date table" is **not** enabled on `DimMonth`; disable Auto date/time (Section 1.7). **Leave all columns visible for now** — do not hide anything yet (see Section 1.4); several, including `DimMonth[period_end]`, are needed to build the visuals in steps 6–7.
5. **Create the DAX measures** from Section 2, in order (helpers first, since later measures reference them). Paste each formula exactly as written; set the format per Section 2.6 as each measure is created.
6. **Build Page 1** per the table in Section 3 — add the slicers first, then the 4 KPI cards, then the line chart, the year-by-year composition column chart (visual 5 — set its Edit Interactions to "None" for both slicers, per the interaction note in Section 3, and add the partial-year subtitle/text box), and the consumer category chart. For every card and axis showing an `(S$M)` measure, set **Display units = None** (Section 2.6) as you build each visual, not as a separate pass afterward.
7. **Build Page 2** per the table in Section 3 — add the KPI card, sector ranking and share charts, the two YoY change charts, the concentration trend line, and the contribution chart. Set the Edit Interactions override noted for visual 5 on this page too (the concentration trend). Set **Display units = None** on the `(S$M)` card and chart as in step 6.
8. **Validate results, then hide technical fields.** Spot-check at least the figures in Section 5 of this document (Aug 2026 total loans, YoY growth, top-3 concentration, Financial & Insurance change and contribution) against the card/visual values shown in Power BI. Also check that selecting a full Year on the `year` slicer still shows a single month-end balance on the KPI cards (the latest month in that year), not a sum of 12 months, and that selecting a `year`/`year_month` combination from different years produces an intentional blank page rather than an error (see the incompatible-slicer note in Section 1.5) — clear one slicer to confirm it recovers. Only once both pages check out, hide the columns listed in Section 1.4.
9. **Save the PBIX** with a clear filename (e.g. `03_Singapore_Finance_Analytics.pbix`) inside the `powerbi/` folder.
10. **Capture two dashboard screenshots** (one per page) once both pages look correct, for use in the final portfolio writeup.

ChatGPT will walk through these steps one at a time after reviewing this document — there is no need to complete all 10 steps in one sitting.

---

## 5. Independent Validation Performed (Python, not DAX)

All of the following were checked with pandas against `powerbi/dim_month.csv`, `powerbi/dim_category.csv`, `data/processed/loan_balances_long.csv`, and the Stage 3 SQL results in `results/`. **21/21 checks passed.** Full detail in the Stage 4 final report; headline results:

- `DimMonth` has exactly 62 unique `period_end` values, `month_index` runs 1…62 consecutively, and its key set exactly matches `FactLoans[period_end]`.
- `DimCategory` has exactly 27 unique `series_id` values matching `FactLoans[series_id]`, with no orphan keys either direction, and all 27 `display_name` values are unique.
- Both relationship keys (`DimMonth[period_end]`, `DimCategory[series_id]`) are unique on the "one" side, and `FactLoans` has no duplicate `(period_end, series_id)` grain — i.e. both relationships are structurally valid one-to-many joins.
- Recomputing the intended measure logic in pandas reproduces the Stage 3 SQL anchors exactly: Aug 2026 total loans S$966,432.7M, YoY growth 13.47%, business loans S$582,024.9M, top-3 concentration 76.87%, Financial & Insurance 12-month change +S$23,150.1M, and its contribution to business growth 34.32%.
- All 62 months' top-3 concentration values (recomputed independently in pandas using the same "re-rank every month" logic as the DAX measure) agree with the Stage 3 SQL `04_business_sector_concentration_monthly.csv` results to within floating-point rounding.
- The first 12 months (by `month_index`) correctly have no 12-months-ago comparison available.

## 6. Known Limitations and What Has NOT Been Tested

- **Python can verify the intended numerical outputs and model logic — it cannot execute DAX.** Every formula in Section 2 was designed and cross-checked against the approved Stage 2/3 figures using equivalent pandas logic, but **no DAX formula has been run inside Power BI Desktop**. Standard DAX risks that can only be confirmed there include: context-transition edge cases inside `CALCULATE`, `TOPN` tie-break behavior with real floating-point ties, visual-level vs. page-level filter interaction behavior, and performance on the full visual set.
- **ChatGPT must review all DAX formulas in Section 2 before manual dashboard construction begins.** This guide is a draft for that review, not a pre-approved final spec.
- Final DAX validation — confirming each measure actually returns the expected value for the anchor checks in Section 5, inside real Power BI visuals — will happen only during manual build in Power BI Desktop on Windows (Step 8 above), not in this stage.
- No PBIX file, dashboard, or screenshot exists yet as of this document.
