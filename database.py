import streamlit as st
from streamlit_gsheets import GSheetsConnection

def get_data():
    """Fetches the latest data from Google Sheets."""
    conn = st.connection("gsheets", type=GSheetsConnection)
    return conn.read(ttl=0)

def update_data(df):
    """Overwrites the Google Sheet with a new dataframe."""
    conn = st.connection("gsheets", type=GSheetsConnection)
    conn.update(data=df)