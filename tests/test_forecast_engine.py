import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from backend.forecast_engine import (
    prepare_forecast_dataset,
    detect_forecast_capabilities,
    fill_missing_periods,
    calculate_trend_diagnostics,
    evaluate_models,
    generate_forecast,
    evaluate_seasonal_naive_eligibility
)
from backend.analytics_engine import prepare_analytics_dataset, aggregate_time_series


# Helper to generate a contiguously filled range of dummy dates
def make_dummy_data(n_days: int, sales_pattern: str = "daily", start_date: str = "2026-07-01") -> pd.DataFrame:
    base = datetime.strptime(start_date, "%Y-%m-%d")
    rows = []
    
    for i in range(n_days):
        curr_date = base + timedelta(days=i)
        
        # Decide if this date has sales
        has_sales = True
        if sales_pattern == "sparse":
            # Only sales every 7th day
            has_sales = (i % 7 == 0)
        elif sales_pattern == "none":
            has_sales = False
            
        if has_sales:
            rows.append({
                "OrderID": f"ORD{i}",
                "OrderDate": curr_date.strftime("%Y-%m-%d"),
                "Quantity": 2,
                "UnitPrice": 100.0,
                "Category": "Office Supplies",
                "DiscountPct": 0.0
            })
            
    if not rows:
        # Return empty conforming structure
        return pd.DataFrame(columns=["OrderID", "OrderDate", "Quantity", "UnitPrice", "Category", "DiscountPct"])
        
    return pd.DataFrame(rows)


def test_empty_and_insufficient_metadata_contracts():
    # 1. EMPTY DATASET
    empty_df = pd.DataFrame()
    prep_df, meta = prepare_forecast_dataset(empty_df)
    
    assert prep_df.empty
    assert meta["capability_state"] == "UNAVAILABLE"
    # Essential keys checklist
    required_keys = [
        "working_row_count", "eligible_row_count", "aggregated_period_count",
        "non_zero_period_count", "date_span_days", "coverage_ratio",
        "selected_frequency", "capability_state", "capability_reasons", "validation_status"
    ]
    for key in required_keys:
        assert key in meta

    # 2. INSUFFICIENT DATASET (3 records spanning 2 days)
    insuf_df = pd.DataFrame({
        "OrderID": ["ORD1", "ORD2", "ORD3"],
        "OrderDate": ["2026-07-01", "2026-07-01", "2026-07-02"],
        "Quantity": [1, 1, 1],
        "UnitPrice": [10.0, 10.0, 10.0],
        "Category": "Peripherals"
    })
    prep_df, meta = prepare_forecast_dataset(insuf_df)
    caps = detect_forecast_capabilities(prep_df, "Daily")
    assert caps["capability_state"] == "UNAVAILABLE"
    for key in required_keys:
        assert key in caps


def test_exhaustive_capability_boundary_days():
    # 1. 13 Days vs 14 Days Boundary
    # 13 Days: Span from 2026-07-01 to 2026-07-14 (13 days offset)
    df_13 = make_dummy_data(14, sales_pattern="daily")  # 14 records, 13 days span
    prep_13, _ = prepare_forecast_dataset(df_13)
    caps_13 = detect_forecast_capabilities(prep_13, "Daily")
    assert caps_13["date_span_days"] == 13
    assert caps_13["capability_state"] == "UNAVAILABLE"
    assert "Date span is too short" in "".join(caps_13["capability_reasons"])

    # 14 Days: Span from 2026-07-01 to 2026-07-15 (14 days offset)
    df_14 = make_dummy_data(15, sales_pattern="daily")  # 15 records, 14 days span
    prep_14, _ = prepare_forecast_dataset(df_14)
    caps_14 = detect_forecast_capabilities(prep_14, "Daily")
    assert caps_14["date_span_days"] == 14
    # With 15 daily records, N=15, N_nz=15, coverage=1.0. This is at least LIMITED (passes unavailable min criteria)
    assert caps_14["capability_state"] in ["LIMITED", "SUITABLE"]


