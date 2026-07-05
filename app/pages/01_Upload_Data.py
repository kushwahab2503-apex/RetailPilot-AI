import streamlit as st
import pandas as pd
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from components.layout import page_header, dataset_status

dataset_status()
page_header("Upload Data", "Upload your business dataset to begin analysis.")

uploaded_file = st.file_uploader("Upload CSV Dataset", type=["csv"])

if uploaded_file:
    # Safely try reading some basic metadata if valid
    try:
        df_preview = pd.read_csv(uploaded_file, nrows=5)
        st.info(f"File '{uploaded_file.name}' received.")
        st.write("File preview:")
        st.dataframe(df_preview)
        
        st.button("Begin Validation Process", type="primary", disabled=True, help="Processing pipeline is under construction.")
    except Exception as e:
        st.error(f"Error reading file: {e}")
        
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
