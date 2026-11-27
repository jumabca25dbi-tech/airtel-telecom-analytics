import base64
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st

px.defaults.template = "plotly_white"

# ---------------------------------------------------------
# FORCE LIGHT THEME (no separate config file needed)
# Writes .streamlit/config.toml on first run if it is missing.
# After the very first run, restart the app once (Ctrl+C, streamlit run app.py).
# ---------------------------------------------------------
_THEME_CFG = """[theme]
base = "light"
primaryColor = "#e31e24"
backgroundColor = "#eef1f5"
secondaryBackgroundColor = "#ffffff"
textColor = "#111827"
"""
try:
    _cfg_path = Path.cwd() / ".streamlit" / "config.toml"
    if not _cfg_path.exists():
        _cfg_path.parent.mkdir(parents=True, exist_ok=True)
        _cfg_path.write_text(_THEME_CFG, encoding="utf-8")
    st._config.set_option("theme.base", "light")
except Exception:
    pass

# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="Airtel Telecom Analytics | Revenue",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "airtel.db"
HERO_IMG_PATH = Path(__file__).resolve().parent / "assets" / "airtel_hero.png"
START_DATE = "2025-01-01"
END_DATE = "2025-06-30"

AIRTEL_RED = "#e31e24"
AIRTEL_DARK_RED = "#9e0b12"
AIRTEL_MID_RED = "#e8383e"
AIRTEL_SOFT_RED = "#f7a8ab"
INK_DARK = "#111827"
INK_SUB = "#4b5563"
CHART_FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'


