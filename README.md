# Singapore Banking Loan Portfolio & Sector Exposure Analytics

## Project overview and objectives

For this project, I analysed outstanding loans to Singapore residents to understand how commercial bank lending is distributed between businesses and consumers, which industries account for the largest exposures, and how those balances have changed over time. I used Python to clean and reshape the official data, DuckDB SQL to answer specific business questions, and Power BI to bring the findings together in an interactive two-page dashboard.

Singapore is a major regional financial hub, and resident bank lending is a closely watched indicator of credit conditions across its business and consumer sectors. The questions I wanted to answer were:

- How has the total loan portfolio changed over the reporting period?
- How has the business-versus-consumer lending composition evolved?
- Which business sectors account for the largest loan balances?
- How has top-three sector concentration evolved over time?
- Which sectors contributed most to recent business lending growth?

Every figure below is read directly from the processed data and SQL outputs described in this repository. The analysis is descriptive: it doesn't establish credit risk, causality or overall bank performance.

## Data source and collection date

**Primary dataset:** [Commercial Banks: Loans And Advances To Residents By Industry](https://data.gov.sg/datasets/d_af0415517a3a3a94b3b74039934ef976/view), the only dataset I used for analytical results.

**Supporting dataset, inspected but not used for analytical results:** [Commercial Banks: Assets And Liabilities](https://data.gov.sg/datasets/d_f357c61441e2850ca4eae05813ebd37b/view).

Both are published by the Singapore Department of Statistics (SingStat), sourced from the Monetary Authority of Singapore (MAS). I retrieved both on 9 November 2026. The primary dataset reports 27 loan categories across 62 consecutive monthly observations, from July 2021 to August 2026, the current MAS reporting basis following a mid-2021 methodology revision (see `docs/STAGE_1_DATA_INSPECTION.md` for the full inspection). This is official, publicly reported banking statistics, not a sample: it aggregates reporting across the commercial banks operating in Singapore.

## Workflow

| Stage | Tooling | Output |
|---|---|---|
| 1. Acquisition and inspection | Python, data.gov.sg API | Verified raw CSV downloads with documented coverage, hierarchy and licensing (`docs/STAGE_1_DATA_INSPECTION.md`) |
| 2. Cleaning and EDA | Python, pandas, matplotlib, Jupyter | Long-format fact table, category dimension and 6 EDA charts (`data/processed/`, `figures/`) |
| 3. DuckDB SQL business analysis | DuckDB SQL | 7 analytical queries with documented results and validation (`sql/`, `results/`) |
| 4. Power BI preparation and dashboard | Power BI Desktop | FactLoans, DimMonth and DimCategory model, DAX measures and a two-page interactive report (`powerbi/`) |
| 5. Publication and documentation | Git, GitHub | This reproducible, publicly published repository |

Each stage's methodology and findings are documented in full under `docs/` (see Repository structure below).

## Dashboard

Both pages share a consistent 2560 x 1440 layout: navy headings, a teal divider under the title, a light background, white rounded visual containers, and a coordinated teal, blue and navy colour scheme. Data labels use teal for positive growth and a muted coral for negative growth, and each page closes with a source and methodology footnote. The KPI cards on both pages are dynamic: they respond to the Year and Month slicers rather than showing a single fixed figure.

### Page 1: Portfolio Overview

![Portfolio Overview dashboard page showing total, business and consumer loan KPIs, a monthly trend line, loan portfolio composition by year and a consumer lending breakdown](powerbi/screenshots/01_portfolio_overview_V2.png)

Titled "Singapore Banking Loan Analytics," subtitled "Portfolio Overview | Commercial Bank Lending | Jul 2021-Aug 2026." Four KPI cards (Total Loans, Business Loans, Consumer Loans, Total YoY Growth), a Monthly Loan Portfolio Trends chart, a Loan Portfolio Composition by Year chart, a Consumer Lending Breakdown chart, and Year and Month slicers.

### Page 2: Sector Exposure & Growth

![Sector Exposure and Growth dashboard page showing business lending KPIs, the top-3 sector concentration trend, a sector exposure ranking, sector YoY growth and growth contributions](powerbi/screenshots/02_sector_exposure_and_growth_V2.png)

Titled "Singapore Banking Loan Analytics," subtitled "Sector Exposure & Growth | Commercial Bank Lending | Jul 2021-Aug 2026." Four KPI cards (Business Loans, Business Loans YoY Change, Top-3 Business Sector Concentration, Business Share), a Top-3 Business Sector Concentration Trend chart, a Business Sector Exposure Ranking chart (loan amounts in S$ billions), a Business Sector YoY Growth chart, a Sector Contributions to Business Lending Growth chart, and Year and Month slicers.

I'm publishing the Power BI report file itself (`powerbi/Singapore_Banking_Loan_Analytics.pbix`) in this repository, since the underlying data carries no redistribution restriction under the licence it's released under (see Attribution and licensing below).

## Key findings

All figures are as of August 2026, the latest month in the dataset, and are read directly from `results/` (the DuckDB SQL output), cross-checked against the dashboard screenshots above.

- Total loans stood at S$966.4B, up 13.47% over the latest 12 months.
- Business loans were S$582.0B and consumer loans S$384.4B. Business lending held a 60.22% share of the total portfolio, and grew by S$67.4B over the latest 12 months.
- The three largest business sectors, Building & Construction, Financial & Insurance Activities and General Commerce, together held a 76.87% concentration of business lending.
- Financial & Insurance Activities grew by S$23.15B over the latest 12 months (a sector growth rate of 17.73%) and contributed 34.32% of the net 12-month increase in business loans, the largest contribution of any sector. I treat these as three distinct measures: share describes a sector's current size relative to the business book, growth rate describes how fast that one sector moved, and contribution to net growth describes how much of the portfolio's total dollar increase is attributable to it.
- Housing & Bridging loans remained the dominant consumer category, at 66.74% of consumer lending.

Full findings, validation detail and sector-by-sector breakdowns are in `docs/STAGE_2_FINDINGS.md` and `docs/STAGE_3_SQL_FINDINGS.md`.

## Data-quality methodology and limitations

- I validated the cleaned long-format data against the raw source, confirming exactly 1,674 observations across 27 categories and 62 months with no missing or duplicate records (`scripts/clean_data.py`).
- The 27 reported series form a hierarchy, not 27 additive sectors. I used the documented parent-child structure throughout and never summed a subtotal together with its own children; business-sector comparisons use exactly the 8 mutually exclusive top-level business sectors, not the 11 finer subsectors nested under 5 of them, which I excluded from additive totals to avoid double-counting, and consumer-category comparisons use the 5 mutually exclusive consumer categories.
- Outstanding balances are end-of-period stocks. I never summed them across months, and month-over-month and 12-month changes are balance comparisons, not new loan origination volumes.
- The reporting series begins July 2021 following a MAS methodology revision (Notices 610 and 1003); the earlier, discontinued series isn't included.
- Published figures carry small rounding residuals (around S$0.1M to S$0.2M) at subtotal levels, which I reconciled and documented rather than treating as errors.
- Sector concentration and growth-contribution figures are descriptive balance-composition statistics. They aren't credit-risk or default-probability measures, and I don't draw causal conclusions from the trends observed.
- The analysis covers data available through August 2026 only.

## Repository structure

```
data/              Original data.gov.sg CSV exports (data/raw/), plus the cleaned fact table and category dimension (data/processed/)
scripts/           clean_data.py (cleaning and validation), run_sql_analysis.py (DuckDB runner), prepare_powerbi_data.py (Power BI dimension builder)
sql/               7 DuckDB SQL queries for the business analysis
results/           7 SQL query result CSVs
notebooks/         Exploratory data analysis (01_eda.ipynb)
figures/           6 EDA charts (PNG)
powerbi/           Singapore_Banking_Loan_Analytics.pbix, the Power BI dimension CSVs, dashboard screenshots and the build guide
docs/              Stage-by-stage inspection, cleaning, SQL, dashboard-audit and publication documentation
requirements.txt   Python dependencies
```

## Reproducibility

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the pipeline in order:
   ```bash
   python scripts/clean_data.py            # data/raw -> data/processed, with validation
   python scripts/run_sql_analysis.py      # runs sql/*.sql -> results/*.csv
   python scripts/prepare_powerbi_data.py  # builds powerbi/dim_category.csv and dim_month.csv
   ```
3. Explore the EDA notebook at `notebooks/01_eda.ipynb`.
4. The published PBIX (`powerbi/Singapore_Banking_Loan_Analytics.pbix`) already contains an imported data model, not a live connection. I built it on Windows via Parallels against local Mac file paths, so refreshing it on another machine means repointing the Power Query source paths to that machine's own copy of `data/processed/` and `powerbi/` first; refresh isn't automatic.

## Attribution and licensing

- **Primary dataset:** [Commercial Banks: Loans And Advances To Residents By Industry](https://data.gov.sg/datasets/d_af0415517a3a3a94b3b74039934ef976/view), the only dataset used for analytical results.
- **Supporting dataset (inspected only):** [Commercial Banks: Assets And Liabilities](https://data.gov.sg/datasets/d_f357c61441e2850ca4eae05813ebd37b/view).
- Published by the Singapore Department of Statistics (SingStat), sourced from the Monetary Authority of Singapore (MAS). Retrieved 9 November 2026.
- Licensed under the [Singapore Open Data Licence](https://developers.data.gov.sg/open-data-licence), which permits redistribution subject to its terms and required attribution. The raw and processed datasets, and the Power BI report file, are published in this repository under that licence.
- This is an independent portfolio project for educational and demonstration purposes. It is not affiliated with or endorsed by the Monetary Authority of Singapore (MAS), the Singapore Department of Statistics (SingStat) or the Singapore Government.
