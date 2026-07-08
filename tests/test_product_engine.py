import pytest
import pandas as pd
import numpy as np
from backend.product_engine import (
    prepare_product_dataset,
    apply_product_filters,
    get_product_performance,
    calculate_product_kpis,
    get_top_bottom_ranking,
    get_pareto_data,
    get_quadrant_analysis_data,
    get_category_product_context,
    detect_product_capabilities
)
from backend.analytics_engine import prepare_analytics_dataset

@pytest.fixture
def base_test_df():
    """
    Standard mock transactions dataframe with all required columns.
    Contains different products, dates, categories, quantity, prices, and discounts.
    """
    return pd.DataFrame({
        "OrderID": ["ORD-001", "ORD-001", "ORD-002", "ORD-003", "ORD-003", "ORD-004", "ORD-005"],
        "OrderDate": ["2026-07-01", "2026-07-01", "2026-07-02", "2026-07-02", "2026-07-02", "2026-07-03", "2026-07-04"],
        "ProductID": ["P-001", "P-002", "P-001", "P-003", "P-004", "P-001", "P-002"],
        "ProductName": ["Mouse", "Keyboard", "Mouse", "Monitor", "Headphones", "Mouse", "Keyboard"],
        "Category": ["Peripherals", "Peripherals", "Peripherals", "Monitors", "Audio", "Peripherals", "Peripherals"],
        "Quantity": [2, 1, 1, 1, 2, 5, 2],
        "UnitPrice": [500.0, 1500.0, 500.0, 12000.0, 1000.0, 500.0, 1500.0],
        "DiscountPct": [10.0, 0.0, 0.0, 5.0, 0.0, 20.0, 10.0]
    })

# 1. Product aggregation correctness
def test_product_aggregation_correctness(base_test_df):
    prep_df, _ = prepare_product_dataset(base_test_df)
    perf = get_product_performance(prep_df)
    
    # We should have 4 products (P-001, P-002, P-003, P-004)
    assert len(perf) == 4
    # P-001 (Mouse) stats:
    # Row 1: Q=2, P=500, D=10% -> Net = 900
    # Row 3: Q=1, P=500, D=0% -> Net = 500
    # Row 6: Q=5, P=500, D=20% -> Net = 2000
    # Total P-001 revenue should be 3400
    p1 = perf[perf["Product_Key"] == "P-001|Mouse"].iloc[0]
    assert p1["Revenue"] == 3400.0
    assert p1["Units Sold"] == 8

# 2. Repeated OrderID handling
def test_repeated_order_id_handling(base_test_df):
    prep_df, _ = prepare_product_dataset(base_test_df)
    perf = get_product_performance(prep_df)
    
    # ORD-001 contains two items. Both items should be processed, but unique order list counted correctly.
    # Keyboard is in ORD-001 and ORD-005. Unique orders = 2.
    kbd = perf[perf["Product_Key"] == "P-002|Keyboard"].iloc[0]
    assert kbd["Unique Orders"] == 2

# 3. Unique order counts
def test_unique_order_counts(base_test_df):
    prep_df, _ = prepare_product_dataset(base_test_df)
    perf = get_product_performance(prep_df)
    
    # Check mouse unique orders (ORD-001, ORD-002, ORD-004) -> 3
    mouse = perf[perf["Product_Key"] == "P-001|Mouse"].iloc[0]
    assert mouse["Unique Orders"] == 3

# 4. Units sold calculation
def test_units_sold_calculation(base_test_df):
    prep_df, _ = prepare_product_dataset(base_test_df)
    perf = get_product_performance(prep_df)
    
    # Monitor units sold = 1
    monitor = perf[perf["Product_Key"] == "P-003|Monitor"].iloc[0]
    assert monitor["Units Sold"] == 1

# 5. Revenue calculation consistency with Analytics engine
def test_revenue_consistency_with_analytics(base_test_df):
    prep_p, _ = prepare_product_dataset(base_test_df)
    prep_a, _ = prepare_analytics_dataset(base_test_df)
    
    # Total revenue must match exactly
    assert prep_p["_Revenue"].sum() == prep_a["_Revenue"].sum()

# 6. Average pricing metric semantics
def test_average_pricing_metrics(base_test_df):
    prep_df, _ = prepare_product_dataset(base_test_df)
    perf = get_product_performance(prep_df)
    
    # Mouse (P-001): Revenue = 3400, Units = 8.
    # Realized Revenue per Unit = 3400 / 8 = 425.0
    # Average Price (UnitPrice mean) = mean(500, 500, 500) = 500.0
    mouse = perf[perf["Product_Key"] == "P-001|Mouse"].iloc[0]
    assert mouse["Average Realized Revenue per Unit"] == 425.0
    assert mouse["Average Price"] == 500.0

