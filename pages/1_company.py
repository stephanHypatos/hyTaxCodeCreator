import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from database import get_companies, get_company_by_acronym, upsert_company

st.set_page_config(page_title="Company Setup", page_icon="🏢", layout="wide")
st.title("🏢 Company Setup")
st.caption("Register your company or load an existing configuration.")

tab_new, tab_load = st.tabs(["New / Update Company", "Load Existing Company"])

# ── Tab 1: New / Update ────────────────────────────────────────────────────
with tab_new:
    st.subheader("Register your company")
    st.info(
        "Your company acronym and name are used to store and retrieve your tax code mapping. "
        "If the acronym already exists, the name will be updated."
    )

    with st.form("company_form"):
        col1, col2 = st.columns(2)
        with col1:
            acronym = st.text_input(
                "Company Acronym *",
                max_chars=6,
                placeholder="e.g. ACME",
                help="Up to 6 characters, will be stored in uppercase.",
            )
        with col2:
            name = st.text_input(
                "Company Name *",
                placeholder="e.g. ACME GmbH",
            )
        submitted = st.form_submit_button("Save & Select", type="primary")

    if submitted:
        acronym = acronym.strip().upper()
        name = name.strip()
        if not acronym:
            st.error("Acronym is required.")
        elif not name:
            st.error("Company name is required.")
        else:
            company = upsert_company(acronym, name)
            st.session_state["company"] = company
            st.success(f"Company **{acronym}** — {name} saved and selected.")
            st.balloons()

# ── Tab 2: Load Existing ───────────────────────────────────────────────────
with tab_load:
    st.subheader("Load an existing company")
    companies = get_companies()

    if not companies:
        st.info("No companies registered yet. Use the 'New / Update Company' tab to create one.")
    else:
        options = {f"{c['acronym']} — {c['name']}": c for c in companies}
        choice = st.selectbox("Select company", list(options.keys()))

        if st.button("Load selected company", type="primary"):
            company = options[choice]
            st.session_state["company"] = company
            st.success(f"Loaded **{company['acronym']}** — {company['name']}.")

# ── Current state banner ───────────────────────────────────────────────────
st.divider()
if st.session_state.get("company"):
    c = st.session_state["company"]
    st.success(
        f"✅ Active company: **{c['acronym']}** — {c['name']}  \n"
        "You can now navigate to **Tax Codes** to assign your codes."
    )
else:
    st.warning("No company selected yet.")
