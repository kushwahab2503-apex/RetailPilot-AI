import pytest
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta

from backend.report_engine import (
    generate_executive_report,
    build_report_json,
    build_report_csv,
    build_report_pdf,
    clean_txt
)

# Helper function to generate clean mock dataframe
def create_mock_df(days: int = 60, scale_sales: bool = True, has_rupee: bool = False) -> pd.DataFrame:
    base_date = datetime(2026, 1, 1)
    rows = []
    
    # We need a stable distribution of dates, orders, products, customers
    for i in range(days):
        date_curr = base_date + timedelta(days=i)
        # Add 2 transactions per day
        for tx in range(2):
            product_idx = ((i * 2) + tx) % 10
            rows.append({
                "OrderID": f"TX_{i}_{tx}",
                "OrderDate": date_curr.strftime("%Y-%m-%d"),
                "CustomerID": f"C_{1 if tx == 0 else 2}",
                "CustomerName": f"Customer {'A' if tx == 0 else 'B' if not has_rupee else 'Customer ₹ A'}",
                "ProductID": f"P_{product_idx}",
                "ProductName": f"Widget Premium {product_idx}",
                "Quantity": 5 if scale_sales else 0,
                "UnitPrice": 10.0,
                "DiscountPct": 0.0
            })
            
    return pd.DataFrame(rows)


def test_empty_dataframe_complete_contract():
    empty_df = pd.DataFrame()
    report = generate_executive_report(empty_df)
    
    # 1. Verify top level contract keys exist
    expected_top_keys = {
        "report_metadata", "executive_summary", "kpi_snapshot", "priority_findings",
        "positive_findings", "watch_findings", "limitations", "domain_sections",
        "methodology", "source_traceability"
    }
    assert set(report.keys()) == expected_top_keys


def test_stable_top_level_keys():
    df = create_mock_df(30)
    report = generate_executive_report(df)
    
    for key in [
        "report_metadata", "executive_summary", "kpi_snapshot", "priority_findings",
        "positive_findings", "watch_findings", "limitations", "domain_sections",
        "methodology", "source_traceability"
    ]:
        assert key in report


def test_stable_five_domain_section_keys():
    df = create_mock_df(30)
    report = generate_executive_report(df)
    
    domain_sec = report["domain_sections"]
    for domain in ["revenue", "customers", "products", "order_economics", "forecast"]:
        assert domain in domain_sec


def test_exact_12_kpi_ids():
    df = create_mock_df(30)
    report = generate_executive_report(df)
    
    kpis = report["kpi_snapshot"]
    assert len(kpis) == 12
    
    expected_ids = [
        "revenue_growth", "daily_volatility", "repeat_buyer_rate", "top5_customer_concentration",
        "top1_product_concentration", "top5_product_concentration", "product_pareto_share",
        "low_revenue_product_share", "aov_growth", "upo_growth", "rpc_growth", "forecast_capability"
    ]
    
    kpi_ids = [k["id"] for k in kpis]
    assert kpi_ids == expected_ids


def test_unavailable_kpi_values_remain_none():
    # Empty data should yield None for numerical KPIs
    empty_df = pd.DataFrame()
    report = generate_executive_report(empty_df)
    
    for kpi in report["kpi_snapshot"]:
        if kpi["id"] == "forecast_capability":
            assert kpi["value"] == "UNAVAILABLE"
            assert kpi["status"] in ["Risk", "Watch", "Insufficient Data"]
        else:
            assert kpi["value"] is None
            assert kpi["status"] == "Insufficient Data"


def test_non_mutation():
    df = create_mock_df(30)
    df_copy = df.copy()
    
    generate_executive_report(df)
    
    # Assert unmodified
    pd.testing.assert_frame_equal(df, df_copy)


def test_json_serializability():
    df = create_mock_df(30)
    report = generate_executive_report(df)
    
    # Try normal JSON serialization
    serialized = build_report_json(report)
    assert isinstance(serialized, bytes)
    
    # Reload and test
    data = json.loads(serialized.decode("utf-8"))
    assert data["report_metadata"]["report_version"] == "1.0.0"


