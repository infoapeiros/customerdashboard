import streamlit as st
from pymongo import MongoClient
import pandas as pd
from datetime import datetime
import altair as alt

# ---------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------
st.set_page_config(
    page_title="Support Dashboard",
    page_icon="📊",
    layout="wide"
)

# ---------------------------------------------------------
# DARK ENTERPRISE UI CSS
# ---------------------------------------------------------
st.markdown("""
<style>
body { background-color: #0E1117; }

.block-container { padding-top: 2rem; }

.section-title {
    font-size: 26px;
    font-weight: 600;
    color: #FFFFFF;
    margin-bottom: 10px;
}

.divider {
    border-bottom: 1px solid #2D3748;
    margin-bottom: 25px;
}

.metric-card {
    padding: 18px;
    border-radius: 14px;
    text-align: center;
    color: white;
    transition: all 0.3s ease-in-out;
}

.metric-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 20px rgba(0,0,0,0.4);
}

.metric-label {
    font-size: 15px;
    opacity: 0.8;
}

.metric-value {
    font-size: 30px;
    font-weight: 700;
    margin-top: 8px;
}

.login-box {
    padding: 40px;
    border-radius: 16px;
    background: linear-gradient(135deg,#1f2937,#111827);
    box-shadow: 0 8px 25px rgba(0,0,0,0.5);
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# METRIC CARD FUNCTION
# ---------------------------------------------------------
def styled_metric(label, value, gradient):
    st.markdown(
        f"""
        <div class="metric-card" style="background:{gradient}">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

ACCESS_KEY = "Raj@apeiros"

# ---------------------------------------------------------
# LOGIN UI
# ---------------------------------------------------------
col1, col2, col3 = st.columns([1,2,1])
with col2:
    st.markdown("<div class='login-box'>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align:center;color:white;'>🔐 Support Dashboard Login</h2>", unsafe_allow_html=True)
    user_key = st.text_input("Enter Access Key", type="password")
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# MAIN DASHBOARD
# ---------------------------------------------------------
if user_key == ACCESS_KEY:

    mongo_uri = st.secrets.get("mongodb", {}).get("uri") if st.secrets else None
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
    wallet_collection = db_wallet['promotionalMessageCredit']
    payment_dt = db_retail['paymentDetails']

    # ---------------------------------------------------------
    # TODAY BILL OVERVIEW
    # ---------------------------------------------------------
    st.markdown("<div class='section-title'>📅 Today's Bill Overview</div>", unsafe_allow_html=True)
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    today = datetime.today()
    start = datetime(today.year, today.month, today.day)
    end = datetime(today.year, today.month, today.day, 23, 59, 59)

    bill_docs_bar = list(billReq.find(
        {"createdAt": {"$gte": start, "$lte": end}},
        {"billId": 1, "storeId": 1, "_id": 0}
    ))

    if bill_docs_bar:
        today_bill_df = pd.DataFrame(bill_docs_bar)
        store_ids_bar = today_bill_df["storeId"].unique().tolist()

        store_map = []
        for i in list(storedetails_collection.find(
            {'_id': {'$in': store_ids_bar}},
            {"_id": 1, "storeName": 1}
        )):
            store_map.append({
                "storeId": i['_id'],
                "storeName": i['storeName']
            })

        store_map_df = pd.DataFrame(store_map)
        today_bill_df = today_bill_df.merge(store_map_df, on='storeId', how='inner')

        bill_count_df = (
            today_bill_df.groupby("storeName")["billId"]
            .count()
            .reset_index()
            .rename(columns={"billId": "billCount"})
        )

        chart = (
            alt.Chart(bill_count_df)
            .mark_bar()
            .encode(
                x=alt.X("storeName:N", sort="-y"),
                y=alt.Y("billCount:Q"),
                tooltip=["storeName", "billCount"]
            )
            .properties(height=400)
        )

        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No Bills Till Now")

    # ---------------------------------------------------------
    # STORE INSIGHTS
    # ---------------------------------------------------------
    st.markdown("<div class='section-title'>🏬 Store Insights</div>", unsafe_allow_html=True)
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    store_names = storedetails_collection.distinct("storeName")
    ind = store_names.index('HP World Panvel')
    selected_store = st.selectbox("Select Store", store_names, index=ind)

    if selected_store:

        store_doc = list(storedetails_collection.find(
            {"storeName": selected_store},
            {'_id': 1, 'tenantId': 1, 'createdAt': 1}
        ))

        for doc in store_doc:
            storeId = doc['_id']
            tenantId = doc['tenantId']
            createdAt = doc['createdAt']

        onboard_date = createdAt.strftime('%d %B %Y')

        # -------- ORIGINAL LOGIC RESTORED --------
        org_doc = list(org.find({'tenantId': tenantId}, {'phoneNumber': 1}))
        phone_list = [i['phoneNumber'] for i in org_doc]
        try:
            phone_value = phone_list[0][0]
        except:
            phone_value = "No Record"

        bill_doc = list(billReq.find({'storeId': storeId}))
        bill_ids = [i['billId'] for i in bill_doc]
        bill_count = len(set(bill_ids))

        total_in_amount = 0
        total_rec_amount = 0
        total_trans_amount = 0

        in_ex_docs = list(in_ex.find({'billId': {'$in': bill_ids}}))
        for i in in_ex_docs:
            try:
                total_in_amount += float(i['InvoiceTotal']['value'])
            except:
                pass

        rec_ex_docs = list(rec_ex.find({'billId': {'$in': bill_ids}}))
        for i in rec_ex_docs:
            try:
                total_rec_amount += float(i['Total']['value'])
            except:
                pass

        trans_bill_docs = list(trans_bill.find({'billId': {'$in': bill_ids}}))
        for i in trans_bill_docs:
            try:
                total_trans_amount += float(i['billAmount'])
            except:
                pass

        final_total_rev = int(total_in_amount + total_rec_amount + total_trans_amount)

        wallet_doc = list(wallet_collection.find({'tenantId': tenantId}))
        try:
            wallet_balance = round(wallet_doc[0]['currentAvailable'], 2)
            wallet_consuption = round(wallet_doc[0]['lifetimeConsumption'], 2)
        except:
            wallet_balance = 0
            wallet_consuption = 0

        payment_doc = list(payment_dt.find({
            'storeId': storeId,
            "transactionStatus": "success"
        }))

        nt = 0
        for i in payment_doc:
            try:
                nt += float(i['netAmount'])
            except:
                pass

        pcg_name = payment_doc[-1]['packageName'] if payment_doc else "No Record"

        todays_bills = list(billReq.find({
            'storeId': storeId,
            'createdAt': {'$gte': start, '$lte': end}
        }))

        td_bill_count = len(todays_bills)

        # ---------------------------------------------------------
        # KPI DISPLAY
        # ---------------------------------------------------------
        st.markdown("### 📈 Performance Overview")
        c1, c2, c3 = st.columns(3)
        with c1:
            styled_metric("Today's Bills 🧾", td_bill_count,
                          "linear-gradient(135deg,#16A34A,#22C55E)")
        with c2:
            styled_metric("Total Bills 📊", bill_count,
                          "linear-gradient(135deg,#2563EB,#3B82F6)")
        with c3:
            styled_metric("Total Revenue 💰", final_total_rev,
                          "linear-gradient(135deg,#9333EA,#A855F7)")

        st.markdown("### 💼 Wallet & Payments")
        c4, c5, c6 = st.columns(3)
        with c4:
            styled_metric("Wallet Balance 💳", wallet_balance,
                          "linear-gradient(135deg,#F59E0B,#FBBF24)")
        with c5:
            styled_metric("Wallet Consumption ⚡", wallet_consuption,
                          "linear-gradient(135deg,#EF4444,#F87171)")
        with c6:
            styled_metric("Total Payment 💵", nt,
                          "linear-gradient(135deg,#06B6D4,#0EA5E9)")

        c7, c8 = st.columns(2)
        with c7:
            styled_metric("Package Name 📦", pcg_name,
                          "linear-gradient(135deg,#334155,#475569)")
        with c8:
            styled_metric("Onboard Date 📅", onboard_date,
                          "linear-gradient(135deg,#1E293B,#334155)")

elif user_key != "":
    st.error("❌ Invalid Access Key")
