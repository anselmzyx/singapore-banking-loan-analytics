# Stage 6A: Publication Inventory & Checklist

**Status:** This checklist documents the Stage 6A publication-preparation review. At the time it was written, Git had not yet been initialised and nothing had been published; it was assembled for independent review before publication was approved. The project has since been published; see Section 6 below for the current status.

## 1. Files Intended for Publication

| Category | Contents |
|---|---|
| Data | `data/raw/*.csv` (2 original), `data/processed/*.csv` (2 cleaned) |
| Scripts | `scripts/clean_data.py`, `scripts/run_sql_analysis.py`, `scripts/prepare_powerbi_data.py` |
| SQL | `sql/*.sql` (7 queries), `results/*.csv` (7 result sets) |
| Notebook & figures | `notebooks/01_eda.ipynb`, `figures/*.png` (6 charts) |
| Power BI | `powerbi/Singapore_Banking_Loan_Analytics.pbix`, `powerbi/screenshots/*.png` (2), `powerbi/dim_category.csv`, `powerbi/dim_month.csv`, `powerbi/POWER_BI_BUILD_GUIDE.md` |
| Documentation | `docs/STAGE_1_DATA_INSPECTION.md`, `docs/STAGE_2_FINDINGS.md`, `docs/STAGE_3_SQL_FINDINGS.md`, `docs/STAGE_5_DASHBOARD_AUDIT.md`, `docs/STAGE_6_PUBLICATION_CHECKLIST.md`, `docs/RESUME_BULLETS.md` |
| Project root | `README.md`, `requirements.txt`, `.gitignore` |

## 2. Files Intentionally Excluded (via `.gitignore`)

