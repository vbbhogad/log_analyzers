import streamlit as st

st.set_page_config(page_title="EMon & McUtils Log Analysis", layout="wide")
st.title("Welcome to the EMon & McUtils Log Analysis App")
st.write(
    """
    Use the sidebar to navigate to the log analysis tools.
    - **McUtils Log Analysis**: Analyze memory controller bandwidth logs.
    - **EMON Log Analysis**: Analyze EMON logs (coming soon).
    - **Ethtools Log Analysis**: Analyze Ethtools logs (coming soon).
    """
)
