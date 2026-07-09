import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from backend.insights_engine import (
    generate_business_insights,
    sort_insights,
    deduplicate_insights,
    DOMAIN_ORDER
)


def test_empty_dataframe_contract():
    # Empty inputs
    empty_df = pd.DataFrame()
    res = generate_business_insights(empty_df, generated_from_cleaned_dataset=True)

    # 1. Complete top-level contract keys exist
    expected_top_keys = {
        "insights", "priority_insights", "positive_insights", "watch_insights",
        "risk_insights", "informational_insights", "domain_counts", "severity_counts", "metadata"
    }
    assert set(res.keys()) == expected_top_keys

    # 2. Count keys exist and reflect zero
    expected_domains = {"Revenue", "Customers", "Products", "Order Economics", "Forecast Readiness", "Data Quality"}
    expected_severities = {"Positive", "Informational", "Watch", "Risk"}
    assert set(res["domain_counts"].keys()) == expected_domains
    assert set(res["severity_counts"].keys()) == expected_severities

    # Data Quality counts 1 due to the limitation insight
    assert res["domain_counts"]["Data Quality"] == 1
    assert res["domain_counts"]["Revenue"] == 0

    # 3. Metadata fields
    assert res["metadata"]["working_row_count"] == 0
    assert res["metadata"]["input_row_count"] == 0
    assert res["metadata"]["generated_from_cleaned_dataset"] is True
    assert "Customers" in res["metadata"]["insufficient_domains"]

    # 4. No fabricated performance insights (only informational limitation details)
    assert len(res["insights"]) == 1
    assert res["insights"][0]["id"] == "data_chronological_unavailable"


def test_exact_revenue_growth_boundaries():
    # Create helper dataset spanning 14 days to split into two 7-day windows:
    # Previous period: Days 1-7 (e.g. 2026-01-01 to 2026-01-07)
    # Recent period: Days 8-14 (e.g. 2026-01-08 to 2026-01-14)
    # Total Span = 14 days, Window size = 7 days.
    
    # 1. Exactly +10.0% Revenue growth -> Positive Acceleration
    # Prev Rev = 100.0, Recent Rev = 110.0
    dates_prev = pd.date_range("2026-01-01", "2026-01-07", freq="D")
    dates_recent = pd.date_range("2026-01-08", "2026-01-14", freq="D")
    
    df_accel = pd.DataFrame({
        "OrderID": [f"O{i}" for i in range(14)],
        "OrderDate": list(dates_prev) + list(dates_recent),
        "Quantity": [1] * 14,
        # Assign Unit Prices to total exactly 100.0 for prev, 110.0 for recent without float division artifacts
        "UnitPrice": [100.0, 0, 0, 0, 0, 0, 0] + [110.0, 0, 0, 0, 0, 0, 0],
        "DiscountPct": [0.0] * 14,
        "CustomerID": [f"C{i}" for i in range(14)],
        "ProductID": [f"P{i}" for i in range(14)]
    })
    
    res = generate_business_insights(df_accel)
    accel_ins = [i for i in res["insights"] if i["id"] == "rev_acceleration"]
    assert len(accel_ins) == 1
    assert accel_ins[0]["severity"] == "Positive"
    assert accel_ins[0]["priority"] == 5

    # 2. Exactly -5.0% Revenue growth -> No decline trigger (Stable range)
    # Prev Rev = 100.0, Recent Rev = 95.0
    df_stable = pd.DataFrame({
        "OrderID": [f"O{i}" for i in range(14)],
        "OrderDate": list(dates_prev) + list(dates_recent),
        "Quantity": [1] * 14,
        "UnitPrice": [100.0, 0, 0, 0, 0, 0, 0] + [95.0, 0, 0, 0, 0, 0, 0],
        "DiscountPct": [0.0] * 14,
        "CustomerID": [f"C{i}" for i in range(14)],
        "ProductID": [f"P{i}" for i in range(14)]
    })
    res_stable = generate_business_insights(df_stable)
    decline_ins = [i for i in res_stable["insights"] if i["id"] in ("rev_softening", "rev_contraction")]
    assert len(decline_ins) == 0

    # 3. Exactly -20.0% Revenue growth -> Watch Softening (not Risk Contraction)
    # Prev Rev = 100.0, Recent Rev = 80.0
    df_soft = pd.DataFrame({
        "OrderID": [f"O{i}" for i in range(14)],
        "OrderDate": list(dates_prev) + list(dates_recent),
        "Quantity": [1] * 14,
        "UnitPrice": [100.0, 0, 0, 0, 0, 0, 0] + [80.0, 0, 0, 0, 0, 0, 0],
        "DiscountPct": [0.0] * 14,
        "CustomerID": [f"C{i}" for i in range(14)],
        "ProductID": [f"P{i}" for i in range(14)]
    })
    res_soft = generate_business_insights(df_soft)
    soft_ins = [i for i in res_soft["insights"] if i["id"] == "rev_softening"]
    contra_ins = [i for i in res_soft["insights"] if i["id"] == "rev_contraction"]
    assert len(soft_ins) == 1
    assert len(contra_ins) == 0
    assert soft_ins[0]["severity"] == "Watch"
    assert soft_ins[0]["priority"] == 2


