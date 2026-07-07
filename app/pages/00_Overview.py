import streamlit as st
from app.components.layout import page_header, dataset_status

dataset_status()

page_header("RetailPilot AI", "AI-Powered Retail Business Intelligence Platform")

if not st.session_state.get("dataset_loaded") and not st.session_state.get("demo_mode"):
    st.markdown("### Analyze Your Data")
    st.info("Upload a dataset to begin analysis.")
    
    st.page_link("pages/01_Upload_Data.py", label="Go to Upload Data")
    st.write("---")
    st.markdown("### Explore Demo Mode")
    st.button("Launch Demo Mode", disabled=True, help="Demo Mode is coming soon.")
else:
    st.success("Platform ready. Navigate via the sidebar to continue analysis.")
    st.write("---")
    
    st.subheader("Dataset Pipeline Status")
    status_col1, status_col2, status_col3 = st.columns(3)
    status_col1.success("✅ Uploaded")
    
    if st.session_state.get("validation_results"):
        status_col2.success("✅ Validated")
    else:
        status_col2.info("⏳ Pending Validation")
        
    if st.session_state.get("cleaned_df") is not None:
        status_col3.success("✅ Cleaned")
    else:
        status_col3.info("⏳ Pending Cleaning")
        
    st.write("---")
    
    st.subheader("High-Level KPIs")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Revenue", "--")
    with col2:
        st.metric("Transactions", "--")
    with col3:
        st.metric("Unique Customers", "--")
    with col4:
        st.metric("Health Score", "--")
