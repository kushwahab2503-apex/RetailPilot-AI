import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from app.components.theme import inject_global_css

from app.components.layout import page_header, dataset_status
from backend.analytics_resolver import resolve_analytics_dataset
from backend.formatters import format_indian_currency, format_indian_number
from backend.insights_engine import generate_business_insights
from backend.analytics_engine import prepare_analytics_dataset
from backend.customer_engine import prepare_customer_dataset, calculate_lifetime_customer_base, get_customer_period_performance
from backend.product_engine import prepare_product_dataset, get_product_performance

# Configure page layout
st.set_page_config(page_title="RetailPilot AI - Deterministic Insights", layout="wide")

# Render layout header status component
dataset_status()
page_header("Insights Intelligence", "Deterministic, evidence-backed strategic actions and analytical limitation audits.")

# Inject shared light enterprise CSS
inject_global_css()

def render_summary_card(label, count, color):
    st.markdown(f"""
        <div class="report-card" style="border-top: 4px solid {color} !important; text-align: center;">
            <div class="card-label">
                {label}
            </div>
            <div class="card-value">
                {count}
            </div>
        </div>
    """, unsafe_allow_html=True)


def render_insight_card(insight):
    # Determine severity layout — uses semantic light palette
    sev = insight["severity"]
    if sev == "Positive":
        bg_color    = "#F0FDF4"
        border_color = "#86EFAC"
        badge_cls   = "badge-positive"
    elif sev == "Watch":
        bg_color    = "#FEFCE8"
        border_color = "#FDE68A"
        badge_cls   = "badge-watch"
    elif sev == "Risk":
        bg_color    = "#FFF5F5"
        border_color = "#FECACA"
        badge_cls   = "badge-risk"
    else:
        bg_color    = "#F0F7FF"
        border_color = "#BFDBFE"
        badge_cls   = "badge-informational"

    evidence_lst = "".join([f"<li>{ev}</li>" for ev in insight.get("evidence", [])])
    val_disp = f"{insight['metric_value']:.2f}" if isinstance(insight.get("metric_value"), float) else str(insight.get("metric_value", "None"))
    val_unit = f" {insight['unit']}" if insight.get("unit") else ""

    comp_disp = ""
    if insight.get("comparison_value") is not None:
        c_val = f"{insight['comparison_value']:.2f}" if isinstance(insight["comparison_value"], float) else str(insight["comparison_value"])
        comp_disp = f" | Threshold: {c_val}"

    st.markdown(f"""
        <div class="insight-card" style="background: {bg_color}; border-color: {border_color};">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap;">
                <h4 style="margin: 0 0 8px 0; color: #172033; font-size: 1.05rem; font-weight: 600; border: none; padding: 0;">
                    {insight['title']}
                </h4>
                <div>
                    <span class="badge badge-domain">{insight['domain']}</span>
                    <span class="badge {badge_cls}">{insight['severity']} (Priority {insight['priority']})</span>
                </div>
            </div>
            <p style="margin: 4px 0 12px 0; font-size: 0.88rem; color: #475569; font-weight: 500;">
                {insight['summary']}
            </p>
            <div style="margin-left: 16px; font-size: 0.82rem; color: #64748B; margin-bottom: 12px;">
                <ul style="margin: 0; padding-left: 0;">
                    {evidence_lst}
                </ul>
            </div>
            <div class="action-box">
                <strong>Recommended Action:</strong> {insight['recommended_action']}
            </div>
            <div class="telemetry-box">
                Telemetry Log &gt; Metric: {insight['metric_name']} | Value: {val_disp}{val_unit}{comp_disp} | Source: {insight['source_engine']}
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
                <li>Return here to view automated insights.</li>
            </ol>
        </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/01_Upload_Data.py", label="Navigate to Dataset Upload Wizard", icon="📤")
else:
    # 1. Compute Insights
    is_cleaned = (source_name == "Cleaned Dataset")
    res = generate_business_insights(resolved_data, generated_from_cleaned_dataset=is_cleaned)

    insights = res["insights"]
    priority_insights = res["priority_insights"]
    meta = res["metadata"]

    st.markdown(f"📊 **Working Source:** `{source_name}` | **Row Count:** {meta['working_row_count']} | **Cleaned Matrix:** `{meta['generated_from_cleaned_dataset']}`")

    # 2. Render Executive Dashboard Summary Row
    st.markdown("### Executive Overview Summary")
    sum_col1, sum_col2, sum_col3, sum_col4, sum_col5 = st.columns(5)
    
    # Calculate counts mapping accurately
    risks_count = res["severity_counts"].get("Risk", 0)
    watches_count = res["severity_counts"].get("Watch", 0)
    positives_count = res["severity_counts"].get("Positive", 0)
    
    # Data Limitations = Informational severity in Data Quality domain
    limitations_count = sum(1 for i in insights if i["domain"] == "Data Quality" and i["severity"] == "Informational")

    with sum_col1:
        render_summary_card("Total Insights", len(insights), "#6366f1")
    with sum_col2:
        render_summary_card("Priority Risks", risks_count, "#ef4444")
    with sum_col3:
        render_summary_card("Watch Items", watches_count, "#f59e0b")
    with sum_col4:
        render_summary_card("Positive Signals", positives_count, "#10b981")
    with sum_col5:
        render_summary_card("Data Limitations", limitations_count, "#3b82f6")

    st.markdown("<div class='custom-divider'></div>", unsafe_allow_html=True)

    # 3. Interactive Sidebar Filters
    st.sidebar.markdown("## Insights Filters")
    sector_filter = st.sidebar.selectbox(
        "Domain Sector",
        options=["All", "Revenue", "Customers", "Products", "Order Economics", "Forecast Readiness", "Data Quality"]
    )
    severity_filter = st.sidebar.selectbox(
        "Severity Level",
        options=["All", "Risk", "Watch", "Positive", "Informational"]
    )

    # Apply filters
    filtered_insights = insights
    if sector_filter != "All":
        filtered_insights = [i for i in filtered_insights if i["domain"] == sector_filter]
    if severity_filter != "All":
        filtered_insights = [i for i in filtered_insights if i["severity"] == severity_filter]

    # Split display: Priority Attention first, then Filtered Explorer
    col_left, col_right = st.columns([1, 1.2])

    with col_left:
        st.markdown("### 🔔 Priority Attention (Priority 1 & 2)")
        if not priority_insights:
            st.info("No crucial high-priority items require immediate action.")
        else:
            for pi in priority_insights:
                render_insight_card(pi)

    with col_right:
        st.markdown(f"### 🔍 Insights Explorer ({len(filtered_insights)} filtered)")
        if not filtered_insights:
            st.info("No insights found matching key metrics filters.")
        else:
            for fi in filtered_insights:
                render_insight_card(fi)

    st.markdown("<div class='custom-divider'></div>", unsafe_allow_html=True)

    # 4. Detailed Sector-Specific Tabs
    st.markdown("### 📊 Sector-Specific Analysis & Methodology")
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Revenue Sector",
        "👥 Customers Sector",
        "📦 Products Sector",
        "💰 Economics Sector",
        "🚦 Forecast & Quality Methodology"
    ])

    with tab1:
        st.markdown("#### Revenue Performance & Trend Volatility")
        try:
            prep_df, _ = prepare_analytics_dataset(resolved_data)
            if prep_df.empty:
                st.warning("No valid transaction rows found after applying validation filters.")
            elif "_Revenue" not in prep_df.columns or "OrderDate" not in prep_df.columns:
                st.warning("Required fields/columns for Revenue chart are missing or could not be derived.")
            else:
                daily_rev = prep_df.groupby("OrderDate")["_Revenue"].sum().reset_index()
                st.line_chart(data=daily_rev, x="OrderDate", y="_Revenue")
        except Exception as e:
            st.error(f"Failed to load revenue visualization: {str(e)}")

        # List domain matching
        rev_ins = [i for i in insights if i["domain"] == "Revenue"]
        if not rev_ins:
            st.info("No revenue insights generated.")
        else:
            for ri in rev_ins:
                st.markdown(f"**{ri['title']}** : {ri['summary']}")

    with tab2:
        st.markdown("#### Customer Cohorts and Retention Analysis")
        try:
            has_cust_cols = "CustomerID" in resolved_data.columns or "CustomerName" in resolved_data.columns
            if has_cust_cols:
                cust_prep, _ = prepare_customer_dataset(resolved_data)
                if cust_prep.empty:
                    st.warning("No customer data available after filtering.")
                elif "Customer_Display" not in cust_prep.columns or "Filtered_Revenue" not in cust_prep.columns:
                    st.warning("Customer identifier or revenue columns are missing in prepared customer data.")
                else:
                    lifetime_base = calculate_lifetime_customer_base(cust_prep)
                    cust_perf = get_customer_period_performance(cust_prep, lifetime_base)
                    if not cust_perf.empty:
                        st.markdown("**Top Customer Accounts by Revenue (Filtered Period):**")
                        st.bar_chart(data=cust_perf.head(10), x="Customer_Display", y="Filtered_Revenue")
                    else:
                        st.info("No customer period performance metrics found to display.")
            else:
                st.info("Customer-level analytics columns are missing. Retention profiling is unavailable.")
        except Exception as e:
            st.error(f"Failed to load customer visualization: {str(e)}")

        cust_ins = [i for i in insights if i["domain"] == "Customers"]
        if not cust_ins:
            st.info("No customer insights generated.")
        else:
            for ci in cust_ins:
                st.markdown(f"**{ci['title']}** : {ci['summary']}")

    with tab3:
        st.markdown("#### Product Portfolio Concentration & Contributor Shares")
        try:
            has_prod_cols = "ProductID" in resolved_data.columns or "ProductName" in resolved_data.columns
            if has_prod_cols:
                prod_prep, _ = prepare_product_dataset(resolved_data)
                if prod_prep.empty:
                    st.warning("No product data available after filtering.")
                elif "Product_Display" not in prod_prep.columns or "Revenue" not in prod_prep.columns:
                    st.warning("Product identifier or revenue columns are missing in prepared product data.")
                else:
                    prod_perf = get_product_performance(prod_prep)
                    if not prod_perf.empty:
                        st.markdown("**Top Product catalog SKUs by Revenue:**")
                        st.bar_chart(data=prod_perf.head(10), x="Product_Display", y="Revenue")
                    else:
                        st.info("No product performance metrics found to display.")
            else:
                st.info("Product catalog identifier columns are missing from the uploaded schema.")
        except Exception as e:
            st.error(f"Failed to load product visualization: {str(e)}")

        prod_ins = [i for i in insights if i["domain"] == "Products"]
        if not prod_ins:
            st.info("No product insights generated.")
        else:
            for pi in prod_ins:
                st.markdown(f"**{pi['title']}** : {pi['summary']}")

    with tab4:
        st.markdown("#### Basket Economics Metrics & Basket Sizes")
        try:
            from backend.business_health_engine import calculate_period_split_dates
            prep_df, _ = prepare_analytics_dataset(resolved_data)
            if prep_df.empty:
                st.warning("No valid transaction rows found after applying validation filters.")
            else:
                split = calculate_period_split_dates(prep_df) if not prep_df.empty else {"split_valid": False}
                if split["split_valid"]:
                    recent_df = prep_df[(prep_df["OrderDate"] >= split["recent_start"]) & (prep_df["OrderDate"] <= split["recent_end"])]
                    prev_df = prep_df[(prep_df["OrderDate"] >= split["prev_start"]) & (prep_df["OrderDate"] <= split["prev_end"])]
                    
                    recent_orders = recent_df["OrderID"].nunique()
                    prev_orders = prev_df["OrderID"].nunique()
                    
                    if not any(col not in prep_df.columns for col in ["OrderID", "_Revenue", "Quantity"]):
                        recent_aov = recent_df["_Revenue"].sum() / recent_orders if recent_orders > 0 else 0.0
                        prev_aov = prev_df["_Revenue"].sum() / prev_orders if prev_orders > 0 else 0.0
                        
                        recent_upo = recent_df["Quantity"].sum() / recent_orders if recent_orders > 0 else 0.0
                        prev_upo = prev_df["Quantity"].sum() / prev_orders if prev_orders > 0 else 0.0

                        econ_metrics = pd.DataFrame([
                            {"Metric": "Average Order Value (AOV)", "Previous Period": f"₹{prev_aov:.2f}", "Recent Period": f"₹{recent_aov:.2f}", "Change": f"{((recent_aov-prev_aov)/prev_aov)*100:+.1f}%" if prev_aov>0 else "N/A"},
                            {"Metric": "Units Per Order (UPO)", "Previous Period": f"{prev_upo:.2f} items", "Recent Period": f"{recent_upo:.2f} items", "Change": f"{((recent_upo-prev_upo)/prev_upo)*100:+.1f}%" if prev_upo>0 else "N/A"}
                        ])
                        st.table(econ_metrics)
                    else:
                        st.warning("Required fields (OrderID, _Revenue, or Quantity) are missing on the prepared data.")
                else:
                    st.info("The comparison periods timeline splits are invalid or insufficient to partition transactions.")
        except Exception as e:
            st.error(f"Failed to load basket economics comparison table: {str(e)}")

        econ_ins = [i for i in insights if i["domain"] == "Order Economics"]
        if not econ_ins:
            st.info("No basket economics insights generated.")
        else:
            for ei in econ_ins:
                st.markdown(f"**{ei['title']}** : {ei['summary']}")

    with tab5:
        st.markdown("#### Forecast Validation & Data Quality Framework")
        st.markdown("""
            ##### Deterministic Insight Validation Rules
            RetailPilot AI generates diagnostic insights dynamically based on mathematical calculations. 
            All insights are explainable, backed by numeric evidence thresholds, and free from composite score bias.
            
            * **Priority Metrics**: Items triggering high severity levels or immediate risk classes are placed under Priority Attention.
            * **Forecast Readiness**: Predictive capability is evaluated strictly based on date coverage, non-zero density distributions, and historical transaction ranges.
        """)
        try:
            from backend.forecast_engine import detect_forecast_capabilities
            prep_df, _ = prepare_analytics_dataset(resolved_data)
            if prep_df.empty:
                st.info("**Current Forecast Modeling Readiness:** `UNAVAILABLE` (Insufficient data)")
            else:
                f_caps = detect_forecast_capabilities(prep_df, "Daily")
                st.info(f"**Current Forecast Modeling Readiness:** `{f_caps.get('capability_state')}`")
                if f_caps.get("capability_reasons"):
                    st.write("Capability evaluation details:")
                    for r in f_caps["capability_reasons"]:
                        st.write(f"- {r}")
        except Exception as e:
            st.error(f"Failed to load forecast eligibility details: {str(e)}")