def test_exact_volatility_boundaries():
    # Volatility boundary details:
    # CV >= 2.0 -> Risk, CV >= 1.2 and < 2.0 -> Watch
    # Daily sales distribution matching volatility CV:
    # For a 10-day dataset:
    # 1. CV = 2.0 boundary
    # Daily sales mean = 20, Std Dev = 40. CV = 2.0
    # Let's create dummy business health metrics response for volatility
    # testing bounds directly in generating insights.
    # To test engine logic accurately, let's verify volatility criteria directly or construct exact CV bounds.
    # Standard deviation of [110, 0, 0, 0, 0, 0, 0, 0, 0, 110] (10 days)
    # Mean: 220 / 10 = 22
    # Variance (ddof=1): ((110-22)^2 * 2 + (0-22)^2 * 8) / 9 = (7744*2 + 484*8)/9 = (15488 + 3872)/9 = 19360/9 = 2151.11
    # Std Dev: sqrt(2151.11) = 46.38
    # CV = 46.38 / 22 = 2.108 >= 2.0 -> Risk
    dates_prev = pd.date_range("2026-01-01", "2026-01-10", freq="D")
    df_vol_risk = pd.DataFrame({
        "OrderID": [f"O{i}" for i in range(10)],
        "OrderDate": list(dates_prev),
        "Quantity": [1] * 10,
        "UnitPrice": [110.0 if i in (0, 9) else 0.0 for i in range(10)],
        "DiscountPct": [0.0] * 10,
        "CustomerID": [f"C{i}" for i in range(10)],
        "ProductID": [f"P{i}" for i in range(10)]
    })
    res_vol_risk = generate_business_insights(df_vol_risk)
    vol_risk = [i for i in res_vol_risk["insights"] if i["id"] == "rev_high_volatility"]
    assert len(vol_risk) == 1
    assert vol_risk[0]["severity"] == "Risk"


