import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import random

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(page_title="Apeiros Admin Panel", layout="wide")

# -------------------------------------------------
# CUSTOM CSS (Premium SaaS Look)
# -------------------------------------------------
st.markdown("""
<style>
html, body, [class*="css"] {
    background-color: #0E1117;
    color: white;
}

.login-box {
    background-color: #1E2228;
    padding: 40px;
    border-radius: 20px;
    box-shadow: 0px 0px 30px rgba(0,0,0,0.5);
    width: 400px;
    margin: auto;
    margin-top: 100px;
}

.card {
    background-color: #1E2228;
    padding: 25px;
    border-radius: 18px;
    text-align: center;
    box-shadow: 0px 4px 20px rgba(0,0,0,0.5);
}

.metric-title {
    font-size:16px;
    color:#AAAAAA;
}

.metric-value {
    font-size:30px;
    font-weight:bold;
}

.section-title {
    font-size:24px;
    margin-top:40px;
    margin-bottom:20px;
    color:#4CAF50;
}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# LOGIN SYSTEM
# -------------------------------------------------
ACCESS_KEY = "Raj@apeiros"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:

    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.title("🔐 Admin Login")
    key = st.text_input("Enter Access Key", type="password")

    if st.button("Login"):
        if key == ACCESS_KEY:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Invalid Access Key")

    st.markdown('</div>', unsafe_allow_html=True)

# -------------------------------------------------
# MAIN DASHBOARD
# -------------------------------------------------
else:

    # SIDEBAR
    st.sidebar.title("⚙️ Admin Controls")

    start_date = st.sidebar.date_input("Start Date", datetime.today() - timedelta(days=30))
    end_date = st.sidebar.date_input("End Date", datetime.today())

    store_filter = st.sidebar.selectbox("Select Store", ["All", "Panvel", "Mumbai", "Delhi", "Kolkata"])

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    st.title("🚀 Apeiros SaaS Admin Panel")

    # -------------------------------------------------
    # DEMO DATA GENERATION
    # -------------------------------------------------
    dates = pd.date_range(start=start_date, end=end_date)

    data = pd.DataFrame({
        "date": dates,
        "revenue": [random.randint(2000, 15000) for _ in dates]
    })

    leaderboard = pd.DataFrame({
        "Store": ["Panvel", "Mumbai", "Delhi", "Kolkata"],
        "Revenue": [250000, 420000, 180000, 310000],
        "Bills": [450, 720, 300, 510]
    }).sort_values("Revenue", ascending=False)

    total_revenue = leaderboard["Revenue"].sum()
    total_bills = leaderboard["Bills"].sum()
    total_stores = 4

    # -------------------------------------------------
    # METRIC CARDS
    # -------------------------------------------------
    def metric_card(title, value):
        st.markdown(f"""
        <div class="card">
            <div class="metric-title">{title}</div>
            <div class="metric-value">{value}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="section-title">📊 Overview</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        metric_card("Total Revenue 💰", f"₹ {total_revenue:,}")

    with col2:
        metric_card("Total Bills 🧾", total_bills)

    with col3:
        metric_card("Active Stores 🏬", total_stores)

    # -------------------------------------------------
    # MONTHLY REVENUE GRAPH
    # -------------------------------------------------
    st.markdown('<div class="section-title">📈 Revenue Trend</div>', unsafe_allow_html=True)

    chart = (
        alt.Chart(data)
        .mark_line(point=True)
        .encode(
            x="date:T",
            y="revenue:Q",
            tooltip=["date", "revenue"]
        )
        .properties(height=400)
    )

    st.altair_chart(chart, use_container_width=True)

    # -------------------------------------------------
    # LEADERBOARD
    # -------------------------------------------------
    st.markdown('<div class="section-title">🏆 Top Performing Stores</div>', unsafe_allow_html=True)

    st.dataframe(leaderboard, use_container_width=True)

    # -------------------------------------------------
    # FOOTER
    # -------------------------------------------------
    st.markdown("""
    <hr style="border:1px solid #222;">
    <p style="text-align:center; color:gray;">
    © 2026 Apeiros Retail SaaS Dashboard
    </p>
    """, unsafe_allow_html=True)
