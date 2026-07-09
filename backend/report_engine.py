import pandas as pd
import numpy as np
import json
from datetime import datetime
from typing import Dict, Any, List

from backend.analytics_engine import prepare_analytics_dataset
from backend.business_health_engine import evaluate_business_health
from backend.insights_engine import generate_business_insights, sort_insights
from backend.forecast_engine import detect_forecast_capabilities


def to_json_serializable(obj: Any) -> Any:
    """
    Recursively normalizes python / numpy / pandas types to native JSON compatible types.
    Prevents Timestamp leakage and numpy serialization issues.
    """
    if isinstance(obj, dict):
        return {str(k): to_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [to_json_serializable(x) for x in obj]
    elif isinstance(obj, tuple):
        return [to_json_serializable(x) for x in obj]
    elif isinstance(obj, (pd.Timestamp, datetime)):
        return obj.strftime("%Y-%m-%d %H:%M:%S")
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return [to_json_serializable(x) for x in obj.tolist()]
    elif pd.isna(obj):
        return None
    else:
        return obj


def clean_txt(text: Any) -> str:
    """
    Encodes unicode text safely for Helvetica FPDF standard fonts by replacing 
    Rupee marks and non-ASCII glyphs.
    """
    if text is None:
        return ""
    text_str = str(text)
    text_str = text_str.replace("₹", "INR ").replace("\u20b9", "INR ")
    text_str = text_str.replace("“", "\"").replace("”", "\"").replace("’", "'").replace("‘", "'")
    text_str = text_str.replace("—", "-")
    return text_str


def generate_executive_report(
    df: pd.DataFrame,
    generated_from_cleaned_dataset: bool = False,
    report_title: str = "RetailPilot AI Executive Business Report"
) -> Dict[str, Any]:
    """
    Generates a deterministic, explainable, export-ready executive business report.
    Orchestrates metrics and insights calculated by domain specific engines without duplication.
    """
    # 1. Analytics preparation and base extraction
    prep_df, prep_meta = prepare_analytics_dataset(df)
    
    # 2. Get business health evaluate results
    health_res = evaluate_business_health(df)
    
    # 3. Get compiled insights
    insights_res = generate_business_insights(df, generated_from_cleaned_dataset)
    
    # 4. Extract dates metadata
    dates_meta = health_res.get("dates_metadata", {})
    min_date = dates_meta.get("min_date")
    max_date = dates_meta.get("max_date")
    span_days = dates_meta.get("span_days", 0)
    
    # 5. Extract forecast capabilities
    f_caps = detect_forecast_capabilities(prep_df, "Daily") if not prep_df.empty else {
        "capability_state": "UNAVAILABLE", 
        "capability_reasons": ["Dataset empty or invalid"]
    }
    f_state = f_caps.get("capability_state", "UNAVAILABLE")
    
    # Track overall statuses
    overall_status = health_res.get("overall_status", "Insufficient Data")
    
    # Build metadata block
    report_metadata = {
        "report_title": report_title,
        "report_version": "1.0.0",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "generated_from_cleaned_dataset": generated_from_cleaned_dataset,
        "source_label": "Cleaned Working Dataset" if generated_from_cleaned_dataset else "Raw Uploaded Dataset",
        "row_count": len(df) if df is not None else 0,
        "date_start": min_date,
        "date_end": max_date,
        "calendar_span_days": span_days,
        "report_status": overall_status
    }
    
    # 6. Map the 12 locked KPIs Snapshot
    kpi_defs = [
        {"id": "revenue_growth", "domain": "Revenue", "label": "Revenue Growth %", "health_key": "revenue_growth", "unit": "%", "source_engine": "business_health_engine"},
        {"id": "daily_volatility", "domain": "Revenue", "label": "Daily Revenue Volatility CV", "health_key": "revenue_volatility", "unit": "CV", "source_engine": "business_health_engine"},
        {"id": "repeat_buyer_rate", "domain": "Customers", "label": "Repeat Buyer Rate %", "health_key": "repeat_rate", "unit": "%", "source_engine": "business_health_engine"},
        {"id": "top5_customer_concentration", "domain": "Customers", "label": "Top-5 Customer Concentration %", "health_key": "top5_customer_concentration", "unit": "%", "source_engine": "business_health_engine"},
        {"id": "top1_product_concentration", "domain": "Products", "label": "Top-1 Product Concentration %", "health_key": "top1_product_concentration", "unit": "%", "source_engine": "business_health_engine"},
        {"id": "top5_product_concentration", "domain": "Products", "label": "Top-5 Product Concentration %", "health_key": "top5_product_concentration", "unit": "%", "source_engine": "business_health_engine"},
        {"id": "product_pareto_share", "domain": "Products", "label": "Product Pareto Share %", "health_key": "pareto_share", "unit": "%", "source_engine": "business_health_engine"},
        {"id": "low_revenue_product_share", "domain": "Products", "label": "Low-Revenue Product Share %", "health_key": "low_performing_share", "unit": "%", "source_engine": "business_health_engine"},
        {"id": "aov_growth", "domain": "Order Economics", "label": "AOV Growth %", "health_key": "aov_growth", "unit": "%", "source_engine": "business_health_engine"},
        {"id": "upo_growth", "domain": "Order Economics", "label": "UPO Growth %", "health_key": "upo_growth", "unit": "%", "source_engine": "business_health_engine"},
        {"id": "rpc_growth", "domain": "Order Economics", "label": "RPC Growth %", "health_key": "rpc_growth", "unit": "%", "source_engine": "business_health_engine"},
        {"id": "forecast_capability", "domain": "Forecast Readiness", "label": "Forecast Capability State", "health_key": "forecast_readiness", "unit": None, "source_engine": "forecast_engine"}
    ]
    
    kpi_snapshot = []
    for definition in kpi_defs:
        metric_data = health_res["metrics"].get(definition["health_key"], {})
        
        # Pull metric details safely
        if definition["id"] == "forecast_capability":
            val = metric_data.get("value", f_state)
            status = metric_data.get("status", "Risk")
        else:
            val = metric_data.get("value")
            status = metric_data.get("status", "Insufficient Data")
            if val is None:
                status = "Insufficient Data"
                
        kpi_snapshot.append({
            "id": definition["id"],
            "domain": definition["domain"],
            "label": definition["label"],
            "value": val,
            "unit": definition["unit"],
            "status": status,
            "source_engine": definition["source_engine"]
        })
        
    # 7. Categorize Insights Findings
    raw_insights = insights_res.get("insights", [])
    sorted_raw_insights = sort_insights(raw_insights)
    
    priority_findings = []
    watch_findings = []
    positive_findings = []
    limitations = []
    
    unique_insight_ids = set()
    for ins in sorted_raw_insights:
        ins_id = ins.get("id")
        if ins_id in unique_insight_ids:
            continue
        unique_insight_ids.add(ins_id)
        
        is_lim = (
            ins.get("domain") in ["Data Quality", "Forecast Readiness"] or 
            ins_id in ["data_chronological_unavailable", "forecast_unavailable_informational", "forecast_ready_limited", "forecast_ready_suitable"] or
            ins.get("status") == "Unavailable"
        )
        
        if is_lim:
            limitations.append(ins)
        elif ins.get("priority") in [1, 2]:
            priority_findings.append(ins)
        elif ins.get("severity") == "Watch":
            watch_findings.append(ins)
        elif ins.get("severity") == "Positive":
            positive_findings.append(ins)
        else:
            limitations.append(ins)
            
    # Compile executive summary paragraph
    perf_domains = {
        "revenue_health": "Revenue Health",
        "customer_health": "Customer Health",
        "product_health": "Product Portfolio Health",
        "order_economics": "Order Economics"
    }
    
    domain_statuses = health_res.get("domain_statuses", {})
    perf_statuses = {k: domain_statuses.get(k, "Insufficient Data") for k in perf_domains.keys()}
    
    insufficient_list = [perf_domains[k] for k, v in perf_statuses.items() if v == "Insufficient Data"]
    risk_list = [perf_domains[k] for k, v in perf_statuses.items() if v == "Risk"]
    watch_list = [perf_domains[k] for k, v in perf_statuses.items() if v == "Watch"]
    strong_list = [perf_domains[k] for k, v in perf_statuses.items() if v in ["Strong", "Stable"]]
    
    if len(insufficient_list) == 4:
        summary_text = "Current data coverage is insufficient for complete business performance evaluation. Available observations are reported separately from unavailable diagnostics."
        headline_text = "Insufficient Data for Diagnostic Evaluation"
    elif len(strong_list) > 0 and (len(risk_list) > 0 or len(watch_list) > 0):
        s_names = ", ".join(strong_list)
        a_names = ", ".join(risk_list + watch_list)
        summary_text = f"The business shows mixed operating conditions, with strengths in {s_names} and attention required in {a_names}."
        headline_text = "Mixed Operating Conditions Detected"
    elif len(risk_list) > 0:
        headline_text = "Action Required: Risk Indicators Detected"
        s_names = ", ".join(risk_list)
        summary_text = f"Immediate attention is required in {len(risk_list)} business domain(s), led by {s_names}."
    elif len(watch_list) > 0:
        headline_text = "Monitoring Recommended: Attention Areas Flagged"
        s_names = ", ".join(watch_list)
        summary_text = f"{len(watch_list)} business domain(s) require monitoring, particularly {s_names}."
    else:
        summary_text = "Business performance indicators are broadly favorable across calculable domains, with no active Risk or Watch classifications."
        headline_text = "Strong Operating Performance"
        
    # Isolation override check:
    # If the business performance is Strong or Stable but the forecast readiness state is UNAVAILABLE, 
    # the summary wording should clearly isolate it.
    if overall_status in ["Strong", "Stable"] and f_state == "UNAVAILABLE":
        summary_text = "Business performance indicators are favorable where calculable, while forecasting remains unavailable because the dataset does not yet satisfy chronological readiness requirements."
        
    executive_summary = {
        "overall_business_status": overall_status,
        "performance_status": overall_status,
        "forecast_readiness_status": f_state,
        "headline": headline_text,
        "summary": summary_text,
        "domain_statuses": {
            "revenue_health": domain_statuses.get("revenue_health", "Insufficient Data"),
            "customer_health": domain_statuses.get("customer_health", "Insufficient Data"),
            "product_health": domain_statuses.get("product_health", "Insufficient Data"),
            "order_economics": domain_statuses.get("order_economics", "Insufficient Data"),
            "forecast_readiness": domain_statuses.get("forecast_readiness", "Risk")
        },
        "indicator_counts": health_res.get("indicator_counts", {
            "Strong": 0, "Stable": 0, "Watch": 0, "Risk": 0, "Insufficient Data": 4
        })
    }
    
    # Compile Domain Sections mapping
    domain_sections = {
        "revenue": {
            "status": domain_statuses.get("revenue_health", "Insufficient Data"),
            "revenue_growth": health_res["metrics"].get("revenue_growth"),
            "revenue_volatility": health_res["metrics"].get("revenue_volatility"),
            "comparison_window": dates_meta,
            "insights": [i for i in sorted_raw_insights if i["domain"] == "Revenue"],
            "limitations": [i for i in sorted_raw_insights if i["domain"] == "Data Quality" and "revenue" in i.get("id", "")]
        },
        "customers": {
            "status": domain_statuses.get("customer_health", "Insufficient Data"),
            "repeat_rate": health_res["metrics"].get("repeat_rate"),
            "onetime_dependence": health_res["metrics"].get("onetime_dependence"),
            "top5_customer_concentration": health_res["metrics"].get("top5_customer_concentration"),
            "insights": [i for i in sorted_raw_insights if i["domain"] == "Customers"]
        },
        "products": {
            "status": domain_statuses.get("product_health", "Insufficient Data"),
            "top1_product_concentration": health_res["metrics"].get("top1_product_concentration"),
            "top5_product_concentration": health_res["metrics"].get("top5_product_concentration"),
            "pareto_share": health_res["metrics"].get("pareto_share"),
            "low_performing_share": health_res["metrics"].get("low_performing_share"),
            "insights": [i for i in sorted_raw_insights if i["domain"] == "Products"]
        },
        "order_economics": {
            "status": domain_statuses.get("order_economics", "Insufficient Data"),
            "aov_growth": health_res["metrics"].get("aov_growth"),
            "upo_growth": health_res["metrics"].get("upo_growth"),
            "rpc_growth": health_res["metrics"].get("rpc_growth"),
            "comparison_window": dates_meta,
            "insights": [i for i in sorted_raw_insights if i["domain"] == "Order Economics"]
        },
        "forecast": {
            "readiness_state": f_state,
            "mapped_status": health_res["metrics"].get("forecast_readiness", {}).get("status", "Risk"),
            "capability_reasons": f_caps.get("capability_reasons", []),
            "insights": [i for i in sorted_raw_insights if i["domain"] == "Forecast Readiness" or i["id"] == "forecast_unavailable_informational"],
            "readiness_note": "Forecast readiness is evaluated as a separate operational capability and is not factored into the overall business performance evaluation."
        }
    }
    
    methodology = {
        "comparison_window_method": "Equal-length calendar split windows anchored at max(OrderDate). Excluded remainder days are left out.",
        "volatility_method": "Daily calendar zero filling. Coefficient of Variation (CV) computed as standard deviation (ddof=1) divided by mean revenue.",
        "classification_note": "Diagnostic thresholds use stateless heuristics based on RetailPilot AI project standards. No composite scoring is employed.",
        "forecast_isolation_note": "Forecast capability evaluation is handled separately and does not taint business performance indicators."
    }

    source_traceability = [
        {"section": "Executive Summary", "source_engine": "business_health_engine", "source_function": "evaluate_business_health"},
        {"section": "Strategic Findings", "source_engine": "insights_engine", "source_function": "generate_business_insights"},
        {"section": "Forecast Readiness", "source_engine": "forecast_engine", "source_function": "detect_forecast_capabilities"},
        {"section": "Analytics Preparation", "source_engine": "analytics_engine", "source_function": "prepare_analytics_dataset"},
        {"section": "Customer Preparation", "source_engine": "customer_engine", "source_function": "prepare_customer_dataset"},
        {"section": "Product Preparation", "source_engine": "product_engine", "source_function": "prepare_product_dataset"}
    ]
    
    return {
        "report_metadata": report_metadata,
        "executive_summary": executive_summary,
        "kpi_snapshot": kpi_snapshot,
        "priority_findings": priority_findings,
        "positive_findings": positive_findings,
        "watch_findings": watch_findings,
        "limitations": limitations,
        "domain_sections": domain_sections,
        "methodology": methodology,
        "source_traceability": source_traceability
    }


def build_report_json(report: Dict[str, Any]) -> bytes:
    """
    Streamlit-independent helper. Encodes executive report definition to raw JSON bytes.
    Ensures safe type conversions.
    """
    clean_report = to_json_serializable(report)
    return json.dumps(clean_report, indent=2).encode("utf-8")


def build_report_csv(report: Dict[str, Any]) -> bytes:
    """
    Streamlit-independent helper. Encodes metrics and findings to flattened CSV structure.
    """
    rows = []
    
    # 1. Flatten KPIs Snapshot
    for kpi in report.get("kpi_snapshot", []):
         rows.append({
             "record_type": "KPI",
             "id": kpi.get("id", ""),
             "domain": kpi.get("domain", ""),
             "label": kpi.get("label", ""),
             "value": str(kpi.get("value", "")) if kpi.get("value") is not None else "",
             "unit": kpi.get("unit", "") if kpi.get("unit") is not None else "",
             "status": kpi.get("status", ""),
             "source_engine": kpi.get("source_engine", ""),
             "title": "",
             "summary": "",
             "severity": "",
             "priority": "",
             "evidence": "",
             "recommended_action": ""
         })
         
    # KPIs sorted by identifier
    rows_kpis = sorted(rows, key=lambda x: x["id"])
    
    # 2. Flatten Findings
    finding_rows = []
    
    findings_sources = [
        ("Priority Finding", report.get("priority_findings", [])),
        ("Watch Finding", report.get("watch_findings", [])),
        ("Positive Finding", report.get("positive_findings", [])),
        ("Limitation", report.get("limitations", []))
    ]
    
    for rec_type, f_list in findings_sources:
        for f in f_list:
            finding_rows.append({
                "record_type": rec_type,
                "id": f.get("id", ""),
                "domain": f.get("domain", ""),
                "label": f.get("metric_name", "") if f.get("metric_name") is not None else "",
                "value": str(f.get("metric_value", "")) if f.get("metric_value") is not None else "",
                "unit": f.get("unit", "") if f.get("unit") is not None else "",
                "status": f.get("status", "") if f.get("status") is not None else "",
                "source_engine": f.get("source_engine", ""),
                "title": f.get("title", ""),
                "summary": f.get("summary", ""),
                "severity": f.get("severity", ""),
                "priority": str(f.get("priority", "")),
                "evidence": "; ".join(f.get("evidence", [])) if isinstance(f.get("evidence"), list) else str(f.get("evidence", "")),
                "recommended_action": f.get("recommended_action", "")
            })
            
    # Deterministic priority / domain / id ordering for findings
    def sort_prio(x):
        try:
            return int(x["priority"])
        except ValueError:
            return 99
            
    finding_rows_sorted = sorted(finding_rows, key=lambda x: (sort_prio(x), x["domain"], x["id"]))
    
    total_records = rows_kpis + finding_rows_sorted
    
    columns = [
        "record_type", "id", "domain", "label", "value", "unit", "status",
        "source_engine", "title", "summary", "severity", "priority",
        "evidence", "recommended_action"
    ]
    df_csv = pd.DataFrame(total_records, columns=columns)
    return df_csv.to_csv(index=False).encode("utf-8")


def build_report_pdf(report: Dict[str, Any]) -> bytes:
    """
    Streamlit-independent helper. Compiles the executive layout into printable FPDF bytes.
    Handles empty properties and status-aware border decoration defensively.
    """
    from fpdf import FPDF
    
    class ExecutiveReportPDF(FPDF):
        def __init__(self, title_text="RetailPilot AI Executive Business Report"):
            super().__init__()
            self.report_title = title_text
            self.alias_nb_pages()
            
        def header(self):
            self.set_font("helvetica", "B", 8)
            self.set_text_color(100, 100, 100)
            self.cell(0, 8, clean_txt(self.report_title).upper(), border="B", align="R")
            self.ln(11)
            
        def footer(self):
            self.set_y(-15)
            self.set_font("helvetica", "I", 8)
            self.set_text_color(160, 160, 160)
            self.cell(0, 10, f"Page {self.page_no()}/{{nb}} | Confidential - RetailPilot AI Decision Support", align="C")

    # Initialize FPDF
    title_text = report.get("report_metadata", {}).get("report_title", "RetailPilot AI Executive Business Report")
    pdf = ExecutiveReportPDF(title_text)
    pdf.add_page()
    
    # 1. Document Title
    pdf.set_font("helvetica", "B", 16)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 10, clean_txt(title_text))
    pdf.ln(10)
    
    # Metadata Overview
    meta = report.get("report_metadata", {})
    pdf.set_font("helvetica", "", 9)
    pdf.set_text_color(100, 116, 139)
    meta_info = (
        f"Generated At: {meta.get('generated_at', 'N/A')} | "
        f"Source: {meta.get('source_label', 'N/A')} ({meta.get('row_count', 0)} rows)\n"
        f"Calendar Coverage Range: {meta.get('date_start', 'N/A')} to {meta.get('date_end', 'N/A')} "
        f"({meta.get('calendar_span_days', 0)} active days)"
    )
    pdf.multi_cell(pdf.epw, 5, clean_txt(meta_info))
    pdf.ln(5)
    
    # 2. Executive summary Narrative Box
    pdf.set_font("helvetica", "B", 12)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 8, "EXECUTIVE SUMMARY BRIEF")
    pdf.ln(8)
    
    summary = report.get("executive_summary", {})
    pdf.set_fill_color(248, 250, 252) # light gray background
    pdf.set_font("helvetica", "B", 10)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, clean_txt(summary.get("headline", "")), fill=True)
    pdf.ln(6)
    pdf.set_font("helvetica", "", 10)
    pdf.set_text_color(30, 41, 59)
    pdf.multi_cell(pdf.epw, 5, clean_txt(summary.get("summary", "")), fill=True)
    pdf.ln(5)
    
    # Business health domains overview block
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 8, "BUSINESS DIAGNOSTICS & FORECAST AUDIT STATUS")
    pdf.ln(8)
    
    # Render overall performance status and forecast capability status side by side
    pdf.set_font("helvetica", "", 10)
    perf_status = summary.get("performance_status", "Insufficient Data")
    forecast_status = summary.get("forecast_readiness_status", "UNAVAILABLE")
    
    pdf.cell(100, 6, f"Business Performance status: {perf_status}")
    pdf.cell(90, 6, f"Forecast Readiness status: {forecast_status}")
    pdf.ln(8)
    
    # 3. KPI Snapshot Table
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 8, "KEY PERFORMANCE INDICATORS SNAPSHOT")
    pdf.ln(8)
    
    # Draw KPI table headers
    pdf.set_font("helvetica", "B", 9)
    pdf.set_fill_color(226, 232, 240)
    pdf.set_text_color(51, 65, 85)
    pdf.cell(45, 7, "Domain", border=1, fill=True)
    pdf.cell(65, 7, "KPI Heuristic Metric", border=1, fill=True)
    pdf.cell(40, 7, "Value", border=1, fill=True, align="R")
    pdf.cell(40, 7, "Status", border=1, fill=True, align="C")
    pdf.ln(7)
    
    pdf.set_font("helvetica", "", 9)
    pdf.set_text_color(15, 23, 42)
    
    for k in report.get("kpi_snapshot", []):
        val = k.get("value")
        unit = k.get("unit")
        
        if val is None:
            val_str = "N/A"
        elif isinstance(val, float):
            unit_str = f" {unit}" if unit else ""
            val_str = f"{val:,.2f}{unit_str}"
        elif isinstance(val, int):
            unit_str = f" {unit}" if unit else ""
            val_str = f"{val:,}{unit_str}"
        else:
            val_str = str(val)
            
        pdf.cell(45, 6, clean_txt(k.get("domain", "")), border=1)
        pdf.cell(65, 6, clean_txt(k.get("label", "")), border=1)
        pdf.cell(40, 6, clean_txt(val_str), border=1, align="R")
        
        # Color Status cell based on mapping
        status_val = k.get("status", "Insufficient Data")
        if status_val in ["Strong", "Stable"]:
            pdf.set_fill_color(220, 252, 220)  # Light Green
            pdf.set_text_color(21, 128, 61)
        elif status_val == "Watch":
            pdf.set_fill_color(254, 243, 199)  # Light Orange
            pdf.set_text_color(180, 83, 9)
        elif status_val == "Risk":
            pdf.set_fill_color(254, 226, 226)  # Light Red
            pdf.set_text_color(185, 28, 28)
        else:
            pdf.set_fill_color(241, 245, 249)  # Light Gray
            pdf.set_text_color(100, 116, 139)
            
        pdf.cell(40, 6, clean_txt(status_val), border=1, fill=True, align="C")
        pdf.set_text_color(15, 23, 42)  # Reset letter colors
        pdf.ln(6)
        
    pdf.ln(5)
    
    # 4. Strategic Findings
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, "EXECUTIVE FINDINGS & DATA LIMITATIONS")
    pdf.ln(8)
    
    findings_sections = [
        ("PRIORITY ACTIONS REQUIRED", report.get("priority_findings", []), (185, 28, 28)),
        ("WATCH ITEMS TO MONITOR", report.get("watch_findings", []), (180, 83, 9)),
        ("POSITIVE OBSERVATIONS", report.get("positive_findings", []), (21, 128, 61)),
        ("DATA QUALITY & MODELING LIMITATIONS", report.get("limitations", []), (71, 85, 105))
    ]
    
    for title, items, color in findings_sections:
        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(*color)
        pdf.cell(0, 6, clean_txt(title))
        pdf.ln(6)
        pdf.set_text_color(15, 23, 42)
        
        if not items:
            pdf.set_font("helvetica", "I", 9)
            pdf.cell(0, 5, "No observations in this category.")
            pdf.ln(5)
        else:
            pdf.set_font("helvetica", "", 9)
            for item in items:
                title_line = f"* {item.get('title', 'Observation')} ({item.get('domain', 'General')})"
                pdf.set_font("helvetica", "B", 9)
                pdf.cell(0, 5, clean_txt(title_line))
                pdf.ln(5)
                
                pdf.set_font("helvetica", "", 9)
                pdf.multi_cell(pdf.epw, 4, f"  Summary: {clean_txt(item.get('summary', ''))}")
                pdf.set_x(pdf.l_margin)
                
                # Check for evidence list
                evidence_list = item.get("evidence", [])
                if evidence_list:
                    pdf.multi_cell(pdf.epw, 4, f"  Evidence: {'; '.join(evidence_list)}")
                    pdf.set_x(pdf.l_margin)
                    
                if item.get("recommended_action"):
                    pdf.multi_cell(pdf.epw, 4, f"  Recommendation: {clean_txt(item.get('recommended_action'))}")
                    pdf.set_x(pdf.l_margin)
                pdf.ln(2)
        pdf.ln(2)
        
    # 5. Domain Report Sections
    pdf.add_page()
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, "DETAILED DOMAIN REPORT EXPLORER")
    pdf.ln(8)
    
    domains_map = [
        ("revenue", "Revenue Health Analysis"),
        ("customers", "Customer Cohorts & Retention Analysis"),
        ("products", "Product portfolio & Catalog Analytics"),
        ("order_economics", "Order Basket Economics Summary"),
        ("forecast", "Forecasting Readiness & capability Analysis")
    ]
    
    for key, name in domains_map:
        data = report.get("domain_sections", {}).get(key, {})
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 6, clean_txt(name.upper()), border="B")
        pdf.ln(6)
        
        pdf.set_font("helvetica", "", 9)
        status_line = f"Domain Status: {data.get('status', data.get('readiness_state', 'Insufficient Data'))}"
        pdf.cell(0, 5, clean_txt(status_line))
        pdf.ln(5)
        
        # Output domain findings
        related_ins = data.get("insights", [])
        if related_ins:
            pdf.cell(0, 5, "Key insights:")
            pdf.ln(5)
            for ins in related_ins:
                pdf.cell(0, 4, f"- {clean_txt(ins.get('title'))}: {clean_txt(ins.get('summary'))}")
                pdf.ln(4)
        else:
            pdf.cell(0, 5, "No specific insights recorded for this domain.")
            pdf.ln(5)
        pdf.ln(4)
        
    # 6. Appendix & Audit Trail Traceability
    pdf.ln(4)
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 8, "METHODOLOGY APPENDIX & DATA AUDIT TRAIL")
    pdf.ln(8)
    
    pdf.set_font("helvetica", "B", 9)
    pdf.cell(0, 5, "Calculation Rules:")
    pdf.ln(5)
    pdf.set_font("helvetica", "", 9)
    for m_key, m_val in report.get("methodology", {}).items():
        pdf.multi_cell(pdf.epw, 4, f"- {m_key.replace('_', ' ').title()}: {clean_txt(m_val)}")
        pdf.set_x(pdf.l_margin)
    pdf.ln(3)
    
    pdf.set_font("helvetica", "B", 9)
    pdf.cell(0, 5, "Source Engine Traceability Logs:")
    pdf.ln(5)
    pdf.set_fill_color(248, 250, 252)
    
    pdf.set_font("helvetica", "B", 8)
    pdf.cell(50, 5, "Report Section", border=1, fill=True)
    pdf.cell(70, 5, "Source Python Module", border=1, fill=True)
    pdf.cell(70, 5, "Source Orchestration Function", border=1, fill=True)
    pdf.ln(5)
    
    pdf.set_font("helvetica", "", 8)
    for trace in report.get("source_traceability", []):
        pdf.cell(50, 5, clean_txt(trace.get("section")), border=1)
        pdf.cell(70, 5, clean_txt(trace.get("source_engine")), border=1)
        pdf.cell(70, 5, clean_txt(trace.get("source_function")), border=1)
        pdf.ln(5)
        
    raw_pdf = pdf.output()
    if isinstance(raw_pdf, bytearray):
        return bytes(raw_pdf)
    elif isinstance(raw_pdf, bytes):
        return raw_pdf
    elif isinstance(raw_pdf, str):
        return raw_pdf.encode("latin-1")
    return bytes(raw_pdf)