def test_exact_repeat_rate_boundaries():
    # Repeat rate < 10.0 -> Risk, 10.0 <= rr < 20.0 -> Watch, >= 40.0 -> Positive
    # Create datasets that yield exact repeat rates.
    # Customer dataset total active 10:
    # 1. Exactly 10.0% Repeat Rate: 1 repeat buyer, 9 one-time buyers.
    # Repeat buyer has 2 unique orders, others have 1 unique order.
    # Total unique orders: 11 unique orders.
    # Total customer keys = 10. Repeat = 1. Repeat rate = 10.0% -> Watch.
    dates = pd.date_range("2026-01-01", "2026-01-14", freq="D")
    
    # 9 customers transact once on day 1
    # Customer C0 transacts twice: day 1 and day 2.
    df_rep = pd.DataFrame({
        "OrderID": [f"O{i}" for i in range(11)],
        "OrderDate": [datetime(2026, 1, 1)] * 10 + [datetime(2026, 1, 2)],
        "Quantity": [1] * 11,
        "UnitPrice": [10.0] * 11,
        "DiscountPct": [0.0] * 11,
        "CustomerID": [f"C{i}" for i in range(10)] + ["C0"],
        "ProductID": [f"P{i}" for i in range(11)]
    })
    res = generate_business_insights(df_rep)
    rep_ins = [i for i in res["insights"] if i["id"] == "cust_weak_retention"]
    assert len(rep_ins) == 1
    assert rep_ins[0]["severity"] == "Watch"


def test_exact_top1_product_concentration_boundaries():
    # Top-1 product concentration limits:
    # >= 50.0 -> Risk
    # >= 30.0 and < 50.0 -> Watch
    # Assign prices to products to yield exact concentrations:
    # Product P0 price = 50.0, P1 price = 50.0. Total sales = 100.0.
    # Concentration = 50.0% -> Risk.
    dates = pd.date_range("2026-01-01", "2026-01-14", freq="D")
    df_top1_risk = pd.DataFrame({
        "OrderID": [f"O{i}" for i in range(14)],
        "OrderDate": list(dates),
        "Quantity": [1] * 14,
        # 7 transactions of P0 (price 10.0), 7 transactions of P1 (price 10.0)
        # P0 revenue = 70.0, P1 revenue = 70.0. Top-1 = 70 / 140 = 50.0%
        "UnitPrice": [10.0] * 14,
        "DiscountPct": [0.0] * 14,
        "CustomerID": [f"C{i}" for i in range(14)],
        "ProductID": ["P0"] * 7 + ["P1"] * 7
    })
    res = generate_business_insights(df_top1_risk)
    top1_risk = [i for i in res["insights"] if i["id"] == "prod_top1_dependency_high"]
    assert len(top1_risk) == 1
    assert top1_risk[0]["severity"] == "Risk"

    # exactly 30% top-1 concentration
    # P0 revenue = 30.0, others = 70.0. Top-1 = 30.0% -> Watch.
    # Let's assign:
    # P0 gets 3 items of price 10.0
    # P1 gets 7 items of price 10.0 => Wait, then P1 is top item (70% concentration).
    # To make P0 top item with exactly 30% concentration, let's have 10 transactions of price 10.0 (Total = 100):
    # P0: 3 transactions of price 10.0 = 30.0
    # P1, P2, P3, P4, P5, P6, P7: 1 transaction of price 10.0 each (7 products, total 70.0)
    # Total revenue = 100.0. Top-1 (P0) revenue = 30.0 (exactly 30.0%).
    # Since active unique products = 8 >= 5, Top-5 concentration is enabled.
    df_top1_watch = pd.DataFrame({
        "OrderID": [f"O{i}" for i in range(10)],
        "OrderDate": [datetime(2026, 1, 1)] * 10,
        "Quantity": [1] * 10,
        "UnitPrice": [10.0] * 10,
        "DiscountPct": [0.0] * 10,
        "CustomerID": [f"C{i}" for i in range(10)],
        "ProductID": ["P0", "P0", "P0", "P1", "P2", "P3", "P4", "P4", "P4", "P4"]
    })
    # Wait, in the above:
    # P4 has 4 transactions (40.0 revenue), P0 has 3 (30.0 revenue), P1, P2, P3 have 1 each.
    # Total revenue = 100.0. Leading item is P4 with 40% concentration (still Watch, matches 30% <= 40% < 50%).
    # Let's adjust so leading is exactly 30%:
    # Product P0: 3 transactions = 30.0
    # Product P1: 2 transactions = 20.0
    # Product P2: 2 transactions = 20.0
    # Product P3: 2 transactions = 20.0
    # Product P4: 1 transaction = 10.0
    # Total revenue = 100.0. Leading P0 = 30.0% exactly. Active unique products = 5.
    df_top1_watch_exact = pd.DataFrame({
        "OrderID": [f"O{i}" for i in range(10)],
        "OrderDate": [datetime(2026, 1, 1)] * 10,
        "Quantity": [1] * 10,
        "UnitPrice": [10.0] * 10,
        "DiscountPct": [0.0] * 10,
        "CustomerID": [f"C{i}" for i in range(10)],
        "ProductID": ["P0", "P0", "P0", "P1", "P2", "P3", "P4", "P5", "P6", "P7"]
    })
    res_exact = generate_business_insights(df_top1_watch_exact)
    top1_watch = [i for i in res_exact["insights"] if i["id"] == "prod_top1_dependency_medium"]
    assert len(top1_watch) == 1
    assert top1_watch[0]["severity"] == "Watch"


