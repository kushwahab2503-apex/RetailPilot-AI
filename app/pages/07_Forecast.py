import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from app.components.theme import inject_global_css

from app.components.layout import page_header, dataset_status
from backend.analytics_resolver import resolve_analytics_dataset
from backend.analytics_engine import aggregate_time_series
from backend.formatters import format_indian_currency, format_indian_number
from backend.forecast_engine import (
    prepare_forecast_dataset,
    detect_forecast_capabilities,
    fill_missing_periods,
    generate_forecast
)

# Configure page layout
st.set_page_config(page_title="RetailPilot AI - Forecast Intelligence", layout="wide")

# Render typical layout statuses
dataset_status()
page_header("Forecast Intelligence", "Deterministic revenue projections, holdout validation audit, and trend diagnostics.")

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
                <li>Navigate back to <b>Forecast Intelligence</b> to project sales.</li>
            </ol>
        </div>
    """, unsafe_allow_html=True)
else:
    # 1. Pre-process basic analytics dataset and extract categories
    prepared_df, meta_prestr = prepare_forecast_dataset(df)
    
    # Category dropdown parameters
    all_categories = sorted(list(set(prepared_df["Category"].fillna("Unknown").astype(str).str.strip().replace({'': 'Unknown', 'nan': 'Unknown'}))))
    
    # 2. Interactive Sidebar Controls
    st.sidebar.markdown(f"**Working Source:** `{source_name}`")
    st.sidebar.markdown("### Forecast Configurations")
    
    selected_category = st.sidebar.selectbox(
        "Product Category Filter",
        options=["All Categories"] + all_categories,
        help="Run forecast projections isolated by product category segment."
    )
    
    # Recommended frequency check based on overall span
    overall_min = prepared_df["OrderDate"].min()
    overall_max = prepared_df["OrderDate"].max()
    overall_span = (overall_max - overall_min).days if pd.notna(overall_min) and pd.notna(overall_max) else 0

    if overall_span < 90:
        recommended_freq = "Daily"
    elif overall_span < 365:
        recommended_freq = "Weekly"
    else:
        recommended_freq = "Monthly"

    freq_labels = {
        "Daily": "Daily (Recommended)" if recommended_freq == "Daily" else "Daily",
        "Weekly": "Weekly (Recommended)" if recommended_freq == "Weekly" else "Weekly",
        "Monthly": "Monthly (Recommended)" if recommended_freq == "Monthly" else "Monthly",
    }
    
    selected_frequency = st.sidebar.radio(
        "Aggregation Interval",
        options=["Daily", "Weekly", "Monthly"],
        index=["Daily", "Weekly", "Monthly"].index(recommended_freq),
        format_func=lambda x: freq_labels[x],
        help="Timeline aggregation granularity. Bypassed frequencies are evaluated for capability."
    )

    # Contextual steps boundary parameters
    if selected_frequency == "Monthly":
        min_h, max_h, def_h = 3, 6, 3
    elif selected_frequency == "Weekly":
        min_h, max_h, def_h = 4, 12, 4
    else:  # Daily
        min_h, max_h, def_h = 7, 30, 7

    selected_horizon = st.sidebar.slider(
        "Forecast Horizon",
        min_value=min_h,
        max_value=max_h,
        value=def_h,
        step=1,
        help="Specify the number of future periods to predict."
    )

    # 3. Filter category and check capability
    cat_filter = None if selected_category == "All Categories" else selected_category
    category_df, meta_cat = prepare_forecast_dataset(df, category=cat_filter)
    
    # Run capability detection independently
    caps = detect_forecast_capabilities(category_df, selected_frequency)
    state = caps["capability_state"]
    reasons = caps["capability_reasons"]
    
    # Setup rendering canvas
    st.subheader("Forecast Engine Diagnostic & Capabilities Overview")
    
    # Render Status Notification box
    if state == "UNAVAILABLE":
        badge_html = '<span class="status-badge badge-unavailable">UNAVAILABLE</span>'
        st.markdown(f"**Capability Status:** {badge_html}", unsafe_allow_html=True)
        st.error(f"Cannot generate forecast projections at the selected frequency: `{selected_frequency}`.")
        
        st.markdown("#### Capability Audit Failures")
        for r in reasons:
            st.markdown(f"- ❌ {r}")
            
        st.info("💡 **Resolution suggestion:** Try selecting a different aggregation frequency (e.g. Daily) or broadening your category filter to retrieve more rows.")
        
    else:
        # LIMITED or SUITABLE
        if state == "SUITABLE":
            badge_html = '<span class="status-badge badge-suitable">SUITABLE</span>'
            st.markdown(f"**Capability Status:** {badge_html}", unsafe_allow_html=True)
            st.success("The dataset satisfies all parameters for robust, validated forecasting.")
        else: # LIMITED
            badge_html = '<span class="status-badge badge-limited">LIMITED BASIS</span>'
            st.markdown(f"**Capability Status:** {badge_html}", unsafe_allow_html=True)
            st.warning("The dataset has limited historical support. Validation split is compressed, or fallback baseline projections are engaged.")
            
        with st.expander("Show Diagnostic Parameter Logs"):
            cols = st.columns(4)
            cols[0].metric("Date Span", f"{caps['date_span_days']} Days")
            cols[1].metric("Aggregated Periods count", caps["aggregated_period_count"])
            cols[2].metric("Non-Zero Periods count", caps["non_zero_period_count"])
            cols[3].metric("Observations Grid Coverage", f"{caps['coverage_ratio']:.2%}")
            for r in reasons:
                st.markdown(f"- ℹ️ {r}")

        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
        
        # 4. Generate forecast projections
        agg_df = aggregate_time_series(category_df, selected_frequency)
        min_d = category_df["OrderDate"].min()
        max_d = category_df["OrderDate"].max()
        filled_df = fill_missing_periods(agg_df, selected_frequency, min_d, max_d)
        
        forecast_df, meta_out = generate_forecast(filled_df, selected_frequency, selected_horizon, state)
        
        # KPI Metric Cards Row
        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            # Active selected model
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Selected Model</div>
                    <div class="metric-value" style="font-size:1.35rem; color:#818cf8; min-height:48px;">{meta_out['model_display_name']}</div>
                    <div class="metric-subtext">{'Best mathematical model fit' if meta_out['is_validated'] else 'Simple unvalidated baseline'}</div>
                </div>
            """, unsafe_allow_html=True)
            
        # Get metrics
        val_metrics = meta_out.get("validation_metrics") or {}
        wape_val = val_metrics.get("WAPE")
        mae_val = val_metrics.get("MAE")
        rmse_val = val_metrics.get("RMSE")
        
        wape_str = f"{wape_val:.2%}" if wape_val is not None else "N/A"
        mae_str = format_indian_currency(mae_val) if mae_val is not None else "N/A"
        rmse_str = format_indian_currency(rmse_val) if rmse_val is not None else "N/A"

        if meta_out["validation_status"] == "Validated (WAPE Unavailable — Zero Target)":
            wape_str = "N/A (Zero Target)"
            
        with c2:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Validation WAPE</div>
                    <div class="metric-value">{wape_str}</div>
                    <div class="metric-subtext">{meta_out['validation_status']}</div>
                </div>
            """, unsafe_allow_html=True)
            
        with c3:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Validation MAE</div>
                    <div class="metric-value">{mae_str}</div>
                    <div class="metric-subtext">Mean absolute residual error</div>
                </div>
            """, unsafe_allow_html=True)
            
        with c4:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Validation RMSE</div>
                    <div class="metric-value">{rmse_str}</div>
                    <div class="metric-subtext">Root mean squared error dispersion</div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
        
        # Timeline plots section
        st.subheader("Revenue Projections Timeline")
        
        # Prepare datasets for charting
        chart_df = forecast_df.copy()
        chart_df["DateString"] = chart_df["Date"].dt.strftime('%b %d, %Y')
        chart_df = chart_df.set_index("Date")
        
        # Rename columns to clear business conventions
        chart_df = chart_df.rename(columns={
            "ActualRevenue": "Actual Revenue",
            "PredictedRevenue": "Predicted Revenue",
            "LowerBound": "Residual-Based Prediction Band (Lower)",
            "UpperBound": "Residual-Based Prediction Band (Upper)"
        })
        
        plot_cols = [
            "Actual Revenue",
            "Predicted Revenue",
            "Residual-Based Prediction Band (Lower)",
            "Residual-Based Prediction Band (Upper)"
        ]
        
        st.line_chart(
            chart_df[plot_cols],
            color=["#6366f1", "#a855f7", "#ec4899", "#f43f5e"],
            height=340
        )
        
        st.caption("Estimated Uncertainty Range highlights the Residual-Based Prediction Band representing projection boundaries derived via empirical in-sample standard errors scaling over steps.")
        
        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
        
        # Diagnostics, model matrices, and categories tabs
        metrics_tab, comparisons_tab, category_tab = st.tabs([
            "📈 Forecast Data Grid",
            "📊 Models Comparison Matrix",
            "🛍️ Segments Capability Audit"
        ])
        
        with metrics_tab:
            st.markdown("#### Historical Actuals and Projected Revenue Stream")
            display_grid = forecast_df.copy()
            # Format outputs
            display_grid["Actual Revenue"] = display_grid["ActualRevenue"].apply(
                lambda x: format_indian_currency(x) if pd.notna(x) else ""
            )
            display_grid["Predicted Revenue"] = display_grid["PredictedRevenue"].apply(
                lambda x: format_indian_currency(x) if pd.notna(x) else ""
            )
            display_grid["Lower Band"] = display_grid["LowerBound"].apply(
                lambda x: format_indian_currency(x) if pd.notna(x) else ""
            )
            display_grid["Upper Band"] = display_grid["UpperBound"].apply(
                lambda x: format_indian_currency(x) if pd.notna(x) else ""
            )
            display_grid["Date"] = display_grid["Date"].dt.strftime('%Y-%m-%d')
            display_grid["Type"] = display_grid["IsForecast"].apply(
                lambda x: "Forecast" if x else "History"
            )
            
            grid_cols = ["Date", "Type", "Actual Revenue", "Predicted Revenue", "Lower Band", "Upper Band"]
            st.dataframe(display_grid[grid_cols], use_container_width=True, hide_index=True)
            
        with comparisons_tab:
            st.markdown("#### Chronological Cross-Validation Analysis")
            comparisons = meta_out.get("model_comparisons") or []
            
            if not comparisons:
                st.info("Validation was bypassed for this dataset configuration. Falling back to baseline equations.")
            else:
                comp_rows = []
                for comp in comparisons:
                    wape_val = comp.get("WAPE")
                    wape_disp = f"{wape_val:.2%}" if wape_val is not None else "N/A"
                    if wape_val is None and meta_out.get("validation_status") == "Validated (WAPE Unavailable — Zero Target)":
                        wape_disp = "N/A (Zero validation target)"
                        
                    comp_rows.append({
                        "Model Mode": comp.get("model"),
                        "Validation WAPE": wape_disp,
                        "Validation MAE": format_indian_currency(comp.get("MAE")),
                        "Validation RMSE": format_indian_currency(comp.get("RMSE")),
                        "Seasonal Eligibility": "✅ Eligible" if comp.get("is_seasonal_eligible") else f"❌ {comp.get('seasonal_reason')}"
                    })
                
                st.dataframe(pd.DataFrame(comp_rows), use_container_width=True, hide_index=True)
                
            st.markdown("""
            **Chronological Validation Process Details:**
            * The validation checks split observations in a strict time order: old values train the coefficients and newer periods act as validation metrics.
            * Tie breaks: `Seasonal Naive` has top priority, followed by `Linear Trend`, `Moving Average`, then `Naive`.
            """)
            
        with category_tab:
            st.markdown("#### Category Independency Diagnostics")
            st.caption("Verifies forecast capabilities separately for categories in the dataset (restricted to top 10 categories by total revenue to avoid performance overhead).")
            
            # Enforce category count protection (choose top 10 by revenue contributions)
            cat_revenues = prepared_df.groupby("Category")["_Revenue"].sum().reset_index()
            cat_top = cat_revenues.sort_values(by="_Revenue", ascending=False).head(10)["Category"].tolist()
            
            cat_audit_rows = []
            for cat in cat_top:
                cat_subset, _ = prepare_forecast_dataset(df, category=cat)
                cat_caps = detect_forecast_capabilities(cat_subset, selected_frequency)
                
                cat_audit_rows.append({
                    "Category": cat,
                    "Total Raw Sales": format_indian_currency(cat_subset["_Revenue"].sum()),
                    "Status": cat_caps["capability_state"],
                    "Validation Status": cat_caps["validation_status"],
                    "Periods count": cat_caps["aggregated_period_count"]
                })
                
            st.dataframe(pd.DataFrame(cat_audit_rows), use_container_width=True, hide_index=True)
            if len(all_categories) > 10:
                st.info(f"Showing top 10 categories out of {len(all_categories)} total categories.")
            
        # Methodology Audit Expander
        with st.expander("Methodology Audit Summary"):
            st.markdown("""
            ### Mathematical Engine & Validation Specifications:
            * **Naive Equation:** $\\hat{y}_{t+h} = y_t$
              Repeats the last observed period. Uses standard errors of training residuals for uncertainty bands.
            * **Moving Average (MA-3):** $\\hat{y}_{t+h} = \\frac{1}{3} \\sum_{i=0}^{2} y_{t-i}$
              Smooves fluctuations by averaging indices. Residual bands scale dynamically.
            * **Linear Trend Equation:** $y_t = \\beta_0 + \\beta_1 \\cdot t$
              Fits standard least-squares parameters. Good for capturing strong upward or downward trends.
            * **Seasonal Naive:** $\\hat{y}_{t+h} = y_{t+h-S}$
              Matches corresponding season of the previous cycle. Requires 2 full cycles (14 days daily, 104 weeks weekly, 24 months monthly) and a minimum of 40% non-zero values.
            * **Residual-Based Prediction Band:** Calculated via $z \\cdot s_e \\cdot \\sqrt{h}$ where $z = 1.96$ and $s_e$ evaluates in-sample standard errors of residuals. No formal normality of error checks are made.
            """)
