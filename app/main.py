"""Servicio HTTP. Aquí vive el orden de los pasos; el modelo solo se llama dentro de la ingesta."""
import asyncio
import hmac
import json
import os
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from fastapi import FastAPI, Header, Request
from fastapi.responses import FileResponse, JSONResponse

from app import db, extract, fetch, models, parse, validate
from app.logs import log, safe_url
from app.models import (JURISDICTION_PATTERN, PAYEE_TYPES, PAYMENT_TYPES, PIPELINE_VERSION, Deadline,
                        DeadlineExceeded, Query)
from app.resolve import resolve

app = FastAPI(title="Withholding rules service", version="1.0")
STATIC = Path(__file__).resolve().parent.parent / "static"


def error(status: int, code: str, request_id: str, **extra):
    return JSONResponse({"error": code, "request_id": request_id, **extra}, status_code=status)


@app.middleware("http")
async def request_context(request: Request, call_next):
    """Plazo y número de petición desde la llegada. El log lleva la ruta, nunca los parámetros."""
    request.state.request_id = uuid.uuid4().hex[:12]
    request.state.deadline = Deadline.start()
    try:
        response = await call_next(request)
    except DeadlineExceeded:
        response = error(504, "deadline_exceeded", request.state.request_id)
    except Exception as exc:  # el detalle no sale al cliente ni al log, solo el tipo
        log("unhandled_error", request_id=request.state.request_id, error_type=type(exc).__name__)
        response = error(500, "internal_error", request.state.request_id)
    response.headers.update({"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY",
                             "Referrer-Policy": "no-referrer"})
    log("request", request_id=request.state.request_id, method=request.method,
        path=request.url.path, status=response.status_code)
    return response


@app.get("/health")
def health():
    conn = db.connect()
    docs = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    found = [r[0] for r in conn.execute("SELECT DISTINCT jurisdiction FROM rules ORDER BY 1")]
    return {"status": "ok", "documents": docs, "jurisdictions": found,
            "rules_version": db.rules_version(conn)}


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/v1/documents")
def documents():
    rows = db.connect().execute(
        "SELECT source_url, content_sha256, kind, pages, status, model_version, claims_total,"
        " claims_rejected, security_events, ingested_at FROM documents ORDER BY id")
    return {"items": [dict(r, security_events=json.loads(r["security_events"])) for r in rows]}


@app.post("/v1/documents")
async def ingest(request: Request, x_ingest_key: str | None = Header(default=None)):
    rid, deadline = request.state.request_id, request.state.deadline
    expected = os.environ.get("INGEST_KEY", "")
    if not expected or not hmac.compare_digest((x_ingest_key or "").encode(), expected.encode()):
        return error(401, "ingest_key_required", rid)
    try:
        url = (await request.json())["source_url"]
        assert isinstance(url, str)
    except Exception:
        return error(422, "source_url_required", rid)
    try:
        fetched = await asyncio.to_thread(fetch.fetch, url, deadline)
    except fetch.FetchError as exc:
        log("fetch_failed", request_id=rid, detail=str(exc))
        return error(502, "fetch_failed", rid, detail=str(exc))
    deadline.check()
    conn, url = db.connect(), safe_url(url, keep_query=True)   # sin usuario ni credenciales
    known = db.find_document(conn, url)
    if (known and known["content_sha256"] == fetched.sha256 and known["status"] == "complete"
            and (known["model_version"] or "").endswith(f"+p{PIPELINE_VERSION}")):
        # Mismo contenido ya leído completo: ni registros duplicados ni gasto de modelo.
        log("ingest_cached", request_id=rid, source_url=url, sha256=fetched.sha256)
        return {"source_url": url, "content_sha256": fetched.sha256, "status": "complete",
                "cached": True, "model_calls": 0}
    try:
        kind = parse.detect_kind(fetched.content, fetched.content_type)
    except ValueError:
        return error(422, "unsupported_document_type", rid)
    pages = await asyncio.to_thread(parse.parse, fetched.content, kind)
    if len(pages) > models.MAX_PAGES:   # antes de gastar una sola llamada al modelo
        return error(413, "too_many_pages", rid, pages=len(pages), max_pages=models.MAX_PAGES)
    scanned = [p.number for p in pages if p.source_kind == "vision"]
    if scanned:   # una página escaneada se transcribe primero; después se valida como cualquier otra
        images = await asyncio.to_thread(lambda: {n: fetched.content if kind == "image" else
                                                  parse.render_page_png(fetched.content, n) for n in scanned})
        pages = await extract.transcribe(pages, images, deadline)
    deadline.check()
    events = validate.detect_injection(pages)
    result = await extract.extract_claims(pages, safe_url(url), deadline)
    result.model_version += f"+p{PIPELINE_VERSION}"   # modelo y versión del proceso que leyó el documento
    by_number = {p.number: p for p in pages}
    years, locale = validate.document_years(pages), parse.detect_number_locale(pages)
    rules, rejected = {}, Counter()
    for claim in result.claims:
        rule, reason = validate.validate_claim(claim, by_number, years, locale, url)
        if rule:   # la misma afirmación repetida es una sola regla
            rules[json.dumps(rule, sort_keys=True)] = rule
        else:      # lo que no se valida se descarta, no se confía; y queda escrito por qué
            rejected[reason] += 1
            log("claim_rejected", request_id=rid, source_url=url, reason=reason,
                claim=claim if isinstance(claim, dict) else str(claim)[:200])
    rules = list(rules.values())
    for rule in rules:
        log("rule_stored", request_id=rid, source_url=url, sha256=fetched.sha256,
            model_version=result.model_version, **rule)
    unread = [p.number for p in pages if not p.text.strip()]
    status = "partial" if result.partial or unread else "complete"
    db.replace_document(conn, url, fetched.sha256, kind, len(pages), status, result.model_version,
                        len(result.claims), sum(rejected.values()), events,
                        datetime.now(timezone.utc).isoformat(timespec="seconds"), rules)
    summary = {"source_url": url, "content_sha256": fetched.sha256, "kind": kind,
               "pages": len(pages), "status": status, "cached": False,
               "model_version": result.model_version, "model_calls": result.groups_total,
               "groups_failed": result.groups_failed, "unread_pages": unread,
               "claims_total": len(result.claims),
               "claims_rejected": dict(rejected), "rules_stored": len(rules),
               "security_events": events, "rules_version": db.rules_version(conn)}
    log("ingest", request_id=rid, **summary)
    if status == "partial":   # leído a medias: se dice, y el resolve lo marcará para revisión
        summary["requires_human_review"] = True
        summary["review_reasons"] = ["document_partially_read"]
    return summary


