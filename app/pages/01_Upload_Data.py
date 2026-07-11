import streamlit as st
import pandas as pd
from app.components.layout import page_header, dataset_status
from backend.data_loader import load_csv
from backend.validator import validate_dataset

import datetime

dataset_status()
page_header("Upload Data", "Upload your business dataset to begin analysis.")

# ── Session State Persistence Check ───────────────────────────────────────
is_loaded = st.session_state.get("dataset_loaded", False)
raw_df = st.session_state.get("raw_df")

if is_loaded and raw_df is not None:
    st.success("✓ Dataset already loaded")
    
    metadata = st.session_state.get("load_metadata", {})
    filename = metadata.get("filename", "Unknown Dataset")
    row_count = metadata.get("row_count", len(raw_df))
    col_count = metadata.get("column_count", len(raw_df.columns))
    timestamp = st.session_state.get("load_timestamp", "N/A")
    
    st.write(f"**Filename:** `{filename}`")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Rows", f"{row_count:,}")
    c2.metric("Columns", f"{col_count:,}")
    c3.metric("Upload Timestamp", timestamp)
    
    st.write("File preview:")
    st.dataframe(raw_df.head(5))
    
    val_result = st.session_state.get("validation_results")
    if val_result is not None:
        st.write("---")
        st.success("Validation Complete ✓")
        st.page_link("pages/03_Data_Cleaning.py", label="Proceed to Data Cleaning", icon="🛠️")
    else:
        if st.button("Validate Dataset", type="primary"):
            with st.spinner("Running dataset validation pipeline..."):
                val_result = validate_dataset(raw_df)
                
                # Reset cleaning framework states completely for the new upload
                for key in ["cleaned_df", "cleaning_config", "cleaning_summary", "cleaning_applied",
                            "cleaned_validation_result"]:
                    st.session_state.pop(key, None)
                    
                st.session_state["dataset_loaded"] = True
                st.session_state["demo_mode"] = False
                st.session_state["raw_df"] = raw_df
                st.session_state["validation_results"] = val_result
                st.session_state["load_timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.rerun()
                
    st.write("")
    if st.button("Replace Dataset", type="secondary"):
        keys_to_clear = [
            "raw_df",
            "cleaned_df",
            "validation_results",
            "cleaned_validation_result",
            "dataset_loaded",
            "load_metadata",
            "load_timestamp",
            "demo_mode",
            "cleaning_config",
            "cleaning_summary",
            "cleaning_applied",
            "analytics_cache",
            "generated reports"
        ]
        for key in keys_to_clear:
            st.session_state.pop(key, None)
        st.rerun()

else:
    uploaded_file = st.file_uploader("Upload CSV Dataset", type=["csv"])
    
    # Enable quick loading of sample/demo dataset
    st.markdown("<div style='text-align: center; color: #64748B; margin: 10px 0;'>&mdash; OR &mdash;</div>", unsafe_allow_html=True)
    if st.button("Load Sample Dataset", type="secondary", use_container_width=True):
        mock_path = "data/sample_retail_data.csv"
        try:
            df = pd.read_csv(mock_path)
            load_result = {
                "success": True,
                "dataframe": df,
                "filename": "sample_retail_data.csv",
                "row_count": len(df),
                "column_count": len(df.columns)
            }
            with st.spinner("Running dataset validation pipeline..."):
                val_result = validate_dataset(df)
                
                # Reset cleaning framework states completely for the new upload
                for key in ["cleaned_df", "cleaning_config", "cleaning_summary", "cleaning_applied",
                            "cleaned_validation_result"]:
                    st.session_state.pop(key, None)
                    
                st.session_state["dataset_loaded"] = True
                st.session_state["demo_mode"] = False
                st.session_state["raw_df"] = df
                st.session_state["load_metadata"] = load_result
                st.session_state["validation_results"] = val_result
                st.session_state["load_timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.rerun()
        except Exception as e:
            st.error(f"Failed to load sample dataset: {e}")
            
    if uploaded_file:
        load_result = load_csv(uploaded_file)
        
        if not load_result["success"]:
            st.error(f"Failed to load file: {load_result['error_message']}")
        else:
            df = load_result["dataframe"]
            st.success(f"File '{load_result['filename']}' received successfully.")
            
            st.write("File metadata:")
            c1, c2 = st.columns(2)
            c1.metric("Rows", load_result["row_count"])
            c2.metric("Columns", load_result["column_count"])
            
            st.write("File preview:")
            st.dataframe(df.head(5))
            
            if st.button("Validate Dataset", type="primary"):
                with st.spinner("Running dataset validation pipeline..."):
                    val_result = validate_dataset(df)
                    
                    # Reset cleaning framework states completely for the new upload
                    for key in ["cleaned_df", "cleaning_config", "cleaning_summary", "cleaning_applied",
                                "cleaned_validation_result"]:
                        st.session_state.pop(key, None)
                        
                    st.session_state["dataset_loaded"] = True
                    st.session_state["demo_mode"] = False
                    st.session_state["raw_df"] = df
                    st.session_state["load_metadata"] = load_result
                    st.session_state["validation_results"] = val_result
                    st.session_state["load_timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.rerun()

st.divider()
st.subheader("Dataset Schema Requirements")
st.markdown("""
The dataset must follow the RetailPilot AI specification.

**Required Fields:**
- `OrderID` (String) - Unique order identifier
- `OrderDate` (Date) - Date of transaction
- `ProductID` (String) - Unique product identifier
- `ProductName` (String) - Product display name
- `Category` (String) - Main product category
- `Quantity` (Integer) - Number of units sold
- `UnitPrice` (Float) - Selling price per unit before discount

**Module-Dependent Fields:**
- `CustomerID` (String) - Required for customer analytics (segmentation & RFM)
- `UnitCost` (Float) - Required for profit and margin analytics

**Optional/Recommended Fields:**
- `SubCategory` (String) - Detailed product classification
- `Brand` (String) - Product brand
- `City` (String) - Sales location
- `DiscountPct` (Float) - Discount percentage
- `PaymentMethod` (String) - Payment method used
- `StockAvailable` (Integer) - Available stock snapshot
""")
