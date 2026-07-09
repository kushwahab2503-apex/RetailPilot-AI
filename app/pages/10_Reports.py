import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

from app.components.layout import page_header, dataset_status
from backend.analytics_resolver import resolve_analytics_dataset
from backend.report_engine import (
    generate_executive_report,
    build_report_json,
    build_report_csv,
    build_report_pdf,
    to_json_serializable
)

st.set_page_config(page_title="RetailPilot AI - Executive Business Reports", layout="wide")

# Navigation header and dataset status widget
dataset_status()
page_header("Executive Reports Center", "Stateless, deterministic executive summaries and structured audit documents.")

# Inject Custom Elegant Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .status-badge {
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.78rem;
        text-transform: uppercase;
        display: inline-block;
    }
    
    .status-strong {
        background: rgba(16, 185, 129, 0.12);
        color: #10b981;
        border: 1px solid #10b981;
    }
    .status-stable {
        background: rgba(59, 130, 246, 0.12);
        color: #3b82f6;
        border: 1px solid #3b82f6;
    }
    .status-watch {
        background: rgba(245, 158, 11, 0.12);
        color: #f59e0b;
        border: 1px solid #f59e0b;
    }
    .status-risk {
        background: rgba(239, 68, 68, 0.12);
        color: #ef4444;
        border: 1px solid #ef4444;
    }
    .status-insufficient {
        background: rgba(156, 163, 175, 0.12);
        color: #9ca3af;
        border: 1px solid #9ca3af;
    }
    
    .card-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
        gap: 16px;
        margin: 15px 0;
    }
    
    .report-card {
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
        border-radius: 10px;
        padding: 16px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.15);
        transition: transform 0.2s ease;
    }
    
    .report-card:hover {
        transform: translateY(-2px);
    }
    
    .report-card-strong {
        border: 1px solid rgba(16, 185, 129, 0.4);
    }
    .report-card-stable {
        border: 1px solid rgba(59, 130, 246, 0.4);
    }
    .report-card-watch {
        border: 1px solid rgba(245, 158, 11, 0.4);
    }
    .report-card-risk {
        border: 1px solid rgba(239, 68, 68, 0.4);
    }
    .report-card-insufficient {
        border: 1px solid rgba(156, 163, 175, 0.4);
    }
    
    .card-label {
        font-size: 0.78rem;
        font-weight: 500;
        color: #9ca3af;
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    
    .card-value {
        font-size: 1.4rem;
        font-weight: 700;
        color: #f3f4f6;
        margin-bottom: 2px;
    }
    
    .card-meta {
        font-size: 0.72rem;
        color: #6b7280;
    }
    
    .brief-container {
        background: #1e293b;
        border-left: 5px solid #6366f1;
        border-radius: 6px;
        padding: 16px;
        margin-bottom: 20px;
    }
    
    .brief-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #f8fafc;
        margin-bottom: 6px;
    }
    
    .brief-body {
        font-size: 0.95rem;
        color: #d1d5db;
        line-height: 1.5;
    }
