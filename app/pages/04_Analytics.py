import streamlit as st

from app.components.layout import page_header, dataset_status

st.set_page_config(page_title="Analytics", layout="wide")
dataset_status()
page_header("Analytics", "Interactive multidimensional business analytics.")

if not st.session_state.get("dataset_loaded") and not st.session_state.get("demo_mode"):
    st.warning("Please upload a dataset or launch Demo Mode first.")
else:
    st.info("Placeholder for main revenue charts, timeline analysis, and breakdown components.")
    col1, col2 = st.columns(2)
    with col1:
        st.container(border=True).markdown("### Chart 1 Placeholder")
    with col2:
        st.container(border=True).markdown("### Chart 2 Placeholder")