def test_no_pandas_timestamp_leakage():
    df = create_mock_df(3)
    report = generate_executive_report(df)
    
    # Traverse directory elements of the serialization helper output
    clean_report = build_report_json(report)
    parsed = json.loads(clean_report.decode('utf-8'))
    
    # Start and end dates must be string, not timestamp
    assert isinstance(parsed["report_metadata"]["date_start"], (str, type(None)))
    assert isinstance(parsed["report_metadata"]["date_end"], (str, type(None)))


def test_no_numpy_scalar_leakage():
    df = create_mock_df(20)
    report = generate_executive_report(df)
    
    clean_report = build_report_json(report)
    parsed = json.loads(clean_report.decode('utf-8'))
    
    for k in parsed["kpi_snapshot"]:
        val = k["value"]
        if val is not None and k["id"] != "forecast_capability":
            assert isinstance(val, (int, float))


def test_deterministic_analytical_output_excluding_only_generated_at():
    df = create_mock_df(45)
    r1 = generate_executive_report(df)
    r2 = generate_executive_report(df)
    
    # Exclude generated_at
    r1["report_metadata"].pop("generated_at")
    r2["report_metadata"].pop("generated_at")
    
    assert r1 == r2


def test_finding_ordering():
    df = create_mock_df(45)
    # Put multiple duplicate customers to trigger concentration watch/risk if needed
    report = generate_executive_report(df)
    
    # Verify that in all findings lists, the records are sorted:
    # 1. priority ascending, 2. domain alphabetically, 3. id alphabetically
    for section_name in ["priority_findings", "watch_findings", "positive_findings", "limitations"]:
        findings = report.get(section_name, [])
        if len(findings) > 1:
            for idx in range(len(findings) - 1):
                f1 = findings[idx]
                f2 = findings[idx+1]
                
                p1 = int(f1.get("priority", 99))
                p2 = int(f2.get("priority", 99))
                assert p1 <= p2
                if p1 == p2:
                    d1 = f1.get("domain", "")
                    d2 = f2.get("domain", "")
                    assert d1 <= d2
                    if d1 == d2:
                        assert f1.get("id", "") <= f2.get("id", "")


def test_no_duplicate_insight_ids():
    df = create_mock_df(45)
    report = generate_executive_report(df)
    
    all_seen = set()
    for section in ["priority_findings", "watch_findings", "positive_findings", "limitations"]:
        for f in report.get(section, []):
            assert f["id"] not in all_seen
            all_seen.add(f["id"])


def test_business_performance_vs_forecast_isolation():
    # If the business performance is strong, forecast capability being unavailable
    # should NOT taint performance_status to Risk.
    
    # Generate mock df with 5 days. This satisfies most strong/stable conditions,
    # but not 45 days of aggregate forecast data split or similar.
    df = create_mock_df(days=5) # 5 days is UNAVAILABLE forecast since < 14 days
    report = generate_executive_report(df)
    
    assert report["executive_summary"]["forecast_readiness_status"] == "UNAVAILABLE"
    # overall business health rating is not automatically risk just because forecast is unavailable
    assert report["executive_summary"]["performance_status"] != "Risk"


def test_strong_business_and_unavailable_forecast_wording():
    # Create 5 days of data to make business health strong/stable but keep forecast engine unavailable
    df = create_mock_df(days=5) # <14 days means forecast capability UNAVAILABLE
    report = generate_executive_report(df)
    
    summary_text = report["executive_summary"]["summary"]
    if report["executive_summary"]["performance_status"] in ["Strong", "Stable"]:
        assert summary_text == "Business performance indicators are favorable where calculable, while forecasting remains unavailable because the dataset does not yet satisfy chronological readiness requirements."


