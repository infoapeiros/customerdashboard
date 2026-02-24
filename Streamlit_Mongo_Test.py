import streamlit as st
from pymongo import MongoClient
import pandas as pd
from datetime import datetime, timedelta
import altair as alt

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(
    page_title="Apeiros Support Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------
# MODERN COLORFUL CSS (Responsive)
# -------------------------------------------------
st.markdown("""
<style>
html, body, [class*="css"] {
    background-color: #0F172A;
    color: white;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}

.card {
    padding: 20px;
    border-radius: 18px;
    text-align: center;
    background: linear-gradient(135deg, #1E293B, #0F172A);
    box-shadow: 0px 6px 25px rgba(0,0,0,0.4);
    margin-bottom: 15px;
}

.metric-title {
    font-size: 15px;
    color: #94A3B8;
}

.metric-value {
    font-size: 26px;
    font-weight: bold;
    color: #38BDF8;
}

.section-title {
    font-size: 22px;
    font-weight: 600;
    margin-top: 35px;
    margin-bottom: 20px;
    color: #22D3EE;
}

@media (max-width: 768px) {
    .metric-value {
        font-size: 20px;
    }
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

    st.markdown("<h2 style='text-align:center;'>🔐 Support Dashboard Login</h2>", unsafe_allow_html=True)
    key = st.text_input("Enter Access Key", type="password")

    if st.button("Login"):
        if key == ACCESS_KEY:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Invalid Access Key")

else:

    # -------------------------------------------------
    # MONGO CONNECTION
    # -------------------------------------------------
    mongo_uri = st.secrets["mongodb"]["uri"]
    client = MongoClient(mongo_uri)

    db_retail = client['apeirosretail']
    db_bills = client['apeirosretaildataprocessing']
    db_wallet = client['apeirosretailcustomermanagement']

    storedetails_collection = db_retail['storeDetails']
    org = db_retail['organizationDetails']
    billReq = db_bills['billRequest']
    in_ex = db_bills['invoiceExtractedData']
    rec_ex = db_bills['receiptExtractedData']
    trans_bill = db_bills['billtransactions']
    payment_dt = db_retail['paymentDetails']
    wallet_collection = db_wallet['promotionalMessageCredit']

    # -------------------------------------------------
    # SIDEBAR FILTER
    # -------------------------------------------------
    st.sidebar.title("📅 Bill Filter")

    filter_option = st.sidebar.radio(
        "Select Filter",
        ["Today", "Last 7 Days", "Last 30 Days", "Custom"]
    )

    today = datetime.today()

    if filter_option == "Today":
        start_datetime = datetime(today.year, today.month, today.day)
        end_datetime = datetime(today.year, today.month, today.day, 23, 59, 59)

    elif filter_option == "Last 7 Days":
        start_datetime = today - timedelta(days=7)
        end_datetime = today

    elif filter_option == "Last 30 Days":
        start_datetime = today - timedelta(days=30)
        end_datetime = today

    else:
        start_date = st.sidebar.date_input("Start Date")
        end_date = st.sidebar.date_input("End Date")
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

    st.title("🚀 Apeiros Support Dashboard")

    # -------------------------------------------------
    # TODAY / FILTERED BILL GRAPH
    # -------------------------------------------------
    st.markdown('<div class="section-title">📊 Bill Count</div>', unsafe_allow_html=True)

    bill_docs_bar = list(billReq.find(
        {"createdAt": {"$gte": start_datetime, "$lte": end_datetime}},
        {"billId": 1, "storeId": 1, "_id": 0}
    ))

    if bill_docs_bar:

        df = pd.DataFrame(bill_docs_bar)
        store_ids = df["storeId"].unique().tolist()

        store_map = list(storedetails_collection.find(
            {'_id': {'$in': store_ids}},
            {"_id": 1, "storeName": 1}
        ))

        store_df = pd.DataFrame(store_map)
        store_df.rename(columns={"_id": "storeId"}, inplace=True)

        df = df.merge(store_df, on="storeId")

        bill_count_df = (
            df.groupby("storeName")["billId"]
            .count()
            .reset_index()
            .rename(columns={"billId": "billCount"})
        )

        total_bills = df["billId"].nunique()

        # Cards
        col1 = st.columns(1)[0]
        with col1:
            st.markdown(f"""
            <div class="card">
                <div class="metric-title">Total Bills</div>
                <div class="metric-value">{total_bills}</div>
            </div>
            """, unsafe_allow_html=True)

        chart = alt.Chart(bill_count_df).mark_bar().encode(
            x=alt.X("storeName:N", sort="-y"),
            y="billCount:Q",
            tooltip=["storeName", "billCount"]
        ).properties(height=350)

        st.altair_chart(chart, use_container_width=True)

    else:
        st.info("No Bills Found For Selected Range")

    # -------------------------------------------------
    # STORE INSIGHTS
    # -------------------------------------------------
    st.markdown('<div class="section-title">🏬 Store Insights</div>', unsafe_allow_html=True)

    store_names = storedetails_collection.distinct("storeName")
    selected_store = st.selectbox("Choose Store", store_names)

    if selected_store:

        store_doc = storedetails_collection.find_one({"storeName": selected_store})
        storeId = store_doc['_id']
        tenantId = store_doc['tenantId']
        onboard_date = store_doc['createdAt'].strftime('%d %B %Y')

        org_doc = org.find_one({'tenantId': tenantId})
        phone_value = org_doc['phoneNumber'][0] if org_doc and org_doc.get("phoneNumber") else "No Record"

        st.markdown(f"""
        <div class="card">
            <div class="metric-title">Phone Number</div>
            <div class="metric-value">{phone_value}</div>
        </div>
        """, unsafe_allow_html=True)
