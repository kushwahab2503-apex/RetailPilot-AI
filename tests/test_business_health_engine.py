import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from backend.business_health_engine import (
    calculate_period_split_dates,
    calculate_daily_volatility,
    evaluate_business_health,
    compute_domain_statuses
)


def test_odd_even_date_span_comparable_windows():
    # 1. Even Date Span: 14 days
    # Range: 2026-01-01 to 2026-01-14 (14 calendar days)
    # window_size = 14 // 2 = 7 days
    # Recent: 2026-01-08 to 2026-01-14
    # Previous: 2026-01-01 to 2026-01-07
    # Remainder: 0 days
    df_even = pd.DataFrame({
        "OrderDate": pd.to_datetime([
            "2026-01-01", "2026-01-07", "2026-01-08", "2026-01-14"
        ])
    })
    res_even = calculate_period_split_dates(df_even)
    assert res_even["is_valid"] is True
    assert res_even["span_days"] == 14
    assert res_even["window_size"] == 7
    assert res_even["recent_start"] == datetime(2026, 1, 8)
    assert res_even["recent_end"] == datetime(2026, 1, 14)
    assert res_even["prev_start"] == datetime(2026, 1, 1)
    assert res_even["prev_end"] == datetime(2026, 1, 7)

    # 2. Odd Date Span: 15 days
    # Range: 2026-01-01 to 2026-01-15 (15 calendar days)
    # window_size = 15 // 2 = 7 days
    # Recent: 2026-01-09 to 2026-01-15
    # Previous: 2026-01-02 to 2026-01-08
    # Excluded Remainder: 2026-01-01 (1 day)
    df_odd = pd.DataFrame({
        "OrderDate": pd.to_datetime([
            "2026-01-01", "2026-01-02", "2026-01-08", "2026-01-09", "2026-01-15"
        ])
    })
    res_odd = calculate_period_split_dates(df_odd)
    assert res_odd["is_valid"] is True
    assert res_odd["span_days"] == 15
    assert res_odd["window_size"] == 7
    assert res_odd["recent_start"] == datetime(2026, 1, 9)
    assert res_odd["recent_end"] == datetime(2026, 1, 15)
    assert res_odd["prev_start"] == datetime(2026, 1, 2)
    assert res_odd["prev_end"] == datetime(2026, 1, 8)


def test_missing_calendar_dates_in_volatility():
    # Volatility should aggregate calendar days min_date to max_date and fill missing with 0.
    # 2026-01-01: 100
    # 2026-01-02 to 2026-01-09: missing (reindexed -> value = 0)
    # 2026-01-10: 100
    # Total days = 10. Daily values: [100.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 100.0]
    # Mean: 200.0 / 10 = 20.0
    # Sample standard deviation (ddof=1) of [100, 0, 0, 0, 0, 0, 0, 0, 0, 100]
    # Variance: ( (100-20)^2 * 2 + (0-20)^2 * 8 ) / 9 = (6400 * 2 + 400 * 8) / 9 = (12800 + 3200) / 9 = 16000 / 9 = 1777.77
    # Std dev = sqrt(1777.77) = 42.1637
    # CV = 42.1637 / 20.0 = 2.108
    df = pd.DataFrame({
        "OrderDate": pd.to_datetime(["2026-01-01", "2026-01-10"]),
        "_Revenue": [100.0, 100.0]
    })
    vol = calculate_daily_volatility(df, datetime(2026, 1, 1), datetime(2026, 1, 10))
    assert vol is not None
    assert pytest.approx(vol, 0.01) == 2.1082


def test_all_zero_revenue_timeline():
    # Setup dataframe with zero revenue across a 15-day range
    dates = pd.date_range("2026-01-01", periods=15, freq="D")
    df = pd.DataFrame({
        "OrderID": [f"O{i}" for i in range(15)],
        "OrderDate": dates,
        "Quantity": [1] * 15,
        "UnitPrice": [0.0] * 15,
        "DiscountPct": [0.0] * 15,
        "CustomerID": [f"C{i}" for i in range(15)],
        "ProductID": [f"P{i}" for i in range(15)]
    })

    health = evaluate_business_health(df)
    # Revenue growth and volatility must handle division by zero or mean <= 0 gracefully.
    assert health["metrics"]["revenue_growth"]["status"] == "Insufficient Data"
    assert health["metrics"]["revenue_volatility"]["status"] == "Insufficient Data"


