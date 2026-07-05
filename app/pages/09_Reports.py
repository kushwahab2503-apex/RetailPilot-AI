import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from components.layout import page_header, dataset_status

st.set_page_config(page_title="Reports", layout="wide")
dataset_status()
page_header("Reports", "Generate and export summarized business documents.")

if not st.session_state.get("dataset_loaded") and not st.session_state.get("demo_mode"):
    st.warning("Please upload a dataset or launch Demo Mode first.")
else:
    st.info("Placeholder for PDF generator options and section selections.")
    st.button("Generate Demo Report")