def test_exhaustive_capability_boundary_coverage():
    # 2. Coverage 0.19 vs 0.20 Boundary
    # Daily aggregation parameters: M = 14. We need a grid of size 100 so coverage can be set precisely.
    # Write custom dates list. 100 days span.
    # If 19 of them are active, coverage = 19/100 = 0.19. Must be UNAVAILABLE.
    dates_19 = [datetime(2026, 7, 1) + timedelta(days=i) for i in range(100)]
    rows_19 = []
    # Fill exactly 19 days with positive sales
    for idx, d in enumerate(dates_19):
        if idx < 19:
            rows_19.append({
                "OrderID": f"ORD{idx}", "OrderDate": d.strftime("%Y-%m-%d"),
                "Quantity": 1, "UnitPrice": 50.0, "Category": "Hardware"
            })
    # Add a transaction on day 99 with price 0.0 to lock the span to 100 days without increasing non-zero count
    rows_19.append({
        "OrderID": "ORD99", "OrderDate": dates_19[99].strftime("%Y-%m-%d"),
        "Quantity": 1, "UnitPrice": 0.0, "Category": "Hardware"
    })
    df_19 = pd.DataFrame(rows_19)
    prep_19, _ = prepare_forecast_dataset(df_19)
    caps_19 = detect_forecast_capabilities(prep_19, "Daily")
    assert caps_19["coverage_ratio"] == 0.19
    assert caps_19["capability_state"] == "UNAVAILABLE"

    # If 20 of them are active, coverage = 20/100 = 0.20. Must be LIMITED/SUITABLE.
    rows_20 = []
    for idx, d in enumerate(dates_19):
        if idx < 20:
            rows_20.append({
                "OrderID": f"ORD{idx}", "OrderDate": d.strftime("%Y-%m-%d"),
                "Quantity": 1, "UnitPrice": 50.0, "Category": "Hardware"
            })
    rows_20.append({
        "OrderID": "ORD99", "OrderDate": dates_19[99].strftime("%Y-%m-%d"),
        "Quantity": 1, "UnitPrice": 0.0, "Category": "Hardware"
    })
    df_20 = pd.DataFrame(rows_20)
    prep_20, _ = prepare_forecast_dataset(df_20)
    caps_20 = detect_forecast_capabilities(prep_20, "Daily")
    assert caps_20["coverage_ratio"] == 0.20
    assert caps_20["capability_state"] in ["LIMITED", "SUITABLE"]


def test_exhaustive_capability_boundary_coverage_suitable():
    # 3. Coverage 0.49 vs 0.50 Boundary (SUITABLE threshold)
    # Target parameter inputs: span = 50 days (>= 45), N = 50 (>= M+H = 21), N_nz = 24 or 25.
    # 24/50 = 0.48 (fails suitability), 25/50 = 0.50 (meets suitability coverage >=0.5)
    base_dates = [datetime(2026, 7, 1) + timedelta(days=i) for i in range(50)]
    
    # 24 active elements
    rows_24 = []
    for i in range(24):
        rows_24.append({
            "OrderID": f"ORD{i}", "OrderDate": base_dates[i].strftime("%Y-%m-%d"),
            "Quantity": 1, "UnitPrice": 50.0, "Category": "A"
        })
    # Add one at the end step to lock the 50 days span
    rows_24.append({
        "OrderID": "ORD49", "OrderDate": base_dates[49].strftime("%Y-%m-%d"),
        "Quantity": 1, "UnitPrice": 50.0, "Category": "A"
    })
    df_24 = pd.DataFrame(rows_24) # N_nz = 25 (the 24 + index 49), N = 50. Wait, coverage = 25/50 = 0.50.
    # Let's adjust counts to get exactly 24/50 = 0.48
    rows_24_exact = []
    for i in range(23):
        rows_24_exact.append({
            "OrderID": f"ORD{i}", "OrderDate": base_dates[i].strftime("%Y-%m-%d"),
            "Quantity": 1, "UnitPrice": 50.0, "Category": "A"
        })
    rows_24_exact.append({
        "OrderID": "ORD49", "OrderDate": base_dates[49].strftime("%Y-%m-%d"),
        "Quantity": 1, "UnitPrice": 50.0, "Category": "A"
    })
    df_24_exact = pd.DataFrame(rows_24_exact) # N_nz = 24, N = 50. Coverage = 0.48
    prep_24, _ = prepare_forecast_dataset(df_24_exact)
    caps_24 = detect_forecast_capabilities(prep_24, "Daily")
    assert caps_24["coverage_ratio"] == 0.48
    assert caps_24["capability_state"] == "LIMITED"  # Fails suitability due to coverage < 0.50

    # 25 active elements. Coverage = 25/50 = 0.50
    rows_25 = []
    for i in range(24):
        rows_25.append({
            "OrderID": f"ORD{i}", "OrderDate": base_dates[i].strftime("%Y-%m-%d"),
            "Quantity": 1, "UnitPrice": 50.0, "Category": "A"
        })
    rows_25.append({
        "OrderID": "ORD49", "OrderDate": base_dates[49].strftime("%Y-%m-%d"),
        "Quantity": 1, "UnitPrice": 50.0, "Category": "A"
    })
    df_25 = pd.DataFrame(rows_25)
    prep_25, _ = prepare_forecast_dataset(df_25)
    caps_25 = detect_forecast_capabilities(prep_25, "Daily")
    assert caps_25["coverage_ratio"] == 0.50
    assert caps_25["capability_state"] == "SUITABLE"