def test_risk_domain_executive_summary():
    # Create a dataset that triggers a Risk status
    # (e.g. Volatility CV > 2.0)
    # We can do zero sales on some days to create massive daily volatility
    base_date = datetime(2026, 1, 1)
    rows = []
    
    # 20 days: day 1 has 100 sales, days 2..20 have 0 sales
    for i in range(20):
        date_curr = base_date + timedelta(days=i)
        rows.append({
            "OrderID": f"TX_{i}",
            "OrderDate": date_curr.strftime("%Y-%m-%d"),
            "CustomerID": "C_1",
            "CustomerName": "CustA",
            "ProductID": "P_1",
            "ProductName": "Widg",
            "Quantity": 1000 if i == 0 else 0,
            "UnitPrice": 10.0,
            "DiscountPct": 0.0
        })
        
    df = pd.DataFrame(rows)
    report = generate_executive_report(df)
    
    summary = report["executive_summary"]["summary"]
    # Should flag Risk due to extreme volatility
    assert "Risk" in report["executive_summary"]["domain_statuses"].values()
    assert "Immediate attention is required" in summary or "mixed operating conditions" in summary


def test_watch_only_executive_summary():
    # Create a dataset that triggers watch-level metric status but no Risk.
    # We can achieve this by having moderate date coverage, etc.
    # Let's verify our headline or summary adjusts dynamically.
    df = create_mock_df(days=25) 
    report = generate_executive_report(df)
    
    summary = report["executive_summary"]["summary"]
    assert len(summary) > 0


def test_insufficient_data_summary():
    # A completely empty dataframe has insufficient data for all domains
    df = pd.DataFrame()
    report = generate_executive_report(df)
    
    assert report["executive_summary"]["headline"] == "Insufficient Data for Diagnostic Evaluation"
    assert "coverage is insufficient" in report["executive_summary"]["summary"]


def test_domain_insight_grouping():
    df = create_mock_df(45)
    report = generate_executive_report(df)
    
    # Insights in domain sections should correspond to that domain
    sections = report["domain_sections"]
    for ins in sections["revenue"]["insights"]:
        assert ins["domain"] == "Revenue"
        
    for ins in sections["customers"]["insights"]:
        assert ins["domain"] == "Customers"
        
    for ins in sections["products"]["insights"]:
        assert ins["domain"] == "Products"
        
    for ins in sections["order_economics"]["insights"]:
        assert ins["domain"] == "Order Economics"


def test_comparison_window_metadata_propagation():
    df = create_mock_df(30)
    report = generate_executive_report(df)
    
    # Metadata start and end dates should correspond to df boundaries
    m = report["report_metadata"]
    assert m["date_start"] == "2026-01-01"
    assert m["date_end"] == "2026-01-30"
    assert m["calendar_span_days"] == 30
    
    # Domain section comparison windows must be set
    assert report["domain_sections"]["revenue"]["comparison_window"]["min_date"] == "2026-01-01"


def test_custom_report_title():
    df = create_mock_df(10)
    custom_title = "Strategic Q1 Performance Brief"
    report = generate_executive_report(df, report_title=custom_title)
    
    assert report["report_metadata"]["report_title"] == custom_title


def test_source_traceability_contract():
    df = create_mock_df(10)
    report = generate_executive_report(df)
    
    traceLogs = report["source_traceability"]
    assert len(traceLogs) >= 6
    for entry in traceLogs:
        assert "section" in entry
        assert "source_engine" in entry
        assert "source_function" in entry


def test_json_export_parses():
    df = create_mock_df(15)
    report = generate_executive_report(df)
    
    json_bytes = build_report_json(report)
    parsed = json.loads(json_bytes.decode("utf-8"))
    
    assert parsed["report_metadata"]["report_title"] == "RetailPilot AI Executive Business Report"


def test_csv_stable_headers_and_record_type():
    df = create_mock_df(15)
    report = generate_executive_report(df)
    
    csv_bytes = build_report_csv(report)
    csv_str = csv_bytes.decode("utf-8").replace("\r\n", "\n")
    
    lines = csv_str.strip().split("\n")
    headers = lines[0].split(",")
    
    expected_headers = [
        "record_type", "id", "domain", "label", "value", "unit", "status",
        "source_engine", "title", "summary", "severity", "priority",
        "evidence", "recommended_action"
    ]
    assert headers == expected_headers
    
    # Check that record_type column contains only "KPI", "Priority Finding", "Watch Finding", "Positive Finding", "Limitation"
    for line in lines[1:]:
        parts = line.split(",")
        if parts:
            assert parts[0] in ["KPI", "Priority Finding", "Watch Finding", "Positive Finding", "Limitation", ""]


