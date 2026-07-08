import streamlit as st
import pandas as pd
from typing import Tuple, Optional

def resolve_analytics_dataset() -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Resolves the working dataframe out of Streamlit's session state.
    Preferred priority:
      1. cleaned_df, if a successful cleaned dataset exists in session state.
      2. raw_df, if the dataset has been successfully validated and loaded.
      3. Otherwise None.
      
    Returns:
        tuple: (df, source_name_str) or (None, None)
        df: the active pandas DataFrame
        source_name_str: "Cleaned Dataset" or "Raw Validated Dataset" (or None)
    """
    # Check if a cleaned dataframe is available and not empty
    if "cleaned_df" in st.session_state and st.session_state["cleaned_df"] is not None:
        return st.session_state["cleaned_df"], "Cleaned Dataset"
        
    # Check if raw dataframe was loaded and validated or active in demo mode
    if "raw_df" in st.session_state and st.session_state["raw_df"] is not None and (st.session_state.get("dataset_loaded", False) or st.session_state.get("demo_mode", False)):
        source_name = "Demo Validated Dataset" if st.session_state.get("demo_mode", False) else "Raw Validated Dataset"
        return st.session_state["raw_df"], source_name
        
    return None, None