| File / folder | Reason |
|---|---|
| `powerbi/Singapore_Banking_Loan_Analytics.pbip`, `.Report/`, `.SemanticModel/` | Legacy PBIP folder-based source, superseded by the published `.pbix`; currently out of sync with it (registers 4 pages vs. the PBIX's approved 2, see `STAGE_5_DASHBOARD_AUDIT.md` §8) and contains plain-text TMDL with the local `\\Mac\Home\...` build-machine file paths. |
| `scripts/powerbi_dashboard_automation.py`, `scripts/validate_powerbi_pbip.py` | Tooling that edited the now-excluded PBIP source; not needed to reproduce the published pipeline (`clean_data.py` → `run_sql_analysis.py` → `prepare_powerbi_data.py`). |
| `docs/POWERBI_DASHBOARD_AUTOMATION_REPORT.md` | Documents the excluded PBIP automation; also the one file found to contain the local build-machine path (see §5 below). |
| `powerbi/backup_pre_dashboard_automation_20261114/` | Local safety backup, not project content. |
| Standard caches/temp/OS/secrets patterns | Python/Jupyter caches, venvs, `.DS_Store`, `.pbi/` local settings, `.env`/secrets patterns, backups, `*.zip`: none currently present as real secrets, excluded as a standing precaution. |

All excluded files **remain intact on disk**; nothing was deleted.

## 3. Source Attribution / Licence Check

- Primary dataset (the only one used analytically): [data.gov.sg d_af0415517a3a3a94b3b74039934ef976](https://data.gov.sg/datasets/d_af0415517a3a3a94b3b74039934ef976/view), cited in README "Attribution and licensing".
- Supporting dataset (inspection only, not used analytically): [data.gov.sg d_f357c61441e2850ca4eae05813ebd37b](https://data.gov.sg/datasets/d_f357c61441e2850ca4eae05813ebd37b/view), cited with its non-analytical role stated.
- Publisher attribution present: Singapore Department of Statistics (SingStat), source Monetary Authority of Singapore (MAS); retrieval date 9 November 2026.
- Licence cited: [Singapore Open Data Licence](https://developers.data.gov.sg/open-data-licence). No additional or invented per-dataset licence was stated, per instruction.

## 4. Final PBIX and Screenshots Verification

**At the time this checklist was first written (Stage 6A, historical):**

| File | Size | SHA-256 |
|---|---|---|
| `powerbi/Singapore_Banking_Loan_Analytics.pbix` | 98,907 bytes | `27b5053600016257c6ea13ffed52af3ec4ed12c809de65d32f87a3fa60074d88` |
| `powerbi/screenshots/01_portfolio_overview.png` | 217,013 bytes | `ef2ebf0de64d9b3c96bbec81f1b4f2a36fdb10a77d0d6ce9e19daea24b149ed5` |
| `powerbi/screenshots/02_sector_exposure_growth.png` | 282,400 bytes | `3500d8f3e5ad6f865e5657912914d59bac4b3eabc2e26a6077b0018b12c742de` |

Confirmed unchanged from the Stage 5 audit at the time (identical hashes), not modified during Stage 6A preparation. The PBIX was re-saved once more after this checklist was written, before the actual GitHub push, bringing it to 99,005 bytes; see `docs/STAGE_5_DASHBOARD_AUDIT.md` for both of those hashes and an explanation of what changed between them.

**Current status (19 November 2026, V2 visual redesign):** the dashboard's visual design was reworked and both screenshots were replaced with `powerbi/screenshots/01_portfolio_overview_V2.png` and `powerbi/screenshots/02_sector_exposure_and_growth_V2.png`; the two filenames in the table above no longer exist in the repository. The current PBIX is 102,949 bytes, SHA-256 `834f6fa8320de9d444885a34b1b575efd9ae0b1d079ea6fb6d6e6892c5aa4b14`. Full current hashes for the PBIX and both `_V2` screenshots are in `docs/STAGE_5_DASHBOARD_AUDIT.md` Sections 2 and 3; they are not repeated here to avoid two copies drifting out of sync.

## 5. README Link Validation

Every relative path referenced in `README.md` was checked against the actual project tree and resolved at the time of this checklist:

`powerbi/screenshots/01_portfolio_overview.png`, `powerbi/screenshots/02_sector_exposure_growth.png`, `docs/STAGE_2_FINDINGS.md`, `docs/STAGE_3_SQL_FINDINGS.md`, `data/processed/`, `scripts/clean_data.py`, `scripts/run_sql_analysis.py`, `sql/`, `results/`, `notebooks/01_eda.ipynb`, `powerbi/`. **All present, no broken links.** (The two screenshot filenames above are historical; following the 19 November 2026 V2 redesign, README now links `powerbi/screenshots/01_portfolio_overview_V2.png` and `powerbi/screenshots/02_sector_exposure_and_growth_V2.png` instead, both likewise confirmed present.)

**Secrets / machine-specific settings check:** grepped all publication-intended text files (scripts, SQL, CSVs, docs, README) for credential-like patterns (API keys, passwords, tokens): **none found**. Separately grepped for the build machine's local path signature (`\\Mac\Home\...`, `/Users/anselm`) across scripts, SQL, results, docs, and README; the only match was in `docs/POWERBI_DASHBOARD_AUTOMATION_REPORT.md`, already excluded from publication (§2).

**Correction from final independent review:** the initial sweep above did not check saved notebook *outputs*, and missed that `notebooks/01_eda.ipynb` contained a saved stdout output from a diagnostic `print("Project root:", ROOT.resolve())` statement, which exposed the notebook author's absolute local Mac project path. This has since been **found and sanitised**: the print statement and its saved output were removed from the notebook (all analytical code, other outputs, charts, execution counts, and the 27-cell structure were preserved unchanged; the notebook was re-verified as valid with zero error outputs and no remaining absolute local-machine paths anywhere in its source or outputs). No other publication-intended file was found to contain a machine-specific path.

One caveat that cannot be fully resolved without rebuilding the model: the published `.pbix` itself is a binary that internally retains the same `\\Mac\Home\...` Power Query source paths (it was not re-pointed or rebuilt in this stage, per the "do not modify the final PBIX" constraint). This is disclosed in README "Reproducibility" (users must update Power Query source paths before refreshing on another machine) rather than hidden.

## 6. Publication Status

**Stage 6A (preparation, historical):** at the time this checklist was first written, GitHub publication had not been approved. No Git repository existed and nothing had been pushed; this checklist, the prepared README and the preparation ZIP were assembled for independent review ahead of that approval.

**Current status:** publication was subsequently approved and completed. The project is now published publicly at [github.com/anselmzyx/singapore-banking-loan-analytics](https://github.com/anselmzyx/singapore-banking-loan-analytics) on the `main` branch. The repository contains exactly the files listed in Section 1 above, minus the exclusions in Section 2, except that the two Power BI screenshots were replaced on 19 November 2026 by the `_V2` redesign described in Section 4 above.
