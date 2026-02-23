import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, time

# --- DATABASE HELPERS ---
def get_connection():
    return sqlite3.connect('tracker.db', check_same_thread=False)

def init_db_in_app():
    """Creates the table if it doesn't exist so you never get that error again."""
    conn = get_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE,
            client_name TEXT,
            start_time TEXT,
            end_time TEXT,
            lunch_mins INTEGER,
            notes TEXT,
            billing_rate REAL DEFAULT 0.0,
            status TEXT DEFAULT 'Pending'
        )
    ''')
    conn.commit()
    conn.close()

# Run the initialization
init_db_in_app()

def run_query(query, params=()):
    with get_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)

def execute_db(query, params=()):
    with get_connection() as conn:
        conn.execute(query, params)
        conn.commit()

# --- APP UI ---
st.set_page_config(page_title="Work Logger", layout="wide")
st.title("⏱️ My Work Logger")

# --- 1. UPDATED INPUT SECTION (Sidebar) ---
with st.sidebar:
    st.header("Add New Entry")
    client = st.text_input("Client Name")
    billing_rate = st.number_input("Hourly Rate ($)", value=50.0, step=5.0)
    date = st.date_input("Date", datetime.now())
    
    col1, col2 = st.columns(2)
    start = col1.time_input("Start", time(9, 0)) 
    end = col2.time_input("End", time(17, 0))
    
    # --- ADD THIS: Live Preview of the 12-hour time ---
    st.caption(f"Saving as: {start.strftime('%I:%M %p')} to {end.strftime('%I:%M %p')}")
    
    lunch = st.number_input("Lunch (minutes)", value=30, step=5)
    notes = st.text_area("Notes/Tasks")

    if st.button("Save Entry"):
        if client:
            # We ensure the string saved to the DB is 12-hour format
            start_str = start.strftime("%I:%M %p")
            end_str = end.strftime("%I:%M %p")
            
            execute_db('''
                INSERT INTO entries (date, client_name, start_time, end_time, lunch_mins, notes, billing_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (date.strftime("%Y-%m-%d"), client, start_str, end_str, lunch, notes, billing_rate))
            st.success(f"Saved: {start_str} - {end_str}")
        else:
            st.error("Please enter a client name.")

# 2. VIEW DATA SECTION
st.header("Current Entries (Pending)")

# Load data from DB
df = run_query("SELECT * FROM entries WHERE status = 'Pending'")

if not df.empty:
    # Convert times to calculation-friendly format
    df['Start'] = pd.to_datetime(df['start_time'], format='%H:%M').dt.time
    df['End'] = pd.to_datetime(df['end_time'], format='%H:%M').dt.time
    
    # Show the table
    st.dataframe(df[['date', 'client_name', 'start_time', 'end_time', 'lunch_mins', 'notes']], use_container_width=True)
else:
    st.info("No pending entries found. Add one in the sidebar!")

# --- REPORTING & WAVE SECTION ---
st.divider()
st.header("Monthly Reporting")

# 1. Filter by Client
unique_clients = run_query("SELECT DISTINCT client_name FROM entries WHERE status = 'Pending'")
selected_client = st.selectbox("Select Client for Report", unique_clients['client_name'].tolist())

if selected_client:
    report_df = run_query("SELECT * FROM entries WHERE client_name = ? AND status = 'Pending'", (selected_client,))
    
    if not report_df.empty:
        def calculate_totals(row):
            fmt = "%I:%M %p" # 12-hour format logic
            start = datetime.strptime(row['start_time'], fmt)
            end = datetime.strptime(row['end_time'], fmt)
            
            # Math: (End - Start) - Lunch
            delta = (end - start).total_seconds() / 3600
            billable_hrs = round(delta - (row['lunch_mins'] / 60), 2)
            total_money = round(billable_hrs * row['billing_rate'], 2)
            return pd.Series([billable_hrs, total_money])

        report_df[['hrs', 'total_cost']] = report_df.apply(calculate_totals, axis=1)
        
        # Display Totals
        total_hrs = report_df['hrs'].sum()
        total_inv = report_df['total_cost'].sum()
        
        st.metric("Total Hours", f"{total_hrs} hrs")
        st.metric("Total Billable", f"${total_inv:,.2f}") # Formats as $1,234.56
        
        # Wave Text Block
        invoice_text = f"TOTAL INVOICE: ${total_inv:,.2f}\n" + "-"*30 + "\n"
        for _, row in report_df.iterrows():
            invoice_text += f"{row['date']} | {row['start_time']}-{row['end_time']} | {row['hrs']} hrs @ ${row['billing_rate']}/hr | {row['notes']}\n"
        
        st.text_area("Copy into Wave:", value=invoice_text, height=200)

        # 3. ARCHIVE BUTTON
        if st.button(f"Mark {selected_client} Entries as Invoiced"):
            execute_db("UPDATE entries SET status = 'Invoiced' WHERE client_name = ? AND status = 'Pending'", (selected_client,))
            st.success(f"Archived {len(report_df)} entries for {selected_client}!")
            st.rerun() # Refresh the app to clear the table 