import warnings

import streamlit as st
from pymongo import MongoClient
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
import altair as alt

# PyMongo warns on Azure Cosmos DB for Mongo API — informational, not an error
warnings.filterwarnings(
    "ignore",
    message=r".*connected to a CosmosDB cluster.*",
    category=UserWarning,
)

# Cosmos DB for Mongo API: avoid giant $in arrays and very long hangs
MONGO_CLIENT_KWARGS = {
    "serverSelectionTimeoutMS": 25_000,
    "connectTimeoutMS": 20_000,
    "socketTimeoutMS": 180_000,
}
BILL_ID_IN_CHUNK = 200
STORE_ID_IN_CHUNK = 150


def _mongo_client(uri: str) -> MongoClient:
    return MongoClient(uri, **MONGO_CLIENT_KWARGS)


def _chunks(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def _bill_values_for_ids(bill_ids, in_ex, rec_ex, trans_bill):
    """Sum invoice + receipt + transaction amounts per billId (chunked for Cosmos)."""
    out = defaultdict(float)
    ids = list(bill_ids)
    for chunk in _chunks(ids, BILL_ID_IN_CHUNK):
        for doc in in_ex.find({"billId": {"$in": chunk}}):
            if doc.get("InvoiceTotal") and doc["InvoiceTotal"].get("value"):
                out[doc["billId"]] += float(doc["InvoiceTotal"]["value"])
        for doc in rec_ex.find({"billId": {"$in": chunk}}):
            if doc.get("Total") and doc["Total"].get("value"):
                out[doc["billId"]] += float(doc["Total"]["value"])
        for doc in trans_bill.find({"billId": {"$in": chunk}}):
            if doc.get("billAmount"):
                out[doc["billId"]] += float(doc["billAmount"])
    return out


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
.metric-value-lifetime {font-size:24px;font-weight:bold;color:#34D399;}
@keyframes apeiros-spin {
    to { transform: rotate(360deg); }
}
.apeiros-loader-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 2rem 1rem;
    gap: 1rem;
}
.apeiros-loader-ring {
    width: 52px;
    height: 52px;
    border: 3px solid rgba(56, 189, 248, 0.15);
    border-top-color: #38bdf8;
    border-right-color: #22d3ee;
    border-radius: 50%;
    animation: apeiros-spin 0.75s linear infinite;
}
.apeiros-loader-text {
    color: #94a3b8;
    font-size: 15px;
    letter-spacing: 0.02em;
}
div[data-testid="stStatus"] > div {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important;
    border: 1px solid rgba(56, 189, 248, 0.25) !important;
    border-radius: 14px !important;
}
</style>
""", unsafe_allow_html=True)


def _valid_access_keys():
    """Passwords from .streamlit/secrets.toml [auth] keys, or built-in defaults."""
    fallback = {"Raj@apeiros", "Tridip26@", "ApeirosSupport3"}
    try:
        auth = st.secrets.get("auth", {})
        raw = auth.get("keys")
        if raw is None:
            return fallback
        keys = raw if isinstance(raw, list) else [raw]
        parsed = {str(k).strip() for k in keys if str(k).strip()}
        return parsed if parsed else fallback
    except Exception:
        return fallback


@st.cache_data(ttl=600, show_spinner=False)
def lifetime_retailer_bill_stats(mongo_uri: str):
    """All-time bill count and value across retailers (cached; streams + chunked queries)."""
    client = _mongo_client(mongo_uri)
    try:
        db_retail = client["apeirosretail"]
        db_bills = client["apeirosretaildataprocessing"]
        bill_req = db_bills["billRequest"]
        storedetails_collection = db_retail["storeDetails"]
        in_ex = db_bills["invoiceExtractedData"]
        rec_ex = db_bills["receiptExtractedData"]
        trans_bill = db_bills["billtransactions"]

        bill_to_store = {}
        cur = bill_req.find(
            {}, {"billId": 1, "storeId": 1, "_id": 0}, batch_size=2000
        )
        for doc in cur:
            bid, sid = doc.get("billId"), doc.get("storeId")
            if bid is not None and sid is not None:
                bill_to_store[bid] = sid

        if not bill_to_store:
            return {"total_bills": 0, "grand_total": 0, "by_store": []}

        bill_ids = list(bill_to_store.keys())
        store_ids = list({bill_to_store[b] for b in bill_ids})

        id_to_name = {}
        for s_chunk in _chunks(store_ids, STORE_ID_IN_CHUNK):
            for sdoc in storedetails_collection.find(
                {"_id": {"$in": s_chunk}}, {"_id": 1, "storeName": 1}
            ):
                id_to_name[sdoc["_id"]] = sdoc.get("storeName") or "Unknown"

        bill_to_value = _bill_values_for_ids(bill_ids, in_ex, rec_ex, trans_bill)

        total_bills = len(bill_to_store)
        grand_total = int(sum(bill_to_value.values()))

        rows = []
        by_store = defaultdict(float)
        for bid, sid in bill_to_store.items():
            name = id_to_name.get(sid, "Unknown")
            v = bill_to_value.get(bid, 0.0)
            by_store[name] += v
        for name, total in sorted(
            by_store.items(), key=lambda x: x[1], reverse=True
        ):
            rows.append({"storeName": name, "totalValue": float(total)})

        return {
            "total_bills": total_bills,
            "grand_total": grand_total,
            "by_store": rows,
        }
    finally:
        client.close()


# ---------------- LOGIN ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Support Dashboard Login")
    st.caption("Use any configured access key from your secrets file.")
    key = st.text_input("Enter Access Key", type="password")
    if st.button("Login", type="primary"):
        with st.spinner("Signing you in…"):
            ok = key in _valid_access_keys()
        if ok:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Invalid Access Key")

else:

    mongo_uri = st.secrets["mongodb"]["uri"]

    st.sidebar.title("📅 Bill Filter")

    filter_option = st.sidebar.radio(
        "Select Range",
        ["Today", "Last 7 Days", "Last 30 Days", "Custom"],
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

    st.sidebar.markdown("---")
    st.sidebar.caption(
        "Lifetime scans **all** bills — can be slow on large data. "
        "Leave off for a fast dashboard."
    )
    st.sidebar.checkbox(
        "Load lifetime totals (all retailers)",
        key="load_lifetime_totals",
        value=False,
    )

    with st.status("Loading dashboard", expanded=True) as load_status:
        load_status.update(label="Connecting to database…", state="running")
        client = _mongo_client(mongo_uri)

        db_retail = client["apeirosretail"]
        db_bills = client["apeirosretaildataprocessing"]
        db_wallet = client["apeirosretailcustomermanagement"]

        storedetails_collection = db_retail["storeDetails"]
        org = db_retail["organizationDetails"]
        billReq = db_bills["billRequest"]
        in_ex = db_bills["invoiceExtractedData"]
        rec_ex = db_bills["receiptExtractedData"]
        trans_bill = db_bills["billtransactions"]
        payment_dt = db_retail["paymentDetails"]
        wallet_collection = db_wallet["promotionalMessageCredit"]

        load_status.update(label="Loading selected date range…", state="running")
        bill_docs_bar = list(
            billReq.find(
                {"createdAt": {"$gte": start_datetime, "$lte": end_datetime}},
                {"billId": 1, "storeId": 1, "_id": 0},
            )
        )

        load_status.update(label="Ready", state="complete")

    st.title("🚀 Apeiros Support Dashboard")

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

        bill_ids_in_range = df["billId"].unique().tolist()
        bill_to_value = _bill_values_for_ids(
            bill_ids_in_range, in_ex, rec_ex, trans_bill
        )

        grand_total_bill_value = int(sum(bill_to_value.values()))

        m1, m2 = st.columns(2)
        with m1:
            st.markdown(f"""
            <div class="card">
                <div class="metric-title">Total Bills</div>
                <div class="metric-value">{total_bills}</div>
            </div>
            """, unsafe_allow_html=True)
        with m2:
            st.markdown(f"""
            <div class="card">
                <div class="metric-title">Bill Value — All Retailers (selected range)</div>
                <div class="metric-value">₹ {grand_total_bill_value:,}</div>
            </div>
            """, unsafe_allow_html=True)

        bill_count_df = (
            df.groupby("storeName")["billId"]
            .count()
            .reset_index()
            .rename(columns={"billId": "billCount"})
        )

        chart = alt.Chart(bill_count_df).mark_bar().encode(
            x=alt.X("storeName:N", sort="-y", title="Store"),
            y=alt.Y("billCount:Q", title="Bills"),
            tooltip=["storeName", "billCount"]
        ).properties(height=400)
        bill_store_df = df.drop_duplicates(subset=["billId"])[["billId", "storeName"]]
        bill_store_df = bill_store_df.assign(
            billValue=bill_store_df["billId"].map(lambda b: bill_to_value.get(b, 0.0))
        )
        value_by_store_df = (
            bill_store_df.groupby("storeName")["billValue"]
            .sum()
            .reset_index()
            .rename(columns={"billValue": "totalValue"})
        )
        value_chart = alt.Chart(value_by_store_df).mark_bar(color="#34D399").encode(
            x=alt.X("storeName:N", sort="-y", title="Store"),
            y=alt.Y("totalValue:Q", title="Total value (₹)"),
            tooltip=[
                alt.Tooltip("storeName", title="Store"),
                alt.Tooltip("totalValue:Q", title="₹ Total", format=","),
            ],
        ).properties(height=400)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(
                '<div class="section-title">📊 Bill Count (selected range)</div>',
                unsafe_allow_html=True,
            )
            st.altair_chart(chart, use_container_width=True)
        with c2:
            st.markdown(
                '<div class="section-title">💰 Bill Value by Retailer (selected range)</div>',
                unsafe_allow_html=True,
            )
            st.altair_chart(value_chart, use_container_width=True)

    else:
        st.info("No Bills Found")

    st.markdown(
        '<div class="section-title">♾️ Lifetime — All Retailers</div>',
        unsafe_allow_html=True,
    )
    if st.session_state.get("load_lifetime_totals"):
        with st.spinner("Computing lifetime totals (chunked queries — please wait)…"):
            try:
                lifetime_payload = lifetime_retailer_bill_stats(mongo_uri)
            except Exception as e:
                st.error(f"Lifetime query failed: `{e}`")
                lifetime_payload = None
        if lifetime_payload is not None:
            lt_bills = lifetime_payload["total_bills"]
            lt_value = lifetime_payload["grand_total"]
            lt_rows = lifetime_payload["by_store"]
            lc1, lc2 = st.columns(2)
            with lc1:
                st.markdown(
                    f"""
                    <div class="card">
                        <div class="metric-title">Lifetime Total Bills</div>
                        <div class="metric-value">{lt_bills:,}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with lc2:
                st.markdown(
                    f"""
                    <div class="card">
                        <div class="metric-title">Lifetime Total Bill Value (All Retailers)</div>
                        <div class="metric-value-lifetime">₹ {lt_value:,}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            if lt_rows:
                lt_df = pd.DataFrame(lt_rows)
                lt_chart = alt.Chart(lt_df).mark_bar(color="#A78BFA").encode(
                    x=alt.X("storeName:N", sort="-y", title="Store"),
                    y=alt.Y("totalValue:Q", title="Lifetime value (₹)"),
                    tooltip=[
                        alt.Tooltip("storeName", title="Store"),
                        alt.Tooltip("totalValue:Q", title="₹ Total", format=","),
                    ],
                ).properties(height=380)
                st.altair_chart(lt_chart, use_container_width=True)
            else:
                st.caption("No lifetime bill data yet.")
    else:
        st.info(
            "Turn on **Load lifetime totals (all retailers)** in the sidebar "
            "when you need all-time numbers (first run may take a few minutes)."
        )

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

        tenant_id_display = str(tenantId)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            card("Phone 📱", phone_value)
        with col2:
            card("Onboard Date ✈️", onboard_date)
        with col3:
            card("Tenant ID 🏢", tenant_id_display)
        with col4:
            card("Bill Count 🧾", bill_count)

        col4, col5, col6 = st.columns(3)
        with col4: card("Total Revenue 💰", f"₹ {final_total_rev:,}")
        with col5: card("Wallet Balance 💼", f"₹ {wallet_balance:,}")
        with col6: card("Total Payment 💵", f"₹ {nt:,}")

        col7 = st.columns(1)[0]
        with col7: card("Package 📦", pcg_name)

        if st.checkbox("Show Bills"):
            st.dataframe(bill_doc)
