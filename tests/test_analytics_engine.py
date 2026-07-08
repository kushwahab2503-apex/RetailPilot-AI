import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from backend.analytics_engine import (
    prepare_analytics_dataset,
    calculate_core_kpis,
    aggregate_time_series,
    calculate_category_performance,
    calculate_city_performance,
    calculate_payment_distribution,
    detect_capabilities,
    apply_filters
)
from backend.formatters import format_indian_currency, format_indian_number

# Test data fixtures or functions
def get_sample_valid_data():
    return pd.DataFrame({
        "OrderID": ["ORD1", "ORD1", "ORD2", "ORD3"],
        "OrderDate": ["2026-07-01", "2026-07-01", "2026-07-02", "2026-07-03"],
        "ProductID": ["P1", "P2", "P1", "P3"],
        "ProductName": ["Mouse", "Keyboard", "Mouse", "Monitor"],
        "Category": ["Peripherals", "Peripherals", "Peripherals", "Monitors"],
        "Quantity": [2, 1, 1, 5],
        "UnitPrice": [500.0, 1500.0, 500.0, 8000.0],
        "DiscountPct": [10.0, 0.0, 20.0, 5.0],
        "City": ["Mumbai", "Mumbai", "Delhi", "Bengaluru"],
        "PaymentMethod": ["UPI", "UPI", "Card", "NetBanking"]
    })

def test_prepare_and_total_revenue():
    # 1. Total revenue calculation & 2. Discount-adjusted net revenue
    df = get_sample_valid_data()
    prepared_df, meta = prepare_analytics_dataset(df)
    
    # Assertions
    # Line 1: 2 * 500 * (1 - 0.1) = 900
    # Line 2: 1 * 1500 * (1 - 0.0) = 1500
    # Line 3: 1 * 500 * (1 - 0.2) = 400
    # Line 4: 5 * 8000 * (1 - 0.05) = 38000
    # Total = 900 + 1500 + 400 + 38000 = 40800
    kpis = calculate_core_kpis(prepared_df, meta["revenue_basis"])
    assert kpis["total_revenue"] == 40800.0
    assert meta["revenue_basis"] == "Net Revenue"

def test_gross_revenue_fallback_no_discount():
    # 3. Gross revenue fallback when DiscountPct is absent
    df = get_sample_valid_data().drop(columns=["DiscountPct"])
    prepared_df, meta = prepare_analytics_dataset(df)
    
    # Line 1: 2 * 500 = 1000
    # Line 2: 1 * 1500 = 1500
    # Line 3: 1 * 500 = 500
    # Line 4: 5 * 8000 = 40000
    # Total = 1000 + 1500 + 500 + 40000 = 43000
    kpis = calculate_core_kpis(prepared_df, meta["revenue_basis"])
    assert kpis["total_revenue"] == 43000.0
    assert meta["revenue_basis"] == "Gross Revenue"

def test_order_count_and_repeated_ids():
    # 4. Unique OrderID counting
    # 5. Repeated OrderID line items do not inflate order count
    df = get_sample_valid_data()
    prepared_df, meta = prepare_analytics_dataset(df)
    kpis = calculate_core_kpis(prepared_df, meta["revenue_basis"])
    
    # Unique orders: ORD1, ORD2, ORD3 (total 3 unique, although row count is 4)
    assert kpis["total_orders"] == 3

def test_units_sold():
    # 6. Units sold calculation
    df = get_sample_valid_data()
    prepared_df, meta = prepare_analytics_dataset(df)
    kpis = calculate_core_kpis(prepared_df, meta["revenue_basis"])
    
    # Quantities: 2, 1, 1, 5 => Total 9
    assert kpis["units_sold"] == 9

def test_average_order_value():
    # 7. Average Order Value
    df = get_sample_valid_data()
    prepared_df, meta = prepare_analytics_dataset(df)
    kpis = calculate_core_kpis(prepared_df, meta["revenue_basis"])
    
    # Total revenue = 40800, Total orders = 3 => AOV = 13600
    assert kpis["average_order_value"] == 13600.0

def test_aov_division_by_zero():
    # Corner case: division by zero
    empty_df = pd.DataFrame(columns=["OrderID", "OrderDate", "Quantity", "UnitPrice", "_Revenue"])
    kpis = calculate_core_kpis(empty_df, "Gross Revenue")
    assert kpis["average_order_value"] == 0.0

