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
        st.sidebar.markdown("""
        <div style='background-color: #111827; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 12px; margin-bottom: 1rem;'>
            <span style='color: #9CA3AF; font-size: 0.9rem;'>No Dataset Loaded</span>
        </div>
        """, unsafe_allow_html=True)
    st.sidebar.divider()
