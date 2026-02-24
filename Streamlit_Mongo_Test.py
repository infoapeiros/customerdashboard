import streamlit as st
from pymongo import MongoClient
import pandas as pd
from datetime import datetime, timedelta
import altair as alt

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(page_title="Apeiros Support Dashboard", layout="wide")

# -------------------------------------------------
# CUSTOM CSS (Professional SaaS UI)
# -------------------------------------------------
st.markdown("""
<style>
html, body, [class*="css"] {
    background-color: #0E1117;
    color: white;
}

.center-container {
    max-width: 1300px;
    margin: auto;
}

.card {
    background-color: #1E2228;
    padding: 25px;
    border-radius: 16px;
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

.section-title {
    font-size:24px;
    margin-top:40px;
    margin-bottom:20px;
    color:#4CAF50;
    text-align:center;
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

    st.sidebar.title("📅 Filters")

    start_date = st.sidebar.date_input("Start Date", datetime.today() - timedelta(days=30))
    end_date = st.sidebar.date_input("End Date", datetime.today())

    st.markdown('<div class="center-container">', unsafe_allow_html=True)
    st.title("🚀 Apeiros Support Dashboard")

    # -------------------------------------------------
    # TODAY BILL COUNT GRAPH
    # -------------------------------------------------
    today = datetime.today()
    start = datetime(today.year, today.month, today.day)
    end = datetime(today.year, today.month, today.day, 23, 59, 59)

    bill_docs_bar = list(billReq.find(
        {"createdAt": {"$gte": start, "$lte": end}},
        {"billId": 1, "storeId": 1, "_id": 0}
    ))

    st.markdown('<div class="section-title">📊 Today Bill Count</div>', unsafe_allow_html=True)

    if bill_docs_bar:

        today_bill_df = pd.DataFrame(bill_docs_bar)
        store_ids_bar = today_bill_df["storeId"].unique().tolist()

        store_map = list(storedetails_collection.find(
            {'_id': {'$in': store_ids_bar}},
            {"_id": 1, "storeName": 1}
        ))

        store_map_df = pd.DataFrame(store_map)
        store_map_df.rename(columns={"_id": "storeId"}, inplace=True)

        today_bill_df = today_bill_df.merge(store_map_df, on="storeId")

        bill_count_df = (
            today_bill_df.groupby("storeName")["billId"]
            .count()
            .reset_index()
            .rename(columns={"billId": "billCount"})
        )

        chart = alt.Chart(bill_count_df).mark_bar().encode(
            x=alt.X("storeName:N", sort="-y"),
            y="billCount:Q",
            tooltip=["storeName", "billCount"]
        ).properties(height=400)

        st.altair_chart(chart, use_container_width=True)

    else:
        st.info("No Bills Today")

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

        bill_doc = list(billReq.find({'storeId': storeId}))
        bill_ids = [i['billId'] for i in bill_doc]

        bill_count = len(set(bill_ids))

        total_in_amount = sum(
            float(i['InvoiceTotal']['value'])
            for i in in_ex.find({'billId': {'$in': bill_ids}})
            if i.get('InvoiceTotal') and i['InvoiceTotal'].get('value')
        )

        total_rec_amount = sum(
            float(i['Total']['value'])
            for i in rec_ex.find({'billId': {'$in': bill_ids}})
            if i.get('Total') and i['Total'].get('value')
        )

        total_trans_amount = sum(
            float(i['billAmount'])
            for i in trans_bill.find({'billId': {'$in': bill_ids}})
            if i.get('billAmount')
        )

        final_total_rev = int(total_in_amount + total_rec_amount + total_trans_amount)

        wallet_doc = wallet_collection.find_one({'tenantId': tenantId})
        wallet_balance = round(wallet_doc.get("currentAvailable", 0), 2) if wallet_doc else 0
        wallet_consuption = round(wallet_doc.get("lifetimeConsumption", 0), 2) if wallet_doc else 0

        payment_doc = list(payment_dt.find(
            {'storeId': storeId, "transactionStatus": "success"}
        ))

        nt = sum(float(i['netAmount']) for i in payment_doc if i.get('netAmount'))

        pcg_name = payment_doc[-1]['packageName'] if payment_doc else "No Record"

        # ---------------- METRIC CARDS ----------------

        def metric_card(title, value):
            st.markdown(f"""
            <div class="card">
                <div class="metric-title">{title}</div>
                <div class="metric-value">{value}</div>
            </div>
            """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)

        with col1:
            metric_card("Phone Number 📱", phone_value)

        with col2:
            metric_card("Onboard Date ✈️", onboard_date)

        with col3:
            metric_card("Bill Count 🧾", bill_count)

        col4, col5, col6 = st.columns(3)

        with col4:
            metric_card("Total Revenue 💰", f"₹ {final_total_rev:,}")

        with col5:
            metric_card("Wallet Balance 💼", f"₹ {wallet_balance:,}")

        with col6:
            metric_card("Total Payments 💵", f"₹ {nt:,}")

        col7 = st.columns(1)[0]
        with col7:
            metric_card("Package 📦", pcg_name)

        if st.checkbox("Show Bills"):
            st.dataframe(bill_doc)

    st.markdown('</div>', unsafe_allow_html=True)