</style>
""", unsafe_allow_html=True)


# Fetch dataset from session resolver
resolved_data, source_name = resolve_analytics_dataset()

# Check dataset presence
if resolved_data is None:
    st.warning("Please upload a dataset or launch Demo Mode first.")
else:
    # Option inputs
    st.sidebar.header("Report Customization")
    custom_title = st.sidebar.text_input("Report Title", value="RetailPilot AI Executive Business Report")
    
    # Process cleaned flag
    is_cleaned = (source_name == "Cleaned Dataset")
    
    # Generate the executive report using stateless orchestration
    try:
        report = generate_executive_report(resolved_data, generated_from_cleaned_dataset=is_cleaned, report_title=custom_title)
    except Exception as e:
        st.error(f"Error compiling report data: {str(e)}")
        report = None
        
    if report is not None:
        metadata = report.get("report_metadata", {})
        summary = report.get("executive_summary", {})
        
        # 1. Report Overview Details
        st.subheader("Report Specification & Coverage")
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Total Rows Processed", f"{metadata.get('row_count', 0):,}")
        with c2:
            st.metric("Active Calendar Span", f"{metadata.get('calendar_span_days', 0)} Days")
        with c3:
            st.metric("Coverage Start Date", str(metadata.get('date_start') or "N/A"))
        with c4:
            st.metric("Coverage End Date", str(metadata.get('date_end') or "N/A"))
            
        # Display overall states
        col_status_left, col_status_right = st.columns(2)
        with col_status_left:
            perf_status = summary.get("performance_status", "Insufficient Data")
            badge_class = "status-strong" if perf_status in ["Strong", "Stable"] else "status-watch" if perf_status == "Watch" else "status-risk" if perf_status == "Risk" else "status-insufficient"
            st.markdown(f"**Business Performance Rating:** <span class='status-badge {badge_class}'>{perf_status}</span>", unsafe_allow_html=True)
            
        with col_status_right:
            forecast_status = summary.get("forecast_readiness_status", "UNAVAILABLE")
            badge_class = "status-strong" if forecast_status == "SUITABLE" else "status-watch" if forecast_status == "LIMITED" else "status-risk"
            st.markdown(f"**Forecast Modeling Capability:** <span class='status-badge {badge_class}'>{forecast_status}</span>", unsafe_allow_html=True)
            
        st.markdown("<div style='height:15px'></div>", unsafe_allow_html=True)
        
        # 2. Executive Brief Box
        st.markdown(f"""
        <div class="brief-container">
            <div class="brief-title">{summary.get("headline", "Diagnostic Brief")}</div>
            <div class="brief-body">{summary.get("summary", "")}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # 3. KPI Snapshot Grid
        st.subheader("Key Performance Heuristics")
        
        kpis = report.get("kpi_snapshot", [])
        
        # Render custom cards in rows
        st.markdown("<div class='card-grid'>", unsafe_allow_html=True)
        for k in kpis:
            val = k.get("value")
            unit = k.get("unit")
            status = k.get("status", "Insufficient Data")
            
            # Format value nicely
            if val is None:
                display_val = "N/A"
            elif isinstance(val, float):
                unit_label = f" {unit}" if unit else ""
                display_val = f"{val:,.2f}{unit_label}"
            elif isinstance(val, int):
                unit_label = f" {unit}" if unit else ""
                display_val = f"{val:,}{unit_label}"
            else:
                display_val = str(val)
                
            # Set card border based on status
            border_cls = "report-card-insufficient"
            if status in ["Strong", "Stable"]:
                border_cls = "report-card-strong"
            elif status == "Watch":
                border_cls = "report-card-watch"
            elif status == "Risk":
                border_cls = "report-card-risk"
                
            st.markdown(f"""
            <div class="report-card {border_cls}">
                <div class="card-label">{k.get('label')}</div>
                <div class="card-value">{display_val}</div>
                <div class="card-meta">Domain: {k.get('domain')} | Engine: {k.get('source_engine')}</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div style='height:15px'></div>", unsafe_allow_html=True)
        
        # 4. Executive Findings tabs
        st.subheader("Diagnostic Observations & Findings")
        
        findings_tabs = st.tabs(["Priority Actions", "Watch Items", "Positive Signals", "Data & Modeling Limitations"])
        
        with findings_tabs[0]:
            p_items = report.get("priority_findings", [])
            if not p_items:
                st.info("No active high-priority findings detected.")
            else:
                for idx, item in enumerate(p_items):
                    with st.expander(f"⚠️ {item.get('title')} ({item.get('domain')})", expanded=True):
                        st.markdown(f"**Brief:** {item.get('summary')}")
                        if item.get("evidence"):
                            st.write("**Evidence:**")
                            for ev in item.get("evidence", []):
                                st.write(f"- {ev}")
                        if item.get("recommended_action"):
                            st.markdown(f"**Action Recommended:** {item.get('recommended_action')}")
                            
        with findings_tabs[1]:
            w_items = report.get("watch_findings", [])
            if not w_items:
                st.info("No active watch items requiring monitoring.")
            else:
                for idx, item in enumerate(w_items):
                    with st.expander(f"🔍 {item.get('title')} ({item.get('domain')})", expanded=False):
                        st.markdown(f"**Brief:** {item.get('summary')}")
                        if item.get("evidence"):
                            st.write("**Evidence:**")
                            for ev in item.get("evidence", []):
                                st.write(f"- {ev}")
                        if item.get("recommended_action"):
                            st.markdown(f"**Action Recommended:** {item.get('recommended_action')}")
                            
        with findings_tabs[2]:
            p_signals = report.get("positive_findings", [])
            if not p_signals:
                st.info("No positive performance signals recorded.")
            else:
                for idx, item in enumerate(p_signals):
                    with st.expander(f"✅ {item.get('title')} ({item.get('domain')})", expanded=False):
                        st.markdown(f"**Brief:** {item.get('summary')}")
                        if item.get("evidence"):
                            st.write("**Evidence:**")
                            for ev in item.get("evidence", []):
                                st.write(f"- {ev}")
                        if item.get("recommended_action"):
                            st.markdown(f"**Action Recommended:** {item.get('recommended_action')}")
                            
        with findings_tabs[3]:
            limitations = report.get("limitations", [])
            if not limitations:
                st.info("No data quality warnings or modeling capability limits recorded.")
            else:
                for idx, item in enumerate(limitations):
                    with st.expander(f"ℹ️ {item.get('title')} ({item.get('domain')})", expanded=False):
                        st.markdown(f"**Brief:** {item.get('summary')}")
                        if item.get("evidence"):
                            st.write("**Evidence:**")
                            for ev in item.get("evidence", []):
                                st.write(f"- {ev}")
                        if item.get("recommended_action"):
                            st.markdown(f"**Resolution Step:** {item.get('recommended_action')}")
                            
        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        
        # 5. Domain Explorer Page Navigation Tabs
        st.subheader("Domain Explorer")
        domain_tabs = st.tabs(["Revenue", "Customers", "Products", "Order Economics", "Forecast Readiness"])
        
        domains_list = [
            ("revenue", domain_tabs[0], "Revenue Diagnostics"),
            ("customers", domain_tabs[1], "Customer Concentration & Retention"),
            ("products", domain_tabs[2], "Product Portfolio Metrics"),
            ("order_economics", domain_tabs[3], "Order Basket Economics"),
            ("forecast", domain_tabs[4], "Forecasting Model Capabilities")
        ]
        # We will populate each domain tab with the data from the engine
        with domain_tabs[0]:
            rev_d = report.get("domain_sections", {}).get("revenue", {})
            st.markdown(f"### Revenue Stream Status: `{rev_d.get('status', 'Insufficient Data')}`")
            # Metrics
            cols = st.columns(2)
            with cols[0]:
                g = rev_d.get("revenue_growth", {})
                st.metric("Revenue Growth", f"{g.get('value', 0):.2f}%" if g.get("value") is not None else "N/A" , delta_color="off")
            with cols[1]:
                v = rev_d.get("revenue_volatility", {})
                st.metric("Revenue Volatility (CV)", f"{v.get('value', 0):.2f}" if v.get("value") is not None else "N/A" , delta_color="off")
                
            ins = rev_d.get("insights", [])
            if ins:
                st.write("**Revenue Domain Observations:**")
                for item in ins:
                    st.write(f"- **{item.get('title')}**: {item.get('summary')}")
                    
        with domain_tabs[1]:
            cust_d = report.get("domain_sections", {}).get("customers", {})
            st.markdown(f"### Customer Cohort Status: `{cust_d.get('status', 'Insufficient Data')}`")
            cols = st.columns(3)
            with cols[0]:
                rr = cust_d.get("repeat_rate", {})
                st.metric("Repeat Buyer Rate", f"{rr.get('value', 0):.2f}%" if rr.get("value") is not None else "N/A")
            with cols[1]:
                od = cust_d.get("onetime_dependence", {})
                st.metric("One-Time Dependence", f"{od.get('value', 0):.2f}%" if od.get("value") is not None else "N/A")
            with cols[2]:
                tc = cust_d.get("top5_customer_concentration", {})
                st.metric("Top-5 Customer Share", f"{tc.get('value', 0):.2f}%" if tc.get("value") is not None else "N/A")
                
            ins = cust_d.get("insights", [])
            if ins:
                st.write("**Customer Domain Observations:**")
                for item in ins:
                    st.write(f"- **{item.get('title')}**: {item.get('summary')}")
                    
        with domain_tabs[2]:
            prod_d = report.get("domain_sections", {}).get("products", {})
            st.markdown(f"### Product Catalog Status: `{prod_d.get('status', 'Insufficient Data')}`")
            cols = st.columns(4)
            with cols[0]:
                tp1 = prod_d.get("top1_product_concentration", {})
                st.metric("Top-1 Concentration", f"{tp1.get('value', 0):.2f}%" if tp1.get("value") is not None else "N/A")
            with cols[1]:
                tp5 = prod_d.get("top5_product_concentration", {})
                st.metric("Top-5 Concentration", f"{tp5.get('value', 0):.2f}%" if tp5.get("value") is not None else "N/A")
            with cols[2]:
                ps = prod_d.get("pareto_share", {})
                st.metric("Pareto Product Share", f"{ps.get('value', 0):.2f}%" if ps.get("value") is not None else "N/A")
            with cols[3]:
                lp = prod_d.get("low_performing_share", {})
                st.metric("Low-Performing Share", f"{lp.get('value', 0):.2f}%" if lp.get("value") is not None else "N/A")
                
            ins = prod_d.get("insights", [])
            if ins:
                st.write("**Product Domain Observations:**")
                for item in ins:
                    st.write(f"- **{item.get('title')}**: {item.get('summary')}")
                    
        with domain_tabs[3]:
            oe_d = report.get("domain_sections", {}).get("order_economics", {})
            st.markdown(f"### Order Balance Status: `{oe_d.get('status', 'Insufficient Data')}`")
            cols = st.columns(3)
            with cols[0]:
                ag = oe_d.get("aov_growth", {})
                st.metric("AOV Growth", f"{ag.get('value', 0):.2f}%" if ag.get("value") is not None else "N/A")
            with cols[1]:
                ug = oe_d.get("upo_growth", {})
                st.metric("UPO Growth", f"{ug.get('value', 0):.2f}%" if ug.get("value") is not None else "N/A")
            with cols[2]:
                rg = oe_d.get("rpc_growth", {})
                st.metric("RPC Growth", f"{rg.get('value', 0):.2f}%" if rg.get("value") is not None else "N/A")
                
            ins = oe_d.get("insights", [])
            if ins:
                st.write("**Order Economics Observations:**")
                for item in ins:
                    st.write(f"- **{item.get('title')}**: {item.get('summary')}")
                    
        with domain_tabs[4]:
            fc_d = report.get("domain_sections", {}).get("forecast", {})
            st.markdown(f"### Forecasting Capability: `{fc_d.get('readiness_state', 'UNAVAILABLE')}`")
            st.info(f"**Diagnostic Status:** {fc_d.get('mapped_status', 'Risk')} — {fc_d.get('readiness_note')}")
            
            reasons = fc_d.get("capability_reasons", [])
            if reasons:
                st.write("**Readiness Requirements Check:**")
                for r in reasons:
                    st.write(f"- {r}")
            else:
                st.write("**All chronological readiness requirements satisfied.**")
                
            ins = fc_d.get("insights", [])
            if ins:
                st.write("**Forecasting Domain Observations:**")
                for item in ins:
                    st.write(f"- **{item.get('title')}**: {item.get('summary')}")
                    
        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        
        # 6. Export Center
        st.subheader("Executive Exports Center")
        
        # Place download buttons side by side
        col_ex_1, col_ex_2, col_ex_3 = st.columns(3)
        
        with col_ex_1:
            try:
                pdf_bytes = build_report_pdf(report)
                if isinstance(pdf_bytes, bytearray):
                    pdf_bytes = bytes(pdf_bytes)
                if not isinstance(pdf_bytes, bytes):
                    raise TypeError(f"Invalid binary data format: {type(pdf_bytes)}")
                st.download_button(
                    label="Download Executive PDF",
                    data=pdf_bytes,
                    file_name=f"executive_brief_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"Failed to compile PDF: {str(e)}")
                
        with col_ex_2:
            try:
                csv_bytes = build_report_csv(report)
                st.download_button(
                    label="Download Flattened CSV Data",
                    data=csv_bytes,
                    file_name=f"executive_metrics_{datetime.now().strftime('%Y%md')}.csv",
                    mime="text/csv"
                )
            except Exception as e:
                st.error(f"Failed to generate CSV: {str(e)}")
                
        with col_ex_3:
            try:
                json_bytes = build_report_json(report)
                st.download_button(
                    label="Download Raw JSON Schema",
                    data=json_bytes,
                    file_name=f"executive_report_{datetime.now().strftime('%Y%md')}.json",
                    mime="application/json"
                )
            except Exception as e:
                st.error(f"Failed to format JSON: {str(e)}")
                
        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        
        # 7. Methodology & Audit Trail
        st.subheader("Methodology Heuristics & Audit Trace")
        
        with st.expander("Methodology Specifications"):
            for m_key, m_val in report.get("methodology", {}).items():
                st.markdown(f"**{m_key.replace('_', ' ').title()}:** {m_val}")
                
        with st.expander("Orchestration Service Logs and Traceability"):
            st.dataframe(pd.DataFrame(report.get("source_traceability", [])))
