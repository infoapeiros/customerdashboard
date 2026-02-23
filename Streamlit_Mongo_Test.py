import streamlit as st
import altair as alt
import pandas as pd
from datetime import datetime

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(page_title="Apeiros Support Dashboard", layout="wide")

# -------------------------------------------------
# CUSTOM CSS (Modern Dark UI)
# -------------------------------------------------
st.markdown("""
<style>
html, body, [class*="css"]  {
    background-color: #0E1117;
    color: white;
}

.dashboard-title {
    text-align: center;
    font-size: 40px;
    font-weight: 700;
    background: linear-gradient(90deg, #4CAF50, #00C9A7);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 20px;
}

.card {
    background-color: #1E2228;
    padding: 25px;
    border-radius: 18px;
    text-align: center;
    box-shadow: 0px 4px 20px rgba(0,0,0,0.5);
    transition: 0.3s;
}

.card:hover {
    transform: translateY(-5px);
}

.metric-title {
    font-size:18px;
    color:#AAAAAA;
    margin-bottom:10px;
}

.metric-value {
    font-size:32px;
    font-weight:bold;
    color:white;
}

.section-title {
    font-size:26px;
    font-weight:bold;
    margin-top:40px;
    margin-bottom:20px;
    color:#4CAF50;
}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# HEADER
# -------------------------------------------------
st.markdown('<div class="dashboard-title">🚀 Apeiros Support Dashboard</div>', unsafe_allow_html=True)

# -------------------------------------------------
# DEMO DATA (Replace with Mongo Values Later)
# -------------------------------------------------
td_bill_count = 45
final_total_rev = 158900
nt = 25000
phone_value = "9876543210"
onboard_date = "15 March 2024"
pcg_name = "Premium Package"
wallet_balance = 1250.75
wallet_consuption = 8750.50

bill_count_df = pd.DataFrame({
    "storeName": ["Panvel", "Mumbai", "Delhi", "Kolkata"],
    "billCount": [25, 40, 18, 30]
})

# -------------------------------------------------
# METRIC CARD FUNCTION
# -------------------------------------------------
def metric_card(title, value):
    st.markdown(f"""
        <div class="card">
            <div class="metric-title">{title}</div>
            <div class="metric-value">{value}</div>
        </div>
    """, unsafe_allow_html=True)

# -------------------------------------------------
# TODAY OVERVIEW
# -------------------------------------------------
st.markdown('<div class="section-title">📊 Today Overview</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    metric_card("Today's Bills 🧾", td_bill_count)

with col2:
    metric_card("Total Revenue 📈", f"₹ {final_total_rev:,}")

with col3:
    metric_card("Total Payments 💵", f"₹ {nt:,}")

# -------------------------------------------------
# STORE INFORMATION
# -------------------------------------------------
st.markdown('<div class="section-title">🏬 Store Information</div>', unsafe_allow_html=True)

col4, col5, col6 = st.columns(3)

with col4:
    metric_card("Phone Number 📞", phone_value)

with col5:
    metric_card("Onboard Date ✈️", onboard_date)

with col6:
    metric_card("Package 📦", pcg_name)

# -------------------------------------------------
# WALLET INFO
# -------------------------------------------------
st.markdown('<div class="section-title">💼 Wallet Information</div>', unsafe_allow_html=True)

col7, col8 = st.columns(2)

with col7:
    metric_card("Wallet Balance 💰", f"₹ {wallet_balance:,}")

with col8:
    metric_card("Wallet Consumption ⚡", f"₹ {wallet_consuption:,}")

# -------------------------------------------------
# CHART SECTION
# -------------------------------------------------
st.markdown('<div class="section-title">📈 Store Wise Bill Count</div>', unsafe_allow_html=True)

chart = (
    alt.Chart(bill_count_df)
    .mark_bar(size=40)
    .encode(
        x=alt.X("storeName:N", sort="-y", title="Store"),
        y=alt.Y("billCount:Q", title="Bills"),
        tooltip=["storeName", "billCount"]
    )
    .properties(height=400)
)

st.altair_chart(chart, use_container_width=True)

# -------------------------------------------------
# FOOTER
# -------------------------------------------------
st.markdown("""
<hr style="border:1px solid #222;">
<p style="text-align:center; color:gray;">
© 2026 Apeiros Retail | Internal Support Dashboard
</p>
""", unsafe_allow_html=True)