# 7. Revenue share sums correctly
def test_revenue_share_sums_to_100(base_test_df):
    prep_df, _ = prepare_product_dataset(base_test_df)
    perf = get_product_performance(prep_df)
    
    assert abs(perf["Revenue Share (%)"].sum() - 100.0) < 1e-5
    assert abs(perf["Unit Share (%)"].sum() - 100.0) < 1e-5

# 8. Deterministic ranking (secondary alphabetical breakdown)
def test_deterministic_ranking(base_test_df):
    # Setup test with equal revenues
    df = pd.DataFrame({
        "OrderID": ["ORD-1", "ORD-2"],
        "OrderDate": ["2026-07-01", "2026-07-02"],
        "ProductID": ["P-B", "P-A"],
        "ProductName": ["Beta", "Alpha"],
        "Quantity": [1, 1],
        "UnitPrice": [100.0, 100.0]
    })
    prep_df, _ = prepare_product_dataset(df)
    perf = get_product_performance(prep_df)
    
    # Both have revenue = 100. Alpha must rank before Beta alphabetically
    assert perf.iloc[0]["Product_Display"] == "[P-A] Alpha"
    assert perf.iloc[0]["Rank"] == 1
    assert perf.iloc[1]["Product_Display"] == "[P-B] Beta"
    assert perf.iloc[1]["Rank"] == 2

# 9. Top N ranking
def test_top_n_ranking(base_test_df):
    prep_df, _ = prepare_product_dataset(base_test_df)
    top_n, _ = get_top_bottom_ranking(prep_df, n=2)
    
    assert len(top_n) == 2
    assert top_n.iloc[0]["Rank"] == 1 # Monitor: Net = 11400 (Top)
    assert top_n.iloc[1]["Rank"] == 2 # Keyboard: Net = 1500 + 2700 = 4200 (Second)

# 10. Bottom N ranking
def test_bottom_n_ranking(base_test_df):
    prep_df, _ = prepare_product_dataset(base_test_df)
    _, bottom_n = get_top_bottom_ranking(prep_df, n=2)
    
    assert len(bottom_n) == 2
    # Least revenue product must be first in bottom N (Headphones: Net = 2000, then Mouse: Net = 3400)
    assert bottom_n.iloc[0]["Revenue"] == 2000.0
    assert bottom_n.iloc[1]["Revenue"] == 3400.0

# 11. Fewer products than N
def test_fewer_products_than_n():
    df = pd.DataFrame({
        "OrderID": ["ORD-001"],
        "OrderDate": ["2026-07-01"],
        "ProductID": ["P-001"],
        "ProductName": ["Mouse"],
        "Quantity": [10],
        "UnitPrice": [50.0]
    })
    prep_df, _ = prepare_product_dataset(df)
    top_n, bottom_n = get_top_bottom_ranking(prep_df, n=5)
    
    assert len(top_n) == 1
    assert len(bottom_n) == 1

# 12. Pareto cumulative percentage limits
def test_pareto_cumulative_pct(base_test_df):
    prep_df, _ = prepare_product_dataset(base_test_df)
    pareto_df, _ = get_pareto_data(prep_df)
    
    # Cumulative percentage of the last product must equal exactly 100.0
    assert abs(pareto_df.iloc[-1]["Cumulative Pct"] - 100.0) < 1e-5

# 13. Approximate 80% contributor identification boundary
def test_pareto_80_percent_contributors(base_test_df):
    prep_df, _ = prepare_product_dataset(base_test_df)
    _, meta = get_pareto_data(prep_df)
    
    # Portfolio Rev: Monitor (11,400) = 54.3%, Keyboard (4,200) = 20%, Mouse (3,400) = 16.2%, Headphones (2,000) = 9.5%
    # Total: 21,000
    # Cumulatives model:
    # 1. Monitor (11,400) -> 54.3%
    # 2. Keyboard (15,600) -> 74.3%
    # 3. Mouse (19,000) -> 90.5% (First crosses 80% threshold!)
    # Should include: 3 products.
    assert meta["contributors_count"] == 3
    assert "[P-003] Monitor" in meta["contributor_displays"]
    assert "[P-002] Keyboard" in meta["contributor_displays"]
    assert "[P-001] Mouse" in meta["contributor_displays"]

# 14. Quantity vs revenue dataset
def test_quantity_revenue_scatter_data(base_test_df):
    prep_df, _ = prepare_product_dataset(base_test_df)
    scatter_df, thresholds = get_quadrant_analysis_data(prep_df)
    
    assert "Quadrant" in scatter_df.columns
    assert "median_units" in thresholds
    assert "median_revenue" in thresholds

