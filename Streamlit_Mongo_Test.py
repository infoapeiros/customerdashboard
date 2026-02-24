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
# CUSTOM CSS
# -------------------------------------------------
st.markdown("""
<style>
html, body, [class*="css"] {
    background-color: #0E1117;
    color: white;
}

/* Centered Container */
.center-container {
    max-width: 1200px;
    margin: auto;
}

/* Login Box */
.login-box {
    background-color: #1E2228;
    padding: 40px;
    border-radius: 20px;
    box-shadow: 0px 0px 30px rgba(0,0,0,0.5);
    width: 400px;
    margin: auto;
    margin-top: 150px;
}

/* Cards */
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
    font-size:28px;
    font-weight:bold;
}

/* Section Title */
.section-title {
    font-size:24px;
    margin-top:40px;
    margin-bottom:20px;
    color:#4CAF50;
    text-align:center;
}
</style>
""", unsafe_allow_html=True)

ACCESS_KEY = "Raj@apeiros"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# -------------------------------------------------
# LOGIN SCREEN
# -------------------------------------------------
if not st.session_state.logged_in:

    with st.container():
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

    st.sidebar.title("⚙️ Admin Controls")

    start_date = st.sidebar.date_input("Start Date", datetime.today() - timedelta(days=30))
    end_date = st.sidebar.date_input("End Date", datetime.today())

    store_filter = st.sidebar.selectbox("Select Store", ["Panvel", "Mumbai", "Delhi", "Kolkata"])

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    st.markdown('<div class="center-container">', unsafe_allow_html=True)

    st.title("🚀 Apeiros SaaS Admin Panel")

    # Demo Data
    dates = pd.date_range(start=start_date, end=end_date)

    data = pd.DataFrame({
        "date": dates,
        "revenue": [random.randint(3000, 20000) for _ in dates]
    })

    leaderboard = pd.DataFrame({
        "Store": ["Panvel", "Mumbai", "Delhi", "Kolkata"],
        "Revenue": [250000, 420000, 180000, 310000],
        "Bills": [450, 720, 300, 510],
        "Phone": ["9876543210", "9123456780", "9988776655", "9090909090"]
    }).sort_values("Revenue", ascending=False)

    selected_store_data = leaderboard[leaderboard["Store"] == store_filter].iloc[0]

    total_revenue = leaderboard["Revenue"].sum()
    total_bills = leaderboard["Bills"].sum()
    total_stores = len(leaderboard)

    # Card Function
    def metric_card(title, value):
        st.markdown(f"""
        <div class="card">
            <div class="metric-title">{title}</div>
            <div class="metric-value">{value}</div>
        </div>
        """, unsafe_allow_html=True)

    # OVERVIEW
    st.markdown('<div class="section-title">📊 Overview</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)

    with col1:
        metric_card("Total Revenue 💰", f"₹ {total_revenue:,}")

    with col2:
        metric_card("Total Bills 🧾", total_bills)

    with col3:
        metric_card("Active Stores 🏬", total_stores)

    # STORE DETAILS
    st.markdown('<div class="section-title">📞 Selected Store Details</div>', unsafe_allow_html=True)
    col4, col5, col6 = st.columns(3)

    with col4:
        metric_card("Store Name 🏬", selected_store_data["Store"])

    with col5:
        metric_card("Mobile Number 📱", selected_store_data["Phone"])

    with col6:
        metric_card("Store Revenue 💵", f"₹ {selected_store_data['Revenue']:,}")

    # GRAPH
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

    # LEADERBOARD
    st.markdown('<div class="section-title">🏆 Top Performing Stores</div>', unsafe_allow_html=True)
    st.dataframe(leaderboard, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)
