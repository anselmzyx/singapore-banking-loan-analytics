# Stage 5 — Dashboard Audit

**Project:** Singapore Banking Loan Portfolio & Sector Exposure Analytics
**Scope:** Audit and packaging of the completed, manually-built, visually-reviewed Power BI dashboard. No analysis was rewritten and no new dashboard work was performed in this stage.

## 1. Dashboard Pages

The final, reviewed PBIX contains **two pages**:

| Order | Internal name | Display name |
|---|---|---|
| 1 | `574dc9bc44b902a975c6` | **01 Portfolio Overview** |
| 2 | `ef41c0f2dc0a4a44bd3c` | **02 Sector Exposure & Growth** |

## 2. PBIX Verification

| File | Size | SHA-256 |
|---|---|---|
| `powerbi/Singapore_Banking_Loan_Analytics.pbix` | 98,907 bytes | `27b5053600016257c6ea13ffed52af3ec4ed12c809de65d32f87a3fa60074d88` |

- The PBIX is a valid ZIP-based OPC package: `unzip -t` reports **no errors**, and it contains the expected internal structure (`Report/`, `DataModel`, `SecurityBindings`, `Settings`, `Version`, etc.).
- It contains exactly 2 pages (above), matching the reviewed screenshots.
- **Not claimed:** that the file opens correctly or runs in Power BI Desktop — this is a file-structure/ZIP-integrity check only, performed outside Power BI.

## 3. Screenshot Verification

| File | Size | Dimensions | SHA-256 |
|---|---|---|---|
| `powerbi/screenshots/01_portfolio_overview.png` | 217,013 bytes | 2082 × 1167 | `ef2ebf0de64d9b3c96bbec81f1b4f2a36fdb10a77d0d6ce9e19daea24b149ed5` |
| `powerbi/screenshots/02_sector_exposure_growth.png` | 282,400 bytes | 2085 × 1168 | `3500d8f3e5ad6f865e5657912914d59bac4b3eabc2e26a6077b0018b12c742de` |

Both are valid, non-corrupt PNG files (confirmed via file-type inspection and by visually opening each) at full-HD-plus resolution — legible for a portfolio dashboard. No duplicate, temporary, or stray screenshot files were found in `powerbi/screenshots/` (exactly these 2 files present).

Visual inspection confirms both pages render as intended: KPI cards, trend line, year-over-year composition chart, and consumer breakdown on Page 1; KPI cards, sector ranking, YoY growth, concentration trend, and growth-contribution charts on Page 2.

## 4. Data Model Summary

Per the semantic model (`Singapore_Banking_Loan_Analytics.SemanticModel`):

- **Tables:** `FactLoans` (1,674 rows, the processed long-format balances), `DimCategory` (27 rows), `DimMonth` (62 rows).
- **Relationships:** `DimMonth[period_end]` (1) → `FactLoans[period_end]` (*), and `DimCategory[series_id]` (1) → `FactLoans[series_id]` (*) — both one-to-many, single direction, active.
- **Measures:** 28 total — the 24 approved DAX measures (Stage 4, corrected naming), 3 pre-existing `S$B` display-convenience measures, and 1 measure (`Business Loans YoY Growth (%)`) added during dashboard automation to support a Page 2 KPI card with no prior equivalent.

## 5. DAX Validation Summary

Two distinct rounds of checking apply here, and they are **not the same thing**:

- **Completed previously, inside Power BI Desktop** (by the user, manually): the DAX measures and visual interactions (slicers, cross-filtering, tooltips) feeding the visuals that actually appear on the final 2-page dashboard were exercised and visually confirmed, as evidenced by the approved screenshots in Section 3, whose card and chart values match the model's live output. **This is not a claim that all 28 measures in the model were individually runtime-tested** — only those bound to a visible visual in the final dashboard were demonstrated this way; measures not surfaced on either page (e.g. any left over from earlier drafting) were not specifically exercised.
- **Performed in this audit, outside Power BI** (static, file-level only): JSON/TMDL structure validity, that all 24 approved measures remain byte-for-byte unchanged from the corrected Stage 4 formulas, that every visual's field references resolve to real TMDL measures/columns, and that the numeric values shown in the two screenshots match the independently-computed Stage 3 SQL results (Section 6). **No DAX was executed by this audit** — correctness of calculation was confirmed by comparing the screenshot's displayed values against the SQL results, not by re-running Power BI.