def test_negative_growth_exact_threshold_boundaries():
    dates = pd.to_datetime(["2026-01-01"] * 7 + ["2026-01-08"] * 7)
    # Total span = 8 days. window_size = 4.
    # Recent: 2026-01-05 to 2026-01-08
    # Previous: 2026-01-01 to 2026-01-04
    # Let's create a dataframe over 14 days where prev_rev is 100.0, and change recent_rev
    dates_14 = pd.to_datetime(["2026-01-01"] * 7 + ["2026-01-08"] * 7) # span = 8 days, but let's make it 14 days
    # Range 2026-01-01 to 2026-01-14
    
    def get_growth_status(prev_val, recent_val):
        df = pd.DataFrame({
            "OrderID": ["O1", "O2"],
            "OrderDate": pd.to_datetime(["2026-01-01", "2026-01-14"]),
            "Quantity": [1, 1],
            "UnitPrice": [prev_val, recent_val],
            "DiscountPct": [0.0, 0.0]
        })
        health = evaluate_business_health(df)
        return health["metrics"]["revenue_growth"]["status"]

    # Boundaries:
    # Strong: >= 10.0%
    # Stable: >= -5.0% and < 10.0%
    # Watch: >= -20.0% and < -5.0%
    # Risk: < -20.0%
    assert get_growth_status(100.0, 110.0) == "Strong"
    assert get_growth_status(100.0, 109.9) == "Stable"
    assert get_growth_status(100.0, 95.0) == "Stable"
    assert get_growth_status(100.0, 94.9) == "Watch"
    assert get_growth_status(100.0, 80.0) == "Watch"
    assert get_growth_status(100.0, 79.9) == "Risk"


def test_fewer_than_5_customers_concentration_context():
    # Only 3 customers.
    df = pd.DataFrame({
        "OrderID": ["O1", "O2", "O3"],
        "OrderDate": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
        "Quantity": [1, 1, 1],
        "UnitPrice": [10.0, 20.0, 70.0],
        "DiscountPct": [0.0, 0.0, 0.0],
        "CustomerID": ["C1", "C2", "C3"]
    })
    health = evaluate_business_health(df)
    meta_t5c = health["metrics"]["top5_customer_concentration"]
    # Value must be 100% since total customers are 3
    assert meta_t5c["value"] == 100.0
    assert meta_t5c["entity_count"] == 3
    assert meta_t5c["context"] == "Small Customer Cohort"
    assert meta_t5c["status"] == "Insufficient Data"


def test_fewer_than_5_products_concentration_context():
    # Only 3 products
    df = pd.DataFrame({
        "OrderID": ["O1", "O2", "O3"],
        "OrderDate": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
        "Quantity": [1, 1, 1],
        "UnitPrice": [10.0, 20.0, 70.0],
        "DiscountPct": [0.0, 0.0, 0.0],
        "ProductID": ["P1", "P2", "P3"]
    })
    health = evaluate_business_health(df)
    meta_t5p = health["metrics"]["top5_product_concentration"]
    assert meta_t5p["value"] == 100.0
    assert meta_t5p["entity_count"] == 3
    assert meta_t5p["context"] == "Small Product Portfolio"
    assert meta_t5p["status"] == "Insufficient Data"


def test_complementary_repeat_one_time_metrics_not_double_counted():
    # Mock statuses where repeat_rate is Strong, and customer_concentration is Stable.
    # onetime_dependence is also Strong (since repeat_rate >= 40% means dependence < 60%).
    # If customer health status counted all three, that would double count repeat rate.
    # Let's verify that compute_domain_statuses does NOT check onetime_dependence.
    metrics = {
        "repeat_rate": {"status": "Strong"},
        "top5_customer_concentration": {"status": "Stable"},
        "onetime_dependence": {"status": "Risk"} # Put Risk to see if it affects anything
    }
    statuses = compute_domain_statuses(metrics)
    # If onetime_dependence was included: "Risk if any primary is Risk OR at least 2 are Risk..."
    # If it is skipped: we only have Strong repeat_rate and Stable concentrations -> Should be Strong or Stable.
    # Since primary repeat_rate is Strong, stable concentration makes it Stable or Strong. Let's see:
    # All calculable are Strong or Stable, and >= 1 is Strong -> Returns Strong!
    # If Risk was included, it would not be Strong or Stable, it would evaluate to Risk or Watch.
    assert statuses["customer_health"] == "Strong"


def test_forecast_unavailable_does_not_degrade_business_status():
    metrics = {
        "revenue_growth": {"status": "Stable"},
        "revenue_volatility": {"status": "Stable"},
        "repeat_rate": {"status": "Stable"},
        "top5_customer_concentration": {"status": "Stable"},
        "top5_product_concentration": {"status": "Stable"},
        "top1_product_concentration": {"status": "Stable"},
        "pareto_share": {"status": "Stable"},
        "low_performing_share": {"status": "Stable"},
        "aov_growth": {"status": "Stable"},
        "upo_growth": {"status": "Stable"},
        "rpc_growth": {"status": "Stable"},
        "forecast_readiness": {"status": "Risk"} # Forecast readiness is Risk
    }
    statuses = compute_domain_statuses(metrics)
    assert statuses["revenue_health"] == "Stable"
    assert statuses["customer_health"] == "Stable"
    assert statuses["product_health"] == "Stable"
    assert statuses["order_economics"] == "Stable"
    assert statuses["forecast_readiness"] == "Risk"