@app.get("/v1/rules")
def rules(jurisdiction: str | None = None, payment_type: str | None = None,
          tax_year: int | None = None, limit: int = 50, offset: int = 0):
    conn, limit, offset = db.connect(), max(1, min(limit, 200)), max(0, offset)
    items = db.list_rules(conn, jurisdiction, payment_type, tax_year, limit, offset)
    total = len(db.list_rules(conn, jurisdiction, payment_type, tax_year))
    return {"items": [{**vars(r), "rate": r.rate and str(r.rate),
                       "flat_amount": r.flat_amount and str(r.flat_amount),
                       "min_amount": r.min_amount and str(r.min_amount)} for r in items],
            "limit": limit, "offset": offset, "total": total,
            "rules_version": db.rules_version(conn)}


def parse_query(params) -> Query:
    """Parámetros estructurados y cerrados. Ningún modelo interpreta la petición."""
    allowed = {"payment_type", "amount", "jurisdiction", "tax_year", "payee_type"}
    if set(params) - allowed:
        raise ValueError("unknown_parameter")
    try:
        amount, year = Decimal(params["amount"]), int(params["tax_year"])
    except (KeyError, InvalidOperation, ValueError):
        raise ValueError("amount_and_tax_year_required")
    payee = params.get("payee_type")
    if (not amount.is_finite() or not Decimal("0.01") <= amount < Decimal("1e15")
            or not 2000 <= year <= 2100
            or params.get("payment_type") not in PAYMENT_TYPES
            or not re.match(JURISDICTION_PATTERN, params.get("jurisdiction", ""))
            or (payee is not None and payee not in PAYEE_TYPES)):
        raise ValueError("invalid_parameter_value")
    return Query(params["payment_type"], amount, params["jurisdiction"], year, payee)


@app.get("/v1/resolve")
def resolve_endpoint(request: Request):
    rid, deadline = request.state.request_id, request.state.deadline
    try:
        query = parse_query(dict(request.query_params))
    except ValueError as exc:
        return error(422, str(exc), rid)
    conn = db.connect()
    deadline.check()
    candidates = db.list_rules(conn, query.jurisdiction, query.payment_type)
    if "-" in query.jurisdiction:   # una regla del país entero vale también en su subdivisión
        candidates += db.list_rules(conn, query.jurisdiction.split("-")[0], query.payment_type)
    response, record = resolve(query, candidates, db.rules_version(conn),
                               db.security_events(conn))
    versions = dict(conn.execute("SELECT source_url, model_version FROM documents"))
    record["rules_used"] = [   # lo necesario para reconstruir la decisión aunque la regla cambie
        {"id": r.id, "source_url": r.source_url, "page": r.page, "rate": r.rate and str(r.rate),
         "min_amount": r.min_amount and str(r.min_amount), "model_version": versions.get(r.source_url)}
        for r in candidates if r.id in record["rule_ids"]]
    partial = [safe_url(r["source_url"]) for r in conn.execute(
        "SELECT source_url FROM documents WHERE status != 'complete'")]
    if partial:   # R3: un documento leído a medias nunca respalda una decisión sin revisión
        response["requires_human_review"] = True
        response["review_reasons"].append("document_partially_read")
        response["decision_trace"].append({"step": "partial_documents", "result": partial})
        record["review_reasons"] = response["review_reasons"]
    deadline.check()   # vencido el plazo se responde 504, nunca un resultado a medias
    with conn:
        conn.execute("INSERT INTO decisions (request_id, created_at, record) VALUES (?,?,?)",
                     (rid, datetime.now(timezone.utc).isoformat(timespec="seconds"),
                      json.dumps(record, default=str)))
    log("decision", request_id=rid, **record)
    response["request_id"] = rid
    return response