## 6. Key Numerical Anchors (screenshot vs. approved SQL results)

| Anchor | Approved (Stage 3 SQL) | Shown on dashboard | Match |
|---|---|---|---|
| Total Loans, Aug 2026 | S$966,432.7M | S$966.4B | ✓ |
| Business Loans, Aug 2026 | S$582,024.9M | S$582.0B | ✓ |
| Consumer Loans, Aug 2026 | S$384,407.8M | S$384.4B | ✓ |
| Total YoY Growth | 13.47% | 13.47% | ✓ |
| Top-3 Business Sector Concentration | 76.87% | 76.87% | ✓ |
| Business Loans YoY Change | S$67,446.4M | +S$67.4B | ✓ |
| Financial & Insurance Growth Contribution | 34.32% | +34.32% | ✓ |

All seven anchors were independently re-verified in this audit directly from `results/01_portfolio_overview_monthly.csv`, `results/04_business_sector_concentration_monthly.csv`, and `results/06_sector_growth_contributions_latest.csv` — all match exactly. Every sector-level figure visible in the Page 2 screenshots (ranking balances, YoY % by sector, contribution % by sector) was also cross-checked against `results/02`, `results/03`, and `results/06` and matches exactly.

## 7. Known Data Limitations

(Carried forward, unchanged, from Stages 1–3 — not re-litigated here.)

- All balances are end-of-period **stocks**, never summed across months.
- The 27-category hierarchy is not 27 additive sectors; business-sector and consumer-category comparisons use exactly the 8 and 5 respective leaf categories.
- Reporting basis begins July 2021 (MAS Notices 610/1003 revision); no discontinued pre-2021 data is included.
- Published figures carry ~S$0.1–0.2M rounding noise at subtotal levels — expected, not a defect.
- Concentration and contribution measures are descriptive balance-composition statistics, not credit-risk or default-probability measures.
- Primary dataset only; the Supporting (Assets & Liabilities) dataset was not merged in.

## 8. Remaining Issues

- **PBIP source / PBIX page-count mismatch:** the live PBIP source folders (`Singapore_Banking_Loan_Analytics.Report/definition/pages/`) still register **4 pages** — "01 Portfolio Overview," "02 Business Sector Exposure & Growth," a "Validation (Temporary)" page, and a "03 Detailed Analysis" page from an earlier automation pass — while the final, reviewed `.pbix` contains only the **2 approved pages**. This means the two artifacts are currently out of sync: re-opening the `.pbip` in Power BI Desktop would show 4 pages, not the 2 that were reviewed and approved. This was not corrected in this audit (out of scope — no PBIX/PBIP edits were made per the Stage 5 safety constraints); it should be resolved before any future PBIP-based edits, by re-saving the `.pbip` from the current approved `.pbix` state or by manually removing the two extra pages from the PBIP source.
  - **Publication note (Stage 6A):** rather than reconciling the two artifacts, the legacy PBIP source (`Singapore_Banking_Loan_Analytics.pbip`, its `.Report/` and `.SemanticModel/` folders) and the automation scripts/report that produced the unused third and fourth pages are being **excluded from public publication**. The 2-page `Singapore_Banking_Loan_Analytics.pbix` is the sole authoritative, published dashboard deliverable going forward. The PBIP source and automation artifacts remain on disk locally for reference but are not part of the publication set (see `docs/STAGE_6_PUBLICATION_CHECKLIST.md`).
- A pre-existing automation-safety backup, `powerbi/backup_pre_dashboard_automation_20261114/`, remains on disk. It is excluded from the Stage 5 ZIP (per the "exclude backups" instruction) but was not deleted, in case it is still wanted as a rollback reference.
- No other issues found. All raw hashes, processed data, scripts, SQL, results, notebook, figures, and documentation from Stages 1–4 are present and unchanged.