def test_exhaustive_capability_boundary_span_days():
    # 4. 44 Days vs 45 Days Boundary for SUITABLE state
    # 44 Days span: 2026-07-01 to 2026-08-15 (45 elements, span is 44 days).
    # All other suitable conditions pass (N=45 >= 21, N_nz=45 >= 5, coverage=1.0 >= 0.5).
    df_44 = make_dummy_data(45, sales_pattern="daily")
    prep_44, _ = prepare_forecast_dataset(df_44)
    caps_44 = detect_forecast_capabilities(prep_44, "Daily")
    assert caps_44["date_span_days"] == 44
    assert caps_44["capability_state"] == "LIMITED" # Fails suitability due to span < 45

    # 45 Days span: 2026-07-01 to 2026-08-16 (46 elements, span is 45 days).
    df_45 = make_dummy_data(46, sales_pattern="daily")
    prep_45, _ = prepare_forecast_dataset(df_45)
    caps_45 = detect_forecast_capabilities(prep_45, "Daily")
    assert caps_45["date_span_days"] == 45
    assert caps_45["capability_state"] == "SUITABLE"


def test_exhaustive_capability_boundary_periods():
    # 5. Exactly M periods (Daily M=14)
    # N=14. Span is 13. UNAVAILABLE because span < 14.
    # Let's write dates such that span is >= 14, but N is exactly 14.
    # E.g., transaction on day 0, then day 3, 6, ..., day 39.
    # 14 periods, start to end is 39 days.
    dates_m = [datetime(2026, 7, 1) + timedelta(days=3 * i) for i in range(14)]
    rows_m = [{
        "OrderID": f"ORD{idx}", "OrderDate": d.strftime("%Y-%m-%d"),
        "Quantity": 1, "UnitPrice": 50.0, "Category": "Hardware"
    } for idx, d in enumerate(dates_m)]
    df_m = pd.DataFrame(rows_m)
    prep_m, _ = prepare_forecast_dataset(df_m)
    caps_m = detect_forecast_capabilities(prep_m, "Daily")
    # After filling missing periods on Daily freq, the total span is 39 days.
    # So N will be 40 periods!
    # To test exactly N = M = 14 aggregated period count, we must feed in 14 consecutive daily records.
    # Wait, 14 consecutive daily records gives span = 13 days, which triggers UNAVAILABLE because span < 14.
    # If we stretch the calendar to span = 14 days, the filled size N will be 15.
    # Is there a frequency where we can check this? Yes! Weekly.
    # Weekly aggregation: M = 8.
    # Let's generate consecutive weekly dates: 8 weeks span (8 periods).
    # Week start dates: Monday of 8 consecutive weeks.
    # Span in days: 7 * 7 = 49 days.
    # Aggregated period count N = 8.
    # Let's verify:
    weekly_dates = [datetime(2026, 7, 6) + timedelta(weeks=i) for i in range(8)]
    rows_w = [{
        "OrderID": f"ORD{idx}", "OrderDate": d.strftime("%Y-%m-%d"),
        "Quantity": 1, "UnitPrice": 50.0, "Category": "Hardware"
    } for idx, d in enumerate(weekly_dates)]
    df_w = pd.DataFrame(rows_w)
    prep_w, _ = prepare_forecast_dataset(df_w)
    caps_w = detect_forecast_capabilities(prep_w, "Weekly")
    assert caps_w["aggregated_period_count"] == 8
    # Since N = 8 >= M (8). It is LIMITED.
    assert caps_w["capability_state"] in ["LIMITED", "SUITABLE"]

    # What if we have N = 7 < M? Weekly M = 8.
    weekly_dates_7 = [datetime(2026, 7, 6) + timedelta(weeks=i) for i in range(7)]
    rows_w7 = [{
        "OrderID": f"ORD{idx}", "OrderDate": d.strftime("%Y-%m-%d"),
        "Quantity": 1, "UnitPrice": 50.0, "Category": "Hardware"
    } for idx, d in enumerate(weekly_dates_7)]
    df_w7 = pd.DataFrame(rows_w7)
    prep_w7, _ = prepare_forecast_dataset(df_w7)
    caps_w7 = detect_forecast_capabilities(prep_w7, "Weekly")
    assert caps_w7["aggregated_period_count"] == 7
    # Since N = 7 < M (8), it must evaluate to UNAVAILABLE
    assert caps_w7["capability_state"] == "UNAVAILABLE"


