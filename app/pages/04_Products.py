import streamlit as st

from app.components.layout import page_header, dataset_status

st.set_page_config(page_title="Products", layout="wide")
dataset_status()
page_header("Products", "Analyze product performance and category trends.")

if not st.session_state.get("dataset_loaded") and not st.session_state.get("demo_mode"):
    st.warning("Please upload a dataset or launch Demo Mode first.")
else:
    st.info("Placeholder for product margin profiles, inventory movement, and rankings.")
