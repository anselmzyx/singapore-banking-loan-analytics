"""
Stage 4 Power BI preparation script for Portfolio 03.

Generates two small Power BI-specific dimension tables from the APPROVED
Stage 2 processed CSVs. This script does not modify, recompute, or re-derive
anything in data/processed/ -- those files remain the Stage 2 source of
truth. It only adds the handful of presentation/indexing columns Power BI
needs that don't belong in the analytical processed data:

  - powerbi/dim_month.csv    (62 rows: one per month, with a sequential
                               month_index for DAX previous-month / 12-month
                               comparisons on a sparse monthly table)
  - powerbi/dim_category.csv (27 rows: the existing category dimension plus
                               a short, unique display_name for chart labels)

data/processed/loan_balances_long.csv is imported into Power BI directly as
the fact table (FactLoans) -- it is not touched or copied here.
"""

from pathlib import Path

import pandas as pd

BALANCES_CSV = "data/processed/loan_balances_long.csv"
CATEGORIES_CSV = "data/processed/loan_categories.csv"
POWERBI_DIR = Path("powerbi")

DIM_MONTH_OUT = POWERBI_DIR / "dim_month.csv"
DIM_CATEGORY_OUT = POWERBI_DIR / "dim_category.csv"

EXPECTED_MONTHS = 62
EXPECTED_CATEGORIES = 27

MONTH_NAMES = {
    1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
    7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December",
}

# Explicit, hand-reviewed series_id -> display_name mapping. Deliberately not
# a regex transform: with only 27 categories, an explicit dict is easier to
# verify for uniqueness and correctness than a "clever" string-shortening
# rule, and it can never accidentally collapse two different categories onto
# the same label.
DISPLAY_NAME_MAP = {
    "total_loans_and_advances_including_bills_financing": "Total Loans",
    "loans_to_businesses_total": "Business Loans (Total)",
    "loans_to_businesses_agriculture_mining_and_quarrying_total": "Agriculture, Mining & Quarrying",
    "loans_to_businesses_agriculture_mining_and_quarrying_agriculture_and_fishing": "Agriculture & Fishing",
    "loans_to_businesses_agriculture_mining_and_quarrying_mining_and_quarrying": "Mining & Quarrying",
    "loans_to_businesses_manufacturing": "Manufacturing",
    "loans_to_businesses_building_and_construction_total": "Building & Construction",
    "loans_to_businesses_building_and_construction_construction": "Construction",
    "loans_to_businesses_building_and_construction_real_property_and_development_of_land": "Real Property & Land Development",
    "loans_to_businesses_general_commerce_total": "General Commerce",
    "loans_to_businesses_general_commerce_wholesale_trade": "Wholesale Trade",
    "loans_to_businesses_general_commerce_retail_trade": "Retail Trade",
    "loans_to_businesses_general_commerce_accommodation_and_food_services_activities": "Accommodation & Food Services",
    "loans_to_businesses_transport_storage_and_communication_total": "Transport, Storage & Communication",
    "loans_to_businesses_transport_storage_and_communication_transport_and_storage": "Transport & Storage",
    "loans_to_businesses_transport_storage_and_communication_information_and_communications": "Information & Communications",
    "loans_to_businesses_financial_and_insurance_activities": "Financial & Insurance",
    "loans_to_businesses_professional_scientific_technical_administrative_support_service_activities": "Professional & Support Services",
    "loans_to_businesses_others_total": "Other Business Sectors",
    "loans_to_businesses_others_electricity_gas_and_water_supply": "Electricity, Gas & Water",
    "loans_to_businesses_others_other_industries": "Other Industries",
    "consumer_loans_total": "Consumer Loans (Total)",
    "consumer_loans_housing_and_bridging_loans": "Housing & Bridging",
    "consumer_loans_natural_persons_car_loans": "Car Loans",
    "consumer_loans_natural_persons_credit_cards": "Credit Cards",
    "consumer_loans_natural_persons_share_financing": "Share Financing",
    "consumer_loans_natural_persons_others": "Other Consumer Loans",
}


def build_dim_month():
    long_df = pd.read_csv(BALANCES_CSV, parse_dates=["period_end"])
    periods = pd.Series(sorted(long_df["period_end"].unique()))

    if len(periods) != EXPECTED_MONTHS:
        raise ValueError(f"Expected {EXPECTED_MONTHS} unique months, found {len(periods)}.")

    dim_month = pd.DataFrame({
        "period_end": periods.dt.strftime("%Y-%m-%d"),
        "year": periods.dt.year,
        "month_number": periods.dt.month,
        "month_name": periods.dt.month.map(MONTH_NAMES),
        "year_month": periods.dt.strftime("%Y-%m"),
        "year_month_sort": (periods.dt.year * 100 + periods.dt.month).astype(int),
        "month_index": range(1, EXPECTED_MONTHS + 1),
    })
    return dim_month


def build_dim_category():
    categories = pd.read_csv(CATEGORIES_CSV)

    if len(categories) != EXPECTED_CATEGORIES:
        raise ValueError(f"Expected {EXPECTED_CATEGORIES} categories, found {len(categories)}.")

    missing = set(categories["series_id"]) - set(DISPLAY_NAME_MAP)
    if missing:
        raise ValueError(f"No display_name mapped for series_id(s): {sorted(missing)}")

    categories = categories.copy()
    categories["display_name"] = categories["series_id"].map(DISPLAY_NAME_MAP)

    dup_names = categories["display_name"][categories["display_name"].duplicated()]
    if len(dup_names):
        raise ValueError(f"display_name is not unique: {sorted(set(dup_names))}")

    # Keep the existing processed columns, in their original order, plus the
    # new display_name column appended at the end.
    ordered_cols = ["series_id", "series_name", "parent_series_id", "indent_level",
                     "category_role", "is_leaf", "row_order", "display_name"]
    return categories[ordered_cols]


def main():
    POWERBI_DIR.mkdir(exist_ok=True)

    dim_month = build_dim_month()
    dim_month.to_csv(DIM_MONTH_OUT, index=False)
    print(f"Wrote {DIM_MONTH_OUT} ({len(dim_month)} rows)")

    dim_category = build_dim_category()
    dim_category.to_csv(DIM_CATEGORY_OUT, index=False)
    print(f"Wrote {DIM_CATEGORY_OUT} ({len(dim_category)} rows)")

    print("\ndim_month.csv preview:")
    print(dim_month.head(3).to_string(index=False))
    print("...")
    print(dim_month.tail(3).to_string(index=False))

    print("\ndim_category.csv preview:")
    print(dim_category[["series_id", "category_role", "display_name"]].to_string(index=False))


if __name__ == "__main__":
    main()
