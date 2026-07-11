import streamlit as st
import textwrap
from app.components.layout import dataset_status
from app.components.theme import inject_global_css

dataset_status()
inject_global_css()



# ── Session state ──────────────────────────────────────────────────────────────
is_loaded = st.session_state.get("dataset_loaded", False) or st.session_state.get("demo_mode", False)
raw_df    = st.session_state.get("raw_df")
cleaned_df = st.session_state.get("cleaned_df")

status, row_count = "empty", 0
if is_loaded:
    if cleaned_df is not None:
        status, row_count = "cleaned", len(cleaned_df)
    else:
        status = "raw"
        row_count = len(raw_df) if raw_df is not None else 0

# ── 1. HERO ────────────────────────────────────────────────────────────────────
if status == "cleaned":
    badge = (
        f'<div class="badge-wrap">'
        f'<div class="status-banner" style="border-color:#6EE7B7;">'
        f'<div class="status-dot" style="background:#059669;"></div>'
        f'<span class="status-text" style="color:#059669;">Cleaned Dataset Ready &bull; {row_count:,} Transactions Active</span>'
        f'</div></div>'
    )
elif status == "raw":
    badge = (
        f'<div class="badge-wrap">'
        f'<div class="status-banner" style="border-color:#FCD34D;">'
        f'<div class="status-dot" style="background:#D97706;"></div>'
        f'<span class="status-text" style="color:#D97706;">Dataset Active (Raw Validated) &bull; {row_count:,} Transactions Active</span>'
        f'</div></div>'
    )
else:
    badge = (
        '<div class="badge-wrap">'
        '<div class="status-banner" style="border-color:#CBD5E1;">'
        '<div class="status-dot" style="background:#94A3B8;"></div>'
        '<span class="status-text">No Active Session &bull; Welcome to RetailPilot AI</span>'
        '</div></div>'
    )

st.markdown(
    f'<div class="hero-container">'
    f'<div class="eyebrow">RETAIL INTELLIGENCE PLATFORM</div>'
    f'<h1 class="hero-title">RetailPilot AI</h1>'
    f'<p class="hero-subtitle">Turn raw retail transactions into clear revenue intelligence,'
    f' deterministic health diagnostics, strategic insights, and executive-ready reports.</p>'
    f'{badge}'
    f'</div>',
    unsafe_allow_html=True,
)

# Hero CTA buttons
if status == "empty":
    _l, _c, _r = st.columns([2.5, 3.0, 2.5])
    with _c:
        st.page_link("pages/01_Upload_Data.py", label="Analyze Your Data", icon="📤", use_container_width=True)
else:
    _l, _c1, _c2, _r = st.columns([1.5, 2.5, 2.5, 1.5])
    with _c1:
        if status == "raw":
            st.page_link("pages/03_Data_Cleaning.py", label="Continue to Data Cleaning", icon="🛠️", use_container_width=True)
        else:
            st.page_link("pages/04_Analytics.py", label="Continue to Analytics", icon="📊", use_container_width=True)
    with _c2:
        if status == "raw":
            st.page_link("pages/04_Analytics.py", label="Explore Analytics", icon="📈", use_container_width=True)
        else:
            st.page_link("pages/08_Business_Health.py", label="Business Health", icon="❤️", use_container_width=True)

st.markdown(
    '<div class="hero-chips-container">'
    '<span class="hero-chip">7 Intelligence Modules</span>'
    '<span class="hero-chip">178+ Automated Tests</span>'
    '<span class="hero-chip">Executive PDF Reports</span>'
    '</div>',
    unsafe_allow_html=True,
)



# ── 2. BUSINESS VALUE ──────────────────────────────────────────────────────────
st.markdown('<div class="section-title">How RetailPilot AI Helps Your Business</div>', unsafe_allow_html=True)
st.markdown("""
<div class="grid-container">
<div class="benefit-card">
<span class="benefit-icon">📈</span>
<div class="benefit-title">Revenue Intelligence</div>
<div class="benefit-desc">Track growth trends, order economics, and volatility with transparent, reproducible calculations.</div>
</div>
<div class="benefit-card">
<span class="benefit-icon">👥</span>
<div class="benefit-title">Customer Behaviour</div>
<div class="benefit-desc">Surface repeat-purchase rates, concentration risk, and retention signals across your buyer base.</div>
</div>
<div class="benefit-card">
<span class="benefit-icon">📦</span>
<div class="benefit-title">Product Portfolio</div>
<div class="benefit-desc">Identify Pareto concentration, dependency risk, and long-tail opportunity in your SKU mix.</div>
</div>
<div class="benefit-card">
<span class="benefit-icon">📋</span>
<div class="benefit-title">Decision Support</div>
<div class="benefit-desc">Forecast readiness diagnostics, prioritised insights, and export-ready executive reports.</div>
</div>
</div>
""", unsafe_allow_html=True)

