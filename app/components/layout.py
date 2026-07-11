import streamlit as st

def page_header(title: str, description: str):
    """Render a consistent page header across all application views."""
    st.title(title)
    st.markdown(description)
    st.divider()

def dataset_status():
    """Display the current dataset context in the sidebar."""
    st.sidebar.markdown("### Context")
    if st.session_state.get("dataset_loaded"):
        st.sidebar.success("Dataset: Ready")
    elif st.session_state.get("demo_mode"):
        st.sidebar.info("Demo Mode: Active")
    else:
        st.sidebar.markdown(
            "<div class='sidebar-status-box'>"
            "<span style='color:#64748B;font-size:0.88rem;font-weight:600;'>"
            "No Dataset Loaded"
            "</span>"
            "</div>",
            unsafe_allow_html=True,
        )
    st.sidebar.divider()
