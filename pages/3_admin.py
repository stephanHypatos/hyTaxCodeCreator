import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import streamlit as st
import pandas as pd
from database import (
    get_scenarios,
    add_scenario,
    update_scenario,
    delete_scenario,
    toggle_scenario_active,
    next_default_code,
    get_country_list,
    add_country_to_list,
    remove_country_from_list,
    get_vat_treatments,
    add_vat_treatment,
    update_vat_treatment,
    delete_vat_treatment,
    get_vat_treatment_labels,
)
from utils.constants import (
    TRANSACTION_TYPES,
    TAX_TYPES,
    SUPPLIER_LOCATIONS,
    ITEM_NATURES,
    COUNTRY_NAMES,
)

st.set_page_config(page_title="Admin", page_icon="🔧", layout="wide")
st.title("🔧 Admin — Scenario Management")

# ── Auth ───────────────────────────────────────────────────────────────────
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

if "admin_authed" not in st.session_state:
    st.session_state["admin_authed"] = False

if not st.session_state["admin_authed"]:
    st.info("This page is password protected.")
    pwd = st.text_input("Admin password", type="password", key="admin_pwd_input")
    if st.button("Unlock", type="primary"):
        if pwd == ADMIN_PASSWORD:
            st.session_state["admin_authed"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()

st.caption("Logged in as admin.")
if st.button("🔒 Lock admin"):
    st.session_state["admin_authed"] = False
    st.rerun()

st.divider()

tab_add, tab_manage, tab_countries, tab_vat = st.tabs([
    "➕ Add Scenario",
    "📑 Manage Scenarios",
    "🌍 Country Lists",
    "🏷️ VAT Treatments",
])

# ── Tab 1: Add Scenario ────────────────────────────────────────────────────
with tab_add:
    st.subheader("Add a new tax scenario")
    next_code = next_default_code()
    st.caption(f"Next default tax code will be: **{next_code}**")

    with st.form("add_scenario_form"):
        col1, col2 = st.columns(2)

        _vat_list = get_vat_treatments()
        _vat_normalized = [v["normalized_name"] for v in _vat_list]
        _vat_labels_map  = {v["normalized_name"]: v["display_name"] for v in _vat_list}

        with col1:
            existing_countries = sorted(set(
                [s["recipient_country"] for s in get_scenarios(active_only=False)]
            ))
            eu_codes = [r["country_code"] for r in get_country_list("EU")]
            non_eu_codes = [r["country_code"] for r in get_country_list("NonEU")]
            all_country_codes = sorted(set(existing_countries + eu_codes + non_eu_codes))
            country_opts = [f"{c} — {COUNTRY_NAMES.get(c, c)}" for c in all_country_codes]
            country_sel = st.selectbox("Recipient Country *", country_opts)
            recipient_country = country_sel.split(" — ")[0]

            transaction_type = st.selectbox("Transaction Type *", TRANSACTION_TYPES)
            tax_type = st.selectbox("Tax Type *", TAX_TYPES)
            tax_rate_input = st.text_input(
                "Tax Rate (as decimal, e.g. 0.19)",
                placeholder="Leave blank for NonTax",
            )

        with col2:
            supplier_location = st.selectbox("Supplier Location", SUPPLIER_LOCATIONS)
            item_nature = st.selectbox("Item Nature", ITEM_NATURES)
            vat_treatment = st.selectbox(
                "VAT Treatment *",
                _vat_normalized,
                format_func=lambda v: _vat_labels_map.get(v, v),
            )
            scenario_name = st.text_input(
                "Scenario Name *",
                placeholder="e.g. DE — Domestic goods 19%",
            )

        notes = st.text_area(
            "Notes (optional)",
            placeholder="Legal references, special conditions, etc.",
        )
        submitted = st.form_submit_button("Add Scenario", type="primary")

    if submitted:
        errors = []
        if not scenario_name.strip():
            errors.append("Scenario name is required.")
        if not recipient_country:
            errors.append("Recipient country is required.")

        tax_rate = None
        if tax_rate_input.strip():
            try:
                tax_rate = float(tax_rate_input.replace(",", "."))
            except ValueError:
                errors.append("Tax rate must be a number (e.g. 0.19).")

        if errors:
            for e in errors:
                st.error(e)
        else:
            new_id = add_scenario({
                "recipient_country": recipient_country,
                "transaction_type": transaction_type,
                "tax_type": tax_type,
                "tax_rate": tax_rate,
                "supplier_location": supplier_location,
                "item_nature": item_nature,
                "vat_treatment": vat_treatment,
                "scenario_name": scenario_name.strip(),
                "notes": notes.strip() or None,
                "is_active": 1,
            })
            st.success(f"Scenario added with code **{next_default_code()}** (ID {new_id}).")
            st.rerun()

# ── Tab 2: Manage Scenarios ────────────────────────────────────────────────
with tab_manage:
    st.subheader("All scenarios")

    all_scenarios = get_scenarios(active_only=False)
    if not all_scenarios:
        st.info("No scenarios yet.")
        st.stop()

    filter_country = st.selectbox(
        "Filter by country",
        ["All"] + sorted(set(s["recipient_country"] for s in all_scenarios)),
        key="filter_country",
    )

    filtered = all_scenarios if filter_country == "All" else [
        s for s in all_scenarios if s["recipient_country"] == filter_country
    ]

    _manage_vat_labels = get_vat_treatment_labels()
    df = pd.DataFrame([
        {
            "ID":            s["id"],
            "Default Tax Code": s["default_code"],
            "Country":       s["recipient_country"],
            "Scenario Name": s["scenario_name"],
            "VAT Treatment": _manage_vat_labels.get(s["vat_treatment"], s["vat_treatment"]),
            "Tax Type":      s["tax_type"],
            "Tax Rate":      f"{s['tax_rate']*100:.2f}%" if s["tax_rate"] is not None else "—",
            "Tx Type":       s["transaction_type"],
            "Supplier":      s["supplier_location"] or "—",
            "Item":          s["item_nature"] or "—",
            "Active":        bool(s["is_active"]),
        }
        for s in filtered
    ])

    edited = st.data_editor(
        df,
        column_config={
            "ID":               st.column_config.NumberColumn("ID", disabled=True, width="small"),
            "Default Tax Code": st.column_config.TextColumn("Default Tax Code", disabled=True, width="small"),
            "Country":          st.column_config.TextColumn("Country", disabled=True, width="small"),
            "Scenario Name":    st.column_config.TextColumn("Scenario", disabled=True, width="large"),
            "VAT Treatment":    st.column_config.TextColumn("VAT Treatment", disabled=True, width="large"),
            "Tax Type":         st.column_config.TextColumn("Tax Type", disabled=True, width="small"),
            "Tax Rate":         st.column_config.TextColumn("Rate", disabled=True, width="small"),
            "Tx Type":          st.column_config.TextColumn("Tx Type", disabled=True, width="small"),
            "Supplier":         st.column_config.TextColumn("Supplier", disabled=True, width="small"),
            "Item":             st.column_config.TextColumn("Item", disabled=True, width="small"),
            "Active":           st.column_config.CheckboxColumn("Active ✏️", width="small"),
        },
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key="manage_table",
    )

    if st.button("💾 Apply Active/Inactive Changes", type="primary"):
        original_active = {row["ID"]: bool(row["Active"]) for row in filtered}
        changed = 0
        for _, row in edited.iterrows():
            sid = int(row["ID"])
            new_active = bool(row["Active"])
            if original_active.get(sid) != new_active:
                toggle_scenario_active(sid, new_active)
                changed += 1
        if changed:
            st.success(f"Updated {changed} scenario(s).")
            st.rerun()
        else:
            st.info("No changes detected.")

    st.divider()

    # ── Edit a scenario ────────────────────────────────────────────────────
    st.subheader("Edit a scenario")
    scenario_opts = {f"{s['default_code']} — {s['scenario_name']}": s for s in filtered}
    if scenario_opts:
        edit_label = st.selectbox("Select scenario to edit", list(scenario_opts.keys()), key="edit_sel")
        s = scenario_opts[edit_label]

        _edit_vat_list    = get_vat_treatments()
        _edit_vat_norm    = [v["normalized_name"] for v in _edit_vat_list]
        _edit_vat_lbl_map = {v["normalized_name"]: v["display_name"] for v in _edit_vat_list}

        _edit_supplier_opts = ["Domestic", "EU", "NonEU"]
        _edit_item_opts     = ["Goods", "Services"]

        with st.form("edit_scenario_form"):
            c1, c2 = st.columns(2)
            with c1:
                edit_country = st.text_input("Recipient Country (ISO)", value=s["recipient_country"], max_chars=2)
                edit_tx_type = st.selectbox("Transaction Type", TRANSACTION_TYPES,
                    index=TRANSACTION_TYPES.index(s["transaction_type"]) if s["transaction_type"] in TRANSACTION_TYPES else 0)
                edit_tax_type = st.selectbox("Tax Type", TAX_TYPES,
                    index=TAX_TYPES.index(s["tax_type"]) if s["tax_type"] in TAX_TYPES else 0)
                edit_rate = st.text_input("Tax Rate (decimal)", value="" if s["tax_rate"] is None else str(s["tax_rate"]))
            with c2:
                edit_supplier = st.selectbox("Supplier Location", _edit_supplier_opts,
                    index=_edit_supplier_opts.index(s["supplier_location"]) if s["supplier_location"] in _edit_supplier_opts else 0)
                edit_item = st.selectbox("Item Nature", _edit_item_opts,
                    index=_edit_item_opts.index(s["item_nature"]) if s["item_nature"] in _edit_item_opts else 0)
                edit_vat = st.selectbox("VAT Treatment", _edit_vat_norm,
                    format_func=lambda v: _edit_vat_lbl_map.get(v, v),
                    index=_edit_vat_norm.index(s["vat_treatment"]) if s["vat_treatment"] in _edit_vat_norm else 0)
                edit_name = st.text_input("Scenario Name", value=s["scenario_name"])
            edit_notes = st.text_area("Notes", value=s["notes"] or "")

            if st.form_submit_button("💾 Save Changes", type="primary"):
                errors = []
                if not edit_name.strip():
                    errors.append("Scenario name is required.")
                if not edit_country.strip() or len(edit_country.strip()) != 2:
                    errors.append("Country must be a 2-letter ISO code.")
                tax_rate_val = None
                if edit_rate.strip():
                    try:
                        tax_rate_val = float(edit_rate.replace(",", "."))
                    except ValueError:
                        errors.append("Tax rate must be a number (e.g. 0.19).")
                if errors:
                    for e in errors:
                        st.error(e)
                else:
                    update_scenario(s["id"], {
                        "recipient_country": edit_country.strip().upper(),
                        "transaction_type":  edit_tx_type,
                        "tax_type":          edit_tax_type,
                        "tax_rate":          tax_rate_val,
                        "supplier_location": edit_supplier,
                        "item_nature":       edit_item,
                        "vat_treatment":     edit_vat,
                        "scenario_name":     edit_name.strip(),
                        "notes":             edit_notes.strip() or None,
                    })
                    st.success(f"Scenario **{s['default_code']}** updated.")
                    st.rerun()

    st.divider()

    # ── Delete a scenario ──────────────────────────────────────────────────
    st.subheader("Delete a scenario")
    st.warning("Deleting removes the scenario and all company tax code assignments for it. This cannot be undone.")
    if scenario_opts:
        del_label = st.selectbox("Select scenario to delete", list(scenario_opts.keys()), key="del_sel")
        del_s = scenario_opts[del_label]
        confirm_del = st.checkbox(f'I confirm I want to permanently delete "{del_s["default_code"]} — {del_s["scenario_name"]}"')
        if st.button("🗑️ Delete Scenario", type="secondary", disabled=not confirm_del):
            delete_scenario(del_s["id"])
            st.success(f"Deleted scenario {del_s['default_code']}.")
            st.rerun()

# ── Tab 3: Country Lists ───────────────────────────────────────────────────
with tab_countries:
    st.subheader("Manage EU and Non-EU country lists")
    st.info(
        "These lists determine how **EU** and **NonEU** supplier locations are expanded "
        "into individual country rows in the import-format export (Sheet 3). "
        "Use ISO alpha-2 codes (e.g. DE, FR, US)."
    )

    col_eu, col_non_eu = st.columns(2)

    # ── EU List ────────────────────────────────────────────────────────────
    with col_eu:
        st.markdown("### 🇪🇺 EU Countries")
        eu_list = get_country_list("EU")
        eu_df = pd.DataFrame(eu_list, columns=["country_code", "country_name"])
        eu_df.columns = ["ISO Code", "Country Name"]
        st.dataframe(eu_df, use_container_width=True, hide_index=True)

        with st.form("add_eu_country"):
            c1, c2 = st.columns([1, 2])
            with c1:
                new_eu_code = st.text_input("ISO Code *", max_chars=2, placeholder="e.g. NO")
            with c2:
                new_eu_name = st.text_input("Country Name", placeholder="e.g. Norway")
            if st.form_submit_button("➕ Add to EU list"):
                code = new_eu_code.strip().upper()
                if not code or len(code) != 2:
                    st.error("Enter a valid 2-letter ISO code.")
                elif add_country_to_list("EU", code, new_eu_name):
                    st.success(f"Added {code} to EU list.")
                    st.rerun()
                else:
                    st.warning(f"{code} is already in the EU list.")

        with st.form("remove_eu_country"):
            eu_codes = [r["country_code"] for r in eu_list]
            remove_eu = st.selectbox("Remove country", eu_codes, key="remove_eu_sel")
            if st.form_submit_button("🗑️ Remove from EU list", type="secondary"):
                remove_country_from_list("EU", remove_eu)
                st.success(f"Removed {remove_eu} from EU list.")
                st.rerun()

    # ── NonEU List ─────────────────────────────────────────────────────────
    with col_non_eu:
        st.markdown("### 🌍 Non-EU Countries")
        non_eu_list = get_country_list("NonEU")
        non_eu_df = pd.DataFrame(non_eu_list, columns=["country_code", "country_name"])
        non_eu_df.columns = ["ISO Code", "Country Name"]
        st.dataframe(non_eu_df, use_container_width=True, hide_index=True)

        with st.form("add_non_eu_country"):
            c1, c2 = st.columns([1, 2])
            with c1:
                new_non_eu_code = st.text_input("ISO Code *", max_chars=2, placeholder="e.g. AU")
            with c2:
                new_non_eu_name = st.text_input("Country Name", placeholder="e.g. Australia")
            if st.form_submit_button("➕ Add to Non-EU list"):
                code = new_non_eu_code.strip().upper()
                if not code or len(code) != 2:
                    st.error("Enter a valid 2-letter ISO code.")
                elif add_country_to_list("NonEU", code, new_non_eu_name):
                    st.success(f"Added {code} to Non-EU list.")
                    st.rerun()
                else:
                    st.warning(f"{code} is already in the Non-EU list.")

        with st.form("remove_non_eu_country"):
            non_eu_codes = [r["country_code"] for r in non_eu_list]
            remove_non_eu = st.selectbox("Remove country", non_eu_codes, key="remove_non_eu_sel")
            if st.form_submit_button("🗑️ Remove from Non-EU list", type="secondary"):
                remove_country_from_list("NonEU", remove_non_eu)
                st.success(f"Removed {remove_non_eu} from Non-EU list.")
                st.rerun()

# ── Tab 4: VAT Treatments ──────────────────────────────────────────────────
with tab_vat:
    st.subheader("Manage VAT Treatments")
    st.info(
        "Each VAT treatment has a **normalized name** (stored in the DB and used in the Import Format export) "
        "and a **display name** (shown in the UI and Sheet 1 of the Excel export)."
    )

    vat_list = get_vat_treatments()
    vat_df = pd.DataFrame(vat_list)[["normalized_name", "display_name"]] if vat_list else pd.DataFrame(columns=["normalized_name", "display_name"])
    vat_df.columns = ["Normalized Name", "Display Name"]
    st.dataframe(vat_df, use_container_width=True, hide_index=True)

    st.divider()
    col_add, col_edit = st.columns(2)

    with col_add:
        st.markdown("#### ➕ Add")
        with st.form("add_vat_form"):
            new_norm = st.text_input("Normalized Name *", placeholder="e.g. RC_IMPORT_§21")
            new_disp = st.text_input("Display Name *", placeholder="e.g. Import VAT §21 UStG")
            if st.form_submit_button("Add VAT Treatment", type="primary"):
                if not new_norm.strip() or not new_disp.strip():
                    st.error("Both fields are required.")
                elif add_vat_treatment(new_norm.strip(), new_disp.strip()):
                    st.success(f"Added **{new_norm.strip()}**.")
                    st.rerun()
                else:
                    st.warning(f"**{new_norm.strip()}** already exists.")

    with col_edit:
        st.markdown("#### ✏️ Edit")
        if vat_list:
            with st.form("edit_vat_form"):
                vat_opts = {v["normalized_name"]: v for v in vat_list}
                sel_norm = st.selectbox("Select to edit", list(vat_opts.keys()))
                sel_v = vat_opts[sel_norm]
                upd_norm = st.text_input("Normalized Name", value=sel_v["normalized_name"])
                upd_disp = st.text_input("Display Name", value=sel_v["display_name"])
                if st.form_submit_button("💾 Save", type="primary"):
                    if not upd_norm.strip() or not upd_disp.strip():
                        st.error("Both fields are required.")
                    else:
                        update_vat_treatment(sel_v["id"], upd_norm.strip(), upd_disp.strip())
                        st.success("Updated.")
                        st.rerun()

    st.divider()
    st.markdown("#### 🗑️ Delete")
    st.warning("Deleting a VAT treatment does not remove scenarios that use it — their stored normalized name remains unchanged.")
    if vat_list:
        with st.form("del_vat_form"):
            del_norm = st.selectbox("Select to delete", [v["normalized_name"] for v in vat_list])
            del_vat_entry = next(v for v in vat_list if v["normalized_name"] == del_norm)
            confirm_vat_del = st.checkbox(f'Confirm delete "{del_norm}"')
            if st.form_submit_button("Delete", type="secondary"):
                if not confirm_vat_del:
                    st.error("Please tick the confirmation checkbox.")
                else:
                    delete_vat_treatment(del_vat_entry["id"])
                    st.success(f"Deleted **{del_norm}**.")
                    st.rerun()
