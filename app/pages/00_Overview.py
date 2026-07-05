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
