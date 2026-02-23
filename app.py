import streamlit as st
import pandas as pd
from datetime import datetime, time
from database import get_data, update_data
from logic import calculate_billable_hours

st.set_page_config(page_title="Work Logger Pro", layout="wide")

# Fetch data using our new module
df = get_data()

# --- SIDEBAR: INPUT ---
with st.sidebar:
    st.header("Add New Entry")
    client = st.text_input("Client Name")
    rate = st.number_input("Hourly Rate ($)", value=50.0, step=5.0)
    date = st.date_input("Date", datetime.now())
    
    col1, col2 = st.columns(2)
    start = col1.time_input("Start", time(9, 0)) 
    end = col2.time_input("End", time(17, 0))
    st.caption(f"Saving as: **{start.strftime('%I:%M %p')}** to **{end.strftime('%I:%M %p')}**")
    
    lunch = st.number_input("Lunch (mins)", value=30, step=5)
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
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            update_data(df)
            st.success(f"Saved {client} entry!")
            st.rerun()

# --- MAIN AREA ---
st.title("⏱️ Work Logger")

# Use Tabs to keep the screen clean on mobile
tab_manage, tab_report = st.tabs(["📋 Manage Entries", "📊 Reporting"])

with tab_manage:
    st.subheader("All Entries")
    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
    if st.button("Save Changes / Deletions"):
        update_data(edited_df)
        st.success("Google Sheet Updated!")
        st.rerun()

with tab_report:
    st.header("Monthly Reporting")
    if not df.empty:
        pending_df = df[df['status'] == 'Pending']
        clients = pending_df['client_name'].unique()
        selected_client = st.selectbox("Select Client", [""] + list(clients))

        if selected_client:
            report_df = pending_df[pending_df['client_name'] == selected_client].copy()
            
            # Use the logic from our logic.py file
            report_df['hrs'] = report_df.apply(
                lambda x: calculate_billable_hours(x['start_time'], x['end_time'], x['lunch_mins']), 
                axis=1
            )
            
            total_hrs = report_df['hrs'].sum()
            total_cash = total_hrs * report_df['billing_rate'].iloc[0]

            c1, c2 = st.columns(2)
            c1.metric("Total Hours", f"{total_hrs} hrs")
            c2.metric("Total Billable", f"${total_cash:,.2f}")

            invoice_text = f"INVOICE SUMMARY: {selected_client}\n" + "-"*30 + "\n"
            for _, row in report_df.iterrows():
                invoice_text += f"{row['date']} | {row['start_time']}-{row['end_time']} | {row['notes']}\n"
            
            st.text_area("Wave Description", value=invoice_text, height=200)