# ── 3. WORKFLOW + CAPABILITIES ─────────────────────────────────────────────────
st.markdown('<div class="section-title">Analysis Workflow &amp; Intelligence Modules</div>', unsafe_allow_html=True)
st.markdown("""
<div class="workflow-container">
<div class="workflow-step">
<div class="workflow-number">1</div>
<div class="workflow-label">Upload</div>
<div class="workflow-sub">CSV transaction dataset</div>
</div>
<div class="workflow-arrow">&rarr;</div>
<div class="workflow-step">
<div class="workflow-number">2</div>
<div class="workflow-label">Validate &amp; Clean</div>
<div class="workflow-sub">Type checks &amp; deduplication</div>
</div>
<div class="workflow-arrow">&rarr;</div>
<div class="workflow-step">
<div class="workflow-number">3</div>
<div class="workflow-label">Analyse</div>
<div class="workflow-sub">Revenue, products, customers</div>
</div>
<div class="workflow-arrow">&rarr;</div>
<div class="workflow-step">
<div class="workflow-number">4</div>
<div class="workflow-label">Diagnose</div>
<div class="workflow-sub">Business health audit</div>
</div>
<div class="workflow-arrow">&rarr;</div>
<div class="workflow-step">
<div class="workflow-number">5</div>
<div class="workflow-label">Insights</div>
<div class="workflow-sub">Strategic priority actions</div>
</div>
<div class="workflow-arrow">&rarr;</div>
<div class="workflow-step">
<div class="workflow-number">6</div>
<div class="workflow-label">Export</div>
<div class="workflow-sub">PDF / CSV reports</div>
</div>
</div>
""", unsafe_allow_html=True)

# Compact capability pills
st.markdown("""
<div class="cap-grid">
<div class="cap-pill cap-analytics"><div class="cap-name">Analytics</div><div class="cap-tag">Revenue &amp; cohorts</div></div>
<div class="cap-pill cap-products"><div class="cap-name">Products</div><div class="cap-tag">SKU &amp; Pareto analysis</div></div>
<div class="cap-pill cap-customers"><div class="cap-name">Customers</div><div class="cap-tag">Retention &amp; concentration</div></div>
<div class="cap-pill cap-forecast"><div class="cap-name">Forecast</div><div class="cap-tag">Exponential smoothing</div></div>
<div class="cap-pill cap-health"><div class="cap-name">Health</div><div class="cap-tag">Multi-domain diagnostics</div></div>
<div class="cap-pill cap-insights"><div class="cap-name">Insights</div><div class="cap-tag">Rule-based priorities</div></div>
<div class="cap-pill cap-reports"><div class="cap-name">Reports</div><div class="cap-tag">Audit-ready exports</div></div>
</div>
""", unsafe_allow_html=True)

# ── 4. TRUST STRIP ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="trust-strip">
<div class="trust-badges">
<span class="badge-item">Deterministic</span>
<span class="badge-item">Explainable Thresholds</span>
<span class="badge-item">No Black-Box Scores</span>
<span class="badge-item">Forecast Readiness</span>
<span class="badge-item">Audit-Ready</span>
</div>
<div class="trust-text">
Every diagnostic status is derived from measurable business metrics with traceable thresholds — no arbitrary composite scores.
</div>
</div>
""", unsafe_allow_html=True)

# Elegant Coming Soon Interactive Demo card at the very bottom
if status == "empty":
    st.markdown(
        """
        <div class="coming-soon-container">
            <div class="coming-soon-card">
                <div class="coming-soon-header">
                    <span class="coming-soon-icon">✨</span>
                    <span class="coming-soon-badge">COMING SOON</span>
                </div>
                <div style="font-size: 1.15rem; font-weight: 600; color: #172033; margin: 8px 0 10px 0; font-family: Inter, sans-serif;">Interactive Demo Mode</div>
                <div class="coming-soon-desc">
                    Explore RetailPilot AI with a pre-configured retail dataset. Experience Analytics, Products, Customers, Forecasting, Business Health, Insights, and Executive Reports without uploading your own data.
                </div>
                <div style="margin-top: 20px;">
                    <button disabled style="
                        width: 100%;
                        max-width: 200px;
                        background-color: #F8FAFC;
                        color: #94A3B8;
                        border: 1px solid #E2E8F0;
                        padding: 8px 16px;
                        border-radius: 8px;
                        font-family: Inter, sans-serif;
                        font-size: 0.88rem;
                        font-weight: 500;
                        cursor: not-allowed;
                    ">Demo Mode</button>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
