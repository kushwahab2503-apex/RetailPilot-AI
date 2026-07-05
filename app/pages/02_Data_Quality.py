import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from components.layout import page_header, dataset_status

st.set_page_config(page_title="Data Quality", layout="wide")
dataset_status()
page_header("Data Quality", "Review and resolve dataset quality anomalies.")

if not st.session_state.get("dataset_loaded") and not st.session_state.get("demo_mode"):
    st.warning("Please upload a dataset or launch Demo Mode first.")
else:
    st.metric("Overall Quality Score", "-- / 100")
    st.info("Placeholder for missing value summary, duplicate count, and cleaning recommendations.")
