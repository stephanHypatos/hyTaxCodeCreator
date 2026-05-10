import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent / "taxcodes.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS scenarios (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient_country CHAR(2)  NOT NULL,
                transaction_type  TEXT     NOT NULL,
                tax_type          TEXT     NOT NULL,
                tax_rate          REAL,
                supplier_location TEXT,
                item_nature       TEXT,
                vat_treatment     TEXT     NOT NULL,
                scenario_name     TEXT     NOT NULL,
                default_code      TEXT     NOT NULL,
                notes             TEXT,
                is_active         BOOLEAN  DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS companies (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                acronym    TEXT NOT NULL UNIQUE,
                name       TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS company_taxcodes (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id   INTEGER REFERENCES companies(id),
                scenario_id  INTEGER REFERENCES scenarios(id),
                company_code TEXT    NOT NULL,
                updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(company_id, scenario_id)
            );

            CREATE TABLE IF NOT EXISTS country_lists (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                list_type    TEXT    NOT NULL,
                country_code CHAR(2) NOT NULL,
                country_name TEXT,
                UNIQUE(list_type, country_code)
            );
        """)


# ── Scenarios ──────────────────────────────────────────────────────────────

def get_scenarios(country: str | None = None, active_only: bool = True):
    sql = "SELECT * FROM scenarios WHERE 1=1"
    params: list = []
    if active_only:
        sql += " AND is_active = 1"
    if country:
        sql += " AND recipient_country = ?"
        params.append(country)
    sql += " ORDER BY default_code"
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def get_distinct_countries() -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT recipient_country FROM scenarios WHERE is_active=1 ORDER BY recipient_country"
        ).fetchall()
    return [r[0] for r in rows]


def next_default_code() -> str:
    with get_conn() as conn:
        row = conn.execute("SELECT MAX(CAST(SUBSTR(default_code,3) AS INTEGER)) FROM scenarios").fetchone()
    n = (row[0] or 0) + 1
    return f"HY{n:02d}"


def add_scenario(data: dict) -> int:
    data["default_code"] = next_default_code()
    cols = ", ".join(data.keys())
    placeholders = ", ".join("?" * len(data))
    with get_conn() as conn:
        cur = conn.execute(f"INSERT INTO scenarios ({cols}) VALUES ({placeholders})", list(data.values()))
        return cur.lastrowid


def toggle_scenario_active(scenario_id: int, active: bool):
    with get_conn() as conn:
        conn.execute("UPDATE scenarios SET is_active=? WHERE id=?", (1 if active else 0, scenario_id))


def delete_scenario(scenario_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM company_taxcodes WHERE scenario_id=?", (scenario_id,))
        conn.execute("DELETE FROM scenarios WHERE id=?", (scenario_id,))


def update_scenario(scenario_id: int, data: dict):
    sets = ", ".join(f"{k}=?" for k in data)
    with get_conn() as conn:
        conn.execute(f"UPDATE scenarios SET {sets} WHERE id=?", list(data.values()) + [scenario_id])


# ── Companies ──────────────────────────────────────────────────────────────

def get_companies() -> list[dict]:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM companies ORDER BY acronym").fetchall()]


def get_company_by_acronym(acronym: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM companies WHERE acronym=?", (acronym.upper(),)).fetchone()
    return dict(row) if row else None


def upsert_company(acronym: str, name: str) -> dict:
    acronym = acronym.upper().strip()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO companies (acronym, name) VALUES (?,?) ON CONFLICT(acronym) DO UPDATE SET name=excluded.name",
            (acronym, name),
        )
        row = conn.execute("SELECT * FROM companies WHERE acronym=?", (acronym,)).fetchone()
    return dict(row)


# ── Company Tax Codes ──────────────────────────────────────────────────────

def get_company_taxcodes(company_id: int) -> dict[int, str]:
    """Returns {scenario_id: company_code}"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT scenario_id, company_code FROM company_taxcodes WHERE company_id=?",
            (company_id,),
        ).fetchall()
    return {r["scenario_id"]: r["company_code"] for r in rows}


def upsert_taxcodes(company_id: int, codes: dict[int, str]):
    """codes = {scenario_id: company_code}. Skips blank codes."""
    with get_conn() as conn:
        for scenario_id, code in codes.items():
            code = code.strip()
            if not code:
                continue
            conn.execute(
                """INSERT INTO company_taxcodes (company_id, scenario_id, company_code, updated_at)
                   VALUES (?,?,?, CURRENT_TIMESTAMP)
                   ON CONFLICT(company_id, scenario_id)
                   DO UPDATE SET company_code=excluded.company_code, updated_at=CURRENT_TIMESTAMP""",
                (company_id, scenario_id, code),
            )


def count_assigned(company_id: int) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM company_taxcodes WHERE company_id=?", (company_id,)
        ).fetchone()
    return row[0]


# ── Country Lists ──────────────────────────────────────────────────────────

def get_country_list(list_type: str) -> list[dict]:
    """list_type: 'EU' or 'NonEU'"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT country_code, country_name FROM country_lists WHERE list_type=? ORDER BY country_code",
            (list_type,),
        ).fetchall()
    return [dict(r) for r in rows]


def add_country_to_list(list_type: str, country_code: str, country_name: str = "") -> bool:
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO country_lists (list_type, country_code, country_name) VALUES (?,?,?)",
                (list_type, country_code.upper().strip(), country_name.strip()),
            )
        return True
    except Exception:
        return False


def remove_country_from_list(list_type: str, country_code: str):
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM country_lists WHERE list_type=? AND country_code=?",
            (list_type, country_code.upper()),
        )


def get_country_codes(list_type: str) -> list[str]:
    return [r["country_code"] for r in get_country_list(list_type)]


# ── Full Mapping ────────────────────────────────────────────────────────────

def get_full_mapping(company_id: int) -> list[dict]:
    """Scenarios joined with company codes for export/display."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
                s.recipient_country,
                s.transaction_type,
                s.tax_type,
                s.tax_rate,
                s.supplier_location,
                s.item_nature,
                s.vat_treatment,
                s.scenario_name,
                s.default_code,
                s.notes,
                COALESCE(ct.company_code, '') AS company_code
            FROM scenarios s
            LEFT JOIN company_taxcodes ct ON ct.scenario_id=s.id AND ct.company_id=?
            WHERE s.is_active=1
            ORDER BY s.recipient_country, s.default_code
            """,
            (company_id,),
        ).fetchall()
    return [dict(r) for r in rows]
