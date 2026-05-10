import sys
from pathlib import Path

# Ensure the package root is on the path so pages can import sibling modules
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from database import init_db
from seed_data import seed

st.set_page_config(
    page_title="Tax Code Creator",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Bootstrap DB on first run
init_db()
seed()

# Session-state defaults
if "company" not in st.session_state:
    st.session_state["company"] = None  # dict with id, acronym, name

st.sidebar.title("🧾 Tax Code Creator")
st.sidebar.caption("AP tax code mapping tool")

if st.session_state["company"]:
    c = st.session_state["company"]
    st.sidebar.success(f"**{c['acronym']}** — {c['name']}")
    if st.sidebar.button("Change company"):
        st.session_state["company"] = None
        st.rerun()
else:
    st.sidebar.warning("No company selected — go to **Company Setup**.")

st.title("Welcome to Tax Code Creator")
st.markdown(
    """
    Use the sidebar to navigate between pages:

    | Page | Purpose |
    |---|---|
    | **1 · Company Setup** | Register or load your company |
    | **2 · Tax Codes** | Assign your company's codes to scenarios |
    | **3 · Admin** | Add / manage scenarios (password protected) |
    | **4 · Export** | View and download your tax code mapping |

    ---
    **How it works**

    Each tax scenario is defined by a set of dimensions — recipient country, transaction type,
    tax type, tax rate, supplier location, item nature and VAT treatment.
    Default codes start with `HY` (e.g. `HY01`). You replace these with your company's own codes
    and export the result as an Excel file.
    """
)
