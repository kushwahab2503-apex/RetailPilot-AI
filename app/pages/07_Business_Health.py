import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from components.layout import page_header, dataset_status

st.set_page_config(page_title="Business Health", layout="wide")
dataset_status()
page_header("Business Health", "Comprehensive organizational stability mapping.")

if not st.session_state.get("dataset_loaded") and not st.session_state.get("demo_mode"):
    st.warning("Please upload a dataset or launch Demo Mode first.")
else:
    st.info("Placeholder for calculated business health gauge and factor breakdown.")
