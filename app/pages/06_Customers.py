import streamlit as st

from app.components.layout import page_header, dataset_status

st.set_page_config(page_title="Customers", layout="wide")
dataset_status()
page_header("Customers", "Customer profiles, segmentation, and RFM discovery.")

if not st.session_state.get("dataset_loaded") and not st.session_state.get("demo_mode"):
    st.warning("Please upload a dataset or launch Demo Mode first.")
else:
    st.info("Placeholder for machine learning customer clustering and value extraction.")
