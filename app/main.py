import sys
import os
# Add project root to sys.path to enable clean absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
from app.components.theme import inject_global_css

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

# Inject global CSS for the initial render pass.
# Each page also calls inject_global_css() independently to guarantee
# the theme is applied regardless of navigation execution order.
inject_global_css()

# Sidebar branding — use st.logo() (official Streamlit API, works with st.navigation())
logo_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "retailpilot_saas_logo.png"
)

if os.path.exists(logo_path):
    st.logo(logo_path, size="large")
    # Inject subtitle + name text below the logo via CSS-safe sidebar markdown
    st.sidebar.markdown(
        "<div style='"
        "text-align:center;"
        "padding:0 8px 20px 8px;"
        "border-bottom:1px solid #E5EAF3;"
        "margin-bottom:8px;'>"
        "<div style='font-size:0.95rem;font-weight:700;color:#172033;"
        "line-height:1.3;letter-spacing:-0.01em;'>RetailPilot AI</div>"
        "<div style='font-size:0.72rem;color:#64748B;font-weight:500;"
        "margin-top:2px;'>Enterprise Retail Intelligence</div>"
        "</div>",
        unsafe_allow_html=True,
    )
else:
    # Graceful fallback — classic RP monogram
    st.sidebar.markdown(
        "<div style='padding:12px 4px 8px 4px;margin-bottom:4px;'>"
        "<div style='display:inline-flex;align-items:center;gap:10px;'>"
        "<div style='width:32px;height:32px;background:#4F46E5;border-radius:8px;"
        "display:flex;align-items:center;justify-content:center;"
        "font-size:0.9rem;font-weight:800;color:#fff;'>RP</div>"
        "<div>"
        "<div style='font-size:0.95rem;font-weight:700;color:#172033;line-height:1.2;'>"
        "RetailPilot AI</div>"
        "<div style='font-size:0.72rem;color:#64748B;font-weight:500;'>"
        "Enterprise Retail Intelligence</div>"
        "</div>"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.sidebar.divider()

pg = st.navigation({
    "WORKSPACE": [
        st.Page("pages/00_Overview.py", title="Overview", icon=":material/dashboard:"),
        st.Page("pages/01_Upload_Data.py", title="Upload Data", icon=":material/upload:"),
        st.Page("pages/02_Data_Quality.py", title="Data Quality", icon=":material/rule:"),
        st.Page("pages/03_Data_Cleaning.py", title="Data Cleaning", icon=":material/cleaning_services:"),
    ],
    "INTELLIGENCE": [
        st.Page("pages/04_Analytics.py", title="Analytics", icon=":material/analytics:"),
        st.Page("pages/05_Products.py", title="Products", icon=":material/shopping_bag:"),
        st.Page("pages/06_Customers.py", title="Customers", icon=":material/group:"),
        st.Page("pages/07_Forecast.py", title="Forecast", icon=":material/trending_up:"),
    ],
    "DECISION SUPPORT": [
        st.Page("pages/08_Business_Health.py", title="Business Health", icon=":material/favorite:"),
        st.Page("pages/09_Insights.py", title="Insights", icon=":material/insights:"),
        st.Page("pages/10_Reports.py", title="Reports", icon=":material/description:"),
    ]
})

pg.run()