def test_exhaustive_capability_boundary_periods_m_plus_h():
    # 6. Exactly M + H periods (Daily M=14, H=7 => 21 periods)
    # Let's construct a dataset with exactly 21 consecutive daily records (span = 20 days).
    # Since span = 20 days < 45 days, capability state is LIMITED.
    # But since N = 21 >= M+H (21), validation status is "Validated (Full)".
    df_21 = make_dummy_data(21, sales_pattern="daily")
    prep_21, _ = prepare_forecast_dataset(df_21)
    caps_21 = detect_forecast_capabilities(prep_21, "Daily")
    assert caps_21["aggregated_period_count"] == 21
    assert caps_21["validation_status"] == "Validated (Full)"
    assert caps_21["capability_state"] == "LIMITED"

    # If N = 20 < M+H (21) (span = 19 days).
    df_20 = make_dummy_data(20, sales_pattern="daily")
    prep_20, _ = prepare_forecast_dataset(df_20)
    caps_20 = detect_forecast_capabilities(prep_20, "Daily")
    assert caps_20["aggregated_period_count"] == 20
    assert caps_20["validation_status"] == "Validated (Compressed)"


def test_sparse_dates_long_date_span():
    # Sparse dates across a long date span must NOT automatically become SUITABLE
    # Span of 100 days (>= 45), but only 10 days have sales (sparsity test)
    # coverage = 10 / 100 = 0.10.
    # Since coverage < 0.20, state must be UNAVAILABLE due to sparse data checks.
    base_dates = [datetime(2026, 7, 1) + timedelta(days=i) for i in range(100)]
    rows = []
    # Force sales only every 10th elements (size 10 total)
    for i in range(0, 100, 10):
        rows.append({
            "OrderID": f"ORD{i}",
            "OrderDate": base_dates[i].strftime("%Y-%m-%d"),
            "Quantity": 1,
            "UnitPrice": 100.0,
            "Category": "Furniture"
        })
    df = pd.DataFrame(rows)
    prep_df, _ = prepare_forecast_dataset(df)
    caps = detect_forecast_capabilities(prep_df, "Daily")
    assert caps["date_span_days"] == 90
    assert caps["coverage_ratio"] == pytest.approx(0.10989, abs=0.001)
    assert caps["capability_state"] == "UNAVAILABLE"