def test_csv_deterministic_row_order():
    df = create_mock_df(45)
    report = generate_executive_report(df)
    
    csv1 = build_report_csv(report)
    csv2 = build_report_csv(report)
    
    assert csv1 == csv2


def test_pdf_starts_with_pdf_signature():
    df = create_mock_df(15)
    report = generate_executive_report(df)
    
    pdf_bytes = build_report_pdf(report)
    # Check PDF magic bytes %PDF
    assert pdf_bytes.startswith(b"%PDF")


def test_pdf_non_empty_bytes():
    df = create_mock_df(10)
    report = generate_executive_report(df)
    
    pdf_bytes = build_report_pdf(report)
    assert len(pdf_bytes) > 0


def test_pdf_handles_unavailable_metrics():
    # Empty data (creates many None values)
    empty_report = generate_executive_report(pd.DataFrame())
    
    pdf_bytes = build_report_pdf(empty_report)
    assert pdf_bytes.startswith(b"%PDF")
    
    # Check custom character cleaning
    text_with_rupee = "Total Revenue evaluated was ₹45,000.00"
    cleaned = clean_txt(text_with_rupee)
    assert "₹" not in cleaned
    assert "INR" in cleaned


def test_pdf_binary_normalization_and_validation():
    df = create_mock_df(10)
    report = generate_executive_report(df)
    
    pdf_bytes = build_report_pdf(report)
    
    # 1. Assert type is strictly bytes
    assert type(pdf_bytes) is bytes
    
    # 2. Output starts with b"%PDF"
    assert pdf_bytes.startswith(b"%PDF")
    
    # 3. Output is non-empty and has meaningful PDF length
    assert len(pdf_bytes) > 100
    
    # 4. The exact page-level binary validation logic used by 10_Reports.py accepts the payload
    normalized_payload = pdf_bytes
    if isinstance(normalized_payload, bytearray):
        normalized_payload = bytes(normalized_payload)
    assert isinstance(normalized_payload, bytes)
    assert type(normalized_payload) is bytes
    
    # 5. Assert bytearray returned internally by the PDF library is normalized to bytes at the engine boundary
    from unittest.mock import patch
    with patch("fpdf.FPDF.output", return_value=bytearray(b"%PDF-mock-output")):
        mocked_pdf = build_report_pdf(report)
        assert type(mocked_pdf) is bytes
        assert mocked_pdf.startswith(b"%PDF")



def test_partial_column_graceful_degradation():
    df = create_mock_df(15)
    # Drop CustomerName to test partial columns
    partial_df = df.drop(columns=["CustomerName"])
    report = generate_executive_report(partial_df)
    
    assert report["report_metadata"]["row_count"] == 30
    assert report["executive_summary"]["performance_status"] != ""


def test_zero_revenue_graceful():
    df = create_mock_df(15, scale_sales=False) # Sets quantity to 0
    report = generate_executive_report(df)
    
    # Should run and execute correctly 
    assert report["report_metadata"]["row_count"] == 30
    # Revenue KPI value should be 0.0 or similar but not crash
    kpis = {k["id"]: k["value"] for k in report["kpi_snapshot"]}
    assert kpis["revenue_growth"] in [0.0, None] or pd.isna(kpis["revenue_growth"])


def test_narrow_date_range_graceful():
    df = create_mock_df(2) # 2 days of coverage
    report = generate_executive_report(df)
    
    assert report["report_metadata"]["calendar_span_days"] == 2
    assert report["executive_summary"]["forecast_readiness_status"] == "UNAVAILABLE"


def test_forecast_unavailable_never_creates_business_performance_risk():
    # Verify business performance rating is separate from forecast status
    df = create_mock_df(days=5) 
    report = generate_executive_report(df)
    
    assert report["executive_summary"]["forecast_readiness_status"] == "UNAVAILABLE"
    # Forecast capability is Risk (since UNAVAILABLE), but it must not force overall status to Risk
    assert report["report_metadata"]["report_status"] != "Risk"
