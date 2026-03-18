import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io

# --- Database Function (On-demand) ---
DB_NAME = "loan_v5_final.db"

def run_query(query, params=(), is_select=False):
    with sqlite3.connect(DB_NAME, timeout=30) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if is_select:
            return cursor.fetchall()
        conn.commit()

# Setup Tables
run_query('''CREATE TABLE IF NOT EXISTS loans 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
              date TEXT, name TEXT, amount REAL, rate REAL, interest REAL, status TEXT)''')
run_query('''CREATE TABLE IF NOT EXISTS settings (key TEXT, value TEXT)''')
run_query("INSERT OR IGNORE INTO settings VALUES ('pin', '1234')")

st.set_page_config(page_title="Loan Manager Pro", layout="wide", page_icon="💰")
# --- Scroll Issue Fix ---
st.markdown(
    """
    <style>
    .main .block-container {
        max-height: 100vh;
        overflow-y: auto;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- PIN Login ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Login to System")
    pin_input = st.text_input("PIN ရိုက်ထည့်ပါ", type="password")
    if st.button("ဝင်မည်", icon="🔓"):
        res = run_query("SELECT value FROM settings WHERE key='pin'", is_select=True)
        current_pin = res[0][0] if res else "1234"
        if pin_input == current_pin:
            st.session_state['logged_in'] = True
            st.rerun()
        else:
            st.error("PIN မှားယွင်းနေပါသည်")
    st.stop()

# --- App UI ---
st.title("💰 Loan Manager Pro")

# --- Sidebar (Password Change & Excel) ---
with st.sidebar:
    st.header("⚙️ Menu")
    
    # Password Change Section
    with st.expander("🔑 Password ပြောင်းရန်"):
        old_p = st.text_input("Old PIN", type="password")
        new_p = st.text_input("New PIN", type="password")
        if st.button("Update Now", icon="🔄"):
            res = run_query("SELECT value FROM settings WHERE key='pin'", is_select=True)
            if old_p == res[0][0]:
                run_query("UPDATE settings SET value=? WHERE key='pin'", (new_p,))
                st.success("Password ပြောင်းပြီးပါပြီ")
            else:
                st.error("Old PIN မှားနေသည်")

    st.divider()
    
    # Excel Download
    try:
        with sqlite3.connect(DB_NAME) as conn:
            df_export = pd.read_sql_query("SELECT * FROM loans", conn)
        towrite = io.BytesIO()
        df_export.to_excel(towrite, index=False, engine='xlsxwriter')
        towrite.seek(0)
        st.download_button("📥 Excel ဒေါင်းလုဒ်", data=towrite, file_name="Loan_Data.xlsx")
    except:
        st.write("ဒေတာ မရှိသေးပါ")

    if st.button("🚪 Logout", use_container_width=True):
        st.session_state['logged_in'] = False
        st.rerun()

# --- Dashboard ---
totals = run_query("SELECT SUM(amount), SUM(CASE WHEN status='Done' THEN interest ELSE 0 END), SUM(CASE WHEN status='Pending' THEN interest ELSE 0 END) FROM loans", is_select=True)
cap, earn, pend = totals[0]

c1, c2, c3 = st.columns(3)
c1.metric("💵 စုစုပေါင်း အရင်း", f"{cap or 0:,.0f} Ks")
c2.metric("📈 ရပြီး အတိုး", f"{earn or 0:,.0f} Ks")
c3.metric("⏳ ရရန် ကျန်ရှိ", f"{pend or 0:,.0f} Ks")

st.divider()

# --- Input Section ---
with st.expander("➕ စာရင်းအသစ်သွင်းရန်", expanded=True):
    col_a, col_b, col_c, col_d = st.columns([1.5, 2, 1.5, 1])
    date_in = col_a.date_input("ရက်စွဲ", datetime.now())
    name_in = col_b.text_input("အမည်")
    amt_in = col_c.number_input("အရင်း", min_value=0, step=1000)
    rate_in = col_d.number_input("အတိုး %", value=5, step=1)
    
    if st.button("သိမ်းမည်", icon="💾", use_container_width=True):
        if name_in and amt_in > 0:
            interest = (amt_in * rate_in) / 100
            run_query("INSERT INTO loans (date, name, amount, rate, interest, status) VALUES (?,?,?,?,?,?)",
                      (date_in.strftime("%d.%m.%Y"), name_in, amt_in, rate_in, interest, "Pending"))
            st.success(f"{name_in} စာရင်းသွင်းပြီးပါပြီ")
            st.rerun()

# --- Table ---
search = st.text_input("🔍 ရှာရန် (အမည်ဖြင့်)...")
with sqlite3.connect(DB_NAME) as conn:
    df = pd.read_sql_query("SELECT * FROM loans ORDER BY id DESC", conn)

if search:
    df = df[df['name'].str.contains(search, case=False, na=False)]

st.subheader("📋 စာရင်းဇယား")
for i, row in df.iterrows():
    with st.container(border=True):
        cols = st.columns([1, 2, 1, 1, 1])
        cols[0].write(f"📅 {row['date']}")
        cols[1].write(f"👤 **{row['name']}**")
        cols[2].write(f"💰 {row['amount']:,.0f} Ks")
        cols[3].write(f"📊 {int(row['rate'])}% ( {row['interest']:,.0f} )")
        
        status_label = "✅ ပြီးပြီ" if row['status'] == "Done" else "⏳ Pending"
        if cols[4].button(status_label, key=f"st_{row['id']}"):
            new_st = "Done" if row['status'] == "Pending" else "Pending"
            run_query("UPDATE loans SET status=? WHERE id=?", (new_st, row['id']))
            st.rerun()
        
        if cols[4].button("🗑️ ဖျက်မည်", key=f"del_{row['id']}"):
            run_query("DELETE FROM loans WHERE id=?", (row['id'],))
            st.rerun()
