import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from app.components.theme import inject_global_css

from app.components.layout import page_header, dataset_status
from backend.analytics_resolver import resolve_analytics_dataset
from backend.customer_engine import (
    prepare_customer_dataset,
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
from backend.formatters import format_indian_currency, format_indian_number

# Configure page layout
st.set_page_config(page_title="RetailPilot AI - Customers Intelligence", layout="wide")

# Render layout headers
dataset_status()
page_header("Customers Intelligence", "Customer behavior, value loyalty patterns, RFM segmentation, and cohort retention profiles.")

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
                <li>Return here to view customer metrics.</li>
            </ol>
        </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/01_Upload_Data.py", label="Navigate to Dataset Upload Wizard", icon="📤")
else:
    # 1. Row preparations
    prepared_cust_df, metadata = prepare_customer_dataset(df)
    caps = detect_customer_capabilities(df)

    if not caps["customer_identity_available"]:
        st.error("Missing Customer Identifier Columns")
        st.warning("This dataset does not contain CustomerID or CustomerName required to map customer profiles. Please upload transaction logs containing customer information.")
    else:
        # Sidebar audits & metadata
        st.sidebar.markdown(f"**Working Source:** `{source_name}`")
        
        st.sidebar.markdown("### System Capabilities")
        with st.sidebar.expander("Customer Capabilities", expanded=True):
            st.markdown(f"**Customer Profiles:** {'✅ Active' if caps['customer_identity_available'] else '❌ Inactive'}")
            st.markdown(f"**Geographics (City):** {'✅ Active' if caps['city_available'] else '⚠️ Missing'}")
            st.markdown(f"**RFM Segmentation:** {'✅ Active' if caps['segmentation_available'] else '❌ Inactive'}")
            st.markdown(f"**Cohort Analysis:** {'✅ Active' if caps['cohort_analysis_available'] else '⚠️ Insufficient Data Span/Pop'}")
            st.markdown(f"**Revenue Basis:** `{metadata['revenue_basis']}`")

        # Step 1: Pre-calculate the lifetime baseline database
        lifetime_base = calculate_lifetime_customer_base(prepared_cust_df)

        st.sidebar.markdown("### Interactive Filters")
        
        # Date Picker
        if not prepared_cust_df.empty:
            min_date = prepared_cust_df["OrderDate"].min().date()
            max_date = prepared_cust_df["OrderDate"].max().date()
        else:
            min_date = datetime.now().date()
            max_date = datetime.now().date()

        date_val = st.sidebar.date_input(
            "Transaction Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )

        if isinstance(date_val, tuple) and len(date_val) == 2:
            start_date, end_date = date_val
        else:
            start_date = date_val[0] if isinstance(date_val, (list, tuple)) else date_val
            end_date = start_date

        # Category check
        avl_cats = sorted(prepared_cust_df["Category"].dropna().unique())
        selected_cats = st.sidebar.multiselect("Category Select", avl_cats, default=avl_cats)

        # Customer Search
        search_inp = st.sidebar.text_input("Customer ID/Name Search", "").strip()

        # Selection of Lifetime Segment & Repeat Status (Filters on historical classifications)
        avl_segments = ["Champions", "Loyal Customers", "Potential Loyalists", "New Customers", "At Risk", "Hibernating"]
        selected_segments = st.sidebar.multiselect("Lifetime Segments Filter", avl_segments, default=avl_segments)
        
        selected_repeat = st.sidebar.multiselect(
            "Lifetime Repeat Status",
            ["Repeat Customer", "One-Time Customer"],
            default=["Repeat Customer", "One-Time Customer"]
        )

        # ----------------------------------------------------
        # HYBRID HISTORICAL FILTER MODEL APPLIER
        # ----------------------------------------------------
        # 1. Filter our Customer Base on lifetime segment/repeat classifications & text search matches
        filtered_lifetime = lifetime_base.copy()
        if search_inp:
            filtered_lifetime = filtered_lifetime[
                filtered_lifetime["Customer_Display"].str.contains(search_inp, case=False, na=False) |
                filtered_lifetime["Customer_Key"].str.contains(search_inp, case=False, na=False)
            ]
        if selected_segments:
            filtered_lifetime = filtered_lifetime[filtered_lifetime["Lifetime_Segment"].isin(selected_segments)]
        else:
            filtered_lifetime = filtered_lifetime.iloc[0:0]

        if selected_repeat:
            filtered_lifetime = filtered_lifetime[filtered_lifetime["Lifetime_Repeat_Status"].isin(selected_repeat)]
        else:
            filtered_lifetime = filtered_lifetime.iloc[0:0]

        # 2. Slice transaction database according to Date Range, Category and filtered Customer Keys list
        filtered_tx = prepared_cust_df.copy()
        filtered_tx = filtered_tx[
            (filtered_tx["OrderDate"].dt.date >= start_date) &
            (filtered_tx["OrderDate"].dt.date <= end_date)
        ]
        if selected_cats:
            filtered_tx = filtered_tx[filtered_tx["Category"].isin(selected_cats)]
        else:
            filtered_tx = filtered_tx.iloc[0:0]

        # Intersect with our active filter lifetime customer keys
        filtered_tx = filtered_tx[filtered_tx["Customer_Key"].isin(filtered_lifetime["Customer_Key"])]

        # Fetch summarized performance & aggregate KPIs
        kpis = calculate_customer_kpis(filtered_tx, filtered_lifetime)

        # RENDER DASHBOARD SUMMARY ROW
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Active Customers</div>
                    <div class="metric-value">{format_indian_number(kpis["active_customers_period"])}</div>
                    <div class="metric-subtext">Active in Period (Lifetime Eligible: {len(filtered_lifetime)})</div>
                </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Repeat Customer Rate</div>
                    <div class="metric-value">{kpis["repeat_customer_rate_lifetime"]:.1f}%</div>
                    <div class="metric-subtext">Lifetime Cohort Basis</div>
                </div>
            """, unsafe_allow_html=True)
            
        with col3:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Avg Revenue/Customer</div>
                    <div class="metric-value">{format_indian_currency(kpis["avg_revenue_per_customer_period"])}</div>
                    <div class="metric-subtext">Calculation on Filtered Period</div>
                </div>
            """, unsafe_allow_html=True)
            
        with col4:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Top Revenue Customer</div>
                    <div class="metric-value" style="font-size:1.15rem; line-height:2.1rem; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{kpis["top_customer_by_revenue_period"]}</div>
                    <div class="metric-subtext">Highest Period sales</div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<div class='custom-divider'></div>", unsafe_allow_html=True)

        # TABBED PORTLET VIEW
        tabs = st.tabs([
            "🏆 Customer Leaderboard",
            "📊 Behavioral Segments",
            "💳 Repeat vs One-Time",
            "📈 Customer Concentration",
            "📍 Geography & Retention"
        ])

        # TAB 1: CUSTOMER LEADERBOARD
        with tabs[0]:
            st.write("### Period Transaction Leaderboards")
            st.write("Displays top customers sorted by transactional volume and metrics in the active period range.")
            
            lead_n = st.slider("Leaderboard Size (N)", min_value=5, max_value=20, value=5)
            rankings = get_customer_ranking_views(filtered_tx, filtered_lifetime, n=lead_n)

            if filtered_tx.empty:
                st.info("No customer transactions matching filter criteria in this period range.")
            else:
                l_col1, l_col2 = st.columns(2)
                with l_col1:
                    st.write(f"#### Top {lead_n} Customers by Revenue")
                    r_df = rankings["Top_Revenue"].copy()
                    r_df["Revenue"] = r_df["Revenue"].apply(format_indian_currency)
                    st.dataframe(r_df, use_container_width=True, hide_index=True)
                    
                    st.write(f"#### Top {lead_n} Customers by Units")
                    u_df = rankings["Top_Units"].copy()
                    u_df["Units"] = u_df["Units"].apply(format_indian_number)
                    st.dataframe(u_df, use_container_width=True, hide_index=True)
                    
                with l_col2:
                    st.write(f"#### Top {lead_n} Customers by Unique Orders")
                    o_df = rankings["Top_Orders"].copy()
                    o_df["Orders"] = o_df["Orders"].apply(format_indian_number)
                    st.dataframe(o_df, use_container_width=True, hide_index=True)
                    
                    # Short visualization bar chart
                    perf_full = get_customer_period_performance(filtered_tx, filtered_lifetime)
                    top_rev_vis = perf_full[perf_full["Filtered_Revenue"] > 0].head(lead_n)
                    if not top_rev_vis.empty:
                        st.write("#### Revenue Visual Plot")
                        chart_df = top_rev_vis.set_index("Customer_Display")[["Filtered_Revenue"]]
                        st.bar_chart(chart_df, color="#6366f1")

        # TAB 2: BEHAVIORAL SEGMENTS
        with tabs[1]:
            st.write("### Lifetime RFM Segments")
            st.write("Segment classifications set against full baseline transaction history.")
            
            # Count distribution
            seg_counts = filtered_lifetime["Lifetime_Segment"].value_counts().reset_index()
            seg_counts.columns = ["Segment", "Customer Count"]
            
            s_col1, s_col2 = st.columns([1, 2])
            with s_col1:
                st.write("#### Customer Distributions")
                st.dataframe(seg_counts, use_container_width=True, hide_index=True)
                
                st.markdown("""
                **Segmentation Rules Reference:**
                - **Champions**: High Recency, high Frequency, high Monetary (R>=4, F>=4, M>=4)
                - **Loyal Customers**: Moderate-to-high Recency and Frequency (R>=3, F>=3)
                - **Potential Loyalists**: Good Recency and value (R>=3, M>=2)
                - **New Customers**: Dynamic Recency, single-order purchases (R>=4, F==1)
                - **At Risk**: Quiet Recency, previously frequent orders (R<=2, F>=2)
                - **Hibernating**: Low levels across R, F, and M (Others)
                """)
            with s_col2:
                # Segment members inspector
                st.write("#### Customer Directory by Segment")
                selected_insp_seg = st.selectbox("Inspect Segment Details", seg_counts["Segment"].unique() if not seg_counts.empty else ["No Segments"])
                
                if not filtered_lifetime.empty and selected_insp_seg in filtered_lifetime["Lifetime_Segment"].values:
                    seg_members = filtered_lifetime[filtered_lifetime["Lifetime_Segment"] == selected_insp_seg].copy()
                    
                    # Format columns
                    seg_members["Lifetime_Revenue"] = seg_members["Lifetime_Revenue"].apply(format_indian_currency)
                    view_cols = ["Customer_Display", "Lifetime_Unique_Orders", "Days_Since_Last_Purchase_Lifetime", "Lifetime_Revenue", "R_Score", "F_Score", "M_Score"]
                    st.dataframe(seg_members[view_cols], use_container_width=True, hide_index=True)

        # TAB 3: REPEAT VS ONE-TIME
        with tabs[2]:
            st.write("### Repeat vs One-Time Sales Integrity")
            st.write("Periods transaction comparison split based on lifetime repeat status classifications.")
            
            rep_df = get_repeat_vs_onetime_summary(filtered_tx, filtered_lifetime)
            
            # Format outputs
            rep_typed = rep_df.copy()
            rep_typed["Revenue"] = rep_typed["Revenue"].apply(format_indian_currency)
            rep_typed["Average Order Value"] = rep_typed["Average Order Value"].apply(format_indian_currency)
            rep_typed["Revenue Share (%)"] = rep_typed["Revenue Share (%)"].apply(lambda val: f"{val:.2f}%")
            
            st.dataframe(rep_typed, use_container_width=True, hide_index=True)
            
            # Bar layout
            if not filtered_tx.empty:
                st.write("#### Period Group Revenues Comparison")
                vis_df = rep_df.set_index("Repeat Status")[["Revenue"]]
                st.bar_chart(vis_df, color="#ec4899")

        # TAB 4: CUSTOMER CONCENTRATION
        with tabs[3]:
            st.write("### Customer Concentration & Pareto Structure")
            st.write("Measures the contribution curve of active customers within the filtered transactions stream.")

            concent_data, concent_meta = get_customer_concentration_data(filtered_tx, filtered_lifetime)
            
            if filtered_tx.empty:
                st.info("No active customer sales records in this date range.")
            else:
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.markdown(f"""
                    <div class="empty-state-box" style="margin-top:20px;">
                        <h4>Concentration Diagnostics</h4>
                        <p><strong>Top 80% contributors count:</strong> {concent_meta["contributors_count"]} customers</p>
                        <p><strong>Active customer footprint:</strong> {concent_meta["total_active_customers"]} customers</p>
                        <p><strong>Pareto Ratio:</strong> {concent_meta["contributors_ratio_pct"]:.2f}% of buyers account for 80% of sales</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.write("#### Pareto Contributors List")
                    st.markdown(", ".join(concent_meta["contributor_displays"][:10]) + ("..." if len(concent_meta["contributor_displays"]) > 10 else ""))
                with c2:
                    st.write("#### Cumulative Revenue Contribution Curve")
                    # Line plot cumulative percentages
                    line_df = concent_data.set_index("Customer_Display")[["Cumulative Pct"]]
                    st.line_chart(line_df, color="#a855f7")

        # TAB 5: GEOGRAPHY & RETENTION
        with tabs[4]:
            # Geographic subsection
            if caps["city_available"]:
                st.write("### Geographical Customer Footprint")
                geo_df = get_geographic_customer_performance(filtered_tx, filtered_lifetime)
                if geo_df is not None:
                    # Format
                    geo_typed = geo_df.copy()
                    geo_typed["Revenue"] = geo_typed["Revenue"].apply(format_indian_currency)
                    geo_typed["Avg Revenue per Customer"] = geo_typed["Avg Revenue per Customer"].apply(format_indian_currency)
                    geo_typed["Repeat Customer Rate (%)"] = geo_typed["Repeat Customer Rate (%)"].apply(lambda v: f"{v:.1f}%")
                    st.dataframe(geo_typed, use_container_width=True, hide_index=True)
                st.markdown("<div class='custom-divider'></div>", unsafe_allow_html=True)
            
            # Retention Cohort Matrix subsection
            st.write("### Customer Acquisition & MoM Retention Heatmap")
            
            if caps["cohort_analysis_available"]:
                counts_matrix, rent_matrix = get_cohort_matrix_data(prepared_cust_df)
                if rent_matrix is not None:
                    st.write("#### Monthly Retention Rate (%)")
                    # Color background gradient representation in styling
                    styled_matrix = rent_matrix.style.background_gradient(cmap="Purples", axis=1).format("{:.1f}%", na_rep="—")
                    st.dataframe(styled_matrix, use_container_width=True)
                    
                    st.write("#### Cohort Active Counts")
                    st.dataframe(counts_matrix.style.format(na_rep="—"), use_container_width=True)
            else:
                st.info("Cohort Heatmap Unavailable")
                st.warning("Insufficient date span, customer count (needs >= 5 customers, unique months >= 3, and date span >= 60 days) to run cohort matrices calculations. Showing Monthly Customer activity timeline instead.")
                
                # Render Monthly Customer/Orders timeline chart
                if len(prepared_cust_df) > 0:
                    st.write("#### Monthly Active Customers & Unique Orders timeline")
                    timeline_df = prepared_cust_df.copy()
                    timeline_df["Month"] = timeline_df["OrderDate"].dt.to_period("M")
                    
                    line_grouped = timeline_df.groupby("Month").agg(
                        Active_Customers=("Customer_Key", "nunique"),
                        Unique_Orders=("OrderID", "nunique")
                    ).reset_index()
                    line_grouped["Month"] = line_grouped["Month"].astype(str)
                    
                    st.line_chart(line_grouped.set_index("Month"), color=["#6366f1", "#ec4899"])

        # CUSTOMER INTEGRITY SUMMARY AUDIT EXPANDER
        st.markdown("<div class='custom-divider'></div>", unsafe_allow_html=True)
        with st.expander("Customer Analytics Integrity Summary", expanded=False):
            a_col1, a_col2 = st.columns(2)
            with a_col1:
                st.write("#### Row Eligibility Diagnostics")
                audit_table = pd.DataFrame({
                    "Stage / Category": [
                        "Working Source Rows",
                        "Analytics-Eligible Rows",
                        "Customer Identity Exclusions",
                        "Final Customer Analysis Rows"
                    ],
                    "Row Count": [
                        metadata["working_row_count"],
                        metadata["eligible_row_count"] + metadata["customer_exclusions"]["missing_customer_identity"],
                        metadata["customer_exclusions"]["missing_customer_identity"],
                        metadata["customer_eligible_rows"]
                    ]
                })
                st.dataframe(audit_table, use_container_width=True, hide_index=True)
            with a_col2:
                st.write("#### Logic Definitions & Specifications")
                st.markdown(f"""
                - **Active Data Source:** `{source_name.upper()}` dataset in session state.
                - **Customer Identity Resolve Rule:** Combines `CustomerID` and `CustomerName` if both exist. Continues without exclusions even if single fields are missing.
                - **Baseline repeat customer:** Any customer key with Lifetime unique orders count $> 1$.
                - **RFM scoring parameter:** Relative percentiles scoring on unique database values (breaks ties deterministically; immune compiles collapses).
                - **Recency Reference Pivot Date:** `{prepared_cust_df["OrderDate"].max().strftime('%Y-%m-%d') if not prepared_cust_df.empty else 'N/A'}` (highest transaction date in database).
                """)
