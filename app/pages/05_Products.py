import streamlit as st
import pandas as pd
import numpy as np
from app.components.theme import inject_global_css

from app.components.layout import page_header, dataset_status
from backend.analytics_resolver import resolve_analytics_dataset
from backend.product_engine import (
    prepare_product_dataset,
    apply_product_filters,
    get_product_performance,
    calculate_product_kpis,
    get_top_bottom_ranking,
    get_pareto_data,
    get_quadrant_analysis_data,
    get_category_product_context,
    detect_product_capabilities
)
from backend.formatters import format_indian_currency, format_indian_number

# Configure layout
st.set_page_config(page_title="RetailPilot AI - Products Intelligence", layout="wide")

# Render layout badges
dataset_status()
page_header("Products Intelligence", "Analyze product-level portfolio statistics, sales performance, Pareto distribution, and pricing margins.")

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
                <li>Return here to view product intelligence analyses.</li>
            </ol>
        </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/01_Upload_Data.py", label="Navigate to Dataset Upload Wizard", icon="📤")
else:
    # 1. First prepare the active product-level dataset (prepares exclusions, handles schema Fallbacks)
    prepared_df, metadata = prepare_product_dataset(df)
    caps = detect_product_capabilities(df)

    st.sidebar.markdown(f"**Working Source:** `{source_name}`")
    st.sidebar.markdown("### Product Capabilities")
    with st.sidebar.expander("Detected Schema Features", expanded=True):
        st.markdown(f"**Product ID/Name:** {'✅ Active' if caps['product_identity_available'] else '❌ Missing Col'}")
        st.markdown(f"**Category context:** {'✅ Active' if caps['category_available'] else '❌ Missing Col'}")
        st.markdown(f"**Quantity Analysis:** {'✅ Active' if caps['quantity_analysis_available'] else '❌ Missing Col'}")
        st.markdown(f"**Revenue Analysis:** {'✅ Active' if caps['revenue_analysis_available'] else '❌ Missing Col'}")
        st.markdown(f"**Pricing Analysis:** {'✅ Active' if caps['pricing_analysis_available'] else '❌ Missing Col'}")
        st.markdown(f"**Revenue Basis:** `{metadata.get('revenue_basis', 'Gross Revenue')}`")

    if not caps["product_identity_available"]:
        st.error("The working dataset does not contain Product ID or Name columns. Product Intelligence cannot be performed.")
    else:
        # Sidebar filters
        st.sidebar.markdown("### Interactive Filters")
        
        # 1. Date Range Picker
        m_date = prepared_df["OrderDate"].min().date() if not prepared_df.empty else datetime.today().date()
        mx_date = prepared_df["OrderDate"].max().date() if not prepared_df.empty else datetime.today().date()
        date_sel = st.sidebar.date_input(
            "Order Date Range",
            value=(m_date, mx_date) if not prepared_df.empty else (m_date, m_date),
            min_value=m_date,
            max_value=mx_date
        )
        
        start_date, end_date = None, None
        if isinstance(date_sel, tuple) and len(date_sel) == 2:
            start_date, end_date = date_sel
        elif isinstance(date_sel, tuple) and len(date_sel) == 1:
            start_date = date_sel[0]
            end_date = start_date
        elif date_sel:
            start_date = date_sel
            end_date = start_date

        # 2. Category Multiselect
        selected_categories = None
        if caps["category_available"]:
            cats_options = sorted(list(set(prepared_df["Category"].fillna("Unknown").astype(str).str.strip().replace({'': 'Unknown', 'nan': 'Unknown'}))))
            selected_categories = st.sidebar.multiselect(
                "Filter by Category",
                options=cats_options,
                default=cats_options
            )

        # 3. Product Search Input
        search_query = st.sidebar.text_input("Search Products (ID/Name)", value="", help="Filter portfolio using ID or name keywords")

        # 4. Configurable Ranking Top N
        rank_n = st.sidebar.number_input("Ranks Limit (N)", min_value=1, max_value=100, value=5, step=1)

        # Apply search and filters BEFORE grouping metrics
        f_df = apply_product_filters(
            prepared_df,
            date_range=(start_date, end_date),
            categories=selected_categories,
            search_query=search_query
        )

        # Calculate KPIs for the active filter set
        kpi_metrics = calculate_product_kpis(f_df)
        rev_basis = metadata.get("revenue_basis", "Gross Revenue")

        # Render KPI cards
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Active Products (Filtered)</div>
                    <div class="metric-value">{format_indian_number(kpi_metrics['total_active_products'])}</div>
                    <div class="metric-subtext">Count of matching products</div>
                </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Top Product (Revenue)</div>
                    <div class="metric-value" style="font-size: 1.1rem; padding: 10px 0;">{kpi_metrics['top_product_by_revenue']}</div>
                    <div class="metric-subtext">Highest revenue generator</div>
                </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Top Product (Volume)</div>
                    <div class="metric-value" style="font-size: 1.1rem; padding: 10px 0;">{kpi_metrics['top_product_by_units']}</div>
                    <div class="metric-subtext">Most units sold</div>
                </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Avg Revenue/Product</div>
                    <div class="metric-value">{format_indian_currency(kpi_metrics['avg_revenue_per_product'])}</div>
                    <div class="metric-subtext">Average portfolio value</div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

        if f_df.empty:
            st.warning("No products match the selected search or filter settings. Please broaden your selections.")
        else:
            # Main Dashboard Tabs
            tab_ranks, tab_pareto, tab_quad, tab_cat = st.tabs([
                "🏆 Rankings Leaderboard",
                "📈 Pareto Contribution",
                "🎯 Value-Volume Quadrants",
                "📂 Category Breakdown"
            ])

            with tab_ranks:
                st.subheader(f"Portfolio Revenue Leaderboard (Top / Bottom {rank_n})")
                
                # Fetch top/bottom ranking tables
                top_items, bottom_items = get_top_bottom_ranking(f_df, n=rank_n)
                
                c_top, c_bot = st.columns(2)
                with c_top:
                    st.markdown(f"#### Top {rank_n} Products by Revenue")
                    if not top_items.empty:
                        # Make vertical chart representing top items
                        st.bar_chart(
                            top_items.set_index("Product_Display")["Revenue"],
                            color="#4f46e5",
                            height=250
                        )
                        disp_top = top_items.copy()
                        disp_top["Revenue"] = disp_top["Revenue"].apply(format_indian_currency)
                        disp_top["Units Sold"] = disp_top["Units Sold"].apply(format_indian_number)
                        disp_top["Revenue Share (%)"] = disp_top["Revenue Share (%)"].apply(lambda v: f"{v:.2f}%")
                        disp_top["Average Realized Revenue per Unit"] = disp_top["Average Realized Revenue per Unit"].apply(format_indian_currency)
                        st.dataframe(
                            disp_top[["Rank", "Product_Display", "Revenue", "Units Sold", "Revenue Share (%)", "Average Realized Revenue per Unit"]],
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.info("No rankings data available.")
                        
                with c_bot:
                    st.markdown(f"#### Bottom {rank_n} Products by Revenue")
                    if not bottom_items.empty:
                        # Make vertical chart representing bottom items
                        st.bar_chart(
                            bottom_items.set_index("Product_Display")["Revenue"],
                            color="#db2777",
                            height=250
                        )
                        disp_bot = bottom_items.copy()
                        disp_bot["Revenue"] = disp_bot["Revenue"].apply(format_indian_currency)
                        disp_bot["Units Sold"] = disp_bot["Units Sold"].apply(format_indian_number)
                        disp_bot["Revenue Share (%)"] = disp_bot["Revenue Share (%)"].apply(lambda v: f"{v:.2f}%")
                        disp_bot["Average Realized Revenue per Unit"] = disp_bot["Average Realized Revenue per Unit"].apply(format_indian_currency)
                        st.dataframe(
                            disp_bot[["Rank", "Product_Display", "Revenue", "Units Sold", "Revenue Share (%)", "Average Realized Revenue per Unit"]],
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.info("No rankings data available.")

                st.markdown("#### Complete Product Performance Directory")
                # Show all items sorted
                perf_overview = get_product_performance(f_df)
                disp_perf = perf_overview.copy()
                disp_perf["Revenue"] = disp_perf["Revenue"].apply(format_indian_currency)
                disp_perf["Average Realized Revenue per Unit"] = disp_perf["Average Realized Revenue per Unit"].apply(format_indian_currency)
                disp_perf["Average Price"] = disp_perf["Average Price"].apply(format_indian_currency)
                disp_perf["Revenue per Order"] = disp_perf["Revenue per Order"].apply(format_indian_currency)
                disp_perf["Units Sold"] = disp_perf["Units Sold"].apply(format_indian_number)
                disp_perf["Unique Orders"] = disp_perf["Unique Orders"].apply(format_indian_number)
                disp_perf["Revenue Share (%)"] = disp_perf["Revenue Share (%)"].apply(lambda v: f"{v:.2f}%")
                disp_perf["Unit Share (%)"] = disp_perf["Unit Share (%)"].apply(lambda v: f"{v:.2f}%")
                
                # Check optional columns to show
                dirs_cols = [
                    "Rank", "Product_Display", "Revenue", "Units Sold", "Unique Orders",
                    "Revenue Share (%)", "Unit Share (%)", "Average Realized Revenue per Unit",
                    "Average Price", "Revenue per Order"
                ]
                st.dataframe(disp_perf[dirs_cols], use_container_width=True, hide_index=True)

            with tab_pareto:
                st.subheader("Pareto Analysis: Cumulative Revenue Contribution")
                
                pareto_df, pareto_meta = get_pareto_data(f_df)
                
                if not pareto_df.empty:
                    # Construct concentration text
                    st.success(
                        f"**Pareto Result:** `{pareto_meta['contributors_count']}` out of `{pareto_meta['total_products']}` unique products "
                        f"({pareto_meta['contributors_ratio_pct']:.1f}%) constitute approximately **80% or more** of cumulative revenue."
                    )
                    
                    # Cumulative chart
                    chart_p = pareto_df.copy()
                    st.line_chart(
                        chart_p.set_index("Product_Display")["Cumulative Pct"],
                        color="#a855f7",
                        height=280
                    )
                    
                    # Table view
                    disp_pareto = pareto_df.copy()
                    disp_pareto["Revenue"] = disp_pareto["Revenue"].apply(format_indian_currency)
                    disp_pareto["Revenue Share (%)"] = disp_pareto["Revenue Share (%)"].apply(lambda v: f"{v:.2f}%")
                    disp_pareto["Cumulative Pct"] = disp_pareto["Cumulative Pct"].apply(lambda v: f"{v:.2f}%")
                    
                    with st.expander("Show Cumulative Contribution List", expanded=False):
                        st.dataframe(disp_pareto, use_container_width=True, hide_index=True)
                else:
                    st.info("Insufficient data to complete Pareto mapping.")

            with tab_quad:
                st.subheader("Portfolio Value-Volume Segment Classifications")
                st.markdown(
                    f"🔬 Classifications are relative to the currently filtered dataset. "
                    f"The median value boundaries act as partitions."
                )
                
                q_df, medians = get_quadrant_analysis_data(f_df)
                
                st.write(
                    f"**Median Threshold Boundaries:** "
                    f"Units Median = `{format_indian_number(medians['median_units'])}`, "
                    f"Revenue Median = `{format_indian_currency(medians['median_revenue'])}` "
                    f"({rev_basis})"
                )
                
                # Render interactive scatter chart
                if not q_df.empty:
                    # Scatter chart where color is 'Quadrant' and size is 'Average Realized Revenue per Unit'
                    st.scatter_chart(
                        q_df,
                        x="Units Sold",
                        y="Revenue",
                        color="Quadrant",
                        size="Average Realized Revenue per Unit",
                        height=350,
                        use_container_width=True
                    )
                    
                    # Formatted breakdown table
                    disp_quad = q_df.copy()
                    disp_quad["Revenue"] = disp_quad["Revenue"].apply(format_indian_currency)
                    disp_quad["Average Realized Revenue per Unit"] = disp_quad["Average Realized Revenue per Unit"].apply(format_indian_currency)
                    disp_quad["Units Sold"] = disp_quad["Units Sold"].apply(format_indian_number)
                    
                    with st.expander("Inspect Segment Lists"):
                        quad_choice = st.selectbox(
                            "Choose Quadrant to inspect:",
                            options=[
                                "high-volume / high-revenue",
                                "high-volume / low-revenue",
                                "low-volume / high-revenue",
                                "low-volume / low-revenue"
                            ]
                        )
                        subset = disp_quad[disp_quad["Quadrant"] == quad_choice]
                        st.write(f"Showing **{len(subset)}** products in segment:")
                        st.dataframe(subset, use_container_width=True, hide_index=True)

            with tab_cat:
                st.subheader("Category-level Performance Profile Context")
                
                cat_ctx = get_category_product_context(f_df)
                
                if cat_ctx is not None:
                    if not cat_ctx.empty:
                        # Bar chart Category Revenue
                        st.bar_chart(
                            cat_ctx.set_index("Category")["Revenue"],
                            color="#3b82f6",
                            horizontal=True,
                            height=250
                        )
                        
                        disp_cat = cat_ctx.copy()
                        disp_cat["Revenue"] = disp_cat["Revenue"].apply(format_indian_currency)
                        disp_cat["Units Sold"] = disp_cat["Units Sold"].apply(format_indian_number)
                        st.dataframe(disp_cat, use_container_width=True, hide_index=True)
                    else:
                        st.info("No category context statistics available.")
                else:
                    st.info("Category details absent in target dataset setup.")

            # Custom Divider
            st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

            # Audit Expander
            with st.expander("🔍 Dataset Analysis Summary & Quality Exclusions Report", expanded=False):
                st.markdown("#### Product Analytics Integrity Summary")
                
                # Double-counting explanation:
                # - 'df' represents resolved working session dataframe source.
                # - 'metadata' has exclusions from 'prepare_analytics_dataset' AND productspecific missing identity counts.
                raw_count = len(df)
                analytics_eligible = metadata.get("valid_row_count", 0)
                product_identity_exclusions = metadata.get("product_exclusions", {}).get("missing_product_identity", 0)
                final_product_rows = metadata.get("product_eligible_rows", 0)

                # Show metrics columns
                ca1, ca2, ca3, ca4 = st.columns(4)
                ca1.metric("1. Working Source Rows", format_indian_number(raw_count))
                ca2.metric("2. Analytics-Eligible Rows", format_indian_number(analytics_eligible))
                ca3.metric("3. Product Exclusions", format_indian_number(product_identity_exclusions))
                ca4.metric("4. Final Analysis Rows", format_indian_number(final_product_rows))
                
                st.markdown("##### Row Extraction Audit Breakdown")
                st.markdown(
                    f"- **Working Source Rows:** Total dataset rows currently active from the session state (`{source_name}`).\n"
                    f"- **Analytics-Eligible Rows:** Rows passing core revenue validation rules (dates valid, quantity > 0, price >= 0, OrderID present).\n"
                    f"- **Product-Identity Exclusions:** Additional rows excluded specifically from Product analysis due to lacking any usable ID or Name (`{product_identity_exclusions}`).\n"
                    f"- **Final Analysis Rows:** Total clean records used to compute aggregate product metrics (`{final_product_rows}`)."
                )

                if product_identity_exclusions > 0:
                    st.warning(f"Excluded {product_identity_exclusions} row(s) because they did not contain a readable ProductID or ProductName value.")
                else:
                    st.success("100% of analytics-eligible transaction rows had valid product identifiers resolved successfully.")
