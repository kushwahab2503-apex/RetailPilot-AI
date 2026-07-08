import pandas as pd
import numpy as np
import pytest
from datetime import datetime, timedelta

from backend.customer_engine import (
    prepare_customer_dataset,
    assign_tie_aware_scores,
    calculate_lifetime_customer_base,
    get_customer_period_performance,
    calculate_customer_kpis,
    get_repeat_vs_onetime_summary,
    get_customer_ranking_views,
    get_customer_concentration_data,
    get_geographic_customer_performance,
    get_cohort_matrix_data,
    detect_customer_capabilities
)
from backend.analytics_engine import prepare_analytics_dataset

@pytest.fixture
def base_sample_data():
    """Provides a baseline robust customer dataset trace."""
    data = {
        "OrderID": ["O1", "O1", "O2", "O3", "O4", "O5", "O6"],
        "OrderDate": [
            "2026-01-10", "2026-01-10", "2026-01-15", 
            "2026-02-10", "2026-03-01", "2026-03-05", "2026-03-15"
        ],
        "CustomerID": ["C100", "C100", "C100", "C200", "C300", "C400", "C500"],
        "CustomerName": ["Alice", "Alice", "Alice", "Bob", "Charlie", "David", "Eve"],
        "ProductID": ["P1", "P2", "P1", "P2", "P3", "P1", "P3"],
        "ProductName": ["Widget A", "Widget B", "Widget A", "Widget B", "Gadget X", "Widget A", "Gadget X"],
        "Category": ["Electronics", "Electronics", "Electronics", "Electronics", "Home", "Electronics", "Home"],
        "Quantity": [2, 1, 3, 1, 5, 2, 1],
        "UnitPrice": [100.0, 150.0, 100.0, 200.0, 50.0, 100.0, 300.0],
        "DiscountPct": [0, 0, 10, 0, 20, 0, 0],
        "City": ["Mumbai", "Mumbai", "Mumbai", "Delhi", "Bangalore", "Delhi", "Mumbai"]
    }
    return pd.DataFrame(data)

def test_customer_aggregation_correctness(base_sample_data):
    prep_df, _ = prepare_customer_dataset(base_sample_data)
    life_df = calculate_lifetime_customer_base(prep_df)
    
    # Alice (C100|Alice) - Orders O1 (items Widget A/B) and O2 (Item Widget A)
    # Revenues in O1: 2*100 = 200, 1*150 = 150. Total = 350.0
    # Revenues in O2: 3*100*(1 - 0.1) = 270.0
    # Alice total: 620.0
    alice_row = life_df[life_df["Customer_Key"] == "C100|Alice"].iloc[0]
    assert alice_row["Lifetime_Revenue"] == 620.0
    assert alice_row["Lifetime_Unique_Orders"] == 2
    assert alice_row["Lifetime_Repeat_Status"] == "Repeat Customer"

def test_repeated_order_id_handling(base_sample_data):
    prep_df, _ = prepare_customer_dataset(base_sample_data)
    life_df = calculate_lifetime_customer_base(prep_df)
    
    # Alice has O1 listed twice (2 different products). This should resolve to 2 unique orders (O1, O2)
    alice_row = life_df[life_df["Customer_Key"] == "C100|Alice"].iloc[0]
    assert alice_row["Lifetime_Unique_Orders"] == 2

def test_unique_order_counts(base_sample_data):
    prep_df, _ = prepare_customer_dataset(base_sample_data)
    ord_summary = prep_df.groupby("Customer_Key")["OrderID"].nunique()
    assert ord_summary["C100|Alice"] == 2
    assert ord_summary["C200|Bob"] == 1

def test_revenue_consistency_with_analytics_engine(base_sample_data):
    prep_cust, _ = prepare_customer_dataset(base_sample_data)
    prep_anal, _ = prepare_analytics_dataset(base_sample_data)

    cust_tot = prep_cust["_Revenue"].sum()
    anal_tot = prep_anal["_Revenue"].sum()
    
    # Check that they match exactly since we wrap analytics dataset preparation
    assert cust_tot == anal_tot

