# hyTaxCodeCreator — System Documentation

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Component 1 — hyTaxCodeCreator (Tax Code Library)](#2-component-1--hytaxcodecreator-tax-code-library)
3. [Component 2 — AI Document Agent Pipeline](#3-component-2--ai-document-agent-pipeline)
4. [Component 3 — Composite Enrichment Service](#4-component-3--composite-enrichment-service)
5. [End-to-End Data Flow](#5-end-to-end-data-flow)
6. [Data Model Reference](#6-data-model-reference)
7. [VAT Treatment Reference](#7-vat-treatment-reference)
8. [Test Invoice Library](#8-test-invoice-library)

---

## 1. System Overview

The system automates AP (Accounts Payable) tax code determination for incoming invoices and credit notes. It consists of three loosely-coupled components:

```
┌─────────────────────────────────────────────────────────────────┐
│                        INCOMING DOCUMENT                        │
│               (invoice PDF / credit note PDF)                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              COMPONENT 2 — AI Agent Pipeline                    │
│                                                                 │
│  ┌─────────────────────┐    ┌────────────────────────────────┐  │
│  │  Jurisdiction Agent │    │    Posting Line Agent          │  │
│  │                     │    │                                │  │
│  │ dispatchCountry     │    │ items.positionTaxRate          │  │
│  │ destinationCountry  │    │ items.category                 │  │
│  │                     │    │ items.taxTreatment             │  │
│  └─────────────────────┘    └────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│          COMPONENT 3 — Composite Enrichment Service             │
│                                                                 │
│   OpenSearch exact-match query on all extracted datapoints      │
│   → returns company tax code if found, else null               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Tax Code (e.g. │
                    │  V2, UE, VS19)  │
                    └─────────────────┘
```

The **OpenSearch index** that powers Component 3 is built from the normalized export produced by **Component 1 — hyTaxCodeCreator**.

---

## 2. Component 1 — hyTaxCodeCreator (Tax Code Library)

### Purpose

hyTaxCodeCreator is a Streamlit web application that serves as the **master registry** of tax scenarios and company-specific tax codes. Finance teams use it to:

- Maintain a curated library of legally standardised AP tax scenarios
- Assign company-internal codes to each scenario (e.g. `V2`, `UE`, `VS19`)
- Export a normalised, import-ready file that feeds the OpenSearch index

### Pages

| Page | Function |
|---|---|
| **Company Setup** | Register or load a company profile (acronym + name). All subsequent work is scoped to this company. |
| **Tax Codes** | Per recipient country: review all active scenarios and assign or update the company's internal tax code for each one. |
| **Admin** | Password-protected. Add, edit, and delete scenarios; manage EU/Non-EU country lists; manage VAT treatment definitions. |
| **Export** | Preview the full mapping and download a 3-sheet Excel file. |

### Database Schema

```sql
-- Core scenario library (managed by admin)
CREATE TABLE scenarios (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    recipient_country CHAR(2)  NOT NULL,   -- ISO alpha-2, e.g. "DE"
    transaction_type  TEXT     NOT NULL,   -- Invoice | CreditNote | Payroll | …
    tax_type          TEXT     NOT NULL,   -- VAT | InsuranceTax | OtherTax | NonTax
    tax_rate          REAL,               -- 0.19, 0.07, 0.0, NULL for NonTax
    supplier_location TEXT,               -- Domestic | EU | NonEU | N/A
    item_nature       TEXT,               -- Goods | Services | Mixed | N/A
    vat_treatment     TEXT     NOT NULL,   -- normalized key, see §7
    scenario_name     TEXT     NOT NULL,   -- human-readable label
    default_code      TEXT     NOT NULL,   -- HY01, HY02, … (auto-incremented)
    notes             TEXT,               -- free-text, legal references
    is_active         BOOLEAN  DEFAULT 1
);

-- Company registry
CREATE TABLE companies (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    acronym  TEXT NOT NULL UNIQUE,        -- e.g. "EPLAN"
    name     TEXT NOT NULL
);

-- Company-specific code overrides
CREATE TABLE company_taxcodes (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id   INTEGER REFERENCES companies(id),
    scenario_id  INTEGER REFERENCES scenarios(id),
    company_code TEXT    NOT NULL,        -- e.g. "V2"
    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, scenario_id)
);

-- Admin-managed EU / Non-EU country lists
CREATE TABLE country_lists (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    list_type    TEXT    NOT NULL,        -- "EU" or "NonEU"
    country_code CHAR(2) NOT NULL,
    country_name TEXT,
    UNIQUE(list_type, country_code)
);

-- Admin-managed VAT treatment definitions
CREATE TABLE vat_treatments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    normalized_name TEXT NOT NULL UNIQUE, -- key used in DB and export
    display_name    TEXT NOT NULL         -- shown in UI and Excel Sheet 1
);
```

### Excel Export Format

The Download Excel button produces a 3-sheet workbook:

#### Sheet 1 — Tax Code Mapping

Human-readable mapping table with all active scenarios and their company codes. Columns:

| Column | Description |
|---|---|
| Recipient Country | ISO alpha-2 |
| Transaction Type | Invoice, CreditNote, Payroll, … |
| Tax Type | VAT, InsuranceTax, OtherTax, NonTax |
| Tax Rate | Formatted percentage (e.g. 19.00%) |
| Supplier Location | Domestic, EU, NonEU, N/A |
| Item Nature | Goods, Services, Mixed, N/A |
| VAT Treatment | Display name (e.g. "Reverse charge — Intra-EU") |
| Scenario Name | Human-readable label |
| Default Tax Code | HY-prefixed fallback code |
| **Company Tax Code** | Company's internal code — the deliverable |
| Notes | Free-text legal references |

#### Sheet 2 — Metadata

Key-value pairs: company name/acronym, export date, country filter applied, row counts.

#### Sheet 3 — Import Format

**This sheet is the source of truth for the OpenSearch index.**

Each row represents one unique, fully-resolved combination of:
`(recipientCountry, vendorCountry, category, taxTreatment)`

EU and NonEU supplier locations are **fanned out** into individual country rows — one row per vendor country, excluding cases where vendor = recipient (no self-supply).

| Column | Description | Example |
|---|---|---|
| `externalId` | Zero-padded sequential ID | `00001` |
| `code` | Company tax code (falls back to HY default) | `V2` |
| `description` | Scenario name | `DE — Intra-EU goods acquisition, reverse charge` |
| `itemsTaxRate` | Tax rate as decimal string | `0`, `0.19`, `0.07` |
| `itemsTaxRateCoupa` | Tax rate as percentage number | `0`, `19`, `7` |
| `recipientCountry` | ISO alpha-2 of recipient | `DE` |
| `vendorCountry` | ISO alpha-2 of vendor/sender | `FR` |
| `category` | Goods or Services | `Goods` |
| `taxTreatment` | Normalized VAT treatment key | `RC_INTRA_EU` |

**Example expansion:** A scenario with `supplier_location = EU` and `recipient_country = DE` will generate 26 rows — one for every EU country except DE itself.

---

## 3. Component 2 — AI Document Agent Pipeline

### Purpose

An LLM-based agent platform that reads incoming invoice and credit note PDFs and extracts structured datapoints used for tax code determination.

### Document Ingestion

Documents (PDF invoices, credit notes) are uploaded to the platform. An LLM agent performs extraction and returns structured JSON.

### Agent A — Jurisdiction Agent

**Task:** Identify where the goods/services originate and where they are delivered.

**Returns:**

```json
{
  "transactionJurisdiction": {
    "dispatchCountry": "FR",
    "destinationCountry": "DE"
  }
}
```

| Field | Description | Notes |
|---|---|---|
| `dispatchCountry` | Country from which goods/services originate | Physical ship-from address if different from billing address (e.g. CH warehouse for EU supplier) |
| `destinationCountry` | Country where goods/services are received | Delivery address if different from billing address (e.g. US subsidiary receiving goods) |

**Edge cases handled:**

- **EU supplier, non-EU dispatch:** If a French company invoices but ships from a Swiss warehouse, `dispatchCountry = CH`. This changes the classification from intra-EU acquisition to import.
- **Billing ≠ delivery country:** If EPLAN DE is billed but goods go to EPLAN US, `destinationCountry = US`. This classifies as an export (§4 Nr.1a).

### Agent B — Posting Line Agent

**Task:** For each line item on the invoice, extract the tax rate, goods/services category, and determine the VAT treatment.

**System prompt context (Tax Treatment Assessment):**

The agent is given a reference table mapping natural-language descriptions to normalized values. The descriptions are intentionally generic — the agent must identify the correct case by context from the invoice text.

| Description on invoice (approximate) | Normalized value returned |
|:--------------------------------------|:--------------------------|
| Standard VAT, normal taxed transaction | `STANDARD` |
| Reverse charge — Intra-EU (Art. 44) | `RC_INTRA_EU` |
| Reverse charge — Domestic §13b UStG | `RC_DOMESTIC_§13b` |
| Reverse charge — Non-EU services | `RC_NONEU_SERVICES` |
| Export outside EU §4 Nr.1a | `EXEMPT_EXPORT` |
| Banking / financial services | `EXEMPT_§4Nr8` |
| Insurance (VAT-exempt) §4 Nr.10 | `EXEMPT_§4Nr10` |
| Postal universal service §4 Nr.11b | `EXEMPT_§4Nr11b` |
| Residential / commercial rent §4 Nr.12 | `EXEMPT_§4Nr12` |
| Healthcare / medical services §4 Nr.14 | `EXEMPT_§4Nr14` |
| Education services §4 Nr.21 | `EXEMPT_§4Nr21` |
| Other exempt (legal basis in notes) | `EXEMPT_OTHER` |
| Kleinunternehmer §19 UStG | `KLEINUNTERNEHMER` |
| No VAT framework (payroll, insurance tax, etc.) | `NON_VAT` |

**Returns (per posting line):**

```json
{
  "items": [
    {
      "positionTaxRate": 0.0,
      "category": "Goods",
      "taxTreatment": "RC_INTRA_EU"
    }
  ]
}
```

| Field | Type | Description |
|---|---|---|
| `positionTaxRate` | float | Tax rate as decimal (0.19, 0.07, 0.0) |
| `category` | string | `Goods` or `Services` |
| `taxTreatment` | string | Normalized key from the reference table above |

**Classification challenges** (cases where the agent must reason beyond surface text):

| Invoice type | Challenge |
|---|---|
| Bank fee invoice | No VAT column, no exemption mention — agent infers §4 Nr.8 from supplier type |
| Doctor/medical invoice | Supplier has no VAT ID; column shows `stfr.` or nothing — infer §4 Nr.14 |
| Insurance premium | Column shows `VSt. 19%` — must distinguish Versicherungsteuer (not recoverable) from USt |
| Italian RC invoice | Note in Italian with legal article references only — agent must map to `RC_INTRA_EU` |
| Rent invoice | No VAT line at all — infer §4 Nr.12 from transaction context |

---

## 4. Component 3 — Composite Enrichment Service

### Purpose

Combines the extracted datapoints from all agents into a single OpenSearch query to look up the company tax code.

### Index Structure

The OpenSearch index is built from **Sheet 3** (Import Format) of the hyTaxCodeCreator export. Each document in the index corresponds to one row:

```json
{
  "externalId":        "00042",
  "code":              "V2",
  "description":       "DE — Intra-EU goods acquisition, reverse charge",
  "itemsTaxRate":      "0",
  "itemsTaxRateCoupa": 0,
  "recipientCountry":  "DE",
  "vendorCountry":     "FR",
  "category":          "Goods",
  "taxTreatment":      "RC_INTRA_EU"
}
```

### Query Logic

The enrichment service constructs an exact-match query using the following field mapping:

| OpenSearch field | Source |
|---|---|
| `recipientCountry` | `transactionJurisdiction.destinationCountry` |
| `vendorCountry` | `transactionJurisdiction.dispatchCountry` |
| `category` | `items.category` |
| `taxTreatment` | `items.taxTreatment` |

**Example query:**

```json
{
  "query": {
    "bool": {
      "must": [
        { "term": { "recipientCountry": "DE" } },
        { "term": { "vendorCountry":    "FR" } },
        { "term": { "category":         "Goods" } },
        { "term": { "taxTreatment":     "RC_INTRA_EU" } }
      ]
    }
  }
}
```

### Result Handling

| Outcome | Behaviour |
|---|---|
| **Exact match found** | Returns `code` (e.g. `V2`) as the determined tax code |
| **No match** | Returns null — document is flagged for manual review |
| **Multiple matches** | Should not occur if index was built correctly (combination is unique) |

---

## 5. End-to-End Data Flow

```
INVOICE PDF
    │
    ▼
┌──────────────────────────────────────────────────┐
│  Jurisdiction Agent                              │
│  Input:  invoice PDF                             │
│  Output: dispatchCountry = "FR"                  │
│          destinationCountry = "DE"               │
└──────────────────────────┬───────────────────────┘
                           │
┌──────────────────────────▼───────────────────────┐
│  Posting Line Agent                              │
│  Input:  invoice PDF + VAT treatment table       │
│  Output: positionTaxRate = 0.0                   │
│          category        = "Goods"               │
│          taxTreatment    = "RC_INTRA_EU"         │
└──────────────────────────┬───────────────────────┘
                           │
┌──────────────────────────▼───────────────────────┐
│  Composite Enrichment Service                    │
│  Query: recipientCountry = "DE"                  │
│         vendorCountry    = "FR"                  │
│         category         = "Goods"               │
│         taxTreatment     = "RC_INTRA_EU"         │
│                                                  │
│  OpenSearch Index (built from Sheet 3 export)    │
│  → Exact match found                             │
│  → code = "V2"                                   │
└──────────────────────────┬───────────────────────┘
                           │
                           ▼
                    Tax Code: "V2"
                    (written back to ERP / AP system)
```

---

## 6. Data Model Reference

### Enumerations

**Transaction Type**

| Value | Description |
|---|---|
| `Invoice` | Standard supplier invoice |
| `CreditNote` | Credit note / Gutschrift |
| `Payroll` | Payroll posting |
| `Compensation` | Damages / compensation payment |
| `Donation` | Donation |
| `InternalPosting` | Internal accounting posting |

**Tax Type**

| Value | Description |
|---|---|
| `VAT` | Standard Umsatzsteuer |
| `InsuranceTax` | Versicherungsteuer (§1 VersStG) — not recoverable |
| `OtherTax` | Other non-VAT tax |
| `NonTax` | No tax framework |

**Supplier Location** (stored in scenario library)

| Value | Description |
|---|---|
| `Domestic` | Supplier in same country as recipient |
| `EU` | Supplier in EU (excluding recipient country) |
| `NonEU` | Supplier outside EU |
| `N/A` | Not applicable (payroll, compensation, etc.) |

**Category** (extracted by posting line agent, used in enrichment)

| Value | Description |
|---|---|
| `Goods` | Physical goods, products |
| `Services` | Intangible services |

---

## 7. VAT Treatment Reference

The `taxTreatment` field is the primary discriminator for tax code determination. It is:
- **Stored** in the scenarios table and in the OpenSearch index (normalized key)
- **Extracted** by the Posting Line Agent from the invoice
- **Displayed** in the UI and Excel Sheet 1 using the configurable display name

| Normalized Key | Default Display Name | Typical Invoice Signal |
|:---|:---|:---|
| `STANDARD` | Standard taxed | Standard VAT %, no special notice |
| `RC_INTRA_EU` | Reverse charge — Intra-EU (Art. 44) | 0% VAT, RC notice, both VAT IDs present |
| `RC_DOMESTIC_§13b` | Reverse charge — Domestic §13b UStG | 0% VAT, "§13b" reference, domestic supplier |
| `RC_NONEU_SERVICES` | Reverse charge — Non-EU services | 0% VAT, non-EU supplier, services |
| `EXEMPT_EXPORT` | Exempt — Export outside EU §4 Nr.1a | 0% VAT, delivery address outside EU |
| `EXEMPT_§4Nr8` | Exempt — Banking/financial §4 Nr.8 | No VAT at all, financial institution supplier |
| `EXEMPT_§4Nr10` | Exempt — Insurance (VAT) §4 Nr.10 | VAT-exempt insurance (not Versicherungsteuer) |
| `EXEMPT_§4Nr11b` | Exempt — Postal universal service §4 Nr.11b | Deutsche Post universal service line items |
| `EXEMPT_§4Nr12` | Exempt — Residential rent §4 Nr.12 | Rent invoice, no VAT shown |
| `EXEMPT_§4Nr14` | Exempt — Healthcare/medical §4 Nr.14 | Medical/occupational health, no VAT ID on supplier |
| `EXEMPT_§4Nr21` | Exempt — Education §4 Nr.21 | Accredited training provider, no VAT line |
| `EXEMPT_OTHER` | Exempt — Other legal basis | Notes field carries the specific legal reference |
| `KLEINUNTERNEHMER` | Kleinunternehmer §19 UStG | Explicit §19 notice, no VAT charged |
| `NON_VAT` | Non-VAT transaction | Payroll, compensation, Versicherungsteuer (§1 VersStG) |

> **Important:** `NON_VAT` covers two distinct cases that must not be confused:
> - **Payroll / compensation / donations:** No tax framework whatsoever
> - **Versicherungsteuer:** A 19% tax is shown on the invoice (`VSt.` column) but it is **not** recoverable Umsatzsteuer — no Vorsteuerabzug is possible

---

## 8. Test Invoice Library

A set of 19 test PDFs is provided in `/test_invoices/` for validating the end-to-end pipeline. All invoices are addressed to **EPLAN GmbH & Co. KG, Monheim am Rhein (DE · DE196815264)**.

### Standard Cases (obvious tax treatment)

| File | Supplier | Scenario | Tax Treatment |
|---|---|---|---|
| `INV-001` | SCM Verlagsgruppe GmbH (DE) | Domestic goods 19% | `STANDARD` |
| `INV-002` | SCM Verlagsgruppe GmbH (DE) | Domestic goods 7% | `STANDARD` |
| `INV-003` | SCM Verlagsgruppe GmbH (DE) | Domestic services 19% | `STANDARD` |
| `INV-004` | SCM Verlagsgruppe GmbH (DE) | Domestic services 7% | `STANDARD` |
| `INV-005` | SCM Verlagsgruppe GmbH (DE) | Construction / §13b reverse charge | `RC_DOMESTIC_§13b` |
| `INV-006` | SCM Verlagsgruppe GmbH (DE) | Kleinunternehmer §19 | `KLEINUNTERNEHMER` |
| `INV-007` | Schneider Electric SAS (FR) | Intra-EU goods, reverse charge | `RC_INTRA_EU` |
| `INV-008` | Schneider Electric SAS (FR) | Intra-EU services, reverse charge | `RC_INTRA_EU` |
| `INV-009` | Open Design Alliance (US) | Non-EU services, reverse charge §13b | `RC_NONEU_SERVICES` |
| `INV-010` | Open Design Alliance (US) | Non-EU goods import (customs) | `EXEMPT_EXPORT` |
| `CN-001` | SCM Verlagsgruppe GmbH (DE) | Credit note, domestic goods 19% | `STANDARD` |

### Address / Jurisdiction Edge Cases

| File | Key Challenge | Expected Jurisdiction Extraction |
|---|---|---|
| `INV-011` | EU supplier (FR) but goods dispatched from CH warehouse | `dispatchCountry = CH` → import, not intra-EU |
| `INV-012` | DE recipient billing address, delivery to EPLAN US (Malvern PA) | `destinationCountry = US` → export §4 Nr.1a |

### Hard Classification Cases (subtle or absent exemption signals)

| File | Supplier | Scenario | What makes it hard |
|---|---|---|---|
| `INV-013` | Dr. med. Thomas Berger (DE) | §4 Nr.14 Healthcare | No supplier VAT ID; column shows `stfr.`; exemption only in tiny footer |
| `INV-014` | Akademie für Berufliche Bildung GmbH (DE) | §4 Nr.21 Education | No tax line at all; single-line footer reference only |
| `INV-015` | Commerzbank AG (DE) | §4 Nr.8 Banking fees | **No VAT mention anywhere** — must infer from supplier type |
| `INV-016` | Monheimer Immobilien Verwaltungs GmbH (DE) | §4 Nr.12 Office rent | Rent format; VAT completely absent; subtle one-liner footer |
| `INV-017` | Allianz Versicherungs-AG (DE) | Versicherungsteuer (NON_VAT) | Shows `VSt. 19%` — looks like recoverable VAT but is §1 VersStG |
| `INV-018` | Siemens S.p.A. (IT) | Intra-EU services RC — subtle | Italian-language legal references only; no plain RC instruction to DE recipient |

### Generating Test Invoices

```bash
pip install reportlab
python3 test_invoices/generate_invoices.py
```

All PDFs are written to the `test_invoices/` directory.

---

*Generated by hyTaxCodeCreator — [github.com/stephanHypatos/hyTaxCodeCreator](https://github.com/stephanHypatos/hyTaxCodeCreator)*
