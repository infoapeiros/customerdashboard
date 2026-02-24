import streamlit as st
from pymongo import MongoClient
import pandas as pd
from datetime import datetime, timedelta
import altair as alt

st.set_page_config(page_title="Apeiros Support Dashboard", layout="wide")

# ---------------- MODERN UI CSS ----------------
st.markdown("""
<style>
html, body, [class*="css"] {
    background-color: #0F172A;
    color: white;
}
.card {
    padding:20px;
    border-radius:18px;
    text-align:center;
    background: linear-gradient(135deg,#1E293B,#0F172A);
    box-shadow:0px 6px 25px rgba(0,0,0,0.4);
    margin-bottom:15px;
}
.metric-title {color:#94A3B8;font-size:14px;}
.metric-value {font-size:24px;font-weight:bold;color:#38BDF8;}
.section-title {font-size:22px;font-weight:600;margin-top:35px;color:#22D3EE;}
</style>
""", unsafe_allow_html=True)

# ---------------- LOGIN ----------------
ACCESS_KEY = "Raj@apeiros"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Support Dashboard Login")
    key = st.text_input("Enter Access Key", type="password")
    if st.button("Login"):
        if key == ACCESS_KEY:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Invalid Access Key")

else:

    # ---------------- MONGO ----------------
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

    # ---------------- FILTER ----------------
    st.sidebar.title("📅 Bill Filter")

    filter_option = st.sidebar.radio(
        "Select Range",
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

    # ---------------- BILL GRAPH ----------------
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

    total_bills = df["billId"].nunique()

    # -------- Total Bill Card --------
    st.markdown(f"""
    <div class="card">
        <div class="metric-title">Total Bills</div>
        <div class="metric-value">{total_bills}</div>
    </div>
    """, unsafe_allow_html=True)

    # -------- Store Wise Grouping --------
    bill_count_df = (
        df.groupby("storeName")["billId"]
        .count()
        .reset_index()
        .rename(columns={"billId": "billCount"})
    )

    # -------- BAR CHART --------
    chart = alt.Chart(bill_count_df).mark_bar().encode(
        x=alt.X("storeName:N", sort="-y", title="Store"),
        y=alt.Y("billCount:Q", title="Bills"),
        tooltip=["storeName", "billCount"]
    ).properties(height=400)

    st.altair_chart(chart, use_container_width=True)

        col = st.columns(1)[0]
        with col:
            st.markdown(f"""
            <div class="card">
                <div class="metric-title">Total Bills</div>
                <div class="metric-value">{total_bills}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No Bills Found")

    # ---------------- STORE INSIGHTS ----------------
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

        def card(title, value):
            st.markdown(f"""
            <div class="card">
                <div class="metric-title">{title}</div>
                <div class="metric-value">{value}</div>
            </div>
            """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1: card("Phone 📱", phone_value)
        with col2: card("Onboard Date ✈️", onboard_date)
        with col3: card("Bill Count 🧾", bill_count)

        col4, col5, col6 = st.columns(3)
        with col4: card("Total Revenue 💰", f"₹ {final_total_rev:,}")
        with col5: card("Wallet Balance 💼", f"₹ {wallet_balance:,}")
        with col6: card("Total Payment 💵", f"₹ {nt:,}")

        col7 = st.columns(1)[0]
        with col7: card("Package 📦", pcg_name)

        if st.checkbox("Show Bills"):
            st.dataframe(bill_doc)
