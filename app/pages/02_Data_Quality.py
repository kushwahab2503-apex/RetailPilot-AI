import streamlit as st
from app.components.layout import page_header, dataset_status

dataset_status()
page_header("Data Quality", "Review and resolve dataset quality anomalies.")

if not st.session_state.get("dataset_loaded") and not st.session_state.get("demo_mode"):
    st.warning("Please upload a dataset or launch Demo Mode first.")
elif "validation_results" not in st.session_state:
    st.info("Dataset loaded. Please run the validation process from the Upload Data page.")
else:
    val_result = st.session_state["validation_results"]
    
    score = val_result["data_quality_score"]
    band = val_result["quality_band"]
    
    st.subheader("Data Quality Score")
    col1, col2 = st.columns(2)
    with col1:
        if band == "Good":
            delta_col = "normal"
            icon = "✅"
        elif band == "Attention Required":
            delta_col = "off"
            icon = "⚠️"
        else:
            delta_col = "inverse"
            icon = "🚨"

        st.metric("Overall Quality Score", f"{score} / 100", delta=band, delta_color=delta_col)
        
    st.divider()
    
    st.subheader("Validation Status")
    if val_result["is_valid"]:
        st.success("Dataset schema is valid.")
    else:
        st.error("Dataset schema is invalid.")
        for err in val_result["errors"]:
            st.error(f"Critical Error: {err}")
            
    if val_result["warnings"]:
        with st.expander("Validation Warnings"):
            for w in val_result["warnings"]:
                st.warning(w)

    st.subheader("Dataset Summary")
    sq = val_result["summary"]
    if sq:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Rows", sq.get("total_rows", 0))
        c2.metric("Missing Cells", sq.get("total_missing", 0))
        c3.metric("Exact Duplicates", sq.get("exact_duplicates", 0))
        c4.metric("Repeated Orders", sq.get("repeated_order_ids", 0))

    if val_result["column_results"]:
        st.subheader("Missing Values")
        for col, res in val_result["column_results"].items():
            st.markdown(f"- **{col}**: {res['missing_count']} missing ({res['missing_pct']}%)")
            
    if val_result["business_rule_results"]:
        st.subheader("Business Rule Violations")
        for rule, count in val_result["business_rule_results"].items():
            st.markdown(f"- **{rule}**: {count} violations")
            
    st.subheader("Module Availability")
    avail = val_result["available_modules"]
    st.markdown(f"""
    - **Core Dashboard**: {'✅' if avail.get('core_dashboard') else '❌'}
    - **Product Analytics**: {'✅' if avail.get('product_analytics') else '❌'}
    - **Customer Analytics**: {'✅' if avail.get('customer_analytics') else '❌'}
    - **Profit Analytics**: {'✅' if avail.get('profit_analytics') else '❌'}
    """)
    
    st.divider()
    if st.session_state.get("cleaned_df") is not None:
        st.success("✅ A cleaned dataset is currently active in the workspace.")
    elif val_result["is_valid"]:
        st.info("💡 Cleaning tools are now available for this dataset on the Data Cleaning page.")