def test_daily_weekly_monthly_aggregation():
    # 8. Daily revenue aggregation
    # 9. Weekly revenue aggregation
    # 10. Monthly revenue aggregation
    raw_df = pd.DataFrame({
        "OrderID": ["ORD1", "ORD2", "ORD3", "ORD4"],
        "OrderDate": ["2026-07-01", "2026-07-06", "2026-07-07", "2026-08-01"], # July 6 & 7 are same week (Mon & Tue)
        "ProductID": ["P1", "P2", "P3", "P4"],
        "Quantity": [1, 1, 1, 1],
        "UnitPrice": [100.0, 200.0, 300.0, 400.0]
    })
    prepared_df, meta = prepare_analytics_dataset(raw_df)
    
    # Daily
    daily = aggregate_time_series(prepared_df, "Daily")
    assert len(daily) == 4
    assert daily.iloc[0]["Revenue"] == 100.0
    
    # Weekly (should group 2026-07-06 and 2026-07-07 together under Monday 2026-07-06)
    weekly = aggregate_time_series(prepared_df, "Weekly")
    # Groups: 2026-07-01 (week start 2026-06-29), 2026-07-06 & 07 (week start 2026-07-06), 2026-08-01 (week start 2026-07-27)
    # Total unique weeks: 3
    assert len(weekly) == 3
    middle_week = weekly[weekly["Date"] == "2026-07-06"]
    assert not middle_week.empty
    assert middle_week.iloc[0]["Revenue"] == 500.0 # 200 + 300
    assert middle_week.iloc[0]["Orders"] == 2 # ORD2, ORD3
    assert middle_week.iloc[0]["Units"] == 2 # 1 + 1

    # Monthly
    monthly = aggregate_time_series(prepared_df, "Monthly")
    # Groups: July 2026 (100 + 200 + 300 = 600), August 2026 (400)
    assert len(monthly) == 2
    july_rev = monthly[monthly["Date"] == "2026-07-01"].iloc[0]["Revenue"]
    aug_rev = monthly[monthly["Date"] == "2026-08-01"].iloc[0]["Revenue"]
    assert july_rev == 600.0
    assert aug_rev == 400.0

def test_category_performance():
    # 11. Category aggregation
    # 12. Revenue share totals approximately 100%
    df = get_sample_valid_data()
    prepared_df, meta = prepare_analytics_dataset(df)
    
    cat_df = calculate_category_performance(prepared_df)
    
    # Categories: Peripherals (rev 900+1500+400=2800), Monitors (rev 38000)
    assert len(cat_df) == 2
    assert cat_df.iloc[0]["Category"] == "Monitors"
    assert cat_df.iloc[0]["Revenue"] == 38000.0
    assert cat_df.iloc[1]["Category"] == "Peripherals"
    assert cat_df.iloc[1]["Revenue"] == 2800.0
    
    assert sum(cat_df["Revenue Share"]) == pytest.approx(100.0)

def test_city_analytics_availability():
    # 13. City analytics availability when City exists
    # 14. City analytics unavailable when City is absent
    df_with_city = get_sample_valid_data()
    prepared_df_c, meta_c = prepare_analytics_dataset(df_with_city)
    city_perf = calculate_city_performance(prepared_df_c)
    assert city_perf is not None
    assert "Mumbai" in city_perf["City"].tolist()

    df_no_city = get_sample_valid_data().drop(columns=["City"])
    prepared_df_nc, meta_nc = prepare_analytics_dataset(df_no_city)
    city_perf_nc = calculate_city_performance(prepared_df_nc)
    assert city_perf_nc is None

def test_payment_method_distribution_order_aware():
    # 15. Payment method distribution is order-aware
    # Multiple items in same order (ORD1 has two lines with UPI)
    df = get_sample_valid_data()
    prepared_df, meta = prepare_analytics_dataset(df)
    
    pay_df = calculate_payment_distribution(prepared_df)
    assert pay_df is not None
    
    # Unique orders:
    # ORD1 -> UPI
    # ORD2 -> Card
    # ORD3 -> NetBanking
    # Order counts: UPI: 1, Card: 1, NetBanking: 1
    # Total unique orders: 3
    assert pay_df.loc[pay_df["PaymentMethod"] == "UPI", "Orders"].values[0] == 1
    assert pay_df.loc[pay_df["PaymentMethod"] == "Card", "Orders"].values[0] == 1
    assert pay_df.loc[pay_df["PaymentMethod"] == "NetBanking", "Orders"].values[0] == 1
    assert sum(pay_df["Order Share (%)"]) == pytest.approx(100.0)

def test_combined_filters():
    # 16. Combined filters work correctly
    df = get_sample_valid_data()
    prepared_df, meta = prepare_analytics_dataset(df)
    
    # Filter on date range, category, and city
    filtered = apply_filters(
        prepared_df,
        date_range=("2026-07-01", "2026-07-02"),
        categories=["Peripherals"],
        cities=["Mumbai"]
    )
    # Lines matching: 
    # ORD1(Mumbai, 2026-07-01, Peripherals) - matches
    # ORD1(Mumbai, 2026-07-01, Peripherals) - matches
    # ORD2(Delhi, 2026-07-02, Peripherals) - excluded by city (Delhi)
    # ORD3(Bengaluru, 2026-07-03, Monitors) - excluded by date and category
    assert len(filtered) == 2
    assert (filtered["OrderID"] == "ORD1").all()