def test_zero_target_validation_semantics():
    # If validation actual revenue sums to zero:
    # - WAPE = None
    # - MAE and RMSE remain valid
    # - validation_status must evaluate to "Validated (WAPE Unavailable — Zero Target)"
    # We construct a dataset where history has values but holdout validation period has exactly zero revenue.
    # Daily aggregation: N = 21. Let's make indices 0..13 positive revenue, 14..20 zero revenue.
    dates = [datetime(2026, 7, 1) + timedelta(days=i) for i in range(21)]
    rows = []
    for i in range(21):
        # validation splits last H=7 steps => indices 14..20. Let's set quantity=0 or no transactions there.
        # Wait, if there are no transactions, fill_missing_periods will make it zero.
        # So we only add transactions for first 14 days.
        if i < 14:
            rows.append({
                "OrderID": f"ORD{i}",
                "OrderDate": dates[i].strftime("%Y-%m-%d"),
                "Quantity": 1,
                "UnitPrice": 100.0,
                "Category": "Toys"
            })
    # To ensure the span completes to 21 days in filled grid, we need the df to lock the min/max dates
    # But wait, prepared_df max date will be dates[13] if we stop there.
    # To force max date to be dates[20] but with 0 revenue, we can add a dummy row on dates[20] with Quantity=0?
    # No, analytics engine excludes rows with Quantity <= 0.
    # Wait, how does aggregate_time_series or resolve bounds get the calendar limit?
    # In Streamlit dashboard, min_date and max_date inputs are bound by prepared_df min and max dates.
    # If we want the holdout validation period to have 0 actual revenue, we can pass dates[20] as max_date to generate_forecast.
    # Wait, evaluate_models takes `df` which is the aggregated filled dataset.
    # So we can construct the filled aggregated DataFrame directly and pass it to evaluate_models!
    # Let's construct a filled aggregated DataFrame with 21 rows:
    # July 1..14: Revenue = 100.0
    # July 15..21: Revenue = 0.0
    agg_rows = []
    for i in range(21):
        curr_d = datetime(2026, 7, 1) + timedelta(days=i)
        agg_rows.append({
            "Date": curr_d,
            "Revenue": 100.0 if i < 14 else 0.0,
            "Orders": 1 if i < 14 else 0,
            "Units": 1 if i < 14 else 0
        })
    agg_df = pd.DataFrame(agg_rows)
    
    val_info = evaluate_models(agg_df, "Daily", "LIMITED")
    assert val_info["validation_status"] == "Validated (WAPE Unavailable — Zero Target)"
    assert val_info["metrics"]["WAPE"] is None
    assert val_info["metrics"]["MAE"] is not None
    assert val_info["metrics"]["RMSE"] is not None


def test_mae_fallback_model_selection():
    # If WAPE is unavailable in model ranking, falls back to MAE, then RMSE, then priority.
    # Let's create an aggregated DataFrame where:
    # Validation period: Revenue is all zero.
    # Train period: has values.
    # Model 1 (Naive): projects last actual (100.0). MAE on validation = 100.0
    # Model 2 (Linear Trend): fits decreasing trend, say projects 10.0. MAE on validation = 10.0
    # Model 2 should win because it has lower MAE (10.0 < 100.0), even though WAPE is None for both.
    agg_rows = []
    # Let's create a linear trend: 20, 19, 18, ..., 7 (length 14 training).
    # Linear projection will project values around 6, 5, 4, 3, 2, 1, 0. average projection ~ 3.0
    # Naive projection will project 7.0.
    # Since validation target actual is 0.0:
    # Linear Trend error: |0 - 3.0| = 3.0. MAE = 3.0
    # Naive error: |0 - 7.0| = 7.0. MAE = 7.0
    # Linear trend is better because 3.0 < 7.0
    for i in range(21):
        curr_d = datetime(2026, 7, 1) + timedelta(days=i)
        if i < 14:
            rev = float(20 - i)
        else:
            rev = 0.0
        agg_rows.append({
            "Date": curr_d,
            "Revenue": rev,
            "Orders": 1 if rev > 0 else 0,
            "Units": 1 if rev > 0 else 0
        })
    agg_df = pd.DataFrame(agg_rows)
    
    # We call generate_forecast
    results, meta = generate_forecast(agg_df, "Daily", 5, "LIMITED")
    assert meta["validation_status"] == "Validated (WAPE Unavailable — Zero Target)"
    # Linear Trend should be selected because of lower MAE
    assert meta["selected_model"] == "Linear Trend"