def test_units_purchased(base_sample_data):
    prep_df, _ = prepare_customer_dataset(base_sample_data)
    perf = get_customer_period_performance(prep_df, calculate_lifetime_customer_base(prep_df))
    
    alice_perf = perf[perf["Customer_Key"] == "C100|Alice"].iloc[0]
    # Alice purchased: 2 (O1) + 1 (O1) + 3 (O2) = 6 units
    assert alice_perf["Filtered_Units_Purchased"] == 6

def test_average_order_value(base_sample_data):
    prep_df, _ = prepare_customer_dataset(base_sample_data)
    perf = get_customer_period_performance(prep_df, calculate_lifetime_customer_base(prep_df))
    
    alice_perf = perf[perf["Customer_Key"] == "C100|Alice"].iloc[0]
    # Total Revenue 620.0, Orders 2 -> AOV = 310.0
    assert alice_perf["Filtered_AOV"] == 310.0

def test_purchase_span_dates(base_sample_data):
    prep_df, _ = prepare_customer_dataset(base_sample_data)
    life_df = calculate_lifetime_customer_base(prep_df)
    
    alice_row = life_df[life_df["Customer_Key"] == "C100|Alice"].iloc[0]
    assert alice_row["Lifetime_First_Purchase_Date"] == pd.Timestamp("2026-01-10")
    assert alice_row["Lifetime_Last_Purchase_Date"] == pd.Timestamp("2026-01-15")
    # DateSpan = 5 days
    assert alice_row["Days_Since_Last_Purchase_Lifetime"] == (pd.Timestamp("2026-03-15") - pd.Timestamp("2026-01-15")).days

def test_repeat_customer_classification(base_sample_data):
    prep_df, _ = prepare_customer_dataset(base_sample_data)
    life_db = calculate_lifetime_customer_base(prep_df)

    repeats = life_db[life_db["Lifetime_Repeat_Status"] == "Repeat Customer"]["Customer_Key"].tolist()
    onetimes = life_db[life_db["Lifetime_Repeat_Status"] == "One-Time Customer"]["Customer_Key"].tolist()

    assert "C100|Alice" in repeats
    assert "C200|Bob" in onetimes

def test_repeat_customer_rate(base_sample_data):
    prep_df, _ = prepare_customer_dataset(base_sample_data)
    life_db = calculate_lifetime_customer_base(prep_df)
    kpis = calculate_customer_kpis(prep_df, life_db)

    # Alice is the only repeat customer out of 5 total customers (Alice, Bob, Charlie, David, Eve)
    # Rate: 1 / 5 = 20%
    assert kpis["repeat_customer_rate_lifetime"] == 20.0
    assert kpis["onetime_customer_rate_lifetime"] == 80.0

def test_revenue_share_totals(base_sample_data):
    prep_df, _ = prepare_customer_dataset(base_sample_data)
    life_db = calculate_lifetime_customer_base(prep_df)
    perf = get_customer_period_performance(prep_df, life_db)

    shares = perf["Revenue_Share_Pct"].sum()
    assert pytest.approx(shares, 0.001) == 100.0

def test_deterministic_ranking_tie_breakers(base_sample_data):
    # Setup data where Bob and Charlie have identical revenues (say 200.0)
    data = {
        "OrderID": ["O1", "O2"],
        "OrderDate": ["2026-01-10", "2026-01-12"],
        "CustomerID": ["C200", "C100"],
        "CustomerName": ["Charlie", "Bob"],  # Alphabetical: Bob < Charlie
        "ProductID": ["P1", "P1"],
        "ProductName": ["W", "W"],
        "Category": ["Cat", "Cat"],
        "Quantity": [2, 2],
        "UnitPrice": [100.0, 100.0],
        "DiscountPct": [0, 0]
    }
    df = pd.DataFrame(data)
    prep_df, _ = prepare_customer_dataset(df)
    life_db = calculate_lifetime_customer_base(prep_df)
    perf = get_customer_period_performance(prep_df, life_db)

    # Bob and Charlie both have 200.0 revenue.
    # Deterministic tie-breaker Customer_Display ascending: "[C100] Bob" should sort before "[C200] Charlie"
    assert perf.iloc[0]["Customer_Display"] == "[C100] Bob"
    assert perf.iloc[1]["Customer_Display"] == "[C200] Charlie"

