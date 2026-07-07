import sys
import os
# Add project root to sys.path to enable clean absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import sys
import os

# Initialize session state variables if they do not exist
if "dataset_loaded" not in st.session_state:
    st.session_state["dataset_loaded"] = False
if "demo_mode" not in st.session_state:
    st.session_state["demo_mode"] = False

st.set_page_config(
    page_title="RetailPilot AI",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom branding in sidebar
st.sidebar.markdown("""
**RP**  
**RetailPilot AI**  
*Retail Intelligence Platform*
""")
st.sidebar.divider()

pg = st.navigation({
    "WORKSPACE": [
        st.Page("pages/00_Overview.py", title="Overview"),
        st.Page("pages/01_Upload_Data.py", title="Upload Data"),
        st.Page("pages/02_Data_Quality.py", title="Data Quality"),
        st.Page("pages/03_Data_Cleaning.py", title="Data Cleaning"),
    ],
    "INTELLIGENCE": [
        st.Page("pages/04_Analytics.py", title="Analytics"),
        st.Page("pages/05_Products.py", title="Products"),
        st.Page("pages/06_Customers.py", title="Customers"),
        st.Page("pages/07_Forecast.py", title="Forecast"),
    ],
    "DECISION SUPPORT": [
        st.Page("pages/08_Business_Health.py", title="Business Health"),
        st.Page("pages/09_Insights.py", title="Insights"),
        st.Page("pages/10_Reports.py", title="Reports"),
    ]
})

pg.run()
