import streamlit as st
import pandas as pd
from datetime import datetime, time
from database import get_data, update_data
from logic import calculate_billable_hours

# 1. MUST be the first Streamlit command
st.set_page_config(page_title="Work Logger Pro", layout="wide")

# --- LOGIN SESSION STATE ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# --- MAIN PAGE LOGIN SCREEN ---
if not st.session_state.authenticated:
    st.title("🔐 Work Logger Pro")
    st.markdown("### Design Portal Login")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        user_input = st.text_input("Username")
        pw_input = st.text_input("Password", type="password")
        if st.button("Login", use_container_width=True):
            if user_input == "admin" and pw_input == st.secrets["password"]:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect Username or Password")
    st.stop()

# --- IF WE GET HERE, THE USER IS LOGGED IN ---
name = "Admin"

# Fetch data
df_entries = get_data("entries")
df_clients = get_data("clients")

# Global Cleanups
df_entries['notes'] = df_entries['notes'].fillna('')

# --- SIDEBAR: INPUT ---
with st.sidebar:
    st.title("Work Logger")
    st.write(f"Logged in as: **{name}**")
    if st.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()
        
    st.divider()
    st.header("Add New Entry")
    
    if not df_clients.empty:
        client_list = df_clients['client_name'].tolist()
        selected_client = st.selectbox("Select Client", client_list)
        client_info = df_clients[df_clients['client_name'] == selected_client].iloc[0]
        current_rate = client_info['hourly_rate']
        st.info(f"Rate: ${current_rate}/hr")
    else:
        st.warning("Please add a client in the Management tab first.")
        selected_client = None

    date = st.date_input("Date", datetime.now(), format="MM-DD-YYYY")
    col1, col2 = st.columns(2)
    start = col1.time_input("Start", time(9, 0)) 
    end = col2.time_input("End", time(17, 0))
    lunch = st.number_input("Lunch (mins)", value=30, step=5)
    notes = st.text_area("Notes")

    if st.button("Save Entry", use_container_width=True) and selected_client:
        new_row = {
            "date": date.strftime("%m-%d-%Y"), # YOUR NEW FORMAT
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
tab_manage, tab_report, tab_history, tab_clients = st.tabs([
    "📋 Manage Pending", 
    "📊 Generate Report", 
    "📜 History",
    "🏢 Client Management"
])

with tab_manage:
    st.subheader("Filter Pending Entries")
    if not df_clients.empty:
        manage_client_list = ["All Clients"] + df_clients['client_name'].tolist()
        filter_client = st.selectbox("View Pending for:", manage_client_list, key="manage_filter")
        
        pending_mask = df_entries['status'] == 'Pending'
        if filter_client != "All Clients":
            display_df = df_entries[pending_mask & (df_entries['client_name'] == filter_client)]
        else:
            display_df = df_entries[pending_mask]
            
        st.write(f"Showing **{len(display_df)}** pending entries.")
        edited_entries = st.data_editor(display_df, num_rows="dynamic", use_container_width=True, key="pending_editor")
        
        if st.button("Save Changes to Pending"):
            df_entries.loc[display_df.index, :] = edited_entries
            update_data(df_entries, "entries")
            st.success("Changes saved!")
            st.rerun()
    else:
        st.info("Add clients to start managing entries.")

with tab_report:
    st.header("Monthly Reporting")
    if not df_entries.empty:
        pending_df = df_entries[df_entries['status'] == 'Pending']
        if not pending_df.empty:
            clients_in_pending = pending_df['client_name'].unique()
            selected_report_client = st.selectbox("Select Client for Report", [""] + list(clients_in_pending), key="report_select")
            
            if selected_report_client:
                report_df = pending_df[pending_df['client_name'] == selected_report_client].copy()
                report_df['hrs'] = report_df.apply(
                    lambda x: calculate_billable_hours(x['start_time'], x['end_time'], x['lunch_mins']), 
                    axis=1
                )
                
                total_hrs = report_df['hrs'].sum()
                current_rate = report_df['billing_rate'].iloc[0]
                total_cash = total_hrs * current_rate
                
                c1, c2 = st.columns(2)
                c1.metric("Total Hours", f"{total_hrs} hrs")
                c2.metric("Billable Amount", f"${total_cash:,.2f}", delta=f"Rate: ${current_rate}/hr", delta_color="normal")
                
                # DATE RANGE LOGIC FOR MM-DD-YYYY
                temp_dates = pd.to_datetime(report_df['date'], format='%m-%d-%Y')
                
                invoice_text = f"INVOICE SUMMARY: {selected_report_client}\n"
                invoice_text += f"Period: {temp_dates.min().strftime('%m-%d-%Y')} to {temp_dates.max().strftime('%m-%d-%Y')}\n"
                invoice_text += f"Total Hours: {total_hrs} | Rate: {current_rate} | Total Amount: ${total_cash:,.2f}\n"
                invoice_text += "-"*30 + "\n"
                
                for _, row in report_df.iterrows():
                    row_hrs = calculate_billable_hours(row['start_time'], row['end_time'], row['lunch_mins'])
                    note_content = str(row['notes']) if row['notes'] != "" else ""
                    invoice_text += f"{row['date']} | {row_hrs} hrs | {note_content}\n"
                
                invoice_text += "-"*30 + "\n"
                invoice_text += f"GRAND TOTAL: {total_hrs} hrs"

                st.text_area("Wave Description (Copy/Paste)", value=invoice_text, height=250)
                st.link_button("Go to Wave Invoices ↗️", "https://next.waveapps.com/e9bfc2ca-dac3-48a0-83b0-d66a9fadc43a/invoices")

                if st.button("Mark All as Invoiced"):
                    today_str = datetime.now().strftime("%m-%d-%Y") # CONSISTENT FORMAT
                    mask = (df_entries['client_name'] == selected_report_client) & (df_entries['status'] == 'Pending')
                    df_entries.loc[mask, 'invoiced_date'] = today_str
                    df_entries.loc[mask, 'status'] = 'Invoiced'
                    update_data(df_entries, "entries")
                    st.success(f"Success! {selected_report_client} marked as invoiced on {today_str}.")
                    st.rerun()
        else:
            st.info("No 'Pending' entries found to report.")
    else:
        st.warning("No entries found in database.")

with tab_history:
    st.header("Invoiced History")
    invoiced_df = df_entries[df_entries['status'] == 'Invoiced']
    
    if not invoiced_df.empty:
        col1, col2 = st.columns(2)
        with col1:
            h_client = st.selectbox("Select Client", ["All"] + list(invoiced_df['client_name'].unique()), key="h_client")
        
        current_h_df = invoiced_df.copy()
        if h_client != "All":
            current_h_df = current_h_df[current_h_df['client_name'] == h_client]
            
        with col2:
            # CHRONOLOGICAL SORTING FOR MM-DD-YYYY
            if not current_h_df.empty and 'invoiced_date' in current_h_df.columns:
                real_dates = pd.to_datetime(current_h_df['invoiced_date'], format='%m-%d-%Y', errors='coerce')
                sorted_unique = sorted(real_dates.dropna().unique(), reverse=True)
                available_dates = ["All Dates"] + [d.strftime('%m-%d-%Y') for d in sorted_unique]
            else:
                available_dates = ["All Dates"]
            h_date = st.selectbox("Select Invoice Date", available_dates, key="h_date")
            
        if h_date != "All Dates":
            current_h_df = current_h_df[current_h_df['invoiced_date'] == h_date]
            
        st.dataframe(current_h_df, use_container_width=True)
    else:
        st.info("No invoice history found yet.")

with tab_clients:
    st.header("Client Settings")
    with st.expander("➕ Add New Client"):
        with st.form("new_client_form", clear_on_submit=True):
            new_name = st.text_input("Client Name")
            new_rate = st.number_input("Default Hourly Rate", min_value=0.0, value=50.0, step=5.0)
            submit_client = st.form_submit_button("Add Client")
            if submit_client and new_name:
                new_c_row = pd.DataFrame([{"client_name": new_name, "hourly_rate": new_rate}])
                df_clients = pd.concat([df_clients, new_c_row], ignore_index=True)
                update_data(df_clients, "clients")
                st.success(f"Added {new_name}!")
                st.rerun()
    st.divider()
    st.subheader("Existing Clients")
    edited_clients = st.data_editor(
        df_clients, 
        num_rows="dynamic", 
        use_container_width=True,
        column_config={"hourly_rate": st.column_config.NumberColumn(format="$%.2f")}
    )
    if st.button("Save Changes to Client List"):
        update_data(edited_clients, "clients")
        st.success("Changes saved!")
        st.rerun()