def test_top_customer_kpi(base_sample_data):
    prep_df, _ = prepare_customer_dataset(base_sample_data)
    life_db = calculate_lifetime_customer_base(prep_df)
    kpis = calculate_customer_kpis(prep_df, life_db)

    assert kpis["top_customer_by_revenue_period"] == "[C100] Alice"

def test_customer_concentration_calculations(base_sample_data):
    prep_df, _ = prepare_customer_dataset(base_sample_data)
    life_db = calculate_lifetime_customer_base(prep_df)
    concent_df, meta = get_customer_concentration_data(prep_df, life_db)

    # Cumulative Pct should sum up to 100 on the last row
    assert pytest.approx(concent_df.iloc[-1]["Cumulative Pct"], 0.001) == 100.0
    assert meta["total_active_customers"] == 5

def test_segmentation_determinism(base_sample_data):
    prep_df, _ = prepare_customer_dataset(base_sample_data)
    life_db = calculate_lifetime_customer_base(prep_df)

    # Checking that segments are successfully calculated
    assert "Lifetime_Segment" in life_db.columns
    assert life_db["Lifetime_Segment"].isna().sum() == 0

def test_identical_rfm_metric_values_get_identical_scores():
    # Make a frequency metric with multiple ties:
    # 5 customers, 4 have Frequency=1, 1 has Frequency=5
    s = pd.Series([1, 1, 1, 1, 5])
    scores = assign_tie_aware_scores(s, ascending=True)

    # Identical values ([1, 1, 1, 1]) must receive identical scores inside the series!
    assert scores[0] == scores[1] == scores[2] == scores[3]
    # The higher frequency value (5) must receive a higher score:
    assert scores[4] > scores[0]

def test_duplicate_heavy_distributions():
    # Extremely skewed case: 99 buyers with Frequency=1, 1 buyer with Frequency=100
    freqs = pd.Series([1] * 99 + [100])
    scores = assign_tie_aware_scores(freqs, ascending=True)
    
    # Check that it doesn't crash (like qcut would) and maps properly
    assert len(scores) == 100
    assert scores[99] == 5 # 100 gets maximum score
    assert scores[0] == 1   # 1s get minimum score

def test_collapsed_monetary_distributions():
    # All buyers have purchase value 250.0
    monetary = pd.Series([250.0, 250.0, 250.0])
    scores = assign_tie_aware_scores(monetary, ascending=True)
    
    # All buyers must receive the constant fallback score 5
    assert (scores == 5).all()

def test_fewer_than_point_5_customers():
    # Only 3 customers
    revenues = pd.Series([10.0, 50.0, 100.0])
    scores = assign_tie_aware_scores(revenues, ascending=True)
    
    assert scores.iloc[0] == 1 # 10.0 gets index 0 -> Score 1
    assert scores.iloc[1] == 3 # 50.0 gets index 1 -> Score 3
    assert scores.iloc[2] == 5 # 100.0 gets index 2 -> Score 5

def test_single_customer_dataset():
    # 1 customer
    revenues = pd.Series([999.0])
    scores = assign_tie_aware_scores(revenues, ascending=True)
    
    assert scores.iloc[0] == 5

def test_customer_id_only_fallback():
    # CustomerName is missing, CustomerID is present
    data = {
        "OrderID": ["O1"], "OrderDate": ["2026-01-10"], "CustomerID": ["C999"],
        "ProductID": ["P1"], "ProductName": ["W"], "Category": ["Cat"], "Quantity": [1], "UnitPrice": [50.0]
    }
    prep_df, meta = prepare_customer_dataset(pd.DataFrame(data))
    assert prep_df.iloc[0]["Customer_Key"] == "C999"
    assert prep_df.iloc[0]["Customer_Display"] == "C999"
    assert meta["customer_exclusions"]["missing_customer_identity"] == 0

