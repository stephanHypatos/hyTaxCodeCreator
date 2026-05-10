TRANSACTION_TYPES = [
    "Invoice",
    "CreditNote",
    "Payroll",
    "Compensation",
    "Donation",
    "InternalPosting",
]

TAX_TYPES = [
    "VAT",
    "InsuranceTax",
    "OtherTax",
    "NonTax",
]

SUPPLIER_LOCATIONS = [
    "Domestic",
    "EU",
    "NonEU",
    "N/A",
]

ITEM_NATURES = [
    "Goods",
    "Services",
    "Mixed",
    "N/A",
]

VAT_TREATMENTS = [
    "STANDARD",
    "RC_INTRA_EU",
    "RC_DOMESTIC_§13b",
    "RC_NONEU_SERVICES",
    "EXEMPT_EXPORT",
    "EXEMPT_§4Nr8",
    "EXEMPT_§4Nr10",
    "EXEMPT_§4Nr11b",
    "EXEMPT_§4Nr12",
    "EXEMPT_§4Nr14",
    "EXEMPT_§4Nr21",
    "EXEMPT_OTHER",
    "KLEINUNTERNEHMER",
    "NON_VAT",
]

VAT_TREATMENT_LABELS = {
    "STANDARD":           "Standard taxed",
    "RC_INTRA_EU":        "Reverse charge — Intra-EU (Art. 44)",
    "RC_DOMESTIC_§13b":   "Reverse charge — Domestic §13b UStG",
    "RC_NONEU_SERVICES":  "Reverse charge — Non-EU services",
    "EXEMPT_EXPORT":      "Exempt — Export outside EU §4 Nr.1a",
    "EXEMPT_§4Nr8":       "Exempt — Banking/financial §4 Nr.8",
    "EXEMPT_§4Nr10":      "Exempt — Insurance (VAT) §4 Nr.10",
    "EXEMPT_§4Nr11b":     "Exempt — Postal universal service §4 Nr.11b",
    "EXEMPT_§4Nr12":      "Exempt — Residential rent §4 Nr.12",
    "EXEMPT_§4Nr14":      "Exempt — Healthcare/medical §4 Nr.14",
    "EXEMPT_§4Nr21":      "Exempt — Education §4 Nr.21",
    "EXEMPT_OTHER":       "Exempt — Other legal basis",
    "KLEINUNTERNEHMER":   "Kleinunternehmer §19 UStG",
    "NON_VAT":            "Non-VAT transaction",
}

# Common EU countries (ISO alpha-2)
EU_COUNTRIES = [
    "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI",
    "FR", "GR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT",
    "NL", "PL", "PT", "RO", "SE", "SI", "SK",
]

COUNTRY_NAMES = {
    "AT": "Austria", "BE": "Belgium", "BG": "Bulgaria", "CY": "Cyprus",
    "CZ": "Czech Republic", "DE": "Germany", "DK": "Denmark", "EE": "Estonia",
    "ES": "Spain", "FI": "Finland", "FR": "France", "GR": "Greece",
    "HR": "Croatia", "HU": "Hungary", "IE": "Ireland", "IT": "Italy",
    "LT": "Lithuania", "LU": "Luxembourg", "LV": "Latvia", "MT": "Malta",
    "NL": "Netherlands", "PL": "Poland", "PT": "Portugal", "RO": "Romania",
    "SE": "Sweden", "SI": "Slovenia", "SK": "Slovakia",
    "CH": "Switzerland", "GB": "United Kingdom", "NO": "Norway",
    "US": "United States", "CN": "China", "JP": "Japan",
}