@st.cache_data
def get_base64_image(img_path_str: str) -> str:
    p = Path(img_path_str)
    if not p.exists():
        return ""
    mime = "image/jpeg" if p.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
    encoded = base64.b64encode(p.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


HERO_IMG_SRC = get_base64_image(str(HERO_IMG_PATH))

# ---------------------------------------------------------
# CSS
# ---------------------------------------------------------
st.markdown(
    f"""
<style>
    .stApp {{
        background: #eef1f5;
        color: {INK_DARK};
        font-family: {CHART_FONT};
        overflow-x: hidden;
    }}
    [data-testid="stAppViewContainer"] {{
        background: #eef1f5;
    }}
    /* Keep the header (it holds the sidebar open/close button) but make it invisible */
    [data-testid="stHeader"] {{
        background: transparent !important;
        height: 0 !important;
        min-height: 0 !important;
    }}
    /* hide only the right-side actions (deploy / menu); keep stToolbar because it holds the sidebar open button */
    [data-testid="stToolbarActions"],
    [data-testid="stAppDeployButton"],
    [data-testid="stMainMenu"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"] {{
        display: none !important;
    }}
    [data-testid="stToolbar"] {{
        display: flex !important;
        visibility: visible !important;
        background: transparent !important;
    }}
    /* Sidebar open button (shown when the sidebar is collapsed) */
    [data-testid="stExpandSidebarButton"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"] {{
        display: flex !important;
        visibility: visible !important;
        position: fixed !important;
        top: 10px !important;
        left: 10px !important;
        z-index: 999999 !important;
        background: {AIRTEL_RED} !important;
        border: 1px solid {AIRTEL_DARK_RED} !important;
        border-radius: 10px !important;
        padding: 2px 4px !important;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.25) !important;
    }}
    [data-testid="stExpandSidebarButton"] *,
    [data-testid="stSidebarCollapsedControl"] *,
    [data-testid="collapsedControl"] * {{
        color: #ffffff !important;
        fill: #ffffff !important;
    }}
    /* Sidebar close button (inside the sidebar) */
    [data-testid="stSidebarCollapseButton"] button,
    [data-testid="stSidebarHeader"] button {{
        background: rgba(255, 255, 255, 0.18) !important;
        border-radius: 8px !important;
    }}
    [data-testid="stSidebarCollapseButton"] *,
    [data-testid="stSidebarHeader"] button * {{
        color: #ffffff !important;
        fill: #ffffff !important;
    }}
    .block-container {{
        padding-top: 0.65rem !important;
        padding-bottom: 1rem !important;
        padding-left: 0.95rem !important;
        padding-right: 0.95rem !important;
        max-width: 100% !important;
    }}
    div[data-testid="stVerticalBlock"] {{
        gap: 0.55rem !important;
    }}

    p, span, label, div, li {{
        color: {INK_DARK};
    }}

    /* Top Header */
    .top-header {{
        background: #ffffff;
        border: 1px solid #d8dee6;
        border-radius: 12px;
        padding: 8px 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
        height: 56px;
        box-sizing: border-box;
    }}
    .brand-group {{
        display: flex;
        align-items: center;
        gap: 10px;
    }}
    .airtel-logo {{
        background: {AIRTEL_RED};
        color: #ffffff !important;
        font-weight: 900;
        font-size: 0.88rem;
        padding: 4px 10px;
        border-radius: 999px;
    }}
    .app-title {{
        font-size: 1rem;
        font-weight: 850;
        color: {INK_DARK} !important;
        line-height: 1.2;
    }}
    .app-sub {{
        font-size: 0.72rem;
        color: {INK_SUB} !important;
        font-weight: 500;
    }}
    .meta-pill {{
        background: #fff1f2;
        border: 1px solid #fecdd3;
        color: {AIRTEL_DARK_RED} !important;
        font-size: 0.72rem;
        font-weight: 700;
        padding: 4px 11px;
        border-radius: 999px;
    }}

    /* View switcher */
    div[data-testid="stRadio"] {{
        background: #ffffff;
        border: 1px solid #d8dee6;
        border-radius: 12px;
        padding: 6px 10px;
        height: 56px;
        display: flex;
        align-items: center;
        justify-content: center;
        box-sizing: border-box;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
    }}
    div[data-testid="stRadio"] > div {{
        background: #f8fafc;
        padding: 3px;
        border-radius: 999px;
        border: 1px solid #cbd5e1;
        gap: 4px;
    }}
    div[data-testid="stRadio"] label {{
        padding: 4px 16px !important;
        border-radius: 999px !important;
        font-size: 0.8rem !important;
        font-weight: 700 !important;
        margin: 0 !important;
    }}
    div[data-testid="stRadio"] label[data-checked="true"] {{
        background: {AIRTEL_RED} !important;
        color: #ffffff !important;
    }}
    div[data-testid="stRadio"] label[data-checked="true"] p,
    div[data-testid="stRadio"] label[data-checked="true"] span {{
        color: #ffffff !important;
    }}

    /* Per-chart filter popover button */
    div[data-testid="stPopover"] button {{
        padding: 2px 10px !important;
        min-height: 26px !important;
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        border: 1px solid {AIRTEL_DARK_RED} !important;
        border-radius: 999px !important;
        background: {AIRTEL_RED} !important;
    }}
    div[data-testid="stPopover"] button,
    div[data-testid="stPopover"] button * {{
        color: #ffffff !important;
    }}

    /* Filter popover body: red panel, all letters white */
    div[data-testid="stPopoverBody"] {{
        background: linear-gradient(180deg, {AIRTEL_RED} 0%, {AIRTEL_DARK_RED} 100%) !important;
        border: 1px solid {AIRTEL_DARK_RED} !important;
    }}
    div[data-testid="stPopoverBody"] * {{
        color: #ffffff !important;
    }}
    div[data-testid="stPopoverBody"] label p {{
        font-size: 0.68rem !important;
        font-weight: 800 !important;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }}
    div[data-testid="stPopoverBody"] div[data-baseweb="select"] > div {{
        background: rgba(255, 255, 255, 0.15) !important;
        border: 1px solid rgba(255, 255, 255, 0.35) !important;
        border-radius: 8px !important;
    }}

    /* Dropdown option lists (sidebar + popovers): dark red, white letters */
    ul[role="listbox"] {{
        background: {AIRTEL_DARK_RED} !important;
    }}
    ul[role="listbox"] li,
    ul[role="listbox"] li * {{
        color: #ffffff !important;
        font-size: 0.8rem !important;
    }}
    ul[role="listbox"] li:hover,
    ul[role="listbox"] li[aria-selected="true"] {{
        background: {AIRTEL_RED} !important;
    }}

    /* Table toolbar (download / search / fullscreen) */
    [data-testid="stElementToolbar"],
    [data-testid="stElementToolbar"] > div {{
        background: {AIRTEL_RED} !important;
        border-radius: 8px !important;
    }}
    [data-testid="stElementToolbar"] {{
        border: 1px solid {AIRTEL_DARK_RED} !important;
        box-shadow: 0 2px 6px rgba(15, 23, 42, 0.18) !important;
    }}
    [data-testid="stElementToolbar"] button {{
        background: transparent !important;
        color: #ffffff !important;
    }}
    [data-testid="stElementToolbar"] button:hover {{
        background: rgba(255, 255, 255, 0.22) !important;
    }}
    [data-testid="stElementToolbar"] svg {{
        color: #ffffff !important;
        fill: currentColor !important;
    }}
    [data-testid="stElementToolbar"] input {{
        color: #ffffff !important;
        background: rgba(255, 255, 255, 0.15) !important;
        border: 1px solid rgba(255, 255, 255, 0.4) !important;
        border-radius: 6px !important;
    }}

    /* ---- Filter dropdowns: force red theme + white letters (all Streamlit versions) ---- */
    [data-testid="stSidebar"] [data-baseweb="select"],
    div[data-testid="stPopoverBody"] [data-baseweb="select"] {{
        background: #111827 !important;
        border: 1px solid rgba(255, 255, 255, 0.4) !important;
        border-radius: 8px !important;
    }}
    [data-testid="stSidebar"] [data-baseweb="select"] div,
    div[data-testid="stPopoverBody"] [data-baseweb="select"] div {{
        background: transparent !important;
        color: #ffffff !important;
    }}
    [data-testid="stSidebar"] [data-baseweb="select"] svg,
    div[data-testid="stPopoverBody"] [data-baseweb="select"] svg {{
        fill: #ffffff !important;
        color: #ffffff !important;
    }}
    /* Dropdown option lists (sidebar + chart filters): black bg, WHITE letters */
    ul[role="listbox"],
    ul[role="listbox"] *,
    div[role="listbox"],
    div[role="listbox"] *,
    [data-testid="stSelectboxVirtualDropdown"],
    [data-testid="stSelectboxVirtualDropdown"] *,
    [data-baseweb="menu"],
    [data-baseweb="menu"] *,
    li[role="option"],
    li[role="option"] *,
    div[role="option"],
    div[role="option"] * {{
        background-color: #111827 !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        font-size: 0.8rem !important;
        opacity: 1 !important;
    }}
    li[role="option"]:hover,
    li[role="option"]:hover *,
    div[role="option"]:hover,
    div[role="option"]:hover *,
    li[role="option"][aria-selected="true"],
    li[role="option"][aria-selected="true"] * {{
        background-color: #374151 !important;
    }}
    /* selected value + typed text inside the sidebar select boxes */
    [data-testid="stSidebar"] [data-baseweb="select"] input {{
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        caret-color: #ffffff !important;
    }}

    /* ---- Select boxes (sidebar + chart filters): BLACK box, WHITE letters ----
       Targets the stSelectbox widget itself (works regardless of baseweb markup). */
    [data-testid="stSidebar"] [data-testid="stSelectbox"] > div:not([data-testid="stWidgetLabel"]),
    [data-testid="stSidebar"] [data-testid="stSelectbox"] > div:not([data-testid="stWidgetLabel"]) *,
    div[data-testid="stPopoverBody"] [data-testid="stSelectbox"] > div:not([data-testid="stWidgetLabel"]),
    div[data-testid="stPopoverBody"] [data-testid="stSelectbox"] > div:not([data-testid="stWidgetLabel"]) * {{
        background-color: #111827 !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        opacity: 1 !important;
    }}
    [data-testid="stSidebar"] [data-testid="stSelectbox"] > div:not([data-testid="stWidgetLabel"]),
    div[data-testid="stPopoverBody"] [data-testid="stSelectbox"] > div:not([data-testid="stWidgetLabel"]) {{
        border-radius: 8px !important;
        border: 1px solid rgba(255, 255, 255, 0.45) !important;
    }}
    [data-testid="stSidebar"] [data-testid="stSelectbox"] svg,
    div[data-testid="stPopoverBody"] [data-testid="stSelectbox"] svg {{
        fill: #ffffff !important;
        color: #ffffff !important;
    }}
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"],
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] * {{
        background-color: transparent !important;
        color: #ffffff !important;
    }}

    /* Map card */
    div[data-testid="stDeckGlJsonChart"] {{
        border: 1px solid #d8dee6;
        border-radius: 0 0 12px 12px;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
    }}

    /* Hero */
    .hero-img-card {{
        width: 100%;
        height: 336px;
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #d8dee6;
        background: #ffffff;
        box-sizing: border-box;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
    }}
    .hero-img-card img {{
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
    }}
    .after-hero-spacer {{
        height: 14px;
        width: 100%;
    }}

    /* KPI cards */
    .kpi-card {{
        background: #ffffff;
        border-top: 1px solid #d8dee6;
        border-right: 1px solid #d8dee6;
        border-bottom: 1px solid #d8dee6;
        border-left: 4px solid {AIRTEL_RED};
        border-radius: 12px;
        overflow: hidden;
        padding: 12px 16px;
        width: 100%;
        box-sizing: border-box;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        height: 100px;
        margin-bottom: 14px;
    }}
    .kpi-text-col {{
        display: flex;
        flex-direction: column;
        justify-content: center;
        gap: 3px;
        min-width: 0;
    }}
    .kpi-label {{
        font-size: 0.68rem;
        font-weight: 800;
        letter-spacing: 0.05em;
        color: {INK_SUB} !important;
        text-transform: uppercase;
        line-height: 1.15;
    }}
    .kpi-num {{
        font-size: 1.26rem;
        font-weight: 900;
        color: {INK_DARK} !important;
        line-height: 1.2;
        white-space: nowrap;
    }}
    .kpi-sub {{
        font-size: 0.72rem;
        font-weight: 600;
        color: {AIRTEL_DARK_RED} !important;
        line-height: 1.2;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .kpi-icon {{
        width: 38px;
        height: 38px;
        border-radius: 10px;
        background: #fff1f2;
        border: 1px solid #fecdd3;
        color: {AIRTEL_RED} !important;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 900;
        font-size: 0.95rem;
        flex-shrink: 0;
    }}
    .right-meta-strip {{
        background: #ffffff;
        border: 1px solid #d8dee6;
        border-radius: 12px;
        padding: 12px 18px;
        width: 100%;
        box-sizing: border-box;
        height: 88px;
        margin-top: 2px;
        margin-bottom: 14px;
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        align-items: center;
        gap: 12px;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
    }}
    .meta-item {{
        display: flex;
        flex-direction: column;
        gap: 3px;
    }}
    .meta-val {{
        font-size: 1.04rem;
        font-weight: 850;
        color: {INK_DARK} !important;
        line-height: 1.2;
    }}

    /* Chart card */
    div[data-testid="stPlotlyChart"] {{
        background: #ffffff;
        border: 1px solid #d8dee6;
        border-radius: 12px;
        padding: 4px 6px;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
    }}

    /* Bottom strip */
    .insight-bar {{
        background: #ffffff;
        border: 1px solid #d8dee6;
        border-left: 4px solid {AIRTEL_RED};
        border-radius: 10px;
        padding: 7px 14px;
        font-size: 0.75rem;
        font-weight: 600;
        color: {INK_DARK} !important;
    }}
    .footer-note {{
        font-size: 0.68rem;
        color: {INK_SUB} !important;
        padding: 0 4px;
    }}

    /* Sidebar */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {AIRTEL_RED} 0%, {AIRTEL_DARK_RED} 100%);
        min-width: 230px !important;
        max-width: 245px !important;
    }}
    [data-testid="stSidebar"] > div:first-child {{
        padding: 0.8rem 0.75rem !important;
    }}
    [data-testid="stSidebar"] * {{
        color: #ffffff !important;
    }}
    [data-testid="stSidebar"] .stSelectbox {{
        margin-bottom: 8px !important;
    }}
    [data-testid="stSidebar"] .stSelectbox label {{
        font-size: 0.68rem !important;
        font-weight: 800 !important;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        margin-bottom: 2px !important;
    }}
    [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div {{
        background: rgba(255, 255, 255, 0.15) !important;
        border: 1px solid rgba(255, 255, 255, 0.35) !important;
        border-radius: 8px !important;
        min-height: 32px !important;
        font-size: 0.8rem !important;
    }}
    [data-testid="stSidebar"] button {{
        background: rgba(255, 255, 255, 0.18) !important;
        border: 1px solid rgba(255, 255, 255, 0.4) !important;
        border-radius: 8px !important;
        padding: 4px 10px !important;
        font-size: 0.76rem !important;
        font-weight: 700 !important;
        margin-bottom: 10px !important;
    }}
    .sb-summary {{
        background: rgba(0, 0, 0, 0.24);
        border: 1px solid rgba(255, 255, 255, 0.25);
        border-radius: 10px;
        padding: 10px 12px;
        margin-top: 10px;
    }}
    .sb-sum-lbl {{
        font-size: 0.65rem;
        font-weight: 800;
        letter-spacing: 0.05em;
        opacity: 0.85;
        text-transform: uppercase;
    }}
    .sb-sum-name {{
        font-size: 0.88rem;
        font-weight: 850;
        margin: 3px 0 8px 0;
    }}
    .sb-sum-row {{
        display: flex;
        justify-content: space-between;
        font-size: 0.78rem;
        padding: 2px 0;
    }}
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# LOAD AND PREPARE DATA
# ---------------------------------------------------------
@st.cache_data
def load_data(db_path):
    if not Path(db_path).exists():
        raise FileNotFoundError(
            f"Database not found: {db_path}. Put airtel.db inside data/raw/."
        )

    conn = sqlite3.connect(db_path)

    customers = pd.read_sql_query(
        """
        SELECT
            c.customer_id,
            c.activation_date,
            c.circle_id,
            c.connection_type,
            c.current_plan_id,
            c.arpu_inr AS stated_arpu,
            c.ab_group,
            c.is_churned,
            ci.circle_name,
            ci.region,
            p.plan_name,
            p.plan_type
        FROM customers c
        LEFT JOIN circles ci ON c.circle_id = ci.circle_id
        LEFT JOIN plans p ON c.current_plan_id = p.plan_id
    """,
        conn,
    )

    recharges = pd.read_sql_query(
        """
        SELECT
            recharge_id,
            customer_id,
            recharge_date,
            amount_inr,
            plan_id,
            channel,
            txn_type
        FROM recharges
        WHERE recharge_date BETWEEN ? AND ?
    """,
        conn,
        params=(START_DATE, END_DATE),
    )

    plans = pd.read_sql_query(
        """
        SELECT plan_id, plan_name, plan_type, price_inr,
               validity_days, data_quota, ott_benefit, is_5g
        FROM plans
    """,
        conn,
    )

    conn.close()

    recharges["recharge_date"] = pd.to_datetime(
        recharges["recharge_date"], errors="coerce"
    )

    revenue = recharges.groupby("customer_id", as_index=False).agg(
        received_revenue_6m=("amount_inr", "sum"),
        recharge_count=("amount_inr", "size"),
        avg_recharge_amount=("amount_inr", "mean"),
    )

    df = customers.merge(revenue, on="customer_id", how="left")
    df["received_revenue_6m"] = df["received_revenue_6m"].fillna(0)
    df["recharge_count"] = df["recharge_count"].fillna(0).astype(int)
    df["avg_recharge_amount"] = df["avg_recharge_amount"].fillna(0)
    df["received_arpu_monthly"] = df["received_revenue_6m"] / 6
    df["stated_arpu"] = pd.to_numeric(df["stated_arpu"], errors="coerce")
    df["revenue_difference"] = df["received_arpu_monthly"] - df["stated_arpu"]

    df["revenue_decile"] = pd.qcut(
        df["received_arpu_monthly"].rank(method="first", ascending=False),
        10,
        labels=[f"D{i}" for i in range(1, 11)],
    )

    return df, recharges, plans


try:
    df, recharge_df, plans_df = load_data(str(DB_PATH))
except Exception as error:
    st.error(f"Unable to load Airtel data: {error}")
    st.info("Expected folder structure: app.py and data/raw/airtel.db")
    st.stop()


# ---------------------------------------------------------
# SIDEBAR (GLOBAL FILTERS)
# ---------------------------------------------------------
with st.sidebar:
    st.markdown(
        "<div style='font-size:0.95rem;font-weight:850;margin-bottom:6px;'>Filters</div>",
        unsafe_allow_html=True,
    )

    if st.button("Reset filters", use_container_width=True, key="reset_sb_btn"):
        st.session_state["sb_conn"] = "All"
        st.session_state["sb_reg"] = "All"
        st.session_state["sb_plan"] = "All"
        st.rerun()

    conn_opts = ["All"] + sorted(
        df["connection_type"].dropna().astype(str).unique().tolist()
    )
    reg_opts = ["All"] + sorted(df["region"].dropna().astype(str).unique().tolist())
    plan_opts = ["All"] + sorted(
        df["plan_name"].dropna().astype(str).unique().tolist()
    )

    sel_conn = st.selectbox("Connection Type", conn_opts, key="sb_conn")
    sel_reg = st.selectbox("Region", reg_opts, key="sb_reg")
    sel_plan = st.selectbox("Plan", plan_opts, key="sb_plan")

    st.markdown(
        """
        <div style='margin-top:8px;'>
            <div style='font-size:0.66rem;font-weight:800;letter-spacing:0.04em;'>REVENUE PERIOD</div>
            <div style='display:flex;justify-content:space-between;font-size:0.74rem;font-weight:700;margin-top:3px;'>
                <span>Jan 2025</span><span>Jun 2025</span>
            </div>
            <div style='height:4px;background:rgba(255,255,255,0.9);border-radius:999px;margin-top:4px;'></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

f_df = df.copy()
if sel_conn != "All":
    f_df = f_df[f_df["connection_type"] == sel_conn]
if sel_reg != "All":
    f_df = f_df[f_df["region"] == sel_reg]
if sel_plan != "All":
    f_df = f_df[f_df["plan_name"] == sel_plan]

f_cust_ids = set(f_df["customer_id"].unique())
f_rech = recharge_df[recharge_df["customer_id"].isin(f_cust_ids)].copy()

with st.sidebar:
    sel_label = (
        f"{sel_reg} • {sel_conn}"
        if (sel_reg != "All" or sel_conn != "All")
        else "All circles & connections"
    )
    st.markdown(
        f"""
        <div class="sb-summary">
            <div class="sb-sum-lbl">Current Selection</div>
            <div class="sb-sum-name">{sel_label}</div>
            <div class="sb-sum-row"><span>Subscribers</span><b>{f_df['customer_id'].nunique():,}</b></div>
            <div class="sb-sum-row"><span>6M Revenue</span><b>₹{f_df['received_revenue_6m'].sum():,.0f}</b></div>
            <div class="sb-sum-row"><span>Txns</span><b>{len(f_rech):,}</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
def style_fig(fig, title_text, height=215, margins=None):
    if margins is None:
        margins = dict(t=42, b=32, l=46, r=14)
    fig.update_layout(
        title=dict(
            text=f"<b>{title_text}</b>",
            font=dict(family=CHART_FONT, color=INK_DARK, size=12),
            x=0.01,
            y=0.97,
            xanchor="left",
            yanchor="top",
        ),
        height=height,
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(family=CHART_FONT, color=INK_DARK, size=10),
        legend=dict(font=dict(family=CHART_FONT, color=INK_DARK, size=9.5)),
        margin=margins,
    )
    fig.update_xaxes(
        tickfont=dict(family=CHART_FONT, color=INK_DARK, size=9.5),
        title_font=dict(family=CHART_FONT, color=INK_DARK, size=9.5),
        showline=True,
        linecolor="#d8dee6",
        gridcolor="#f1f5f9",
    )
    fig.update_yaxes(
        tickfont=dict(family=CHART_FONT, color=INK_DARK, size=9.5),
        title_font=dict(family=CHART_FONT, color=INK_DARK, size=9.5),
        showline=True,
        linecolor="#d8dee6",
        gridcolor="#f1f5f9",
    )
    return fig


def chart_filter(key, base_df, base_rech, extra=()):
    """Per-chart filter (applied on top of the sidebar filter).
    Returns (filtered_df, filtered_recharges).
    extra: "channel" and/or "txn" for recharge-level filters."""
    with st.popover("⚙ Filter", use_container_width=True):
        conn = st.selectbox(
            "Connection Type",
            ["All"] + sorted(base_df["connection_type"].dropna().astype(str).unique()),
            key=f"{key}_conn",
        )
        reg = st.selectbox(
            "Region",
            ["All"] + sorted(base_df["region"].dropna().astype(str).unique()),
            key=f"{key}_reg",
        )
        plan = st.selectbox(
            "Plan",
            ["All"] + sorted(base_df["plan_name"].dropna().astype(str).unique()),
            key=f"{key}_plan",
        )
        chan = txn = "All"
        if "channel" in extra:
            chan = st.selectbox(
                "Channel",
                ["All"] + sorted(base_rech["channel"].dropna().astype(str).unique()),
                key=f"{key}_chan",
            )
        if "txn" in extra:
            txn = st.selectbox(
                "Txn Type",
                ["All"] + sorted(base_rech["txn_type"].dropna().astype(str).unique()),
                key=f"{key}_txn",
            )

    d = base_df
    if conn != "All":
        d = d[d["connection_type"] == conn]
    if reg != "All":
        d = d[d["region"] == reg]
    if plan != "All":
        d = d[d["plan_name"] == plan]

    rc = base_rech[base_rech["customer_id"].isin(set(d["customer_id"]))]
    if chan != "All":
        rc = rc[rc["channel"] == chan]
    if txn != "All":
        rc = rc[rc["txn_type"] == txn]
    return d, rc


# Approximate circle coordinates (lat, lon) for the heatmap.
# Matched against circles.circle_name first, then circles.region.
CIRCLE_COORDS = {
    "Andhra Pradesh": (16.5062, 80.6480),
    "Assam": (26.1445, 91.7362),
    "Bihar": (25.5941, 85.1376),
    "Delhi": (28.6139, 77.2090),
    "Gujarat": (23.0225, 72.5714),
    "Haryana": (29.0588, 76.0856),
    "Himachal Pradesh": (31.1048, 77.1734),
    "Jammu and Kashmir": (34.0837, 74.7973),
    "Karnataka": (12.9716, 77.5946),
    "Kerala": (9.9312, 76.2673),
    "Kolkata": (22.5726, 88.3639),
    "Madhya Pradesh": (23.2599, 77.4126),
    "Maharashtra": (19.0760, 72.8777),
    "Mumbai": (19.0760, 72.8777),
    "North East": (25.5788, 91.8933),
    "Odisha": (20.2961, 85.8245),
    "Punjab": (30.7333, 76.7794),
    "Rajasthan": (26.9124, 75.7873),
    "Tamil Nadu": (13.0827, 80.2707),
    "Uttar Pradesh": (26.8467, 80.9462),
    "Uttarakhand": (30.3165, 78.0322),
    "West Bengal": (22.5726, 88.3639),
}


# ---------------------------------------------------------
# TOP BAR + VIEW SWITCHER
# ---------------------------------------------------------
h1, h2, h3 = st.columns([2.2, 1.3, 1.1], gap="small")
with h1:
    st.markdown(
        """
        <div class="top-header">
            <div class="brand-group">
                <span class="airtel-logo">airtel</span>
                <div>
                    <div class="app-title">Airtel Telecom Analytics</div>
                    <div class="app-sub">Revenue & Plan Analysis • Jan–Jun 2025 • 22,000 records</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with h2:
    active_view = st.radio(
        "View Mode",
        ["Overview", "Details"],
        horizontal=True,
        label_visibility="collapsed",
        key="view_mode_radio",
    )
with h3:
    st.markdown(
        """
        <div class="top-header" style="justify-content:flex-end;gap:8px;">
            <span class="meta-pill">Jan–Jun 2025</span>
            <span class="meta-pill">Domain B • Revenue</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------
# KPI METRICS (sidebar filter only)
# ---------------------------------------------------------
tot_rev = f_df["received_revenue_6m"].sum()
tot_subs = f_df["customer_id"].nunique()
avg_arpu_m = tot_rev / tot_subs / 6 if tot_subs else 0.0
avg_stated = f_df["stated_arpu"].mean() if not f_df.empty else 0.0
arpu_gap = avg_arpu_m - avg_stated
plan_cnt = f_df["plan_name"].nunique()
top_chan = (
    f_rech.groupby("channel")["amount_inr"].sum().idxmax()
    if (not f_rech.empty and f_rech["channel"].notna().any())
    else "N/A"
)


# ---------------------------------------------------------
# OVERVIEW PAGE
# ---------------------------------------------------------
if active_view == "Overview":
    hero_col, kpi_col = st.columns([1.05, 1.35], gap="small")

    with hero_col:
        if HERO_IMG_SRC:
            st.markdown(
                f'<div class="hero-img-card"><img src="{HERO_IMG_SRC}" alt="Airtel Hero" /></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div class='hero-img-card' style='display:flex;align-items:center;justify-content:center;font-size:0.8rem;'>Place <b>airtel_hero.png</b> inside <b>assets/</b></div>",
                unsafe_allow_html=True,
            )

    with kpi_col:
        ka, kb = st.columns(2, gap="small")
        with ka:
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-text-col">
                        <div class="kpi-label">6M Received Revenue</div>
                        <div class="kpi-num">₹{tot_rev:,.0f}</div>
                        <div class="kpi-sub">{len(f_rech):,} recharge txns</div>
                    </div>
                    <div class="kpi-icon">₹</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with kb:
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-text-col">
                        <div class="kpi-label">Received / Sub / Mo</div>
                        <div class="kpi-num">₹{avg_arpu_m:,.2f}</div>
                        <div class="kpi-sub">Gap vs stated: ₹{arpu_gap:+,.2f}</div>
                    </div>
                    <div class="kpi-icon">↗</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        kc, kd = st.columns(2, gap="small")
        with kc:
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-text-col">
                        <div class="kpi-label">Unique Subscribers</div>
                        <div class="kpi-num">{tot_subs:,}</div>
                        <div class="kpi-sub">{plan_cnt} active plans</div>
                    </div>
                    <div class="kpi-icon">👥</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with kd:
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-text-col">
                        <div class="kpi-label">Top Channel</div>
                        <div class="kpi-num">{top_chan}</div>
                        <div class="kpi-sub">Avg txn ₹{(f_rech['amount_inr'].mean() if not f_rech.empty else 0):,.0f}</div>
                    </div>
                    <div class="kpi-icon">⚡</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            f"""
            <div class="right-meta-strip">
                <div class="meta-item">
                    <div class="kpi-label">Avg Stated ARPU</div>
                    <div class="meta-val">₹{avg_stated:,.2f}</div>
                </div>
                <div class="meta-item">
                    <div class="kpi-label">Active Period</div>
                    <div class="meta-val">6 Months</div>
                </div>
                <div class="meta-item">
                    <div class="kpi-label">Data Source</div>
                    <div class="meta-val">airtel.db</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="after-hero-spacer"></div>', unsafe_allow_html=True)

    # ===================== ROW 1 =====================
    r1a, r1b, r1c = st.columns(3, gap="small")

    # ---------- Chart 1: Particle Network (hub filter) ----------
    with r1a:
        hub_names = [
            "Prepaid Core",
            "Airtel App",
            "Postpaid Hub",
            "UPI & AutoPay",
            "5G & OTT Plans",
        ]
        with st.popover("⚙ Filter", use_container_width=True):
            sel_hubs = st.multiselect(
                "Hubs", hub_names, default=hub_names, key="c1_hubs"
            )
        keep = [i for i, n in enumerate(hub_names) if n in sel_hubs]

        if keep:
            rng = np.random.default_rng(42)
            hubs_x = np.array([0.22, 0.52, 0.80, 0.36, 0.68])
            hubs_y = np.array([0.72, 0.48, 0.75, 0.25, 0.28])

            px_list, py_list, ps_list, pc_list, pt_list, ph_list = (
                [], [], [], [], [], [],
            )
            palette = [AIRTEL_RED, AIRTEL_DARK_RED, AIRTEL_SOFT_RED, "#334155"]
            for idx, (hx, hy) in enumerate(zip(hubs_x, hubs_y)):
                n_pts = 14
                angles = rng.uniform(0, 2 * np.pi, n_pts)
                radii = rng.uniform(0.05, 0.16, n_pts)
                xs = np.clip(hx + radii * np.cos(angles), 0.04, 0.96)
                ys = np.clip(hy + radii * np.sin(angles), 0.06, 0.92)
                for j in range(n_pts):
                    size = float(rng.uniform(4.5, 9.0))
                    if idx not in keep:
                        continue
                    px_list.append(float(xs[j]))
                    py_list.append(float(ys[j]))
                    ps_list.append(size)
                    pc_list.append(palette[(idx + j) % len(palette)])
                    pt_list.append(f"{hub_names[idx]} · Node {j + 1}")
                    ph_list.append(idx)

            edge_x, edge_y = [], []
            for a, b in [(0, 1), (1, 2), (0, 3), (1, 3), (1, 4), (2, 4), (3, 4)]:
                if a in keep and b in keep:
                    edge_x.extend([hubs_x[a], hubs_x[b], None])
                    edge_y.extend([hubs_y[a], hubs_y[b], None])
            for i in range(len(px_list)):
                h = ph_list[i]
                edge_x.extend([hubs_x[h], px_list[i], None])
                edge_y.extend([hubs_y[h], py_list[i], None])

            fig1 = go.Figure()
            fig1.add_trace(
                go.Scatter(
                    x=edge_x,
                    y=edge_y,
                    mode="lines",
                    line=dict(color="rgba(227, 30, 36, 0.22)", width=1),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )
            fig1.add_trace(
                go.Scatter(
                    x=px_list,
                    y=py_list,
                    mode="markers",
                    marker=dict(
                        size=ps_list,
                        color=pc_list,
                        opacity=0.88,
                        line=dict(color="#ffffff", width=0.8),
                    ),
                    text=pt_list,
                    hovertemplate="%{text}<extra></extra>",
                    showlegend=False,
                )
            )
            fig1.add_trace(
                go.Scatter(
                    x=hubs_x[keep],
                    y=hubs_y[keep],
                    mode="markers+text",
                    marker=dict(
                        size=16,
                        color=AIRTEL_RED,
                        line=dict(color="#ffffff", width=2),
                    ),
                    text=[hub_names[i].split()[0] for i in keep],
                    textposition="top center",
                    textfont=dict(size=8.5, color=INK_DARK),
                    hovertext=[hub_names[i] for i in keep],
                    hovertemplate="<b>%{hovertext}</b><extra></extra>",
                    showlegend=False,
                )
            )
            style_fig(
                fig1,
                "1. Particle Network",
                height=215,
                margins=dict(t=36, b=10, l=10, r=10),
            )
            fig1.update_xaxes(
                visible=False, range=[0.0, 1.0], showgrid=False, showline=False
            )
            fig1.update_yaxes(
                visible=False, range=[0.0, 1.02], showgrid=False, showline=False
            )
            st.plotly_chart(fig1, use_container_width=True, key="ov_c1")
        else:
            st.caption("Select at least one hub")

    # ---------- Chart 2: Decile share ----------
    with r1b:
        c_df, _ = chart_filter("c2", f_df, f_rech)
        if not c_df.empty:
            g2 = (
                c_df.groupby("revenue_decile", observed=False)["received_revenue_6m"]
                .sum()
                .reset_index()
            )
            tot_d = g2["received_revenue_6m"].sum()
            g2["pct"] = g2["received_revenue_6m"] / tot_d * 100 if tot_d else 0
            fig2 = px.area(g2, x="revenue_decile", y="pct", markers=True)
            fig2.update_traces(
                line_color=AIRTEL_RED,
                fillcolor="rgba(227, 30, 36, 0.20)",
                marker=dict(color=AIRTEL_DARK_RED, size=6),
            )
            style_fig(
                fig2,
                "2. Decile Revenue Share",
                height=215,
                margins=dict(t=38, b=30, l=42, r=12),
            )
            fig2.update_xaxes(title_text="Decile (D1 = Top)")
            fig2.update_yaxes(title_text="Share (%)")
            st.plotly_chart(fig2, use_container_width=True, key="ov_c2")
        else:
            st.caption("No data for this filter")

    # ---------- Chart 3: Revenue by plan ----------
    with r1c:
        c_df, _ = chart_filter("c3", f_df, f_rech)
        g3 = (
            c_df.groupby("plan_name", as_index=False)["received_revenue_6m"]
            .sum()
            .sort_values("received_revenue_6m", ascending=False)
        )
        g3 = g3[g3["received_revenue_6m"] > 0]
        if not g3.empty:
            if len(g3) > 5:
                top5 = g3.head(5).copy()
                other_val = g3.iloc[5:]["received_revenue_6m"].sum()
                g3_plot = pd.concat(
                    [
                        top5,
                        pd.DataFrame(
                            [
                                {
                                    "plan_name": "Other Plans",
                                    "received_revenue_6m": other_val,
                                }
                            ]
                        ),
                    ],
                    ignore_index=True,
                )
            else:
                g3_plot = g3

            fig3 = px.pie(
                g3_plot,
                names="plan_name",
                values="received_revenue_6m",
                hole=0.52,
                color_discrete_sequence=[
                    AIRTEL_RED,
                    AIRTEL_DARK_RED,
                    AIRTEL_MID_RED,
                    "#f4777b",
                    AIRTEL_SOFT_RED,
                    "#cbd5e1",
                ],
            )
            fig3.update_traces(
                textposition="inside",
                textinfo="percent",
                textfont=dict(color="#ffffff", size=10),
            )
            style_fig(
                fig3,
                "3. Revenue by Plan",
                height=215,
                margins=dict(t=36, b=10, l=10, r=10),
            )
            fig3.update_layout(
                showlegend=True,
                legend=dict(
                    orientation="v",
                    yanchor="middle",
                    y=0.45,
                    xanchor="left",
                    x=1.02,
                    font=dict(size=9.5, color=INK_DARK),
                ),
            )
            st.plotly_chart(fig3, use_container_width=True, key="ov_c3")
        else:
            st.caption("No data for this filter")

    # ===================== ROW 2 =====================
    r2a, r2b, r2c = st.columns(3, gap="small")

    # ---------- Chart 4: Connection share ----------
    with r2a:
        c_df, _ = chart_filter("c4", f_df, f_rech)
        if not c_df.empty:
            sh = c_df.groupby("connection_type", as_index=False).agg(
                subs=("customer_id", "nunique"),
                rev=("received_revenue_6m", "sum"),
            )
            s_tot = sh["subs"].sum()
            r_tot = sh["rev"].sum()
            sh["s_pct"] = sh["subs"] / s_tot * 100 if s_tot else 0
            sh["r_pct"] = sh["rev"] / r_tot * 100 if r_tot else 0
            fig4 = go.Figure()
            pal = [AIRTEL_RED, AIRTEL_SOFT_RED, AIRTEL_DARK_RED, "#cbd5e1"]
            for i, row in sh.reset_index(drop=True).iterrows():
                fig4.add_trace(
                    go.Bar(
                        y=["Subscribers", "Revenue"],
                        x=[row["s_pct"], row["r_pct"]],
                        name=str(row["connection_type"]),
                        orientation="h",
                        marker_color=pal[i % len(pal)],
                        text=[f"{row['s_pct']:.1f}%", f"{row['r_pct']:.1f}%"],
                        textposition="inside",
                        textfont=dict(color="#ffffff", size=10),
                    )
                )
            fig4.update_layout(
                barmode="stack",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.01,
                    xanchor="right",
                    x=1.0,
                ),
            )
            style_fig(
                fig4,
                "4. Connection Share",
                height=215,
                margins=dict(t=46, b=28, l=76, r=12),
            )
            st.plotly_chart(fig4, use_container_width=True, key="ov_c4")
        else:
            st.caption("No data for this filter")

    # ---------- Chart 5: Monthly trend ----------
    with r2b:
        _, c_rech = chart_filter("c5", f_df, f_rech, extra=("channel", "txn"))
        if not c_rech.empty:
            m_df = (
                c_rech.dropna(subset=["recharge_date"])
                .assign(ym=c_rech["recharge_date"].dt.to_period("M").astype(str))
                .groupby("ym", as_index=False)["amount_inr"]
                .sum()
                .sort_values("ym")
            )
            fig5 = px.line(m_df, x="ym", y="amount_inr", markers=True)
            fig5.update_traces(
                line_shape="spline",
                line_color=AIRTEL_RED,
                line_width=3,
                marker=dict(color=AIRTEL_DARK_RED, size=7),
            )
            style_fig(
                fig5,
                "5. Monthly Revenue Trend",
                height=215,
                margins=dict(t=38, b=30, l=50, r=12),
            )
            fig5.update_xaxes(title_text="Month")
            fig5.update_yaxes(title_text="Revenue (₹)")
            st.plotly_chart(fig5, use_container_width=True, key="ov_c5")
        else:
            st.caption("No data for this filter")

    # ---------- Chart 6: Funnel ----------
    with r2c:
        c_df, _ = chart_filter("c6", f_df, f_rech)
        if not c_df.empty:
            all_subs_cnt = c_df["customer_id"].nunique()
            active_rech_cnt = int((c_df["recharge_count"] >= 1).sum())
            multi_rech_cnt = int((c_df["recharge_count"] >= 3).sum())
            top_tier_cnt = int(c_df["revenue_decile"].isin(["D1", "D2", "D3"]).sum())

            fig6 = go.Figure(
                go.Funnelarea(
                    values=[
                        all_subs_cnt,
                        active_rech_cnt,
                        multi_rech_cnt,
                        top_tier_cnt,
                    ],
                    labels=["All Subs", "Recharged", "3+ Txns", "Top 30% Rev"],
                    marker=dict(
                        colors=[
                            AIRTEL_RED,
                            AIRTEL_MID_RED,
                            "#f26b70",
                            AIRTEL_SOFT_RED,
                        ],
                        line=dict(color="#ffffff", width=1.5),
                    ),
                    textinfo="value+percent",
                    textfont=dict(color="#ffffff", size=9.5),
                    hoverinfo="label+value+percent",
                )
            )
            style_fig(
                fig6,
                "6. Subscriber Funnel Area",
                height=215,
                margins=dict(t=38, b=12, l=12, r=12),
            )
            fig6.update_layout(showlegend=False)
            st.plotly_chart(fig6, use_container_width=True, key="ov_c6")
        else:
            st.caption("No data for this filter")


# ---------------------------------------------------------
# DETAILS PAGE
# ---------------------------------------------------------
else:
    d1a, d1b = st.columns(2, gap="small")

    # ---------- Chart 7: Channel lollipop ----------
    with d1a:
        _, c_rech = chart_filter("c7", f_df, f_rech, extra=("txn",))
        if not c_rech.empty and c_rech["channel"].notna().any():
            ch = (
                c_rech.dropna(subset=["channel"])
                .groupby("channel", as_index=False)["amount_inr"]
                .sum()
                .sort_values("amount_inr", ascending=True)
            )
            fig7 = go.Figure()
            for _, row in ch.iterrows():
                fig7.add_trace(
                    go.Scatter(
                        x=[0, row["amount_inr"]],
                        y=[row["channel"], row["channel"]],
                        mode="lines",
                        line=dict(color=AIRTEL_SOFT_RED, width=4),
                        showlegend=False,
                        hoverinfo="skip",
                    )
                )
            fig7.add_trace(
                go.Scatter(
                    x=ch["amount_inr"],
                    y=ch["channel"],
                    mode="markers+text",
                    marker=dict(color=AIRTEL_RED, size=11),
                    text=ch["amount_inr"].map(lambda v: f"₹{v:,.0f}"),
                    textposition="middle right",
                    textfont=dict(color=INK_DARK, size=9.5),
                    showlegend=False,
                )
            )
            style_fig(
                fig7,
                "7. Revenue by Recharge Channel",
                height=225,
                margins=dict(t=38, b=30, l=86, r=60),
            )
            st.plotly_chart(fig7, use_container_width=True, key="dt_c7")
        else:
            st.caption("No data for this filter")

    # ---------- Chart 8: Treemap ----------
    with d1b:
        _, c_rech = chart_filter("c8", f_df, f_rech, extra=("channel",))
        if not c_rech.empty and c_rech["txn_type"].notna().any():
            tx = (
                c_rech.dropna(subset=["txn_type"])
                .fillna({"channel": "Unknown"})
                .groupby(["txn_type", "channel"], as_index=False)
                .agg(cnt=("recharge_id", "count"), amt=("amount_inr", "sum"))
            )
            fig8 = px.treemap(
                tx,
                path=["txn_type", "channel"],
                values="cnt",
                color="amt",
                color_continuous_scale=["#ffe4e6", AIRTEL_MID_RED, AIRTEL_DARK_RED],
            )
            fig8.update_traces(
                textinfo="label+value",
                textfont=dict(color=INK_DARK, size=10),
            )
            style_fig(
                fig8,
                "8. Transaction Type & Channel Mix",
                height=225,
                margins=dict(t=36, b=10, l=10, r=10),
            )
            fig8.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig8, use_container_width=True, key="dt_c8")
        else:
            st.caption("No data for this filter")

    d2a, d2b = st.columns(2, gap="small")

    # ---------- Chart 9: Circle Network Heatmap ----------
    with d2a:
        c_df, _ = chart_filter("c9", f_df, f_rech)
        st.markdown(
            "<div style='background:#ffffff;border:1px solid #d8dee6;border-radius:12px 12px 0 0;padding:7px 12px;font-size:0.82rem;font-weight:800;'>9. Neon Network Map (Revenue)</div>",
            unsafe_allow_html=True,
        )
        hm = (
            c_df.dropna(subset=["circle_name"])
            .groupby(["circle_name", "region"], as_index=False, dropna=False)
            .agg(
                subs=("customer_id", "nunique"),
                rev=("received_revenue_6m", "sum"),
            )
        )

        def _coord(row, idx):
            c = CIRCLE_COORDS.get(str(row["circle_name"]))
            if c is None:
                c = CIRCLE_COORDS.get(str(row["region"]))
            return c[idx] if c else None

        hm["lat"] = hm.apply(lambda r: _coord(r, 0), axis=1)
        hm["lon"] = hm.apply(lambda r: _coord(r, 1), axis=1)
        unmatched = int(hm["lat"].isna().sum())
        hm = hm.dropna(subset=["lat", "lon"]).copy()

        if hm.empty:
            st.caption("No circle coordinates matched for this filter")
        else:
            max_rev = hm["rev"].max() or 1
            hm["weight"] = hm["rev"] / max_rev
            hm["size"] = 10 + hm["weight"] * 26
            hm["rev_txt"] = hm["rev"].map(lambda v: f"₹{v:,.0f}")
            hm["subs_txt"] = hm["subs"].map(lambda v: f"{v:,}")

            hm["radius"] = 18000 + hm["weight"] * 50000
            hm["src_lon"] = 78.9629
            hm["src_lat"] = 20.5937

            arc_layer = pdk.Layer(
                "ArcLayer",
                data=hm,
                get_source_position="[src_lon, src_lat]",
                get_target_position="[lon, lat]",
                get_source_color=[255, 45, 65, 120],
                get_target_color=[255, 110, 170, 255],
                get_width=2,
                great_circle=False,
                pickable=False,
            )
            glow_outer = pdk.Layer(
                "ScatterplotLayer",
                data=hm,
                get_position="[lon, lat]",
                get_radius="radius * 3.2",
                get_fill_color=[255, 30, 60, 35],
                filled=True,
                stroked=False,
                radius_min_pixels=14,
                radius_max_pixels=60,
            )
            glow_mid = pdk.Layer(
                "ScatterplotLayer",
                data=hm,
                get_position="[lon, lat]",
                get_radius="radius * 1.8",
                get_fill_color=[255, 45, 75, 90],
                filled=True,
                stroked=False,
                radius_min_pixels=9,
                radius_max_pixels=38,
            )
            core = pdk.Layer(
                "ScatterplotLayer",
                data=hm,
                get_position="[lon, lat]",
                get_radius="radius",
                get_fill_color=[255, 70, 95, 255],
                get_line_color=[255, 255, 255, 255],
                line_width_min_pixels=1,
                stroked=True,
                filled=True,
                pickable=True,
                radius_min_pixels=4,
                radius_max_pixels=16,
            )
            deck = pdk.Deck(
                layers=[arc_layer, glow_outer, glow_mid, core],
                initial_view_state=pdk.ViewState(
                    latitude=21.5, longitude=79.0, zoom=3.3, pitch=30
                ),
                map_style="dark",
                tooltip={
                    "html": "<b>{circle_name}</b><br/>Subscribers: {subs_txt}<br/>6M Revenue: {rev_txt}",
                    "style": {
                        "backgroundColor": "#111827",
                        "color": "#ffffff",
                        "border": "1px solid #ff2d41",
                        "fontSize": "11px",
                    },
                },
            )
            st.pydeck_chart(deck, height=317, use_container_width=True)
            if unmatched:
                st.caption(f"{unmatched} circle(s) skipped (no coordinates)")

    # ---------- Plan table ----------
    with d2b:
        c_df, _ = chart_filter("tbl", f_df, f_rech)
        st.markdown(
            "<div style='background:#ffffff;border:1px solid #d8dee6;border-radius:12px 12px 0 0;padding:7px 12px;font-size:0.82rem;font-weight:800;'>Plan Revenue vs Stated ARPU Table</div>",
            unsafe_allow_html=True,
        )
        if not c_df.empty:
            ptbl = (
                c_df.groupby("plan_name", as_index=False)
                .agg(
                    Subs=("customer_id", "nunique"),
                    Rev_6M=("received_revenue_6m", "sum"),
                    Rec_Mo=("received_arpu_monthly", "mean"),
                    Stated=("stated_arpu", "mean"),
                )
                .sort_values("Rev_6M", ascending=False)
                .round(1)
            )
            st.dataframe(ptbl, use_container_width=True, hide_index=True, height=317)
        else:
            st.caption("No data for this filter")


# ---------------------------------------------------------
# BOTTOM INSIGHT & FOOTNOTE
# ---------------------------------------------------------
top_p_name = (
    f_df.groupby("plan_name")["received_revenue_6m"].sum().idxmax()
    if (not f_df.empty and f_df["received_revenue_6m"].sum() > 0)
    else "N/A"
)
st.markdown(
    f"""
    <div class="insight-bar">
        ⚡ Overall insight: 6M received revenue ₹{tot_rev:,.0f} across {tot_subs:,} subscribers · Top plan: {top_p_name} · Avg received/sub/mo: ₹{avg_arpu_m:,.2f} (vs stated ₹{avg_stated:,.2f})
    </div>
    <div class="footer-note">
        Jan–Jun 2025 received recharge revenue (recharges.amount_inr) · First page displays assets/airtel_hero.png · Switch between Overview and Details above.
    </div>
    """,
    unsafe_allow_html=True,
)