import streamlit as st
from datetime import datetime
from app.components.layout import dataset_status

dataset_status()

# Inject styling and premium layout
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    .hero-container {
        text-align: center;
        padding: 40px 20px 20px 20px;
        margin-bottom: 2rem;
        background: radial-gradient(circle at center, rgba(99, 102, 241, 0.08) 0%, transparent 70%);
        border-radius: 20px;
        width: 100%;
        max-width: 800px;
        margin-left: auto;
        margin-right: auto;
    }
    
    .eyebrow {
        font-size: 0.85rem;
        font-weight: 700;
        color: #6366f1;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        margin-bottom: 0.75rem;
        text-align: center;
        width: 100%;
        margin-left: auto;
        margin-right: auto;
    }
    
    .hero-title {
        font-size: 3.5rem;
        font-weight: 800;
        line-height: 1.15;
        margin-bottom: 1.25rem;
        background: linear-gradient(135deg, #ffffff 40%, #a5b4fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.02em;
        text-align: center;
        width: 100%;
        margin-left: auto;
        margin-right: auto;
    }
    
    .hero-subtitle {
        font-size: 1.25rem;
        font-weight: 500;
        color: #d1d5db;
        max-width: 800px;
        margin: 0 auto 1.25rem auto;
        line-height: 1.5;
        text-align: center;
    }
    
    .hero-supporting {
        font-size: 0.95rem;
        color: #9ca3af;
        max-width: 750px;
        margin: 0 auto 2.25rem auto;
        line-height: 1.6;
        text-align: center;
    }
    
    .status-banner {
        background: rgba(17, 24, 39, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 12px 24px;
        margin: 0 auto;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        backdrop-filter: blur(8px);
        max-width: fit-content;
    }
    
    .status-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        animation: pulse-glow 2s infinite;
    }
    
    @keyframes pulse-glow {
        0% { transform: scale(0.9); opacity: 0.6; }
        50% { transform: scale(1.1); opacity: 1; }
        100% { transform: scale(0.9); opacity: 0.6; }
    }
    
    .status-text {
        font-size: 0.9rem;
        font-weight: 600;
        color: #e5e7eb;
        letter-spacing: 0.02em;
    }
    
    .section-title {
        font-size: 1.75rem;
        font-weight: 700;
        color: #ffffff;
        margin-top: 3.5rem;
        margin-bottom: 2rem;
        text-align: center;
        letter-spacing: -0.01em;
    }
    
    /* Responsive Grid */
    .grid-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        gap: 20px;
        margin-bottom: 2rem;
        max-width: 1200px;
        margin-left: auto;
        margin-right: auto;
    }
    
    .benefit-card {
        background: linear-gradient(135deg, #131927 0%, #0e1320 100%);
        border: 1px solid rgba(255, 255, 255, 0.04);
        border-radius: 12px;
        padding: 24px;
        transition: transform 0.22s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.22s ease, box-shadow 0.22s ease;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }
    
    .benefit-card:hover {
        transform: translateY(-4px);
        border-color: rgba(99, 102, 241, 0.3);
        box-shadow: 0 12px 30px rgba(99, 102, 241, 0.1);
    }
    
    .benefit-icon {
        font-size: 1.6rem;
        margin-bottom: 0.9rem;
        display: inline-block;
    }
    
    .benefit-title {
        font-size: 1.15rem;
        font-weight: 600;
        color: #ffffff;
        margin-bottom: 0.5rem;
    }
    
    .benefit-desc {
        font-size: 0.88rem;
        color: #9ca3af;
        line-height: 1.5;
    }
    
    /* Workflow strip */
    .workflow-container {
        display: flex;
        align-items: stretch;
        background: rgba(19, 25, 39, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.04);
        border-radius: 12px;
        padding: 24px;
        margin-top: 1rem;
        margin-bottom: 2rem;
        gap: 12px;
        justify-content: space-between;
        max-width: 1200px;
        margin-left: auto;
        margin-right: auto;
    }
    
    .workflow-step {
        display: flex;
        flex-direction: column;
        align-items: center;
        flex: 1;
        text-align: center;
        padding: 8px;
    }
    
    .workflow-number {
        width: 26px;
        height: 26px;
        border-radius: 50%;
        background-color: rgba(99, 102, 241, 0.12);
        color: #a5b4fc;
        font-size: 0.78rem;
        font-weight: 700;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 0.6rem;
        border: 1px solid rgba(99, 102, 241, 0.3);
    }
    
    .workflow-label {
        font-size: 0.95rem;
        font-weight: 600;
        color: #ffffff;
        margin-bottom: 0.25rem;
    }
    
    .workflow-sub {
        font-size: 0.78rem;
        color: #9ca3af;
        line-height: 1.35;
    }
    
    .workflow-arrow {
        color: #4b5563;
        font-size: 1.2rem;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
    }
    
    @media (max-width: 768px) {
        .workflow-container {
            flex-direction: column;
            align-items: center;
            gap: 16px;
        }
        .workflow-arrow {
            transform: rotate(90deg);
            margin: 6px 0;
        }
        .workflow-step {
            width: 100%;
        }
    }
    
    /* Capabilities Matrix */
    .capabilities-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 16px;
        margin-bottom: 2rem;
        max-width: 1200px;
        margin-left: auto;
        margin-right: auto;
    }
    
    .cap-item {
        background: linear-gradient(135deg, #131927 0%, #0e1320 100%);
        border-radius: 12px;
        padding: 20px;
        border-left: 4px solid #4b5563;
        border-top: 1px solid rgba(255, 255, 255, 0.04);
        border-right: 1px solid rgba(255, 255, 255, 0.04);
        border-bottom: 1px solid rgba(255, 255, 255, 0.04);
        transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.2s ease;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }
    
    .cap-item:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35);
    }
    
    .cap-title {
        font-size: 1.05rem;
        font-weight: 700;
        margin-bottom: 0.4rem;
    }
    
    .cap-desc {
        font-size: 0.85rem;
        color: #9ca3af;
        line-height: 1.45;
    }
    
    /* Domain matching accents */
    .cap-analytics { border-left-color: #3b82f6; }
    .cap-analytics .cap-title { color: #60a5fa; }
    
    .cap-products { border-left-color: #f59e0b; }
    .cap-products .cap-title { color: #fbbf24; }
    
    .cap-customers { border-left-color: #8b5cf6; }
    .cap-customers .cap-title { color: #a78bfa; }
    
    .cap-forecast { border-left-color: #06b6d4; }
    .cap-forecast .cap-title { color: #22d3ee; }
    
    .cap-health { border-left-color: #10b981; }
    .cap-health .cap-title { color: #34d399; }
    
    .cap-insights { border-left-color: #a855f7; }
    .cap-insights .cap-title { color: #c084fc; }
    
    .cap-reports { border-left-color: #4f46e5; }
    .cap-reports .cap-title { color: #818cf8; }
    
    /* Trust / Heuristic Strip */
    .trust-strip {
        background: rgba(17, 24, 39, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 24px 30px;
        margin: 4rem auto;
        text-align: center;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05);
        max-width: 1200px;
    }
    
    .trust-badges {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 12px;
        margin-bottom: 1.25rem;
    }
    
    .badge-item {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.06);
        color: #d1d5db;
        padding: 6px 16px;
        border-radius: 30px;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
    }
    
    .trust-text {
        font-size: 0.88rem;
        color: #9ca3af;
        max-width: 800px;
        margin: 0 auto;
        line-height: 1.6;
    }
    
    /* final cta bottom */
    .cta-container {
        text-align: center;
        background: linear-gradient(135deg, #161c2d 0%, #0e1320 100%);
        border: 1px solid rgba(99, 102, 241, 0.16);
        border-radius: 12px;
        padding: 40px 20px;
        margin: 4rem auto 2rem auto;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        max-width: 1200px;
    }
    
    .cta-title {
        font-size: 1.65rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 0.75rem;
    }
    
    .cta-desc {
        font-size: 0.95rem;
        color: #9ca3af;
        margin-bottom: 1.75rem;
    }
    
    .demo-info-box {
        background: rgba(239, 68, 68, 0.08);
        border: 1px solid rgba(239, 68, 68, 0.2);
        border-radius: 8px;
        padding: 10px 16px;
        color: #fca5a5;
        font-size: 0.85rem;
        margin-top: 10px;
        display: inline-block;
        max-width: 600px;
    }
</style>
""", unsafe_allow_html=True)

# Determine the dataset state
is_loaded = st.session_state.get("dataset_loaded", False) or st.session_state.get("demo_mode", False)
raw_df = st.session_state.get("raw_df")
cleaned_df = st.session_state.get("cleaned_df")

status = "empty"
row_count = 0

if is_loaded:
    if cleaned_df is not None:
        status = "cleaned"
        row_count = len(cleaned_df)
    else:
        status = "raw"
        row_count = len(raw_df) if raw_df is not None else 0

# 1. PREMIUM HERO SECTION
status_banner_html = ""
if status == "cleaned":
    status_banner_html = f"""
    <div style="text-align: center; margin-top: 1.5rem;">
        <div class="status-banner" style="border-color: rgba(16, 185, 129, 0.4);">
            <div class="status-dot" style="background-color: #10b981; box-shadow: 0 0 10px #10b981;"></div>
            <span class="status-text">Cleaned Dataset Ready &bull; {row_count:,} Transactions Active</span>
        </div>
    </div>
    """
elif status == "raw":
    status_banner_html = f"""
    <div style="text-align: center; margin-top: 1.5rem;">
        <div class="status-banner" style="border-color: rgba(245, 158, 11, 0.4);">
            <div class="status-dot" style="background-color: #f59e0b; box-shadow: 0 0 10px #f59e0b;"></div>
            <span class="status-text">Dataset Active (Raw Validated) &bull; {row_count:,} Transactions Active</span>
        </div>
    </div>
    """
else:
    status_banner_html = """
    <div style="text-align: center; margin-top: 1.5rem;">
        <div class="status-banner" style="border-color: rgba(255, 255, 255, 0.1);">
            <div class="status-dot" style="background-color: #9ca3af; box-shadow: 0 0 10px #9ca3af;"></div>
            <span class="status-text">No Active Session &bull; Welcome to RetailPilot AI</span>
        </div>
    </div>
    """

st.markdown(f"""
<div class="hero-container">
    <div class="eyebrow">RETAIL INTELLIGENCE PLATFORM</div>
    <h1 class="hero-title">RetailPilot AI</h1>
    <p class="hero-subtitle">Turn retail transaction data into clear business intelligence, explainable diagnostics, forecasts, and executive actions.</p>
    <p class="hero-supporting">Upload your sales data and move from raw transactions to validated analytics, customer and product intelligence, business health diagnostics, strategic insights, and export-ready executive reports.</p>
    {status_banner_html}
</div>
""", unsafe_allow_html=True)

# Render Hero CTA Buttons
c_btn_l, c_btn1, c_btn2, c_btn_r = st.columns([2.5, 1.8, 1.8, 2.5])

with c_btn1:
    if status == "empty":
        st.page_link("pages/01_Upload_Data.py", label="Analyze Your Data", icon="📤", use_container_width=True)
    elif status == "raw":
        st.page_link("pages/03_Data_Cleaning.py", label="Continue to Data Cleaning", icon="🛠️", use_container_width=True)
    else:  # status == "cleaned"
        st.page_link("pages/04_Analytics.py", label="Continue to Analytics Dashboard", icon="📊", use_container_width=True)

with c_btn2:
    if status == "empty":
        st.button("Explore Demo Mode", key="hero_demo_disabled", disabled=True, use_container_width=True)
    elif status == "raw":
        st.page_link("pages/04_Analytics.py", label="Explore Analytics Dashboards", icon="📈", use_container_width=True)
    else:  # status == "cleaned"
        st.page_link("pages/08_Business_Health.py", label="Inspect Business Health", icon="❤️", use_container_width=True)

# Centered explanatory box under columns for empty state
if status == "empty":
    st.markdown("""
    <div style="text-align: center; margin-top: 15px; margin-bottom: 2rem;">
        <div class="demo-info-box" style="text-align: left; margin: 0 auto; display: inline-block;">
            <strong>Demo Mode Unavailable:</strong> Sample retail data and synthetic generation scripts have been disabled in this workspace to enforce strict client data isolation. Please upload your transaction CSV file in the Upload section to start.
        </div>
    </div>
    """, unsafe_allow_html=True)

# 2. BUSINESS VALUE SECTION
st.markdown('<div class="section-title">How RetailPilot AI Helps Your Business</div>', unsafe_allow_html=True)
st.markdown("""
<div class="grid-container">
    <div class="benefit-card">
        <div class="benefit-icon">📈</div>
        <div class="benefit-title">Understand Performance</div>
        <div class="benefit-desc">Track revenue trends, order economics, growth patterns, and volatility using transparent calculations.</div>
    </div>
    <div class="benefit-card">
        <div class="benefit-icon">👥</div>
        <div class="benefit-title">Know Your Customers</div>
        <div class="benefit-desc">Measure repeat buying behavior, customer concentration, retention signals, and revenue contribution.</div>
    </div>
    <div class="benefit-card">
        <div class="benefit-icon">📦</div>
        <div class="benefit-title">Optimize Product Portfolio</div>
        <div class="benefit-desc">Identify product dependency, concentration risk, long-tail contribution, and portfolio balance.</div>
    </div>
    <div class="benefit-card">
        <div class="benefit-icon">📋</div>
        <div class="benefit-title">Plan With Confidence</div>
        <div class="benefit-desc">Evaluate forecast readiness, surface evidence-backed strategic insights, and generate executive reports.</div>
    </div>
</div>
""", unsafe_allow_html=True)

# 3. SIMPLE WORKFLOW SECTION
st.markdown('<div class="section-title">From Raw Data to Business Decisions</div>', unsafe_allow_html=True)
st.markdown("""
<div class="workflow-container">
    <div class="workflow-step">
        <div class="workflow-number">1</div>
        <div class="workflow-label">Upload Data</div>
        <div class="workflow-sub">Provide transaction CSV dataset</div>
    </div>
    <div class="workflow-arrow">&rarr;</div>
    <div class="workflow-step">
        <div class="workflow-number">2</div>
        <div class="workflow-label">Validate & Clean</div>
        <div class="workflow-sub">Verify types & sanitize records</div>
    </div>
    <div class="workflow-arrow">&rarr;</div>
    <div class="workflow-step">
        <div class="workflow-number">3</div>
        <div class="workflow-label">Analyze Performance</div>
        <div class="workflow-sub">Review revenue & cohorts</div>
    </div>
    <div class="workflow-arrow">&rarr;</div>
    <div class="workflow-step">
        <div class="workflow-number">4</div>
        <div class="workflow-label">Diagnose Health</div>
        <div class="workflow-sub">Audit metrics against thresholds</div>
    </div>
    <div class="workflow-arrow">&rarr;</div>
    <div class="workflow-step">
        <div class="workflow-number">5</div>
        <div class="workflow-label">Extract Insights</div>
        <div class="workflow-sub">Derive strategic priority actions</div>
    </div>
    <div class="workflow-arrow">&rarr;</div>
    <div class="workflow-step">
        <div class="workflow-number">6</div>
        <div class="workflow-label">Export Reports</div>
        <div class="workflow-sub">Download PDF/CSV summaries</div>
    </div>
</div>
""", unsafe_allow_html=True)

# 4. INTELLIGENCE CAPABILITIES SECTION
st.markdown('<div class="section-title">One Platform. Complete Retail Intelligence.</div>', unsafe_allow_html=True)
st.markdown("""
<div class="capabilities-grid">
    <div class="cap-item cap-analytics">
        <div class="cap-title">Analytics</div>
        <div class="cap-desc">Overview of core metrics, seasonal transaction counts, sales run-rates, and cumulative trends.</div>
    </div>
    <div class="cap-item cap-products">
        <div class="cap-title">Products</div>
        <div class="cap-desc">Product share concentrations, Pareto 80/20 distribution filters, and low-performing SKU reviews.</div>
    </div>
    <div class="cap-item cap-customers">
        <div class="cap-title">Customers</div>
        <div class="cap-desc">Customer cohort behavior summaries, repeat purchasing rates, and Top-5 buyer concentrations.</div>
    </div>
    <div class="cap-item cap-forecast">
        <div class="cap-title">Forecast</div>
        <div class="cap-desc">Predictive forecasting using triple exponential smoothing and chronological holdout splits.</div>
    </div>
    <div class="cap-item cap-health">
        <div class="cap-title">Business Health</div>
        <div class="cap-desc">Consolidated health indicators and diagnostics across finance, portfolio, and operations.</div>
    </div>
    <div class="cap-item cap-insights">
        <div class="cap-title">Insights</div>
        <div class="cap-desc">Deterministic engine extracting actionable next steps based on mathematical thresholds.</div>
    </div>
    <div class="cap-item cap-reports">
        <div class="cap-title">Executive Reports</div>
        <div class="cap-desc">Consolidated printable summaries, metrics snapshot, and data audit traceability logs.</div>
    </div>
</div>
""", unsafe_allow_html=True)

# 5. TRUST / METHODOLOGY STRIP
st.markdown("""
<div class="trust-strip">
    <div class="trust-badges">
        <span class="badge-item">Deterministic Diagnostics</span>
        <span class="badge-item">Explainable Thresholds</span>
        <span class="badge-item">Evidence-Backed Insights</span>
        <span class="badge-item">Forecast Readiness Checks</span>
        <span class="badge-item">Audit-Ready Reports</span>
    </div>
    <div class="trust-text">
        No arbitrary black-box business score. Every diagnostic status and strategic observation is traceable to measurable business metrics.
    </div>
</div>
""", unsafe_allow_html=True)

# 6. FINAL CTA SECTION
st.markdown('<div class="cta-container">', unsafe_allow_html=True)
st.markdown('<div class="cta-title">Ready to Understand Your Business Better?</div>', unsafe_allow_html=True)
st.markdown('<div class="cta-desc">Start with your transaction dataset or explore the platform using Demo Mode.</div>', unsafe_allow_html=True)

c_cta_l, c_cta1, c_cta2, c_cta_r = st.columns([2.5, 1.8, 1.8, 2.5])
with c_cta1:
    if status == "empty":
        st.page_link("pages/01_Upload_Data.py", label="Upload Dataset", icon="📤", use_container_width=True)
    elif status == "raw":
        st.page_link("pages/03_Data_Cleaning.py", label="Clean Active Dataset", icon="🛠️", use_container_width=True)
    else:  # status == "cleaned"
        st.page_link("pages/04_Analytics.py", label="Open Core Analytics", icon="📊", use_container_width=True)

with c_cta2:
    if status == "empty":
        st.button("Explore Demo", key="final_demo_disabled", disabled=True, use_container_width=True)
    elif status == "raw":
        st.page_link("pages/04_Analytics.py", label="Open Analytics", icon="📊", use_container_width=True)
    else:  # status == "cleaned"
        st.page_link("pages/08_Business_Health.py", label="Open Business Health", icon="❤️", use_container_width=True)

st.markdown('</div>', unsafe_allow_html=True)
