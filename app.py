import streamlit as st
import pandas as pd
from datetime import datetime, time
from database import get_data, update_data
from logic import calculate_billable_hours

st.set_page_config(page_title="Work Logger Pro", layout="wide")

# Fetch both sheets
df_entries = get_data("entries")
df_clients = get_data("clients")

# --- SIDEBAR: INPUT ---
with st.sidebar:
    st.header("Add New Entry")
    
    # Dropdown for clients
    if not df_clients.empty:
        client_list = df_clients['client_name'].tolist()
        selected_client = st.selectbox("Select Client", client_list)
        
        # Automatically find the rate for the selected client
        client_info = df_clients[df_clients['client_name'] == selected_client].iloc[0]
        current_rate = client_info['hourly_rate']
        st.info(f"Rate: ${current_rate}/hr")
    else:
        st.warning("Please add a client in the Management tab first.")
        selected_client = None

    date = st.date_input("Date", datetime.now())
    col1, col2 = st.columns(2)
    start = col1.time_input("Start", time(9, 0)) 
    end = col2.time_input("End", time(17, 0))
    lunch = st.number_input("Lunch (mins)", value=30, step=5)
    notes = st.text_area("Notes")

    if st.button("Save Entry") and selected_client:
        new_row = {
            "date": date.strftime("%Y-%m-%d"),
            "client_name": selected_client,
            "start_time": start.strftime("%I:%M %p"),
            "end_time": end.strftime("%I:%M %p"),
            "lunch_mins": int(lunch),
            "notes": notes,
            "billing_rate": float(current_rate),
            "status": "Pending"
        }
        df_entries = pd.concat([df_entries, pd.DataFrame([new_row])], ignore_index=True)
        update_data(df_entries, "entries")
        st.success("Entry Saved!")
        st.rerun()

# --- MAIN AREA ---
tab_manage, tab_report, tab_clients = st.tabs(["📋 Manage Entries", "📊 Reporting", "🏢 Client Management"])

with tab_manage:
    st.subheader("Time Entries")
    edited_entries = st.data_editor(df_entries, num_rows="dynamic", use_container_width=True)
    if st.button("Save Entry Changes"):
        update_data(edited_entries, "entries")
        st.rerun()

with tab_report:
    st.header("Monthly Reporting")
    if not df_entries.empty:
        # Filter for only Pending items
        pending_df = df_entries[df_entries['status'] == 'Pending']
        
        if not pending_df.empty:
            clients_in_pending = pending_df['client_name'].unique()
            selected_report_client = st.selectbox("Select Client for Report", [""] + list(clients_in_pending))

            if selected_report_client:
                report_df = pending_df[pending_df['client_name'] == selected_report_client].copy()
                
                # Use the logic from our logic.py file
                report_df['hrs'] = report_df.apply(
                    lambda x: calculate_billable_hours(x['start_time'], x['end_time'], x['lunch_mins']), 
                    axis=1
                )
                
                total_hrs = report_df['hrs'].sum()
                # Get rate from the entry (which was saved from the client list)
                current_rate = report_df['billing_rate'].iloc[0]
                total_cash = total_hrs * current_rate

                c1, c2 = st.columns(2)
                c1.metric("Total Hours", f"{total_hrs} hrs")
                c2.metric("Total Billable", f"${total_cash:,.2f}")

                # Format description for Wave
                invoice_text = f"INVOICE SUMMARY: {selected_report_client}\n" + "-"*30 + "\n"
                for _, row in report_df.iterrows():
                    invoice_text += f"{row['date']} | {row['start_time']}-{row['end_time']} | {row['notes']}\n"
                
                st.text_area("Wave Description (Copy/Paste)", value=invoice_text, height=200)
                
                if st.button("Mark All as Invoiced"):
                    # Update status for these specific entries
                    df_entries.loc[df_entries['client_name'] == selected_report_client, 'status'] = 'Invoiced'
                    update_data(df_entries, "entries")
                    st.success(f"Updated {selected_report_client} entries to 'Invoiced'!")
                    st.rerun()
        else:
            st.info("No 'Pending' entries found. Everything is currently invoiced!")
    else:
        st.warning("No entries found in the database.")