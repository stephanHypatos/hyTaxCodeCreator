# hyTaxCodeCreator

A Streamlit app for mapping company-specific AP tax codes to standardised tax scenarios across countries.

## What it does

Companies use their own internal tax codes (e.g. `V2`, `UE`) in their ERP/AP systems. These map to legally standardised tax scenarios that vary by recipient country, transaction type, VAT treatment, and more. This app lets finance teams:

- Assign company-specific codes to a library of pre-defined tax scenarios
- Manage scenarios and country lists via an admin interface
- Export a styled Excel mapping file with an import-ready format for tools like Coupa

## Pages

| Page | Purpose |
|---|---|
| **Company Setup** | Create or load a company profile (acronym + name) |
| **Tax Codes** | Assign company codes to scenarios per recipient country |
| **Admin** | Add/edit/delete scenarios; manage EU and Non-EU country lists |
| **Export** | Preview the full mapping and download as Excel |

## Excel Export

The downloaded file contains 3 sheets:

- **Sheet 1 — Tax Code Mapping**: full scenario table with default and company codes
- **Sheet 2 — Metadata**: company info, export date, filter applied, row counts
- **Sheet 3 — Import Format**: normalised rows ready for import, with EU/Non-EU supplier locations expanded to individual country codes

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

The SQLite database (`taxcodes.db`) is created automatically on first run and seeded with starter scenarios for Germany and France, plus EU and Non-EU country lists.

## Admin access

The Admin page is password-protected. Default password: `admin123`.

Set a custom password via environment variable:

```bash
export ADMIN_PASSWORD=your_password
streamlit run app.py
```

## Scenario dimensions

Each scenario is defined by 8 dimensions:

| Dimension | Example values |
|---|---|
| Recipient Country | DE, FR, AT (ISO alpha-2) |
| Transaction Type | Invoice, CreditNote, Payroll, Compensation, Donation |
| Tax Type | VAT, InsuranceTax, OtherTax, NonTax |
| Tax Rate | 0.19, 0.07, 0.0, null |
| Supplier Location | Domestic, EU, NonEU, N/A |
| Item Nature | Goods, Services, Mixed, N/A |
| VAT Treatment | STANDARD, RC_INTRA_EU, RC_NONEU_SERVICES, EXEMPT_§4Nr14, … |
| Scenario Name | Human-readable label |

## Tech stack

- [Streamlit](https://streamlit.io) — UI
- SQLite — persistence (built-in, no server needed)
- [pandas](https://pandas.pydata.org) — dataframe display
- [openpyxl](https://openpyxl.readthedocs.io) — Excel export