def test_explicit_domain_order_sorting():
    # Sort order: priority ascending, DOMAIN_ORDER, id ascending
    mock_insights = [
        {"id": "c", "domain": "Customers", "priority": 5},
        {"id": "a", "domain": "Revenue", "priority": 5},
        {"id": "z", "domain": "Revenue", "priority": 1},
        {"id": "b", "domain": "Data Quality", "priority": 4},
        {"id": "d", "domain": "Customers", "priority": 2}
    ]
    sorted_res = sort_insights(mock_insights)
    
    # Expected ordering:
    # 1. Priority 1: 'z' (Revenue)
    # 2. Priority 2: 'd' (Customers)
    # 3. Priority 4: 'b' (Data Quality)
    # 4. Priority 5: 'a' (Revenue) (explicit order 1 comes before Customers order 2)
    # 5. Priority 5: 'c' (Customers)
    assert [i["id"] for i in sorted_res] == ["z", "d", "b", "a", "c"]


def test_backend_semantic_deduplication_consistency():
    # Create two duplicate product insights representing concentration overlap
    insights_list = [
        {
            "id": "prod_top1_dependency_high",
            "domain": "Products",
            "title": "High Single Product Dependency Risk",
            "severity": "Risk",
            "priority": 1
        },
        {
            "id": "prod_top5_concentration_high",
            "domain": "Products",
            "title": "High Portfolio Concentration Risk",
            "severity": "Risk",
            "priority": 1
        }
    ]
    # Under severity tie and priority tie, Top-1 dependency takes precedence over Top-5
    deduped = deduplicate_insights(insights_list)
    assert len(deduped) == 1
    assert deduped[0]["id"] == "prod_top1_dependency_high"


def test_source_metadata_truthfulness():
    df = pd.DataFrame({
        "OrderID": ["O1"], "OrderDate": [datetime(2026, 1, 1)], "Quantity": [1],
        "UnitPrice": [10.0], "DiscountPct": [0.0], "CustomerID": ["C1"], "ProductID": ["P1"]
    })
    
    # Truthfulness flag True
    res_true = generate_business_insights(df, generated_from_cleaned_dataset=True)
    assert res_true["metadata"]["generated_from_cleaned_dataset"] is True

    # Truthfulness flag False
    res_false = generate_business_insights(df, generated_from_cleaned_dataset=False)
    assert res_false["metadata"]["generated_from_cleaned_dataset"] is False


def test_forecast_unavailable_as_informational():
    # Small dataset spanning < 14 days causes UNAVAILABLE capability state
    df_short = pd.DataFrame({
        "OrderID": ["O1", "O2"],
        "OrderDate": [datetime(2026, 1, 1), datetime(2026, 1, 3)],
        "Quantity": [1, 2],
        "UnitPrice": [10.0, 15.0],
        "DiscountPct": [0.0, 0.0],
        "CustomerID": ["C1", "C2"],
        "ProductID": ["P1", "P2"]
    })
    res = generate_business_insights(df_short)
    
    # Forecast readiness checks
    fc_ins = [i for i in res["insights"] if i["id"] == "fc_readiness_unavailable"]
    assert len(fc_ins) == 1
    assert fc_ins[0]["severity"] == "Informational"
    assert fc_ins[0]["priority"] == 4