def test_unvalidated_fallback_rules():
    # Unvalidated path: do not label any model as Best Model.
    # Select MA-3 if N >= 3 periods, else Naive.
    # 1. Size N = 4 (insufficient for validation which needs M=14) => state = UNAVAILABLE
    agg_4 = pd.DataFrame([
        {"Date": datetime(2026, 7, 1) + timedelta(days=i), "Revenue": float(100 + i), "Orders": 1, "Units": 1}
        for i in range(4)
    ])
    results_4, meta_4 = generate_forecast(agg_4, "Daily", 3, "UNAVAILABLE")
    assert meta_4["selected_model"] == "Moving Average"
    assert meta_4["model_display_name"] == "Fallback Baseline (Unvalidated Projection)"
    assert meta_4["is_validated"] is False
    assert meta_4["validation_metrics"] is None

    # 2. Size N = 2 => fallback matches Naive
    agg_2 = pd.DataFrame([
        {"Date": datetime(2026, 7, 1) + timedelta(days=i), "Revenue": float(100 + i), "Orders": 1, "Units": 1}
        for i in range(2)
    ])
    results_2, meta_2 = generate_forecast(agg_2, "Daily", 3, "UNAVAILABLE")
    assert meta_2["selected_model"] == "Naive"
    assert meta_2["model_display_name"] == "Fallback Baseline (Unvalidated Projection)"
    assert meta_2["is_validated"] is False


def test_category_specific_insufficiency():
    # Evaluate forecast capabilities independently per category.
    # Group A: Dense records (Suitable)
    # Group B: Sparse records (Unavailable)
    rows = []
    base_date = datetime(2026, 7, 1)
    
    # Group A: 50 consecutive days of records
    for i in range(50):
        rows.append({
            "OrderID": f"ORDA{i}",
            "OrderDate": (base_date + timedelta(days=i)).strftime("%Y-%m-%d"),
            "Quantity": 1,
            "UnitPrice": 10.0,
            "Category": "Electronics"
        })
    # Group B: only 2 days of records
    for i in range(2):
        rows.append({
            "OrderID": f"ORDB{i}",
            "OrderDate": (base_date + timedelta(days=i)).strftime("%Y-%m-%d"),
            "Quantity": 1,
            "UnitPrice": 10.0,
            "Category": "Books"
        })
        
    df = pd.DataFrame(rows)
    
    # Test Electronics
    prep_a, _ = prepare_forecast_dataset(df, category="Electronics")
    caps_a = detect_forecast_capabilities(prep_a, "Daily")
    assert caps_a["capability_state"] == "SUITABLE"
    
    # Test Books
    prep_b, _ = prepare_forecast_dataset(df, category="Books")
    caps_b = detect_forecast_capabilities(prep_b, "Daily")
    assert caps_b["capability_state"] == "UNAVAILABLE"


def test_frequency_change_recalculation_and_rejection():
    # 30 days dataset
    df = make_dummy_data(30, sales_pattern="daily")
    prep_df, _ = prepare_forecast_dataset(df)

    # 1. Daily frequency is LIMITED
    caps_daily = detect_forecast_capabilities(prep_df, "Daily")
    assert caps_daily["capability_state"] == "LIMITED"
    assert caps_daily["selected_frequency"] == "Daily"

    # 2. Monthly frequency is UNAVAILABLE (Unsupported frequency rejection)
    caps_monthly = detect_forecast_capabilities(prep_df, "Monthly")
    assert caps_monthly["capability_state"] == "UNAVAILABLE"
    assert caps_monthly["selected_frequency"] == "Monthly"
    assert "Insufficient aggregated periods count" in "".join(caps_monthly["capability_reasons"])

