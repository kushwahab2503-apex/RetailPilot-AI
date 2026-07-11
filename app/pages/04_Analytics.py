import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from app.components.theme import inject_global_css

from app.components.layout import page_header, dataset_status
from backend.analytics_resolver import resolve_analytics_dataset
from backend.analytics_engine import (
    prepare_analytics_dataset,
    calculate_core_kpis,
    aggregate_time_series,
    calculate_category_performance,
    calculate_city_performance,
    calculate_payment_distribution,
    detect_capabilities,
    apply_filters
)
from backend.formatters import format_indian_currency, format_indian_number

# Configure page layout
st.set_page_config(page_title="RetailPilot AI - Business Analytics", layout="wide")

# Render typical layout statuses
dataset_status()
page_header("Business Analytics", "Interactive multidimensional analysis of sales, orders, and transactional KPIs.")

# Inject shared light enterprise CSS
inject_global_css()

# Resolve dataset from session state
df, source_name = resolve_analytics_dataset()

if df is None:
    st.warning("Please upload a dataset or validate/clean your data on the preceding pages to activate this view.")
    st.markdown("""
        <div class="empty-state-box">
            <h4>Quick start guide:</h4>
            <ol>
                <li>Go to the <b>Upload Data</b> page in the left navigation sidebar.</li>
                <li>Upload your raw transaction CSV and trigger validation.</li>
                <li>(Optional) Clean the dataset under <b>Data Cleaning</b>.</li>
                <li>Return here to view business performance reports.</li>
            </ol>
        </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/01_Upload_Data.py", label="Navigate to Dataset Upload Wizard", icon="📤")
else:
    # 1. Prepare and scrub the analytics dataset
    prepared_df, metadata = prepare_analytics_dataset(df)
    
    # 2. Capabilities mapping for this data source
    caps = detect_capabilities(df)
    
    # Render Status Info in the Sidebar
    st.sidebar.markdown(f"**Working Source:** `{source_name}`")
    
    # Capability Detection Checklists in sidebars
    st.sidebar.markdown("### System Capabilities")
    with st.sidebar.expander("Detected Features", expanded=True):
        st.markdown(f"**KPI Computations:** {'✅ Active' if caps['core_kpis_available'] else '❌ Missing Columns'}")
        st.markdown(f"**Time-series Streams:** {'✅ Active' if caps['time_analytics_available'] else '❌ Missing Calendar'}")
        st.markdown(f"**Categories Breakdown:** {'✅ Active' if caps['category_analytics_available'] else '❌ Missing Groups'}")
        st.markdown(f"**Geographics (City):** {'✅ Active' if caps['city_analytics_available'] else '⚠️ Missing Column'}")
        st.markdown(f"**Payment Breakdown:** {'✅ Active' if caps['payment_analytics_available'] else '⚠️ Missing Column'}")
        st.markdown(f"**Profit Margin Analytics:** {'✅ Active' if caps['profit_analytics_available'] else '⚠️ Cost Column Missing'}")
        st.markdown(f"**Revenue Basis:** `{metadata['revenue_basis']}`")

    # Filter Sidebar Section
    st.sidebar.markdown("### Interactive Filters")
    
    # Date Range picker
    min_date = prepared_df["OrderDate"].min().date()
    max_date = prepared_df["OrderDate"].max().date()
    
    # Use key to persist state if desired, or reset values standardly
    date_val = st.sidebar.date_input(
        "Order Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    # Safely convert date range
    start_filt, end_filt = None, None
    if isinstance(date_val, tuple) and len(date_val) == 2:
        start_filt, end_filt = date_val
    elif isinstance(date_val, tuple) and len(date_val) == 1:
        start_filt = date_val[0]
        end_filt = start_filt
    elif date_val:
        start_filt = date_val
        end_filt = start_filt
        
    # Categories selector
    av_categories = sorted(list(set(prepared_df["Category"].fillna("Unknown").astype(str).str.strip().replace({'': 'Unknown', 'nan': 'Unknown'}))))
    sel_categories = st.sidebar.multiselect(
        "Product Category",
        options=av_categories,
        default=av_categories,
        help="Select specific categories to filter the charts."
    )
    
    # City selector (dynamic capability)
    sel_cities = None
    if caps["city_analytics_available"]:
        av_cities = sorted(list(set(prepared_df["City"].fillna("Unknown").astype(str).str.strip().replace({'': 'Unknown', 'nan': 'Unknown'}))))
        sel_cities = st.sidebar.multiselect(
            "Geographic Cities",
            options=av_cities,
            default=av_cities
        )
        
    # Payment Method key selector (dynamic capability)
    sel_payment_methods = None
    if caps["payment_analytics_available"]:
        av_payments = sorted(list(set(prepared_df["PaymentMethod"].fillna("Unknown").astype(str).str.strip().replace({'': 'Unknown', 'nan': 'Unknown'}))))
        sel_payment_methods = st.sidebar.multiselect(
            "Payment Mode",
            options=av_payments,
            default=av_payments
        )
        
    # Apply filters dynamically on prepared dataset
    filtered_df = apply_filters(
        prepared_df,
        date_range=(start_filt, end_filt),
        categories=sel_categories,
        cities=sel_cities,
        payment_methods=sel_payment_methods
    )
    
    # Calculate KPIs for the active filter set
    kpis = calculate_core_kpis(filtered_df, metadata["revenue_basis"])
    
    if filtered_df.empty:
        st.error("No transactions fit the selected filter credentials. Please broaden your metrics in the sidebar.")
    else:
        # Dashboard UI
        # 1. KPI cards row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Total Revenue ({kpis['revenue_basis']})</div>
                    <div class="metric-value">{format_indian_currency(kpis['total_revenue'])}</div>
                    <div class="metric-subtext">Sum of all transaction line values</div>
                </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Unique Orders</div>
                    <div class="metric-value">{format_indian_number(kpis['total_orders'])}</div>
                    <div class="metric-subtext">Orders across the active date range</div>
                </div>
            """, unsafe_allow_html=True)
            
        with col3:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Units Sold</div>
                    <div class="metric-value">{format_indian_number(kpis['units_sold'])}</div>
                    <div class="metric-subtext">Cumulative sum of items purchased</div>
                </div>
            """, unsafe_allow_html=True)
            
        with col4:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Avg Order Value (AOV)</div>
                    <div class="metric-value">{format_indian_currency(kpis['average_order_value'])}</div>
                    <div class="metric-subtext">Revenue contribution per order</div>
                </div>
            """, unsafe_allow_html=True)
            
        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
        
        # 2. Chart Section Tab Bar
        st.subheader("Sales Streams & Timeline Integrations")
        
        time_tab, breakdown_tab = st.tabs(["📈 Timeline & Sales Aggregation", "📊 Dimensional Breakdown Analysis"])
        
        with time_tab:
            c_freq_col, c_spacer = st.columns([1, 3])
            with c_freq_col:
                frequency = st.radio("Aggregation Interval", options=["Daily", "Weekly", "Monthly"], horizontal=True)
                
            time_series_data = aggregate_time_series(filtered_df, frequency)
            
            if time_series_data.empty:
                st.info("Insufficient time streams to aggregate.")
            else:
                # Setup chart formatting where X-axis is the Date
                # Set index to Date to feed into line_chart/bar_chart cleanly
                chart_df = time_series_data.copy()
                chart_df["DateString"] = chart_df["Date"].dt.strftime('%b %d, %Y')
                
                st.markdown("#### Revenue Performance Timeline")
                st.line_chart(
                    chart_df.rename(columns={"Revenue": f"Revenue ({metadata['revenue_basis']})"}).set_index("Date")["Revenue (" + metadata['revenue_basis'] + ")"],
                    color="#6366f1",
                    height=280
                )
                
                left_chart_c, right_chart_c = st.columns(2)
                with left_chart_c:
                    st.markdown("#### Transaction Count Trend")
                    st.bar_chart(
                        chart_df.set_index("Date")["Orders"],
                        color="#a855f7",
                        height=220
                    )
                with right_chart_c:
                    st.markdown("#### Unit Volumetric Analysis")
                    st.bar_chart(
                        chart_df.set_index("Date")["Units"],
                        color="#ec4899",
                        height=220
                    )
        
        with breakdown_tab:
            # Splits screen layout
            breakdown_c1, breakdown_c2 = st.columns(2)
            
            with breakdown_c1:
                st.markdown("#### Category Sales Contribution")
                cat_perf = calculate_category_performance(filtered_df)
                
                # Chart
                st.bar_chart(
                    cat_perf.set_index("Category")["Revenue"],
                    color="#4f46e5",
                    horizontal=True,
                    height=240
                )
                # Formatted DataFrame
                disp_cat_perf = cat_perf.copy()
                disp_cat_perf["Revenue"] = disp_cat_perf["Revenue"].apply(format_indian_currency)
                disp_cat_perf["Units Sold"] = disp_cat_perf["Units Sold"].apply(format_indian_number)
                disp_cat_perf["Revenue Share"] = disp_cat_perf["Revenue Share"].apply(lambda val: f"{val:.2f}%")
                st.dataframe(disp_cat_perf, use_container_width=True, hide_index=True)
                
            with breakdown_c2:
                # Dynamic breakdowns based on present columns
                if caps["city_analytics_available"] and caps["payment_analytics_available"]:
                    sub_tab_c, sub_tab_p = st.tabs(["📍 Geographic Distribution", "💳 Payment Systems"])
                    
                    with sub_tab_c:
                        city_perf = calculate_city_performance(filtered_df)
                        if city_perf is not None:
                            st.bar_chart(
                                city_perf.set_index("City")["Revenue"],
                                color="#2563eb",
                                horizontal=True,
                                height=240
                            )
                            disp_city = city_perf.copy()
                            disp_city["Revenue"] = disp_city["Revenue"].apply(format_indian_currency)
                            disp_city["Units Sold"] = disp_city["Units Sold"].apply(format_indian_number)
                            disp_city["Revenue Share"] = disp_city["Revenue Share"].apply(lambda val: f"{val:.2f}%")
                            st.dataframe(disp_city, use_container_width=True, hide_index=True)
                            
                    with sub_tab_p:
                        pm_dist = calculate_payment_distribution(filtered_df)
                        if pm_dist is not None:
                            st.bar_chart(
                                pm_dist.set_index("PaymentMethod")["Orders"],
                                color="#db2777",
                                horizontal=True,
                                height=240
                            )
                            disp_pm = pm_dist.copy()
                            disp_pm["Revenue"] = disp_pm["Revenue"].apply(format_indian_currency)
                            disp_pm["Orders"] = disp_pm["Orders"].apply(format_indian_number)
                            disp_pm["Order Share (%)"] = disp_pm["Order Share (%)"].apply(lambda val: f"{val:.2f}%")
                            st.dataframe(disp_pm, use_container_width=True, hide_index=True)
                
                elif caps["city_analytics_available"]:
                    st.markdown("#### Geographic Distribution")
                    city_perf = calculate_city_performance(filtered_df)
                    if city_perf is not None:
                        st.bar_chart(
                            city_perf.set_index("City")["Revenue"],
                            color="#2563eb",
                            horizontal=True,
                            height=240
                        )
                        disp_city = city_perf.copy()
                        disp_city["Revenue"] = disp_city["Revenue"].apply(format_indian_currency)
                        disp_city["Units Sold"] = disp_city["Units Sold"].apply(format_indian_number)
                        disp_city["Revenue Share"] = disp_city["Revenue Share"].apply(lambda val: f"{val:.2f}%")
                        st.dataframe(disp_city, use_container_width=True, hide_index=True)
                        
                elif caps["payment_analytics_available"]:
                    st.markdown("#### Payment Systems Distribution")
                    pm_dist = calculate_payment_distribution(filtered_df)
                    if pm_dist is not None:
                        st.bar_chart(
                            pm_dist.set_index("PaymentMethod")["Orders"],
                            color="#db2777",
                            horizontal=True,
                            height=240
                        )
                        disp_pm = pm_dist.copy()
                        disp_pm["Revenue"] = disp_pm["Revenue"].apply(format_indian_currency)
                        disp_pm["Orders"] = disp_pm["Orders"].apply(format_indian_number)
                        disp_pm["Order Share (%)"] = disp_pm["Order Share (%)"].apply(lambda val: f"{val:.2f}%")
                        st.dataframe(disp_pm, use_container_width=True, hide_index=True)
                else:
                    st.info("Additional dimensions like City or PaymentMethod are not found or fully missing in dataset.")
                            
        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
        
        # 3. Data Integrity & Exclusion Report Expander
        with st.expander("🔍 Dataset Analysis Summary & Quality Exclusions", expanded=False):
            st.markdown("#### Row Eligibility Details")
            c_meta1, c_meta2, c_meta3 = st.columns(3)
            c_meta1.metric("Imported Rows", format_indian_number(metadata["row_count_analyzed"]))
            c_meta2.metric("Valid Rows Processed", format_indian_number(metadata["valid_row_count"]))
            c_meta3.metric("Excluded Rows", format_indian_number(metadata["excluded_row_count"]))
            
            if metadata["excluded_row_count"] > 0:
                st.warning(f"Exclusion checks disqualified {metadata['excluded_row_count']} row(s) based on structural validation rules.")
                
                # Format exclusion reason details
                exc_details = []
                for k, v in metadata["exclusions"].items():
                    r_name = k.replace("_", " ").title()
                    exc_details.append({"Exclusion Criterion": r_name, "Exclusions Count": format_indian_number(v)})
                
                st.table(pd.DataFrame(exc_details))
            else:
                st.success("All source check rows satisfied analytical eligibility constraints (100% data pass rate).")
                
            st.markdown("---")
            st.markdown("#### Revenue Computations Method")
            if metadata["revenue_basis"] == "Net Revenue":
                st.success(f"**Net Revenue Calculations Applied.** Uses discount adjustment equation: `Quantity * UnitPrice * (1 - DiscountPct/100)`.")
                if metadata["invalid_discount_fallback_count"] > 0:
                    st.info(f"💡 Note: Applied fallback Gross Revenue to **{metadata['invalid_discount_fallback_count']}** row(s) containing missing/NaN or out-of-bounds `DiscountPct` configurations.")
            else:
                st.warning(f"**Fall back to Gross Revenue.** No `DiscountPct` configuration present in input dataset columns. Equations resolved as: `Quantity * UnitPrice`.")