def test_deterministic_executive_findings():
    # Validate sentence formats
    df = pd.DataFrame({
        "OrderID": ["O1", "O2"],
        "OrderDate": pd.to_datetime(["2026-01-01", "2026-01-14"]),
        "Quantity": [1, 2],
        "UnitPrice": [10.0, 15.0],
        "DiscountPct": [0.0, 0.0],
        "CustomerID": ["C1", "C2"],
        "ProductID": ["P1", "P2"]
    })
    health = evaluate_business_health(df)
    finds = health["executive_findings"]
    
    # RevenueGrowth decreased from 10 to 30? Wait.
    # Prev: 2026-01-01 to 2026-01-07. Order O1 is 2026-01-01, rev = 10.
    # Recent: 2026-01-08 to 2026-01-14. Order O2 is 2026-01-14, rev = 30.
    # growth = (30 - 10)/10 * 100 = 200%.
    # Should say: "Revenue increased 200.0%..."
    rg_msgs = finds["strengths"]
    assert any("Revenue increased 200.0% in the recent comparison window" in m for m in rg_msgs)


def test_metadata_keys_valid_empty():
    # Invalid/Empty dataset check
    empty_df = pd.DataFrame()
    res_empty = evaluate_business_health(empty_df)
    assert "dates_metadata" in res_empty
    assert "metrics" in res_empty
    assert "domain_statuses" in res_empty
    assert "executive_findings" in res_empty
    assert res_empty["metrics"]["revenue_growth"]["status"] == "Insufficient Data"
    assert res_empty["domain_statuses"]["revenue_health"] == "Insufficient Data"

    # Valid dataset check
    dates = pd.to_datetime(["2026-01-01"] * 5 + ["2026-01-15"] * 5)
    df = pd.DataFrame({
        "OrderID": [f"O{i}" for i in range(10)],
        "OrderDate": dates,
        "Quantity": [1] * 10,
        "UnitPrice": [10.0] * 10,
        "DiscountPct": [0.0] * 10,
        "CustomerID": [f"C{i%2}" for i in range(10)],
        "ProductID": [f"P{i%2}" for i in range(10)]
    })
    res_valid = evaluate_business_health(df)
    assert res_valid["dates_metadata"]["span_days"] == 15
    assert res_valid["domain_statuses"]["revenue_health"] in ["Strong", "Stable", "Watch", "Risk", "Insufficient Data"]


def test_input_dataframe_non_mutation():
    df = pd.DataFrame({
        "OrderID": ["O1", "O2"],
        "OrderDate": pd.to_datetime(["2026-01-01", "2026-01-14"]),
        "Quantity": [1, 2],
        "UnitPrice": [10.0, 15.0],
        "DiscountPct": [0.0, 0.0]
    })
    df_copy = df.copy()
    _ = evaluate_business_health(df)
    pd.testing.assert_frame_equal(df, df_copy)


def test_mixed_status_domains_aggregation_and_overall():
    # 1. Calculable Risk metrics plus one Insufficient Data metric
    metrics_risk = {
        "revenue_growth": {"status": "Risk"},
        "revenue_volatility": {"status": "Insufficient Data"}
    }
    statuses_risk = compute_domain_statuses(metrics_risk)
    assert statuses_risk["revenue_health"] == "Risk"

    # 2. Calculable Strong/Stable metrics plus one Insufficient Data metric
    metrics_strong = {
        "repeat_rate": {"status": "Strong"},
        "top5_customer_concentration": {"status": "Insufficient Data"}
    }
    statuses_strong = compute_domain_statuses(metrics_strong)
    assert statuses_strong["customer_health"] == "Strong"

    metrics_stable_only = {
        "repeat_rate": {"status": "Stable"},
        "top5_customer_concentration": {"status": "Insufficient Data"}
    }
    statuses_stable = compute_domain_statuses(metrics_stable_only)
    assert statuses_stable["customer_health"] == "Stable"

    # 3. Fully insufficient domain inputs
    metrics_empty = {
        "revenue_growth": {"status": "Insufficient Data"},
        "revenue_volatility": {"status": "Insufficient Data"}
    }
    statuses_empty = compute_domain_statuses(metrics_empty)
    assert statuses_empty["revenue_health"] == "Insufficient Data"


def test_forecast_readiness_isolation_from_overall_status():
    # Proves that an otherwise Strong/Stable business with UNAVAILABLE forecast readiness
    # (which gets forecast_readiness = Risk status) is not automatically classified as overall Risk.
    
    dates = pd.to_datetime([f"2026-01-{day:02d}" for day in range(1, 11)])
    df = pd.DataFrame({
        "OrderID": [f"O{i}" for i in range(10)],
        "OrderDate": dates,
        "Quantity": [1] * 10,
        "UnitPrice": [10.0] * 10,
        "DiscountPct": [0.0] * 10,
        "CustomerID": ["C1"] * 5 + ["C2"] * 5,
        "ProductID": [f"P{i}" for i in range(10)]
    })
    
    res = evaluate_business_health(df)
    
    # Forecast readiness should be Risk because date_span_days = 9 < 14
    assert res["domain_statuses"]["forecast_readiness"] == "Risk"
    
    # Business performance domains should not be Risk (specifically overall_status should NOT be Risk)
    assert res["overall_status"] != "Risk"
    
    # Let's verify indicator_counts has only 4 business domains (excluding forecast readiness)
    counts = res["indicator_counts"]
    total_counted = sum(counts.values())
    assert total_counted == 4
    assert "forecast_readiness" not in counts