def test_unavailable_metrics_never_emit_fake_insights():
    # Remove CustomerID/CustomerName columns to make customers metrics unavailable
    df_nocust = pd.DataFrame({
        "OrderID": ["O1", "O2", "O3", "O4", "O5", "O6" ,"O7", "O8", "O9", "O10", "O11", "O12", "O13", "O14"],
        "OrderDate": pd.date_range("2026-01-01", "2026-01-14", freq="D"),
        "Quantity": [1] * 14,
        "UnitPrice": [10.0] * 14,
        "DiscountPct": [0.0] * 14,
        "ProductID": ["P1"] * 14
    })
    res = generate_business_insights(df_nocust)
    
    # Assert no customer repeat-rate / concentration / economics insights are emitted
    cust_ins = [i for i in res["insights"] if i["domain"] == "Customers"]
    assert len(cust_ins) == 0  # No customer domain insights are generated
    
    # Assert the data quality warning is emitted under Data Quality
    dq_ins = [i for i in res["insights"] if i["domain"] == "Data Quality" and i["id"] == "data_missing_customers"]
    assert len(dq_ins) == 1
    assert "Customers" in res["metadata"]["insufficient_domains"]


def test_idempotency_of_repeated_runs():
    df = pd.DataFrame({
        "OrderID": [f"O{i}" for i in range(14)],
        "OrderDate": pd.date_range("2026-01-01", "2026-01-14", freq="D"),
        "Quantity": [1] * 14,
        "UnitPrice": [10.0] * 14,
        "DiscountPct": [0.0] * 14,
        "CustomerID": [f"C{i}" for i in range(14)],
        "ProductID": [f"P{i}" for i in range(14)]
    })
    
    res1 = generate_business_insights(df, generated_from_cleaned_dataset=True)
    res2 = generate_business_insights(df, generated_from_cleaned_dataset=True)

    # Identical returned content check
    assert res1 == res2


def test_revenue_timeline_construction_from_raw_resolved_dataframe():
    from backend.analytics_engine import prepare_analytics_dataset
    
    # Construct a raw resolved dataframe that does not contain "_Revenue", only raw transaction fields
    raw_df = pd.DataFrame({
        "OrderID": ["O1", "O2", "O3"],
        "OrderDate": ["2026-01-01", "2026-01-01", "2026-01-02"],
        "Quantity": [2, 1, 5],
        "UnitPrice": [10.0, 20.0, 15.0],
        "DiscountPct": [0.0, 10.0, 0.0]
    })
    
    # Assert _Revenue is NOT in raw_df
    assert "_Revenue" not in raw_df.columns
    
    # Pass through prepare_analytics_dataset
    prep_df, _ = prepare_analytics_dataset(raw_df)
    
    # Assert _Revenue and OrderDate are now in prep_df
    assert "_Revenue" in prep_df.columns
    assert "OrderDate" in prep_df.columns
    
    # Enforce timezone/date structure
    assert pd.api.types.is_datetime64_any_dtype(prep_df["OrderDate"])
    
    # Perform grouping as done in the dashboard tab1
    daily_rev = prep_df.groupby("OrderDate")["_Revenue"].sum().reset_index()
    
    assert len(daily_rev) == 2
    # O1: 2 * 10 = 20.0; O2: 1 * 20 * (1 - 0.1) = 18.0; Total for 2026-01-01 = 38.0
    # O3: 5 * 15 = 75.0; Total for 2026-01-02 = 75.0
    assert float(daily_rev.iloc[0]["_Revenue"]) == 38.0
    assert float(daily_rev.iloc[1]["_Revenue"]) == 75.0
