import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
from database import (
    get_distinct_countries,
    get_scenarios,
    get_company_taxcodes,
    upsert_taxcodes,
    count_assigned,
)
from utils.constants import VAT_TREATMENT_LABELS, COUNTRY_NAMES

st.set_page_config(page_title="Tax Codes", page_icon="📋", layout="wide")
st.title("📋 Tax Code Assignment")

# ── Guard ──────────────────────────────────────────────────────────────────
company = st.session_state.get("company")
if not company:
    st.warning("Please select a company first on the **Company Setup** page.")
    st.stop()

company_id = company["id"]
st.caption(f"Company: **{company['acronym']}** — {company['name']}")

# ── Country selector ───────────────────────────────────────────────────────
countries = get_distinct_countries()
if not countries:
    st.error("No scenarios in the database. Ask an admin to add scenarios.")
    st.stop()

country_options = {
    f"{c} — {COUNTRY_NAMES.get(c, c)}": c for c in countries
}
selected_label = st.selectbox("Recipient Country", list(country_options.keys()))
selected_country = country_options[selected_label]

# ── Load scenarios + existing company codes ────────────────────────────────
scenarios = get_scenarios(country=selected_country)
existing_codes = get_company_taxcodes(company_id)

if not scenarios:
    st.info(f"No active scenarios for {selected_country}.")
    st.stop()

# Build display dataframe
rows = []
for s in scenarios:
    rows.append({
        "id": s["id"],
        "Default Tax Code": s["default_code"],
        "Scenario Name": s["scenario_name"],
        "VAT Treatment": VAT_TREATMENT_LABELS.get(s["vat_treatment"], s["vat_treatment"]),
        "Tax Type": s["tax_type"],
        "Tax Rate": f"{s['tax_rate']*100:.1f}%" if s["tax_rate"] is not None else "—",
        "Supplier Location": s["supplier_location"] or "—",
        "Item Nature": s["item_nature"] or "—",
        "Transaction Type": s["transaction_type"],
        "Notes": s["notes"] or "",
        "Company Tax Code": existing_codes.get(s["id"], ""),
    })

df = pd.DataFrame(rows)

# ── Summary metrics ────────────────────────────────────────────────────────
total = len(scenarios)
assigned = count_assigned(company_id)
col1, col2, col3 = st.columns(3)
col1.metric("Total Scenarios", total)
col2.metric("Codes Assigned (all countries)", assigned)
col3.metric("Scenarios This Country", total)

st.divider()
st.subheader(f"Scenarios for {selected_country} — {COUNTRY_NAMES.get(selected_country, '')}")
st.info(
    "Edit the **Company Code** column with your company's internal tax codes. "
    "Click **Save Changes** when done. Leave blank to keep the default HY code."
)

# ── Editable table ─────────────────────────────────────────────────────────
display_cols = [
    "Default Tax Code", "Scenario Name", "VAT Treatment",
    "Tax Type", "Tax Rate", "Supplier Location", "Item Nature",
    "Transaction Type", "Notes", "Company Tax Code",
]

column_config = {
    "Default Tax Code":  st.column_config.TextColumn("Default Tax Code", disabled=True, width="small"),
    "Scenario Name":     st.column_config.TextColumn("Scenario", disabled=True, width="large"),
    "VAT Treatment":     st.column_config.TextColumn("VAT Treatment", disabled=True, width="large"),
    "Tax Type":          st.column_config.TextColumn("Tax Type", disabled=True, width="small"),
    "Tax Rate":          st.column_config.TextColumn("Tax Rate", disabled=True, width="small"),
    "Supplier Location": st.column_config.TextColumn("Supplier", disabled=True, width="small"),
    "Item Nature":       st.column_config.TextColumn("Item Nature", disabled=True, width="small"),
    "Transaction Type":  st.column_config.TextColumn("Tx Type", disabled=True, width="small"),
    "Notes":             st.column_config.TextColumn("Notes", disabled=True, width="medium"),
    "Company Tax Code":  st.column_config.TextColumn(
        "Company Tax Code ✏️",
        help="Enter your company's internal AP tax code here",
        width="small",
    ),
}

edited_df = st.data_editor(
    df[display_cols],
    column_config=column_config,
    use_container_width=True,
    hide_index=True,
    num_rows="fixed",
    key=f"editor_{selected_country}",
)

# ── Save ───────────────────────────────────────────────────────────────────
if st.button("💾 Save Changes", type="primary"):
    id_col = df["id"].tolist()
    new_codes_col = edited_df["Company Tax Code"].tolist()
    codes_to_save = {
        scenario_id: code
        for scenario_id, code in zip(id_col, new_codes_col)
        if str(code).strip()
    }
    upsert_taxcodes(company_id, codes_to_save)
    st.success(f"Saved {len(codes_to_save)} code(s) for **{company['acronym']}**.")
    st.rerun()