def test_customer_name_only_fallback():
    # CustomerID is missing, CustomerName is present
    data = {
        "OrderID": ["O1"], "OrderDate": ["2026-01-10"], "CustomerName": ["Dave Sparks"],
        "ProductID": ["P1"], "ProductName": ["W"], "Category": ["Cat"], "Quantity": [1], "UnitPrice": [50.0]
    }
    prep_df, meta = prepare_customer_dataset(pd.DataFrame(data))
    assert prep_df.iloc[0]["Customer_Key"] == "Dave Sparks"
    assert prep_df.iloc[0]["Customer_Display"] == "Dave Sparks"
    assert meta["customer_exclusions"]["missing_customer_identity"] == 0

def test_missing_customer_identity_handling():
    # Both are NaN/empty
    data = {
        "OrderID": ["O1"], "OrderDate": ["2026-01-10"],
        "ProductID": ["P1"], "ProductName": ["W"], "Category": ["Cat"], "Quantity": [1], "UnitPrice": [50.0]
    }
    prep_df, meta = prepare_customer_dataset(pd.DataFrame(data))
    assert prep_df.empty
    assert meta["customer_exclusions"]["missing_customer_identity"] == 1

def test_city_analytics(base_sample_data):
    prep_df, _ = prepare_customer_dataset(base_sample_data)
    life_db = calculate_lifetime_customer_base(prep_df)
    city_df = get_geographic_customer_performance(prep_df, life_db)

    assert "Mumbai" in city_df["City"].values
    assert city_df[city_df["City"] == "Mumbai"].iloc[0]["Active Customers"] == 2

def test_missing_city_handling():
    data = {
        "OrderID": ["O1"], "OrderDate": ["2026-01-10"], "CustomerID": ["C1"],
        "ProductID": ["P1"], "ProductName": ["W"], "Category": ["Cat"], "Quantity": [1], "UnitPrice": [50.0]
    }
    prep_df, _ = prepare_customer_dataset(pd.DataFrame(data))
    life_db = calculate_lifetime_customer_base(prep_df)
    city_df = get_geographic_customer_performance(prep_df, life_db)
    
    assert city_df is None # returns None when column is absent

def test_empty_dataframe_handling():
    prep_df, meta = prepare_customer_dataset(pd.DataFrame())
    assert prep_df.empty
    assert "working_row_count" in meta
    assert "eligible_row_count" in meta
    assert "customer_eligible_rows" in meta
    assert "customer_exclusions" in meta
    assert "missing_customer_identity" in meta["customer_exclusions"]
    assert meta["working_row_count"] == 0
    assert meta["eligible_row_count"] == 0
    assert meta["customer_eligible_rows"] == 0
    assert meta["customer_exclusions"]["missing_customer_identity"] == 0

    life_db = calculate_lifetime_customer_base(prep_df)
    assert life_db.empty

    perf = get_customer_period_performance(prep_df, life_db)
    assert perf.empty

def test_input_dataframe_non_mutation(base_sample_data):
    df_copy = base_sample_data.copy()
    prepare_customer_dataset(base_sample_data)
    pd.testing.assert_frame_equal(base_sample_data, df_copy)

def test_capabilities_verification(base_sample_data):
    caps = detect_customer_capabilities(base_sample_data)
    assert caps["customer_identity_available"] is True
    assert caps["city_available"] is True

def test_historical_repeat_customer_remains_repeat_in_filtered_period(base_sample_data):
    prep_df, _ = prepare_customer_dataset(base_sample_data)
    life_db = calculate_lifetime_customer_base(prep_df)
    
    # Alice is historically a "Repeat Customer" (orders = 2)
    alice_base = life_db[life_db["Customer_Key"] == "C100|Alice"].iloc[0]
    assert alice_base["Lifetime_Repeat_Status"] == "Repeat Customer"

    # Filter transactions so that ONLY Alice's order O2 is included (date: 2026-01-15)
    filtered = prep_df[prep_df["OrderDate"] == "2026-01-15"].copy()
    perf = get_customer_period_performance(filtered, life_db)
    
    alice_perf = perf[perf["Customer_Key"] == "C100|Alice"].iloc[0]
    # Check that in output performance table Alice's repeat status remains "Repeat Customer"
    assert alice_perf["Lifetime_Repeat_Status"] == "Repeat Customer"
    # Even though in this filtered period she has only 1 order
    assert alice_perf["Filtered_Orders"] == 1

