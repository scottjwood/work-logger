import streamlit as st
import pandas as pd
from datetime import datetime, time
from database import get_data, update_data
from logic import calculate_billable_hours
import streamlit_authenticator as stauth

# 1. MUST be the first Streamlit command
st.set_page_config(page_title="Work Logger Pro", layout="wide")

# --- SIMPLE SECURE LOGIN ---
# We define the user data directly for clarity
credentials = {
    "usernames": {
        "admin": {
            "name": "Admin",
            "password": st.secrets["password"]
        }
    }
}

authenticator = stauth.Authenticate(
    credentials,
    "work_logger_cookie",
    "signature_key",
    cookie_expiry_days=30
)

# Render the login widget
# Note: 'location' moved to the Authenticate object in some versions, 
# but calling it here is usually safest.
authentication_status = authenticator.login()

if st.session_state.get("authentication_status"):
    authenticator.logout(location="sidebar")
    st.sidebar.success(f"Welcome, {st.session_state['name']}")
elif st.session_state.get("authentication_status") is False:
    st.error("Username/password is incorrect")
    st.stop()
elif st.session_state.get("authentication_status") is None:
    st.warning("Please enter your username and password")
    st.stop()

# --- IF WE GET HERE, THE USER IS LOGGED IN ---
st.sidebar.success(f"Welcome, {name}")
authenticator.logout(location="sidebar")

# Fetch both sheets
df_entries = get_data("entries")
df_clients = get_data("clients")

# --- SIDEBAR: INPUT ---
with st.sidebar:
    st.success(f"Hello, {user_name}!")
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
        pending_df = df_entries[df_entries['status'] == 'Pending']
        if not pending_df.empty:
            clients_in_pending = pending_df['client_name'].unique()
            selected_report_client = st.selectbox("Select Client for Report", [""] + list(clients_in_pending))
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
                c2.metric("Total Billable", f"${total_cash:,.2f}")
                invoice_text = f"INVOICE SUMMARY: {selected_report_client}\n" + "-"*30 + "\n"
                for _, row in report_df.iterrows():
                    invoice_text += f"{row['date']} | {row['start_time']}-{row['end_time']} | {row['notes']}\n"
                st.text_area("Wave Description (Copy/Paste)", value=invoice_text, height=200)
                if st.button("Mark All as Invoiced"):
                    df_entries.loc[df_entries['client_name'] == selected_report_client, 'status'] = 'Invoiced'
                    update_data(df_entries, "entries")
                    st.success(f"Updated {selected_report_client} entries!")
                    st.rerun()
        else:
            st.info("No 'Pending' entries found.")
    else:
        st.warning("No entries found.")

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