"""
app/components/theme.py
-----------------------
Shared light enterprise design system for RetailPilot AI.

Call inject_global_css() at the top of every page that renders
custom HTML cards, dividers, or status badges.

CSS injection strategy
----------------------
Streamlit 1.56 uses st.navigation() / st.Page() (MPAv2). In this
model main.py re-runs on every page navigation and pg.run() executes
the page script in the same render pass. CSS injected in main.py
therefore appears on every page. However, per the design brief, every
page also calls inject_global_css() explicitly so that the theme is
self-contained regardless of execution order or future architecture
changes.
"""

import streamlit as st


# ── Shared rules extracted from pages 04–10 ───────────────────────────────
# Shared:  .metric-card, .metric-label, .metric-value, .metric-subtext,
#          .custom-divider, .status-badge + all semantic variants,
#          .gradient-text, empty-state guide box, Inter font import.
#
# Page-specific CSS intentionally kept in their respective files:
#   00_Overview.py  — hero-container, eyebrow, hero-title, hero-subtitle,
#                     status-banner, badge-wrap, section-title, grid-container,
#                     benefit-card, workflow-*, cap-pill/cap-*, trust-strip,
#                     cta-container, demo-info-box  (all unique to overview layout)
#   06_Customers.py — cohort heatmap uses Pandas styler (no extra CSS needed)
#   07_Forecast.py  — badge-suitable / badge-limited / badge-unavailable
#                     (forecast-specific three-state readiness system; kept in page)
# ─────────────────────────────────────────────────────────────────────────────