def test_filtered_kpis_change_while_historical_classification_stable(base_sample_data):
    prep_df, _ = prepare_customer_dataset(base_sample_data)
    life_db = calculate_lifetime_customer_base(prep_df)

    # Setup base KPIs
    all_kpis = calculate_customer_kpis(prep_df, life_db)
    assert all_kpis["active_customers_period"] == 5

    # Filter to March date range (Charlie, David, Eve are active: total 3 customers)
    march_df = prep_df[prep_df["OrderDate"] >= "2026-03-01"].copy()
    filtered_kpis = calculate_customer_kpis(march_df, life_db)
    
    assert filtered_kpis["active_customers_period"] == 3
    # Check that repeat customer rate (which is a lifetime base metric) remains exactly stable (20.0%)
    assert filtered_kpis["repeat_customer_rate_lifetime"] == 20.0

def test_cohort_disabled_when_population_or_coverage_is_insufficient(base_sample_data):
    # base_sample_data has 5 customers spanning Jan to March (3 unique months, span 60 days).
    # Cohort analysis should be enabled:
    caps = detect_customer_capabilities(base_sample_data)
    assert caps["cohort_analysis_available"] is True

    # Now make customer population 3 (fewer than 5 customers)
    small_pop = base_sample_data[base_sample_data["CustomerID"].isin(["C100", "C200", "C300"])].copy()
    caps_small = detect_customer_capabilities(small_pop)
    assert caps_small["cohort_analysis_available"] is False

    # Now make date span short (all orders within Jan, i.e., span < 60 days)
    short_date = base_sample_data.copy()
    short_date["OrderDate"] = "2026-01-10"
    caps_short = detect_customer_capabilities(short_date)
    assert caps_short["cohort_analysis_available"] is False

def test_segment_filter_uses_historical_segmentation(base_sample_data):
    prep_df, _ = prepare_customer_dataset(base_sample_data)
    life_db = calculate_lifetime_customer_base(prep_df)

    # Let's select customers with Lifetime_Segment = "Champions"
    # Find which customers are champions:
    champs_keys = life_db[life_db["Lifetime_Segment"] == "Champions"]["Customer_Key"].tolist()
    
    # Simulate segment filter input = ["Champions"]
    filtered_customers = life_db[life_db["Lifetime_Segment"].isin(["Champions"])]
    
    # Filter transactions database using that list of champions
    filtered_tx = prep_df[prep_df["Customer_Key"].isin(filtered_customers["Customer_Key"])]
    
    # Calculating stats
    perf = get_customer_period_performance(filtered_tx, life_db)
    
    # Non-champs must have 0 filtered revenue because their transactions were filtered out
    for _, row in perf.iterrows():
        if row["Customer_Key"] not in champs_keys:
            assert row["Filtered_Revenue"] == 0.0

def test_metadata_contract_valid_dataset(base_sample_data):
    prepared_df, meta = prepare_customer_dataset(base_sample_data)
    assert meta["working_row_count"] == len(base_sample_data)
    assert meta["customer_eligible_rows"] == len(prepared_df)
    assert meta["customer_exclusions"]["missing_customer_identity"] == 0
    # No records were excluded due to customer identity, so eligible_row_count equals valid_row_count
    assert meta["eligible_row_count"] == meta["valid_row_count"]

def test_metadata_contract_missing_customer_identity(base_sample_data):
    # Strip CustomerID and CustomerName columns
    no_cust = base_sample_data.drop(columns=["CustomerID", "CustomerName"])
    prepared_df, meta = prepare_customer_dataset(no_cust)
    assert prepared_df.empty
    assert meta["working_row_count"] == len(base_sample_data)
    assert meta["customer_eligible_rows"] == 0
    # All valid rows processed by base analytics engine are excluded because they have no customer info
    assert meta["customer_exclusions"]["missing_customer_identity"] == meta["valid_row_count"]
    # Final eligible_row_count should be 0
    assert meta["eligible_row_count"] == 0
