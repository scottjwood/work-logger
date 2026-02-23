import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

def get_data(worksheet_name="entries"):
    """Fetches data with a fallback to prevent 'Empty Data' errors."""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet=worksheet_name, ttl=0)
        
        # If the sheet exists but has NO data, return a structured empty DataFrame
        if df is None or df.empty:
            if worksheet_name == "clients":
                return pd.DataFrame(columns=["client_name", "hourly_rate"])
            else:
                return pd.DataFrame(columns=["date", "client_name", "start_time", "end_time", "lunch_mins", "notes", "billing_rate", "status"])
        return df
    except Exception:
        # If the worksheet doesn't even exist yet, return the structure
        if worksheet_name == "clients":
            return pd.DataFrame(columns=["client_name", "hourly_rate"])
        return pd.DataFrame(columns=["date", "client_name", "start_time", "end_time", "lunch_mins", "notes", "billing_rate", "status"])

def update_data(df, worksheet_name="entries"):
    conn = st.connection("gsheets", type=GSheetsConnection)
    conn.update(worksheet=worksheet_name, data=df)