import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from app.components.layout import page_header, dataset_status
from backend.analytics_resolver import resolve_analytics_dataset
from backend.formatters import format_indian_currency, format_indian_number
from backend.business_health_engine import evaluate_business_health, calculate_daily_volatility
from backend.analytics_engine import prepare_analytics_dataset

# Configure page layout
st.set_page_config(page_title="RetailPilot AI - Business Health Diagnoses", layout="wide")

# Render layout header status component
dataset_status()
page_header("Business Health Intelligence", "Stateless diagnostic audits evaluating organizational growth, volatility, concentrations, and readiness.")

# Standard CSS Inject for Premium Theme & Design aesthetics
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 20px;
        text-align: left;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(99, 102, 241, 0.4);
    }
    .metric-label {
        font-size: 0.82rem;
        font-weight: 500;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 1.65rem;
        font-weight: 700;
        color: #f3f4f6;
        margin-bottom: 2px;
    }
    .metric-subtext {
        font-size: 0.72rem;
        color: #6b7280;
    }
    .custom-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.08), transparent);
        margin: 20px 0;
    }
    .date-badge {
        background: #1e1b4b;
        color: #c7d2fe;
        border: 1px solid #4338ca;
        border-radius: 4px;
        padding: 4px 8px;
        font-family: monospace;
        font-size: 0.82rem;
    }
</style>
""", unsafe_allow_html=True)


# Domain card styling helper
def render_domain_card(title: str, status: str, subtitle: str = ""):
    bg_color = "rgba(16, 185, 129, 0.08)"
    border_color = "#10b981"
    text_color = "#10b981"
    
    if status == "Stable":
        bg_color = "rgba(59, 130, 246, 0.08)"
        border_color = "#3b82f6"
        text_color = "#3b82f6"
    elif status == "Watch":
        bg_color = "rgba(245, 158, 11, 0.08)"
        border_color = "#f59e0b"
        text_color = "#f59e0b"
    elif status == "Risk":
        bg_color = "rgba(239, 68, 68, 0.08)"
        border_color = "#ef4444"
        text_color = "#ef4444"
    elif status == "Insufficient Data":
        bg_color = "rgba(156, 163, 175, 0.08)"
        border_color = "#9ca3af"
        text_color = "#9ca3af"
        
    st.markdown(f"""
        <div style="
            background: {bg_color};
            border-left: 5px solid {border_color};
            border-top: 1px solid rgba(255,255,255,0.05);
            border-right: 1px solid rgba(255,255,255,0.05);
            border-bottom: 1px solid rgba(255,255,255,0.05);
            border-radius: 8px;
            padding: 16px;
            text-align: left;
            min-height: 120px;
        ">
            <div style="font-size: 0.72rem; font-weight: 600; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px;">
                {title}
            </div>
            <div style="font-size: 1.35rem; font-weight: 700; color: {text_color}; margin-bottom: 4px;">
                {status}
            </div>
            <div style="font-size: 0.72rem; color: #d1d5db;">
                {subtitle}
            </div>
        </div>
    """, unsafe_allow_html=True)


# Main layout resolution
resolved_data, source_name = resolve_analytics_dataset()

if resolved_data is None:
    st.warning("Please upload a dataset or validate/clean your data on the preceding pages to activate this view.")
    st.markdown("""
        <div style='padding: 20px; border-radius: 8px; background-color: #111827; border: 1px solid rgba(255, 255, 255, 0.05); margin-top: 15px;'>
            <h4 style='margin-top: 0;'>Quick start guide:</h4>
            <ol>
                <li>Go to the <b>Upload Data</b> page in the left navigation sidebar.</li>
                <li>Upload your raw transaction CSV and trigger validation.</li>
                <li>(Optional) Clean the dataset under <b>Data Cleaning</b>.</li>
                <li>Return here to view health diagnostics reports.</li>
            </ol>
        </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/01_Upload_Data.py", label="Navigate to Dataset Upload Wizard", icon="📤")
