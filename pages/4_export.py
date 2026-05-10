import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date
import streamlit as st
import pandas as pd
from database import get_full_mapping, count_assigned, get_distinct_countries, get_country_codes
from utils.constants import VAT_TREATMENT_LABELS, COUNTRY_NAMES
from utils.excel_export import build_excel

st.set_page_config(page_title="Export", page_icon="📤", layout="wide")
st.title("📤 Export Tax Code Mapping")

# ── Guard ──────────────────────────────────────────────────────────────────
company = st.session_state.get("company")
if not company:
    st.warning("Please select a company first on the **Company Setup** page.")
    st.stop()

company_id = company["id"]
assigned = count_assigned(company_id)

st.caption(f"Company: **{company['acronym']}** — {company['name']}")

if assigned == 0:
    st.warning(
        "No codes assigned yet. Go to **Tax Codes** to assign at least one company code before exporting."
    )

# ── Filters ────────────────────────────────────────────────────────────────
countries = get_distinct_countries()
country_opts = ["All countries"] + [f"{c} — {COUNTRY_NAMES.get(c, c)}" for c in countries]
filter_label = st.selectbox("Filter by country (optional)", country_opts)
filter_country = None if filter_label == "All countries" else filter_label.split(" — ")[0]

show_unassigned = st.checkbox("Include scenarios without a company code", value=True)

# ── Load data ──────────────────────────────────────────────────────────────
all_rows = get_full_mapping(company_id)

if filter_country:
    all_rows = [r for r in all_rows if r["recipient_country"] == filter_country]

if not show_unassigned:
    all_rows = [r for r in all_rows if r["company_code"]]

if not all_rows:
    st.info("No rows to display with the current filters.")
    st.stop()

# ── Display dataframe ──────────────────────────────────────────────────────
st.divider()
st.subheader("Preview")

df = pd.DataFrame([
    {
        "Country":          r["recipient_country"],
        "Tx Type":          r["transaction_type"],
        "Tax Type":         r["tax_type"],
        "Tax Rate":         f"{r['tax_rate']*100:.2f}%" if r["tax_rate"] is not None else "—",
        "Supplier":         r["supplier_location"] or "—",
        "Item":             r["item_nature"] or "—",
        "VAT Treatment":    VAT_TREATMENT_LABELS.get(r["vat_treatment"], r["vat_treatment"]),
        "Scenario":         r["scenario_name"],
        "Default Tax Code": r["default_code"],
        "Company Tax Code": r["company_code"] if r["company_code"] else "⚠️ not set",
        "Notes":            r["notes"] or "",
    }
    for r in all_rows
])

st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Company Tax Code": st.column_config.TextColumn("Company Tax Code", width="small"),
        "Default Tax Code": st.column_config.TextColumn("Default Tax Code", width="small"),
        "Country":      st.column_config.TextColumn("Country", width="small"),
        "Tax Rate":     st.column_config.TextColumn("Tax Rate", width="small"),
        "Supplier":     st.column_config.TextColumn("Supplier", width="small"),
        "Item":         st.column_config.TextColumn("Item", width="small"),
    },
)

assigned_count = sum(1 for r in all_rows if r["company_code"])
col1, col2, col3 = st.columns(3)
col1.metric("Rows shown", len(all_rows))
col2.metric("Company codes assigned", assigned_count)
col3.metric("Not yet assigned", len(all_rows) - assigned_count)

# ── Excel download ─────────────────────────────────────────────────────────
st.divider()
st.subheader("Download Excel")

eu_codes     = get_country_codes("EU")
non_eu_codes = get_country_codes("NonEU")
excel_bytes  = build_excel(all_rows, company, eu_codes, non_eu_codes, filter_country)
filename = f"{company['acronym']}_taxcodes_{date.today().isoformat()}.xlsx"

st.download_button(
    label="⬇️ Download Excel",
    data=excel_bytes,
    file_name=filename,
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    type="primary",
)
expanded_count = sum(
    len([c for c in eu_codes if c != r["recipient_country"]]) if r["supplier_location"] == "EU"
    else len([c for c in non_eu_codes if c != r["recipient_country"]]) if r["supplier_location"] == "NonEU"
    else 1
    for r in all_rows
)
st.caption(
    f"File: `{filename}` · 3 sheets · "
    f"Sheet 1: {len(all_rows)} scenarios · "
    f"Sheet 3: {expanded_count} expanded rows (EU/NonEU resolved per country)"
)