# 15. Median-based segment classification
def test_median_segment_classification():
    # Setup controlled metrics
    # P1: Q=2, R=20 (Low volume, Low revenue)
    # P2: Q=4, R=50 (High volume, Low revenue)
    # P3: Q=6, R=500 (High volume, High revenue)
    # P4: Q=2, R=80 (Low volume, High revenue)
    # Medians: Units = 3.0, Revenue = 65.0
    df = pd.DataFrame({
        "OrderID": ["O1", "O2", "O3", "O4"],
        "OrderDate": ["2026-07-01", "2026-07-02", "2026-07-03", "2026-07-04"],
        "ProductID": ["P1", "P2", "P3", "P4"],
        "ProductName": ["A", "B", "C", "D"],
        "Quantity": [2, 4, 6, 2],
        "UnitPrice": [10.0, 12.5, 83.33, 40.0]
    })
    prep_df, _ = prepare_product_dataset(df)
    scatter_df, thresholds = get_quadrant_analysis_data(prep_df)
    
    assert thresholds["median_units"] == 3.0
    assert thresholds["median_revenue"] == 65.0  # median of [20, 50, 499.98, 80] = 65.0
    
    p1 = scatter_df[scatter_df["Product_Display"] == "[P1] A"].iloc[0]
    assert p1["Quadrant"] == "low-volume / low-revenue"
    
    p3 = scatter_df[scatter_df["Product_Display"] == "[P3] C"].iloc[0]
    assert p3["Quadrant"] == "high-volume / high-revenue"

# 16. Category filtering/context
def test_category_context(base_test_df):
    prep_df, _ = prepare_product_dataset(base_test_df)
    cat_df = get_category_product_context(prep_df)
    
    assert len(cat_df) == 3
    # Peripherals Category has two products (Mouse, Keyboard)
    periph = cat_df[cat_df["Category"] == "Peripherals"].iloc[0]
    assert periph["Active Products"] == 2
    assert periph["Top Product"] == "[P-002] Keyboard"

# 17. Missing Category column
def test_missing_category_column(base_test_df):
    df_no_cat = base_test_df.drop(columns=["Category"])
    prep_df, _ = prepare_product_dataset(df_no_cat)
    
    cat_df = get_category_product_context(prep_df)
    assert cat_df is None
    
    caps = detect_product_capabilities(df_no_cat)
    assert caps["category_available"] is False

# 18. ProductID-only fallback
def test_product_id_only_fallback(base_test_df):
    df_no_name = base_test_df.drop(columns=["ProductName"])
    prep_df, meta = prepare_product_dataset(df_no_name)
    
    assert not prep_df.empty
    assert meta["product_exclusions"]["missing_product_identity"] == 0
    assert prep_df.iloc[0]["Product_Display"] == "P-001"

# 19. ProductName-only fallback
def test_product_name_only_fallback(base_test_df):
    df_no_id = base_test_df.drop(columns=["ProductID"])
    prep_df, meta = prepare_product_dataset(df_no_id)
    
    assert not prep_df.empty
    assert meta["product_exclusions"]["missing_product_identity"] == 0
    assert prep_df.iloc[0]["Product_Display"] == "Mouse"

# 20. Empty dataframe graceful response
def test_empty_dataframe():
    df = pd.DataFrame(columns=["OrderID", "OrderDate", "ProductID", "ProductName", "Quantity", "UnitPrice"])
    prep_df, meta = prepare_product_dataset(df)
    
    assert prep_df.empty
    assert meta["product_eligible_rows"] == 0
    
    perf = get_product_performance(prep_df)
    assert perf.empty
    
    kpis = calculate_product_kpis(prep_df)
    assert kpis["total_active_products"] == 0

# 21. Missing required product identity (exclusions details)
def test_missing_product_identity_exclusions(base_test_df):
    # Modify rows to lack both fields or be NaN
    df = base_test_df.copy()
    df.loc[0, "ProductID"] = np.nan
    df.loc[0, "ProductName"] = np.nan
    
    prep_df, meta = prepare_product_dataset(df)
    # The first row (index 0) must be excluded
    assert len(prep_df) == len(base_test_df) - 1
    assert meta["product_exclusions"]["missing_product_identity"] == 1

# 22. Input DataFrame non-mutation validation
def test_input_dataframe_non_mutation(base_test_df):
    df_copy = base_test_df.copy()
    _, _ = prepare_product_dataset(df_copy)
    
    assert df_copy.equals(base_test_df)

# 23. Consistency in basic exclusions with Analytics engine
def test_consistency_in_basic_exclusions(base_test_df):
    # Setup data with a negative UnitPrice
    df = base_test_df.copy()
    df.loc[0, "UnitPrice"] = -10.0
    
    prep_p, meta_p = prepare_product_dataset(df)
    prep_a, meta_a = prepare_analytics_dataset(df)
    
    # Basic exclusions must match
    assert meta_p["exclusions"]["invalid_price"] == meta_a["exclusions"]["invalid_price"]
    assert len(prep_p) == len(prep_a)

# 24. Product capability detection
def test_product_capability_detection(base_test_df):
    caps = detect_product_capabilities(base_test_df)
    assert caps["product_identity_available"] is True
    assert caps["quantity_analysis_available"] is True
    assert caps["revenue_analysis_available"] is True
    
    caps_empty = detect_product_capabilities(None)
    assert caps_empty["product_identity_available"] is False
