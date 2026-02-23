import streamlit as st
from streamlit_gsheets import GSheetsConnection

def get_data(worksheet_name="entries"):
    """Fetches data from a specific worksheet."""
    conn = st.connection("gsheets", type=GSheetsConnection)
    # We use the worksheet parameter to switch between tabs
    return conn.read(worksheet=worksheet_name, ttl=0)

def update_data(df, worksheet_name="entries"):
    """Updates a specific worksheet."""
    conn = st.connection("gsheets", type=GSheetsConnection)
    conn.update(worksheet=worksheet_name, data=df)