else:
    # 1. Compute Business Health Diagnostics
    result = evaluate_business_health(resolved_data)
    meta_dates = result["dates_metadata"]
    metrics = result["metrics"]
    domain_statuses = result["domain_statuses"]
    findings = result["executive_findings"]

    st.markdown(f"📊 **Working Source:** `{source_name}`")
    
    # Overall Business Health Banner
    overall_status = result.get("overall_status", "Insufficient Data")
    indicator_counts = result.get("indicator_counts", {})
    
    # Select color scheme based on overall status
    status_colors = {
        "Strong": {"bg": "rgba(16, 185, 129, 0.08)", "border": "#10b981", "text": "#10b981", "badge": "🟢"},
        "Stable": {"bg": "rgba(59, 130, 246, 0.08)", "border": "#3b82f6", "text": "#3b82f6", "badge": "🔵"},
        "Watch": {"bg": "rgba(245, 158, 11, 0.08)", "border": "#f59e0b", "text": "#f59e0b", "badge": "🟡"},
        "Risk": {"bg": "rgba(239, 68, 68, 0.08)", "border": "#ef4444", "text": "#ef4444", "badge": "🔴"},
        "Insufficient Data": {"bg": "rgba(156, 163, 175, 0.08)", "border": "#9ca3af", "text": "#9ca3af", "badge": "⚪"}
    }
    
    style = status_colors.get(overall_status, status_colors["Insufficient Data"])
    
    st.markdown(f"""
        <div style="
            background: {style['bg']};
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-left: 8px solid {style['border']};
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 24px;
            text-align: left;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        ">
            <h3 style="margin: 0 0 4px 0; color: #f3f4f6; font-size: 1.15rem; font-weight: 600; border: none; padding: 0;">
                Overall Business Health Profile: <span style="color: {style['text']}; font-weight: 700;">{style['badge']} {overall_status}</span>
            </h3>
            <p style="margin: 0 0 16px 0; color: #9ca3af; font-size: 0.78rem;">
                Derived across the 4 business-performance domains (Revenue, Customer, Product, and Economics). Forecast Readiness is evaluated separately.
            </p>
            <div style="display: flex; gap: 16px; flex-wrap: wrap;">
                <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); padding: 8px 14px; border-radius: 8px; text-align: center; min-width: 100px;">
                    <div style="font-size: 0.68rem; color: #9ca3af; text-transform: uppercase; font-weight: 500; letter-spacing: 0.03em;">🟢 Strong</div>
                    <div style="font-size: 1.15rem; font-weight: 700; color: #10b981; margin-top: 2px;">{indicator_counts.get('Strong', 0)}</div>
                </div>
                <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); padding: 8px 14px; border-radius: 8px; text-align: center; min-width: 100px;">
                    <div style="font-size: 0.68rem; color: #9ca3af; text-transform: uppercase; font-weight: 500; letter-spacing: 0.03em;">🔵 Stable</div>
                    <div style="font-size: 1.15rem; font-weight: 700; color: #3b82f6; margin-top: 2px;">{indicator_counts.get('Stable', 0)}</div>
                </div>
                <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); padding: 8px 14px; border-radius: 8px; text-align: center; min-width: 100px;">
                    <div style="font-size: 0.68rem; color: #9ca3af; text-transform: uppercase; font-weight: 500; letter-spacing: 0.03em;">🟡 Watch</div>
                    <div style="font-size: 1.15rem; font-weight: 700; color: #f59e0b; margin-top: 2px;">{indicator_counts.get('Watch', 0)}</div>
                </div>
                <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); padding: 8px 14px; border-radius: 8px; text-align: center; min-width: 100px;">
                    <div style="font-size: 0.68rem; color: #9ca3af; text-transform: uppercase; font-weight: 500; letter-spacing: 0.03em;">🔴 Risk</div>
                    <div style="font-size: 1.15rem; font-weight: 700; color: #ef4444; margin-top: 2px;">{indicator_counts.get('Risk', 0)}</div>
                </div>
                <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); padding: 8px 14px; border-radius: 8px; text-align: center; min-width: 120px;">
                    <div style="font-size: 0.68rem; color: #9ca3af; text-transform: uppercase; font-weight: 500; letter-spacing: 0.03em;">⚪ Insufficient</div>
                    <div style="font-size: 1.15rem; font-weight: 700; color: #9ca3af; margin-top: 2px;">{indicator_counts.get('Insufficient Data', 0)}</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # 2. Executive Diagnostic Profile Cards Grid
    st.markdown("### Executive Diagnostic Profile")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        rev_g_val = metrics["revenue_growth"]["value"]
        rev_subtitle = f"Growth: {rev_g_val:+.1f}%" if rev_g_val is not None else "Insufficient Timeline"
        render_domain_card("Revenue Health", domain_statuses["revenue_health"], rev_subtitle)
        
    with col2:
        rr_val = metrics["repeat_rate"]["value"]
        rr_subtitle = f"Repeat Rate: {rr_val:.1f}%" if rr_val is not None else "Missing Cust ID"
        render_domain_card("Customer Health", domain_statuses["customer_health"], rr_subtitle)
        
    with col3:
        p5_val = metrics["top5_product_concentration"]["value"]
        p5_subtitle = f"Top 5 Pct: {p5_val:.1f}%" if p5_val is not None else "Missing Products"
        render_domain_card("Product Health", domain_statuses["product_health"], p5_subtitle)
        
    with col4:
        aov_g_val = metrics["aov_growth"]["value"]
        aov_subtitle = f"AOV Growth: {aov_g_val:+.1f}%" if aov_g_val is not None else "Insufficient Timeline"
        render_domain_card("Order Economics", domain_statuses["order_economics"], aov_subtitle)
        
    with col5:
        fc_val = metrics["forecast_readiness"]["value"]
        render_domain_card("Forecast Readiness", domain_statuses["forecast_readiness"], f"State: {fc_val}")

    st.markdown("<div class='custom-divider'></div>", unsafe_allow_html=True)

    # 3. Calendar Comparison Windows Details
    st.markdown("### Comparable Comparison Windows Details")
    if meta_dates["split_valid"]:
        st.markdown(f"""
        Metric growth and economic trends are calculated by comparing equal-length chronological calendar windows anchored at `max(OrderDate)`:
        *   **Recent Window**: <span class='date-badge'>{meta_dates['recent_start']}</span> to <span class='date-badge'>{meta_dates['recent_end']}</span> ({meta_dates['window_size']} calendar days)
        *   **Previous Window**: <span class='date-badge'>{meta_dates['prev_start']}</span> to <span class='date-badge'>{meta_dates['prev_end']}</span> ({meta_dates['window_size']} calendar days)
        """, unsafe_allow_html=True)
        # Check remainder
        min_date_raw = pd.to_datetime(meta_dates["min_date"])
        prev_start_raw = pd.to_datetime(meta_dates["prev_start"])
        remainder_days = (prev_start_raw - min_date_raw).days
        if remainder_days > 0:
            remainder_end = (prev_start_raw - timedelta(days=1)).strftime("%Y-%m-%d")
            st.markdown(f"💡 *Earliest Remainder Period excluded from growth calculations*: <span class='date-badge'>{meta_dates['min_date']}</span> to <span class='date-badge'>{remainder_end}</span> ({remainder_days} days offset)", unsafe_allow_html=True)
    else:
        st.info(f"Comparison windows are unavailable because the active dataset span ({meta_dates['span_days']} days) is too short. Minimum window sizes require at least 2 span days.")

    st.markdown("<div class='custom-divider'></div>", unsafe_allow_html=True)

    # 4. Executive Finding Logs Checklist
    st.markdown("### Executive Findings Checklist")
    
    with st.expander("🟢 Strengths Diagnostic Logs", expanded=True):
        if findings["strengths"]:
            for f in findings["strengths"]:
                st.markdown(f"✅ {f}")
        else:
            st.write("*No domain-level Strengths detected under current diagnostic bands.*")

    with st.expander("🔴 Risks Diagnostic Logs", expanded=True):
        if findings["risks"]:
            for f in findings["risks"]:
                st.markdown(f"❌ **Risk:** {f}")
        else:
            st.write("*No critical Risk conditions detected under current diagnostic bands.*")

    with st.expander("🟡 Watch Items Diagnostic Logs", expanded=True):
        if findings["watches"]:
            for f in findings["watches"]:
                st.markdown(f"⚠️ **Watch:** {f}")
        else:
            st.write("*No watch conditions triggered under current diagnostic bands.*")

    with st.expander("⚪ Key Data Limitations Logs", expanded=True):
        if findings["limitations"]:
            for f in findings["limitations"]:
                st.markdown(f"ℹ️ {f}")
        else:
            st.write("*No relevant data limitations identified.*")

    st.markdown("<div class='custom-divider'></div>", unsafe_allow_html=True)

    # 5. Factor Breakdown tabs
    st.markdown("### Domain Factors Audit Grid")
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Revenue & Volatility",
        "👥 Customer RFM Profile",
        "📦 Catalog & Products Portfolio",
        "💵 Economic Trends",
        "🔮 Forecasting Suitability"
    ])

    with tab1:
        st.markdown("#### Revenue Performance")
        st.caption("⚠️ **Diagnostic Heuristics Disclaimer**: Volatility and Growth thresholds represent configurable diagnostic bands and project heuristics, not universal industry definitions.")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("""<div class='metric-card'>
                <div class='metric-label'>Revenue Growth %</div>
                <div class='metric-value'>""" + (f"{rev_g_val:+.1f}%" if rev_g_val is not None else "N/A") + """</div>
                <div class='metric-subtext'>Status: """ + metrics["revenue_growth"]["status"] + """</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            vol_val = metrics["revenue_volatility"]["value"]
            st.markdown("""<div class='metric-card'>
                <div class='metric-label'>Daily Revenue Volatility (CV)</div>
                <div class='metric-value'>""" + (f"{vol_val:.2f}" if vol_val is not None else "N/A") + """</div>
                <div class='metric-subtext'>Status: """ + metrics["revenue_volatility"]["status"] + """</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("##### Daily Calendar sales timeline index")
        st.caption("Volatilities are computed over the full normalized daily calendar grid, zero-filling empty sales days to capture absolute variations.")
        prep_df, _ = prepare_analytics_dataset(resolved_data)
        min_dt = pd.to_datetime(meta_dates["min_date"])
        max_dt = pd.to_datetime(meta_dates["max_date"])
        
        if not prep_df.empty and pd.notna(min_dt) and pd.notna(max_dt):
            work_df = prep_df.copy()
            work_df["OrderDate_Day"] = pd.to_datetime(work_df["OrderDate"]).dt.normalize()
            daily_rev = work_df.groupby("OrderDate_Day")["_Revenue"].sum()
            all_dates = pd.date_range(start=min_dt.normalize(), end=max_dt.normalize(), freq='D')
            daily_rev = daily_rev.reindex(all_dates, fill_value=0.0)
            
            chart_df = pd.DataFrame({"Daily Revenue": daily_rev.values}, index=all_dates)
            st.line_chart(chart_df)

    with tab2:
        st.markdown("#### Customer RFM Profile & Dependence")
        st.caption("⚠️ **Diagnostic Heuristics Disclaimer**: Repeat and Concentration metrics represent configurable diagnostic bands and project heuristics, not universal industry definitions.")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("""<div class='metric-card'>
                <div class='metric-label'>Repeat Buyer Rate</div>
                <div class='metric-value'>""" + (f"{rr_val:.1f}%" if rr_val is not None else "N/A") + """</div>
                <div class='metric-subtext'>Status: """ + metrics["repeat_rate"]["status"] + """</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            dep_val = metrics["onetime_dependence"]["value"]
            st.markdown("""<div class='metric-card'>
                <div class='metric-label'>One-Time Buyer Dependence</div>
                <div class='metric-value'>""" + (f"{dep_val:.1f}%" if dep_val is not None else "N/A") + """</div>
                <div class='metric-subtext'>Status (Complement): """ + metrics["onetime_dependence"]["status"] + """</div>
            </div>""", unsafe_allow_html=True)
        with c3:
            c5_val = metrics["top5_customer_concentration"]["value"]
            c5_meta = metrics["top5_customer_concentration"]
            c_label = f" ({c5_meta['context']})" if c5_meta.get("context") != "Normal" else ""
            st.markdown("""<div class='metric-card'>
                <div class='metric-label'>Top-5 Customer Concentration</div>
                <div class='metric-value'>""" + (f"{c5_val:.1f}%" if c5_val is not None else "N/A") + """</div>
                <div class='metric-subtext'>Status: """ + c5_meta["status"] + c_label + """</div>
            </div>""", unsafe_allow_html=True)

        if rr_val is not None:
            st.markdown("##### Repeat vs One-Time Sales Balance Ratio")
            st.progress(rr_val / 100.0)
            st.caption(f"Active unique repeat customers accounts for {rr_val:.1f}% of buyers database in standard transaction span.")

    with tab3:
        st.markdown("#### Product Portfolio Concentration")
        st.caption("⚠️ **Diagnostic Heuristics Disclaimer**: Concentration, Pareto, and Segment contribution metrics represent configurable diagnostic bands and project heuristics, not universal industry definitions.")
        
        c1, c2 = st.columns(2)
        with c1:
            p5_val = metrics["top5_product_concentration"]["value"]
            p5_meta = metrics["top5_product_concentration"]
            p_label = f" ({p5_meta['context']})" if p5_meta.get("context") != "Normal" else ""
            st.markdown("""<div class='metric-card'>
                <div class='metric-label'>Top-5 Product Concentration</div>
                <div class='metric-value'>""" + (f"{p5_val:.1f}%" if p5_val is not None else "N/A") + """</div>
                <div class='metric-subtext'>Status: """ + p5_meta["status"] + p_label + """</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            p1_val = metrics["top1_product_concentration"]["value"]
            st.markdown("""<div class='metric-card'>
                <div class='metric-label'>Top-1 Product Concentration</div>
                <div class='metric-value'>""" + (f"{p1_val:.1f}%" if p1_val is not None else "N/A") + """</div>
                <div class='metric-subtext'>Status: """ + metrics["top1_product_concentration"]["status"] + """</div>
            </div>""", unsafe_allow_html=True)

        c3, c4 = st.columns(2)
        with c3:
            par_val = metrics["pareto_share"]["value"]
            st.markdown("""<div class='metric-card'>
                <div class='metric-label'>Product Pareto Share %</div>
                <div class='metric-value'>""" + (f"{par_val:.1f}%" if par_val is not None else "N/A") + """</div>
                <div class='metric-subtext'>Status: """ + metrics["pareto_share"]["status"] + """</div>
            </div>""", unsafe_allow_html=True)
            st.caption("Percentage of elements yielding 80% contribution. A low percentage implies strong reliance on few products.")
        with c4:
            low_val = metrics["low_performing_share"]["value"]
            st.markdown("""<div class='metric-card'>
                <div class='metric-label'>Long-Tail Product Share</div>
                <div class='metric-value'>""" + (f"{low_val:.1f}%" if low_val is not None else "N/A") + """</div>
                <div class='metric-subtext'>Status: """ + metrics["low_performing_share"]["status"] + """</div>
            </div>""", unsafe_allow_html=True)
            st.caption("Percentage of unique products contributing < 0.5% sales revenue (Slow Revenue Contribution long-tail share).")

    with tab4:
        st.markdown("#### Economic Diagnostics Trends")
        st.caption("⚠️ **Diagnostic Heuristics Disclaimer**: Order economics growth thresholds represent configurable diagnostic bands and project heuristics, not universal industry definitions.")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            aov_val = metrics["aov_growth"]["value"]
            st.markdown("""<div class='metric-card'>
                <div class='metric-label'>Average Order Value Growth</div>
                <div class='metric-value'>""" + (f"{aov_val:+.1f}%" if aov_val is not None else "N/A") + """</div>
                <div class='metric-subtext'>Status: """ + metrics["aov_growth"]["status"] + """</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            upo_val = metrics["upo_growth"]["value"]
            st.markdown("""<div class='metric-card'>
                <div class='metric-label'>Units Per Order Growth</div>
                <div class='metric-value'>""" + (f"{upo_val:+.1f}%" if upo_val is not None else "N/A") + """</div>
                <div class='metric-subtext'>Status: """ + metrics["upo_growth"]["status"] + """</div>
            </div>""", unsafe_allow_html=True)
        with c3:
            rpc_val = metrics["rpc_growth"]["value"]
            st.markdown("""<div class='metric-card'>
                <div class='metric-label'>Rev Per Customer Growth</div>
                <div class='metric-value'>""" + (f"{rpc_val:+.1f}%" if rpc_val is not None else "N/A") + """</div>
                <div class='metric-subtext'>Status: """ + metrics["rpc_growth"]["status"] + """</div>
            </div>""", unsafe_allow_html=True)

    with tab5:
        st.markdown("#### Forecasting Suitability Check")
        st.caption("Data readiness checker reused directly from Forecast Intelligence Module capability diagnostics.")
        
        fc_readiness = metrics["forecast_readiness"]
        
        st.markdown(f"**Current capability diagnostic state:** `{fc_readiness['value']}`")
        st.markdown(f"**Domain Mapping Status:** `{fc_readiness['status']}`")
        
        if fc_readiness['reasons']:
            st.markdown("**Diagnostic observations:**")
            for r in fc_readiness['reasons']:
                st.markdown(f"🔹 {r}")
        else:
            st.success("Dataset matches all parameters for robust forecasting.")

    st.markdown("<div class='custom-divider'></div>", unsafe_allow_html=True)

    # 6. Methodology expander
    with st.expander("📖 View Mathematical Diagnostics Methodology Rules"):
        st.markdown("""
        ### Calculation Details, Methods & Classifications
        
        #### I. Time-split Window Logic
        We calculate growth values dynamically by splitting the active timeline into two equal-sized blocks anchored on `max(OrderDate)`:
        - We find count of calendar days $T$ between the earliest date and latest date `max(OrderDate)`.
        - Half window size = $H = \\lfloor(T / 2)\\rfloor$ days.
        - **Recent window**: last $H$ days inclusive.
        - **Previous window**: preceding $H$ days.
        - Earliest days remaining if $T$ is odd are left out of comparison groups.
        
        #### II. Volatility Calculations
        We compile the complete calendar day timeline from day 1 to day $T$. Any calendar day lacking sales is filled with `0.0`.
        Daily Coefficient of Variation has formula:
        $$CV = \\frac{\\sigma}{\\mu}$$
        - $\\sigma$ represents standard deviation of daily sales (evaluated as sample standard deviation with standard degrees of freedom $ddof=1$).
        - $\\mu$ represents average daily revenue.
        
        #### III. Category Classification Thresholds (Adaptive Project Heuristics)
        The diagnostic category bands (Stable, Strong, Watch, Risk) used are configurable heuristics optimized for diagnostic profiling. They should not be conflated with universal industry benchmarks:
        - **Revenue Growth**: Strong ($\ge 10\\%$); Stable ($\ge -5\\%$); Watch ($\ge -20\\%$); Risk ($< -20\\%$).
        - **Daily Volatility (CV)**: Strong ($< 0.50$); Stable ($< 1.20$); Watch ($< 2.00$); Risk ($\\ge 2.00$).
        - **Repeat Customer Rate**: Strong ($\ge 40\\%$); Stable ($\ge 20\\%$); Watch ($\ge 10\\%$); Risk ($< 10\\%$).
        - **Top-5 Customer Concentration**: Strong ($< 20\\%$); Stable ($< 50\\%$); Watch ($< 70\\%$); Risk ($\\ge 70\\%$).
        - **Top-5 Product Concentration**: Strong ($< 40\\%$); Stable ($< 60\\%$); Watch ($< 80\\%$); Risk ($\\ge 80\\%$).
        - **Top-1 Product Concentration**: Strong ($< 15\\%$); Stable ($< 30\\%$); Watch ($< 50\\%$); Risk ($\\ge 50\\%$).
        - **Product Pareto Share**: Strong ($\ge 30\\%$); Stable ($\ge 20\\%$); Watch ($\ge 10\\%$); Risk ($< 10\\%$).
        - **Long-Tail Product Share**: Strong ($< 20\\%$); Stable ($< 50\\%$); Watch ($< 75\\%$); Risk ($\\ge 75\\%$).
        - **Order Economics Growths (AOV/UPO/RPC)**: Strong ($\ge 5\\%$); Stable ($\ge -2\\%$); Watch ($\ge -10\\%$); Risk ($< -10\\%$).
        """)
