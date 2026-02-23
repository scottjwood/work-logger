import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, time

st.set_page_config(page_title="Work Logger Pro", layout="wide")

# --- CONNECT TO GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Read the data (ttl=0 ensures it doesn't cache old data)
df = conn.read(ttl=0)

# --- SIDEBAR: INPUT ---
with st.sidebar:
    st.header("Add New Entry")
    client = st.text_input("Client Name")
    rate = st.number_input("Hourly Rate ($)", value=50.0)
    date = st.date_input("Date", datetime.now())
    
    col1, col2 = st.columns(2)
    start = col1.time_input("Start", time(9, 0)) 
    end = col2.time_input("End", time(17, 0))
    
    lunch = st.number_input("Lunch (mins)", value=30)
    notes = st.text_area("Notes")

    if st.button("Save to Sheets"):
        if client:
            new_row = {
                "date": date.strftime("%Y-%m-%d"),
                "client_name": client,
                "start_time": start.strftime("%I:%M %p"),
                "end_time": end.strftime("%I:%M %p"),
                "lunch_mins": int(lunch),
                "notes": notes,
                "billing_rate": float(rate),
                "status": "Pending"
            }
            # Add new row to existing data
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            conn.update(data=df)
            st.success("Saved!")
            st.rerun()
        else:
            st.error("Client name required")

# --- MAIN AREA: MANAGE & EDIT ---
st.title("⏱️ Work Logger")

st.subheader("All Entries")
st.write("Tip: Double click a cell to edit. Select a row and press 'Delete' to remove.")
# This editor allows you to change data and delete rows
edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)

if st.button("Save Changes / Deletions"):
    conn.update(data=edited_df)
    st.success("Google Sheet Updated!")
    st.rerun()

# --- REPORTING ---
st.divider()
st.header("Monthly Reporting")

if not df.empty:
    pending_df = df[df['status'] == 'Pending']
    clients = pending_df['client_name'].unique()
    selected_client = st.selectbox("Select Client for Report", [""] + list(clients))

    if selected_client:
        report_df = pending_df[pending_df['client_name'] == selected_client].copy()
        
        def calculate_hours(row):
            fmt = "%I:%M %p"
            try:
                s = datetime.strptime(row['start_time'], fmt)
                e = datetime.strptime(row['end_time'], fmt)
                diff = (e - s).total_seconds() / 3600
                return round(diff - (row['lunch_mins'] / 60), 2)
            except:
                return 0.0

        report_df['hrs'] = report_df.apply(calculate_hours, axis=1)
        total_hrs = report_df['hrs'].sum()
        total_cash = total_hrs * report_df['billing_rate'].iloc[0] if not report_df.empty else 0

        col1, col2 = st.columns(2)
        col1.metric("Total Hours", f"{total_hrs} hrs")
        col2.metric("Total Billable", f"${total_cash:,.2f}")

        # Wave Block
        invoice_text = f"INVOICE SUMMARY: {selected_client}\n" + "-"*30 + "\n"
        for _, row in report_df.iterrows():
            invoice_text += f"{row['date']} | {row['start_time']}-{row['end_time']} | {row['notes']}\n"
        
        st.text_area("Wave Description Copy/Paste", value=invoice_text, height=200)