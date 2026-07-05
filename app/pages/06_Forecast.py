import streamlit as st

from app.components.layout import page_header, dataset_status

st.set_page_config(page_title="Forecast", layout="wide")
dataset_status()
page_header("Forecast", "Machine Learning driven revenue and demand projection.")

if not st.session_state.get("dataset_loaded") and not st.session_state.get("demo_mode"):
    st.warning("Please upload a dataset or launch Demo Mode first.")
else:
    st.info("Placeholder for historical vs prediction charts, models evaluation, and future trend insights.")
