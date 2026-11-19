"""SQLite: esquema y acceso. Toda regla guardada aquí salió de la ingesta."""
import hashlib
import json
import os
import sqlite3
from decimal import Decimal

from app.models import Rule

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
  id INTEGER PRIMARY KEY, source_url TEXT NOT NULL UNIQUE, content_sha256 TEXT NOT NULL,
  kind TEXT NOT NULL, pages INTEGER NOT NULL, status TEXT NOT NULL,
  model_version TEXT, claims_total INTEGER DEFAULT 0, claims_rejected INTEGER DEFAULT 0,
  security_events TEXT DEFAULT '[]', ingested_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rules (
  id INTEGER PRIMARY KEY AUTOINCREMENT, document_id INTEGER NOT NULL REFERENCES documents(id),
  source_url TEXT NOT NULL, jurisdiction TEXT NOT NULL, payment_type TEXT NOT NULL,
  tax_year INTEGER NOT NULL, kind TEXT NOT NULL, condition TEXT NOT NULL,
  rate TEXT, flat_amount TEXT, min_amount TEXT, threshold_inclusive INTEGER NOT NULL,
  page INTEGER NOT NULL, quote TEXT NOT NULL, source_kind TEXT NOT NULL,
  UNIQUE(document_id, jurisdiction, payment_type, tax_year, kind, rate, flat_amount,
         min_amount, page, quote)
);
CREATE TABLE IF NOT EXISTS decisions (
  id INTEGER PRIMARY KEY, request_id TEXT NOT NULL, created_at TEXT NOT NULL,
  record TEXT NOT NULL
);
"""


def connect(path=None):
    conn = sqlite3.connect(path or os.environ.get("DATABASE_PATH", "withholding.db"))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def _dec(value):
    return None if value is None else Decimal(value)


def row_to_rule(row) -> Rule:
    return Rule(
        id=row["id"], source_url=row["source_url"], jurisdiction=row["jurisdiction"],
        payment_type=row["payment_type"], tax_year=row["tax_year"], kind=row["kind"],
        condition=row["condition"], rate=_dec(row["rate"]),
        flat_amount=_dec(row["flat_amount"]), min_amount=_dec(row["min_amount"]),
        threshold_inclusive=bool(row["threshold_inclusive"]), page=row["page"],
        quote=row["quote"], source_kind=row["source_kind"],
    )


def find_document(conn, source_url):
    return conn.execute("SELECT * FROM documents WHERE source_url = ?", (source_url,)).fetchone()


def replace_document(conn, source_url, sha, kind, pages, status, model_version,
                     claims_total, claims_rejected, security_events, ingested_at, rules):
    """Guarda un documento y sus reglas en una sola transacción. `rules` son dicts validados."""
    with conn:
        old = find_document(conn, source_url)
        if old:
            conn.execute("DELETE FROM rules WHERE document_id = ?", (old["id"],))
            conn.execute("DELETE FROM documents WHERE id = ?", (old["id"],))
        doc_id = conn.execute(
            "INSERT INTO documents (source_url, content_sha256, kind, pages, status,"
            " model_version, claims_total, claims_rejected, security_events, ingested_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (source_url, sha, kind, pages, status, model_version, claims_total,
             claims_rejected, json.dumps(security_events), ingested_at),
        ).lastrowid
        for r in rules:
            conn.execute(
                "INSERT OR IGNORE INTO rules (document_id, source_url, jurisdiction,"
                " payment_type, tax_year, kind, condition, rate, flat_amount, min_amount,"
                " threshold_inclusive, page, quote, source_kind) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (doc_id, source_url, r["jurisdiction"], r["payment_type"], r["tax_year"],
                 r["kind"], r["condition"], r["rate"], r["flat_amount"], r["min_amount"],
                 int(r["threshold_inclusive"]), r["page"], r["quote"], r["source_kind"]),
            )
    return doc_id


def list_rules(conn, jurisdiction=None, payment_type=None, tax_year=None, limit=None, offset=0):
    where, args = [], []
    for column, value in (("jurisdiction", jurisdiction), ("payment_type", payment_type),
                          ("tax_year", tax_year)):
        if value is not None:
            where.append(f"{column} = ?")
            args.append(value)
    sql = "SELECT * FROM rules" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY id"
    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        args += [limit, offset]
    return [row_to_rule(r) for r in conn.execute(sql, args)]


def rules_version(conn) -> str:
    """Huella de todas las reglas válidas, en orden estable."""
    digest = hashlib.sha256()
    for row in conn.execute(
        "SELECT source_url, jurisdiction, payment_type, tax_year, kind, condition, rate,"
        " flat_amount, min_amount, threshold_inclusive, page, quote FROM rules"
        " ORDER BY source_url, page, jurisdiction, payment_type, tax_year, quote, rate"
    ):
        digest.update(json.dumps(list(row), ensure_ascii=False).encode("utf-8"))
    return "sha256:" + digest.hexdigest()


def security_events(conn):
    """Intentos de instrucción incrustada en cualquier documento ingerido, tenga reglas o no."""
    rows = conn.execute("SELECT source_url, security_events FROM documents ORDER BY id")
    return [dict(e, source_url=row["source_url"]) for row in rows
            for e in json.loads(row["security_events"])]