_GLOBAL_CSS = """
<style>
/* ── Font & Typography ─────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp {
    font-family: Inter, ui-sans-serif, system-ui, -apple-system,
                 BlinkMacSystemFont, "Segoe UI", sans-serif;
    color: #172033;
}

/* ── App Layout & Background ───────────────────────────────────────────── */
.stApp, [data-testid="stAppViewContainer"] {
    background-color: #F5F7FA !important;
}

[data-testid="stHeader"] {
    background-color: transparent !important;
}

/* Bound and Center Content Layout */
[data-testid="stAppViewContainer"] [data-testid="stMainViewContainer"] > div:first-child {
    max-width: 1200px !important;
    margin: 0 auto !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
}

/* ── Sidebar Customizations ────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background-color: #FFFFFF !important;
    border-right: 1px solid #E5E7EB !important;
    box-shadow: none !important;
    width: 250px !important;
    min-width: 250px !important;
    max-width: 250px !important;
    height: 100vh !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
}

section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    background-color: #FFFFFF !important;
    padding-left: 8px !important;
    padding-right: 8px !important;
    height: 100% !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
}

/* Reset default page link list paddings in navigation container */
div[data-testid="stSidebarNav"] {
    padding-left: 0px !important;
    padding-right: 0px !important;
    margin-left: 0px !important;
    margin-right: 0px !important;
}

div[data-testid="stSidebarNavItems"] {
    padding-left: 0px !important;
    padding-right: 0px !important;
    margin-left: 0px !important;
    margin-right: 0px !important;
}

/* ── Sidebar Logo & Brand Header ──────────────────────────────── */

/* Style the official st.logo() sidebar header as a full brand block   */
[data-testid="stSidebarHeader"] {
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    text-align: center !important;
    height: auto !important;
    min-height: 130px !important;
    padding: 20px 12px 16px 12px !important;
    border-bottom: 1px solid #E5E7EB !important;
    margin-bottom: 0 !important;
    position: relative !important;
    width: 100% !important;
    box-sizing: border-box !important;
    overflow: visible !important;
    clip: auto !important;
}

/* Center all direct children of the header (logo wrapper div) */
[data-testid="stSidebarHeader"] > * {
    text-align: center !important;
    width: 100% !important;
}

/* Logo image — square, 52px, fully visible, contain */
[data-testid="stSidebarLogo"] {
    width: 52px !important;
    height: 52px !important;
    min-width: 52px !important;
    min-height: 52px !important;
    max-width: 52px !important;
    max-height: 52px !important;
    object-fit: contain !important;
    object-position: center !important;
    display: block !important;
    margin: 0 auto 8px auto !important;
    overflow: visible !important;
    flex-shrink: 0 !important;
}

/* Center the logo anchor wrapper */
[data-testid="stSidebarHeader"] a {
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    width: 100% !important;
    overflow: visible !important;
}

/* Collapse button absolutely positioned — doesn't affect logo centering */
[data-testid="stSidebarCollapseButton"] {
    position: absolute !important;
    top: 8px !important;
    right: 8px !important;
    width: auto !important;
    flex-shrink: 0 !important;
}

/* App name: RetailPilot AI — 22px bold dark */
[data-testid="stSidebarHeader"] > div:first-child::after {
    content: "RetailPilot AI";
    display: block;
    text-align: center;
    font-size: 22px;
    font-weight: 700;
    color: #172033;
    line-height: 1.25;
    letter-spacing: -0.02em;
    margin-top: 0;
    width: 100%;
}

/* Tagline: Enterprise Retail Intelligence — 12px muted */
[data-testid="stSidebarHeader"]::after {
    content: "Enterprise Retail Intelligence";
    display: block;
    text-align: center;
    font-size: 12px;
    font-weight: 500;
    color: #64748B;
    margin-top: 3px;
    padding-bottom: 0;
    width: 100%;
}

/* 24px spacing before WORKSPACE heading (first nav section) */
[data-testid="stSidebarNav"] {
    padding-top: 24px !important;
}

/* Brand Identity Block: hide old fallback RP monogram if shown */
[data-testid="stSidebarContent"] div[style*="padding:12px 4px 8px 4px"] {
    display: none !important;
}

/* Compact Rounded Navigation items */
div[data-testid="stSidebarNavItems"] a,
[data-testid="stSidebarContent"] [data-testid="stPageLink"] a,
[data-testid="stSidebarContent"] a,
[data-testid="stSidebarNavLink"] {
    border-radius: 8px !important;
    margin: 2px 0px !important; /* Stretch to occupy the available 8px sidebar padding */
    padding: 6px 12px !important;
    gap: 8px !important; /* Tighter gap between icon and label */
    display: inline-flex !important;
    align-items: center !important;
    justify-content: flex-start !important;
    color: #64748B !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
    text-decoration: none !important;
    width: 100% !important;
    box-sizing: border-box !important;
    transition: all 200ms ease !important;
}

/* Tighten the navigation item inner layout spans */
div[data-testid="stSidebarNavItems"] a > span,
[data-testid="stSidebarContent"] a > span,
[data-testid="stSidebarNavLink"] > span {
    margin: 0 !important;
    padding: 0 !important;
    flex-grow: 0 !important;
    flex-shrink: 0 !important;
    display: inline-flex !important;
    align-items: center !important;
}

/* Nesting layout div reset */
div[data-testid="stSidebarNavItems"] a > span:last-child div,
[data-testid="stSidebarContent"] a > span:last-child div,
[data-testid="stSidebarNavLink"] > span:last-child div {
    margin: 0 !important;
    padding: 0 !important;
    display: inline-block !important;
}

/* Ensure no text truncation inside links and that it uses the inline alignment */
div[data-testid="stSidebarNavItems"] a p,
[data-testid="stSidebarContent"] a p,
[data-testid="stSidebarNavLink"] p {
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    color: inherit !important;
    text-transform: none !important; /* Prevent headers text-transform: uppercase from cascading */
    white-space: nowrap !important;
    margin: 0 !important;
    padding: 0 !important;
    text-overflow: clip !important;
    overflow: visible !important;
}

/* Icon layout adjustments inside standard navigation */
[data-testid="stSidebarNavLinkIcon"] {
    margin-right: 0px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
}

div[data-testid="stSidebarNavItems"] a:hover,
[data-testid="stSidebarContent"] a:hover,
[data-testid="stSidebarNavLink"]:hover {
    background-color: #F8FAFC !important;
    color: #172033 !important;
    transform: none !important;
}

/* Active navigation item styling: Light indigo background, thin left border, dark text */
div[data-testid="stSidebarNavItems"] a[aria-current="page"],
[data-testid="stSidebarContent"] a[aria-current="page"],
div[data-testid="stSidebarNavItems"] a.active,
[data-testid="stSidebarContent"] a.active,
[data-testid="stSidebarNavLink"][aria-current="page"] {
    background-color: #EEF2FF !important;
    color: #172033 !important;
    border-left: 4px solid #4F46E5 !important;
    font-weight: 600 !important;
    box-shadow: none !important;
    border-radius: 0 8px 8px 0 !important;
    margin-left: 0 !important;
    padding-left: 8px !important; /* Starts content (4px border + 8px padding) at 12px, aligning with the 12px padding of inactive pages */
    padding-right: 12px !important;
}

div[data-testid="stSidebarNavItems"] a[aria-current="page"] span,
[data-testid="stSidebarContent"] a[aria-current="page"] span,
[data-testid="stSidebarNavLink"][aria-current="page"] span {
    color: #172033 !important;
}

/* Group headings inside sidebar: WORKSPACE, INTELLIGENCE, DECISION SUPPORT */
div[data-testid="stSidebarNav"] header p,
div[data-testid="stSidebarNavItems"] header p,
[data-testid="stSidebarNav"] header span,
[data-testid="stSidebarNav"] header div {
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.05em !important;
    color: #64748B !important;
    text-transform: uppercase !important;
    padding-left: 12px !important; /* Aligns headings with the icons (12px inset inside link list) */
    margin-top: 14px !important;
    margin-bottom: 4px !important;
}

/* Sidebar Divider */
section[data-testid="stSidebar"] hr {
    margin-left: 0px !important;
    margin-right: 0px !important;
    margin-top: 12px !important;
    margin-bottom: 12px !important;
}

/* Sidebar Context / Ready status box override */
.sidebar-status-box {
    background-color: #F8FAFC !important;
    border: 1px solid #E5E7EB !important;
    border-radius: 8px !important;
    padding: 8px 12px !important;
    margin: 8px 0px 10px 0px !important; /* Stretch to available width */
}

/* ── Element Container Overrides (Fade In Animations) ────────────────── */
.stApp .element-container, .metric-card, .benefit-card, .report-card, .insight-card, .domain-card, .empty-state-box {
    animation: fadeIn 200ms ease forwards;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(4px); }
    to { opacity: 1; transform: translateY(0); }
}

/* ── Native Streamlit Widget Refinements ────────────────────────────────── */
/* Buttons */
.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button {
    border-radius: 12px !important;
    font-weight: 600 !important;
    padding: 0 20px !important;
    font-size: 0.9rem !important;
    height: 44px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    transition: all 200ms ease !important;
    border: 1px solid #E5E7EB !important;
    box-shadow: 0 1px 2px rgba(15,23,42,0.03) !important;
}

.stButton > button[kind="primary"],
.stDownloadButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"],
button[data-testid="baseButton-primary"] {
    background-color: #4F46E5 !important;
    color: #FFFFFF !important;
    border: 1px solid #4F46E5 !important;
}

.stButton > button[kind="primary"]:hover,
button[data-testid="baseButton-primary"]:hover {
    background-color: #4338CA !important;
    border-color: #4338CA !important;
    transform: translateY(-1.5px) !important;
    box-shadow: 0 4px 10px rgba(79, 70, 229, 0.12) !important;
}

.stButton > button[kind="secondary"],
button[data-testid="baseButton-secondary"],
.stDownloadButton > button,
.stFormSubmitButton > button {
    background-color: #FFFFFF !important;
    color: #172033 !important;
    border: 1px solid #E5E7EB !important;
}

.stButton > button[kind="secondary"]:hover,
button[data-testid="baseButton-secondary"]:hover,
.stDownloadButton > button:hover,
.stFormSubmitButton > button:hover {
    background-color: #F8FAFC !important;
    border-color: #CBD5E1 !important;
    color: #172033 !important;
    transform: translateY(-1.5px) !important;
    box-shadow: 0 2px 6px rgba(15,23,42,0.02) !important;
}

/* Page Link Override (Fix width and height text cutting) */
[data-testid="stPageLink"] > a,
[data-testid="stPageLink"] {
    background-color: #FFFFFF !important;
    border: 1px solid #E5E7EB !important;
    border-radius: 12px !important;
    padding: 0 20px !important;
    height: 44px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    color: #172033 !important;
    font-weight: 600 !important;
    text-decoration: none !important;
    box-shadow: 0 1px 2px rgba(15,23,42,0.03) !important;
    width: 100% !important;
    box-sizing: border-box !important;
    transition: all 200ms ease !important;
}

[data-testid="stPageLink"] > a:hover,
[data-testid="stPageLink"]:hover {
    background-color: #F8FAFC !important;
    border-color: #CBD5E1 !important;
    color: #172033 !important;
    transform: translateY(-1.5px) !important;
    box-shadow: 0 4px 10px rgba(15,23,42,0.04) !important;
}

[data-testid="stPageLink"] a,
[data-testid="stPageLink"] {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 8px !important;
}
[data-testid="stPageLink"] a *,
[data-testid="stPageLink"] * {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: auto !important;
    flex-grow: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}
[data-testid="stPageLink"] p {
    color: inherit !important;
    font-weight: 600 !important;
}

/* Metric styling */
[data-testid="stMetricValue"] {
    font-weight: 700 !important;
    color: #172033 !important;
}
[data-testid="stMetricLabel"] {
    color: #64748B !important;
    text-transform: uppercase !important;
    font-size: 0.74rem !important;
    letter-spacing: 0.05em !important;
}

/* Expanders */
.stExpander {
    border-radius: 12px !important;
    border: 1px solid #E5E7EB !important;
    background-color: #FFFFFF !important;
    box-shadow: 0 1px 2px rgba(15,23,42,0.01) !important;
    overflow: hidden !important;
    margin-bottom: 16px !important;
}
.stExpander > details {
    border: none !important;
}
.stExpander > details > summary {
    padding: 12px 18px !important;
    font-weight: 600 !important;
    color: #172033 !important;
}
.stExpander > details > summary:hover {
    background-color: #F8FAFC !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px !important;
    border-bottom: 2px solid #E5E7EB !important;
    padding-bottom: 4px !important;
}
.stTabs [data-baseweb="tab"] {
    background-color: transparent !important;
    border: none !important;
    color: #64748B !important;
    font-weight: 500 !important;
    padding: 8px 16px !important;
    border-radius: 6px !important;
    transition: all 200ms ease !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: #172033 !important;
    background-color: #F8FAFC !important;
}
.stTabs [aria-selected="true"] {
    color: #4F46E5 !important;
    background-color: #EEF2FF !important;
    font-weight: 600 !important;
}

/* Dataframe & Tables */
[data-testid="stTable"], .stDataFrame {
    border: 1px solid #E5E7EB !important;
    border-radius: 12px !important;
    overflow: hidden !important;
    box-shadow: 0 1px 3px rgba(15,23,42,0.01) !important;
    background: #FFFFFF !important;
}

/* Form selectors */
.stSelectbox > div[data-baseweb="select"], div[data-baseweb="select"], .stSelectbox > div {
    border-radius: 10px !important;
    border: 1px solid #E5E7EB !important;
    background-color: #FFFFFF !important;
}

/* ── Standard Premium Cards ── */
.metric-card, .benefit-card, .report-card, .insight-card, .domain-card {
    background: #FFFFFF !important;
    border: 1px solid #E5E7EB !important;
    border-radius: 18px !important;
    padding: 24px !important;
    box-shadow: 0 2px 8px rgba(15,23,42,0.03) !important;
    transition: transform 200ms ease, 
                border-color 200ms ease, 
                box-shadow 200ms ease !important;
    box-sizing: border-box !important;
}

.metric-card:hover, .benefit-card:hover, .report-card:hover, .insight-card:hover, .domain-card:hover {
    transform: translateY(-2px) !important;
    border-color: #C7D2FE !important;
    box-shadow: 0 4px 14px rgba(15,23,42,0.06) !important;
}

.metric-label {
    font-size: 0.78rem;
    font-weight: 600;
    color: #64748B;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    margin-bottom: 6px;
}
.metric-value {
    font-size: 1.7rem;
    font-weight: 700;
    color: #172033;
    margin-bottom: 2px;
    line-height: 1.15;
}
.metric-subtext {
    font-size: 0.75rem;
    color: #8C9BAE;
}

/* ── Divider ─────────────────────────────────────────────────────────────── */
.custom-divider {
    height: 1px;
    background: #E5E7EB;
    margin: 20px 0;
    border: none;
}

/* ── Status badges (Consolidated System) ─────────────────────────────────── */
.status-badge, .badge {
    padding: 4px 10px;
    border-radius: 9999px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.02em;
    text-transform: uppercase;
    display: inline-block;
    border-width: 1px;
    border-style: solid;
    line-height: 1.3;
}

/* Strong / Suitable (Green) */
.badge-strong, .status-strong, .badge-suitable, .badge-positive {
    background: #EFFDF5 !important;
    color: #16A34A !important;
    border-color: #DCFCE7 !important;
}

/* Stable / Informational (Blue) */
.badge-stable, .status-stable, .badge-informational {
    background: #EFF6FF !important;
    color: #2563EB !important;
    border-color: #DBEAFE !important;
}

/* Watch / Limited (Orange / Amber) */
.badge-watch, .status-watch, .badge-limited {
    background: #FFFBEB !important;
    color: #F59E0B !important;
    border-color: #FEF3C7 !important;
}

/* Risk / Unavailable / Danger (Red) */
.badge-risk, .status-risk, .badge-unavailable, .badge-danger {
    background: #FEF2F2 !important;
    color: #DC2626 !important;
    border-color: #FEE2E2 !important;
}

/* Insufficient / Domain (Gray) */
.badge-insufficient, .status-insufficient, .badge-domain {
    background: #F8FAFC !important;
    color: #64748B !important;
    border-color: #E2E8F0 !important;
}

/* ── Gradient text ── */
.gradient-text {
    color: #172033 !important;
    font-weight: 800;
}

/* ── Empty-state illustrated guide box ──────────────────────────────────── */
.empty-state-box {
    background: #FFFFFF !important;
    border: 1px solid #E5E7EB !important;
    border-radius: 18px !important;
    padding: 32px !important;
    box-shadow: 0 4px 12px rgba(15,23,42,.03) !important;
    max-width: 640px !important;
    margin: 24px auto !important;
    text-align: left !important;
    position: relative !important;
    overflow: hidden !important;
}
.empty-state-box::before {
    content: "" !important;
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    width: 4px !important;
    height: 100% !important;
    background: #4F46E5 !important;
}
.empty-state-box h4 {
    font-size: 1.1rem !important;
    color: #172033 !important;
    font-weight: 700 !important;
    margin-top: 0 !important;
    margin-bottom: 12px !important;
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
}
.empty-state-box h4::before {
    content: "✦" !important;
    font-size: 1.1rem !important;
    color: #4F46E5 !important;
}
.empty-state-box ol {
    margin: 0 !important;
    padding-left: 20px !important;
    color: #64748B !important;
}
.empty-state-box li {
    margin-bottom: 8px !important;
    font-size: 0.9rem !important;
    line-height: 1.5 !important;
}
.empty-state-box b {
    color: #172033 !important;
}

/* ── Overview Layout Components ─────────────────────────────────────────── */
.hero-container {
    text-align: center;
    padding: 40px 32px 32px 32px !important;
    margin: 0 auto 1.5rem auto !important;
    background: #FFFFFF !important;
    border: 1px solid #E5E7EB !important;
    border-radius: 20px !important;
    width: 100% !important;
    max-width: 1100px !important;
    box-shadow: 0 4px 12px rgba(15,23,42,0.03) !important;
}
.eyebrow {
    font-size: 0.74rem;
    font-weight: 700;
    color: #4F46E5;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 0.5rem;
    text-align: center;
}
.hero-title {
    font-size: clamp(2.4rem, 4vw, 3.2rem) !important;
    font-weight: 800 !important;
    line-height: 1.2 !important;
    margin: 0 auto 0.6rem auto !important;
    color: #172033 !important;
    text-align: center;
    width: 100%;
}
.hero-subtitle {
    font-size: 0.95rem !important;
    font-weight: 400 !important;
    color: #64748B !important;
    max-width: 600px !important;
    margin: 0 auto 1.2rem auto !important;
    line-height: 1.55 !important;
    text-align: center;
}
.badge-wrap { text-align: center; margin-top: 1rem; }

.status-banner {
    background: #F8FAFC;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
    padding: 8px 18px;
    display: inline-flex;
    align-items: center;
    gap: 8px;
}
.status-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
}
.status-text {
    font-size: 0.82rem;
    font-weight: 600;
    color: #475569;
    letter-spacing: 0.01em;
    white-space: nowrap;
}

/* Info chips section in Hero card */
.hero-chips-container {
    display: flex;
    justify-content: center;
    gap: 12px;
    margin-top: 20px;
    flex-wrap: wrap;
}
.hero-chip {
    background-color: #F1F5F9;
    color: #475569;
    font-size: 0.78rem;
    font-weight: 600;
    padding: 6px 14px;
    border-radius: 9999px;
    border: 1px solid #E2E8F0;
    display: inline-flex;
    align-items: center;
}

.section-title {
    font-size: 1.35rem;
    font-weight: 700;
    color: #172033;
    margin: 2rem auto 1.25rem auto;
    text-align: center;
    max-width: 1100px;
}

/* Benefit grid items height logic */
.grid-container {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 16px;
    margin: 0 auto 2rem auto;
    max-width: 1100px;
}
.benefit-card {
    min-height: 170px !important;
}
.benefit-icon { font-size: 1.3rem; margin-bottom: 0.5rem; display: block; }
.benefit-title {
    font-size: 0.95rem;
    font-weight: 700;
    color: #172033;
    margin-bottom: 0.3rem;
}
.benefit-desc { font-size: 0.84rem; color: #64748B; line-height: 1.5; }

/* Workflow Strip */
.workflow-container {
    display: flex;
    align-items: center;
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 18px;
    padding: 20px;
    margin: 0 auto 0.75rem auto;
    gap: 8px;
    justify-content: space-between;
    max-width: 1100px;
    box-shadow: 0 2px 8px rgba(15,23,42,0.02);
}
.workflow-step {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex: 1;
    text-align: center;
    padding: 4px 2px;
}
.workflow-number {
    width: 26px; height: 26px;
    border-radius: 50%;
    background: #EEF2FF;
    color: #4F46E5;
    font-size: 0.75rem;
    font-weight: 700;
    display: flex; align-items: center; justify-content: center;
    margin-bottom: 0.4rem;
    border: 1px solid #C7D2FE;
}
.workflow-label {
    font-size: 0.84rem;
    font-weight: 600;
    color: #172033;
    margin-bottom: 0.1rem;
}
.workflow-sub { font-size: 0.74rem; color: #64748B; line-height: 1.3; }
.workflow-arrow {
    color: #CBD5E1;
    font-size: 0.9rem;
    font-weight: 700;
    flex-shrink: 0;
}

/* Capability compact pills layout */
.cap-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 12px;
    margin: 1.25rem auto 0 auto;
    max-width: 1100px;
}
.cap-pill {
    border-radius: 12px;
    padding: 12px 14px;
    border-left: 3px solid #CBD5E1;
    background: #FFFFFF;
    border-top: 1px solid #E5E7EB;
    border-right: 1px solid #E5E7EB;
    border-bottom: 1px solid #E5E7EB;
    box-shadow: 0 1px 2px rgba(15,23,42,0.01);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    box-sizing: border-box;
}
.cap-pill:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(15,23,42,0.04);
}
.cap-name {
    font-size: 0.88rem;
    font-weight: 700;
    margin-bottom: 0.1rem;
}
.cap-tag { font-size: 0.74rem; color: #64748B; line-height: 1.35; }

.cap-analytics { border-left-color: #4F46E5; } .cap-analytics .cap-name { color: #4F46E5; }
.cap-products  { border-left-color: #F59E0B; } .cap-products  .cap-name { color: #F59E0B; }
.cap-customers { border-left-color: #7C3AED; } .cap-customers .cap-name { color: #7C3AED; }
.cap-forecast  { border-left-color: #0891B2; } .cap-forecast  .cap-name { color: #0891B2; }
.cap-health    { border-left-color: #16A34A; } .cap-health    .cap-name { color: #16A34A; }
.cap-insights  { border-left-color: #9333EA; } .cap-insights  .cap-name { color: #9333EA; }
.cap-reports   { border-left-color: #2563EB; } .cap-reports   .cap-name { color: #2563EB; }

/* Trust Strip */
.trust-strip {
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 18px;
    padding: 20px;
    margin: 2rem auto 0 auto;
    text-align: center;
    max-width: 1100px;
    box-shadow: 0 1px 3px rgba(15,23,42,0.01);
}
.trust-badges {
    display: flex; flex-wrap: wrap;
    justify-content: center; gap: 8px;
    margin-bottom: 0.8rem;
}
.badge-item {
    background: #F8FAFC;
    border: 1px solid #E5E7EB;
    color: #475569;
    padding: 4px 12px;
    border-radius: 30px;
    font-size: 0.72rem; font-weight: 600;
    letter-spacing: 0.02em; text-transform: uppercase;
}
.trust-text { font-size: 0.84rem; color: #64748B; max-width: 700px; margin: 0 auto; line-height: 1.55; }

/* Final CTA */
.cta-container {
    text-align: center;
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-top: 4px solid #4F46E5;
    border-radius: 18px;
    padding: 32px 24px;
    margin: 2rem auto;
    box-shadow: 0 4px 12px rgba(15,23,42,0.03);
    max-width: 1100px;
}
.cta-title { font-size: 1.3rem; font-weight: 700; color: #172033; margin-bottom: 0.4rem; }
.cta-desc  { font-size: 0.88rem; color: #64748B; margin-bottom: 1.25rem; }
.demo-info-box {
    background: #FFFBEB;
    border: 1px solid #FEF3C7;
    border-radius: 8px;
    padding: 8px 16px;
    color: #B45309;
    font-size: 0.82rem;
    display: inline-block;
    max-width: 580px;
    text-align: left;
}

/* ── Business Health Domain Cards & general elements ────────────────────── */
.date-badge {
    background: #EEF2FF;
    color: #4F46E5;
    border: 1px solid #C7D2FE;
    border-radius: 4px;
    padding: 2px 6px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 0.82rem;
    font-weight: 600;
}

.domain-card {
    min-height: 130px !important;
    text-align: left !important;
    padding: 20px !important;
    border-left-width: 5px !important;
}

.domain-card-strong {
    border-left-color: #16A34A !important;
}
.domain-card-strong .domain-status { color: #16A34A; }

.domain-card-stable {
    border-left-color: #2563EB !important;
}
.domain-card-stable .domain-status { color: #2563EB; }

.domain-card-watch {
    border-left-color: #F59E0B !important;
}
.domain-card-watch .domain-status { color: #F59E0B; }

.domain-card-risk {
    border-left-color: #DC2626 !important;
}
.domain-card-risk .domain-status { color: #DC2626; }

.domain-card-insufficient {
    border-left-color: #64748B !important;
}
.domain-card-insufficient .domain-status { color: #64748B; }

/* ── Insights Page Components ───────────────────────────────────────────── */
.insight-card {
    margin-bottom: 16px !important;
    padding: 24px !important;
}
.telemetry-box {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 0.78rem;
    background: #F8FAFC;
    border: 1px solid #E5E7EB;
    padding: 8px 12px;
    border-radius: 6px;
    color: #475569;
    margin-top: 10px;
}
.action-box {
    background: #EEF2FF;
    border-left: 4px solid #4F46E5;
    padding: 12px;
    border-radius: 0 8px 8px 0;
    margin-top: 10px;
    font-size: 0.86rem;
    line-height: 1.5;
    color: #312E81;
}

/* ── Executive Reports Center Components ────────────────────────────────── */
.brief-container {
    background: #FFFFFF;
    border-left: 4px solid #4F46E5;
    border-radius: 0 8px 8px 0;
    padding: 18px 20px;
    margin-bottom: 20px;
    border-top: 1px solid #E5E7EB;
    border-right: 1px solid #E5E7EB;
    border-bottom: 1px solid #E5E7EB;
}
.brief-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #172033;
    margin-bottom: 6px;
}
.brief-body {
    font-size: 0.92rem;
    color: #475569;
    line-height: 1.5;
}

.card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 16px;
    margin: 16px 0;
}
.report-card {
    padding: 20px !important;
}
.report-card-strong { border: 1px solid #16A34A !important; }
.report-card-stable { border: 1px solid #2563EB !important; }
.report-card-watch  { border: 1px solid #F59E0B !important; }
.report-card-risk   { border: 1px solid #DC2626 !important; }
.report-card-insufficient { border: 1px solid #64748B !important; }

.card-label {
    font-size: 0.78rem;
    font-weight: 600;
    color: #64748B;
    text-transform: uppercase;
    margin-bottom: 4px;
    letter-spacing: 0.02em;
}
.card-value {
    font-size: 1.35rem;
    font-weight: 700;
    color: #172033;
    margin-bottom: 2px;
}
.card-meta {
    font-size: 0.72rem;
    color: #8C9BAE;
}

/* ── Coming Soon Interactive Demo Card ───────────────────────────────────── */
.coming-soon-container {
    display: flex;
    justify-content: center;
    align-items: center;
    margin-top: 4rem; /* Generous whitespace above it */
    margin-bottom: 2rem;
    width: 100%;
}
.coming-soon-card {
    background-color: #FFFFFF !important;
    border: 1px solid #E5E7EB !important;
    border-radius: 16px !important;
    padding: 24px !important;
    max-width: 650px !important;
    width: 100% !important;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03) !important;
    text-align: center !important;
    box-sizing: border-box !important;
}
.coming-soon-header {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    margin-bottom: 12px;
}
.coming-soon-icon {
    font-size: 1.1rem;
    color: #4F46E5 !important; /* Small indigo accent icon */
}
.coming-soon-badge {
    background-color: #EEF2FF !important; /* light indigo background */
    color: #4F46E5 !important; /* indigo text */
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    padding: 2px 8px !important;
    border-radius: 9999px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}
.coming-soon-title {
    font-size: 1.25rem !important;
    font-weight: 600 !important;
    color: #172033 !important;
    margin: 8px 0 10px 0 !important;
}
.coming-soon-desc {
    font-size: 0.88rem !important;
    color: #64748B !important;
    line-height: 1.5 !important;
    margin: 0 !important;
}
</style>
"""


def inject_global_css() -> None:
    """Inject the shared light enterprise CSS into the current Streamlit page.

    Call this once near the top of every page that renders custom HTML
    components (.metric-card, .status-badge, .custom-divider, etc.).
    Pages that rely solely on native Streamlit widgets do not require
    this call, but calling it is harmless.
    """
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)