def test_empty_filter_result():
    # 17. Empty filter result is handled safely
    df = get_sample_valid_data()
    prepared_df, meta = prepare_analytics_dataset(df)
    
    filtered = apply_filters(
        prepared_df,
        categories=["Laptops"] # No category laptops exists
    )
    assert filtered.empty
    
    # Test aggregation on empty filtered DataFrame
    ts = aggregate_time_series(filtered, "Daily")
    assert ts.empty
    
    cat = calculate_category_performance(filtered)
    assert cat.empty
    
    kpis = calculate_core_kpis(filtered, "Net Revenue")
    assert kpis["total_revenue"] == 0.0
    assert kpis["total_orders"] == 0

def test_non_mutation():
    # 18. Original dataframe is not mutated
    df = get_sample_valid_data()
    orig_copy = df.copy()
    
    prepared_df, meta = prepare_analytics_dataset(df)
    # Check that df remains unchanged
    pd.testing.assert_frame_equal(df, orig_copy)
    
    # Apply filtering
    apply_filters(prepared_df, categories=["Peripherals"])
    pd.testing.assert_frame_equal(df, orig_copy)

def test_invalid_rows_exclusion():
    # 19. Invalid revenue rows are handled according to documented eligibility rules
    raw_df = pd.DataFrame({
        "OrderID": ["ORD1", " ", np.nan, "ORD4", "ORD5", "ORD6"], # Empty or spaces
        "OrderDate": ["2026-07-01", "2026-07-02", "2026-07-03", "2026-07-04", np.nan, "2026-07-06"], # nan date
        "ProductID": ["P1", "P2", "P3", "P4", "P5", "P6"],
        "Quantity": [5, 10, 15, -2, 5, 2], # Negative quantity
        "UnitPrice": [100.0, 200.0, 300.0, 400.0, 500.0, -100.0] # Negative price
    })
    
    prepared_df, meta = prepare_analytics_dataset(raw_df)
    
    # Disqualifications:
    # ROW 0: Valid (ORD1, 2026-07-01, Product P1, Q: 5, P: 100.0) -> Valid row count = 1
    # ROW 1: Invalid OrderID -> Excluded
    # ROW 2: Invalid OrderID -> Excluded
    # ROW 3: Negative Quantity -> Excluded
    # ROW 4: NaN OrderDate -> Excluded
    # ROW 5: Negative UnitPrice -> Excluded
    
    assert len(prepared_df) == 1
    assert prepared_df.iloc[0]["OrderID"] == "ORD1"
    assert meta["valid_row_count"] == 1
    assert meta["excluded_row_count"] == 5

def test_capability_detection():
    # 20. Capability detection works
    df = get_sample_valid_data()
    caps = detect_capabilities(df)
    assert caps["core_kpis_available"] is True
    assert caps["city_analytics_available"] is True
    assert caps["payment_analytics_available"] is True

    # Drop City and Payment
    df_slim = df.drop(columns=["City", "PaymentMethod"])
    caps_slim = detect_capabilities(df_slim)
    assert caps_slim["core_kpis_available"] is True
    assert caps_slim["city_analytics_available"] is False
    assert caps_slim["payment_analytics_available"] is False

def test_empty_dataframe_handling():
    # 21. Empty dataframe handling
    empty_df = pd.DataFrame()
    prepared_df, meta = prepare_analytics_dataset(empty_df)
    assert prepared_df.empty
    assert meta["row_count_analyzed"] == 0
    assert meta["excluded_row_count"] == 0

    caps = detect_capabilities(empty_df)
    for k, v in caps.items():
        assert v is False

def test_missing_optional_columns():
    # 22. Missing optional columns do not break core analytics
    df = pd.DataFrame({
        "OrderID": ["ORD1"],
        "OrderDate": ["2026-07-01"],
        "ProductID": ["P1"],
        "ProductName": ["Mouse"],
        "Category": ["Peripherals"],
        "Quantity": [2],
        "UnitPrice": [500.0]
    })
    prepared_df, meta = prepare_analytics_dataset(df)
    kpis = calculate_core_kpis(prepared_df, meta["revenue_basis"])
    assert kpis["total_revenue"] == 1000.0
    
    caps = detect_capabilities(df)
    assert caps["city_analytics_available"] is False
    assert caps["payment_analytics_available"] is False

def test_indian_formatters():
    # Testing our formatters suite
    assert format_indian_currency(950) == "₹950"
    assert format_indian_currency(12500) == "₹12.5K"
    assert format_indian_currency(45201) == "₹45,201"
    assert format_indian_currency(840000) == "₹8.4L"
    assert format_indian_currency(12000000) == "₹1.2Cr"
    assert format_indian_currency(None) == "₹—"
    assert format_indian_currency(float('nan')) == "₹—"
    assert format_indian_currency(-12000000) == "-₹1.2Cr"
    
    assert format_indian_number(950) == "950"
    assert format_indian_number(12500) == "12.5K"
    assert format_indian_number(840000) == "8.4L"
