import streamlit as st
import pandas as pd
from app.components.layout import page_header, dataset_status
from backend.data_loader import load_csv
from backend.validator import validate_dataset

dataset_status()
page_header("Upload Data", "Upload your business dataset to begin analysis.")

uploaded_file = st.file_uploader("Upload CSV Dataset", type=["csv"])

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
                
                st.session_state["dataset_loaded"] = True
                st.session_state["demo_mode"] = False
                st.session_state["raw_df"] = df
                st.session_state["load_metadata"] = load_result
                st.session_state["validation_results"] = val_result
                
                if val_result["is_valid"]:
                    st.success("Validation complete! Navigate to Data Quality to review the results.")
                else:
                    st.error("Validation failed! Navigate to Data Quality to review critical errors.")

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
