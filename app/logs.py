"""Registro JSON por evento, con redacción. Frontera de R7: el monto llega ya como rango
(resolve.amount_band) y aquí además se limpian claves, credenciales y parámetros de URL."""
import json
import re
import sys
from datetime import datetime, timezone
from urllib.parse import urlsplit

# "amount" a secas es el monto del pago (confidencial). Los umbrales del documento
# (min_amount, flat_amount) y el rango (amount_band) son públicos o ya minimizados.
SENSITIVE_KEY = re.compile(r"key|token|secret|sign|auth|password|credential|^amount$", re.I)
SECRET_VALUE = re.compile(r"sk-ant-[\w-]+|Bearer\s+\S+", re.I)
URL = re.compile(r"https?://[^\s\"'<>]+")


def safe_url(url: str, keep_query: bool = False) -> str:
    """La URL sin usuario ni fragmento. Para guardarla se conservan los parámetros que
    identifican el documento (?id=123) y se quitan los que parecen credenciales."""
    parts = urlsplit(url)
    query = "&".join(p for p in parts.query.split("&")
                     if p and not SENSITIVE_KEY.search(p.split("=")[0])) if keep_query else ""
    return f"{parts.scheme}://{parts.hostname or ''}{parts.path}" + (f"?{query}" if query else "")


def redact(value, key=""):
    if SENSITIVE_KEY.search(key):
        return "[redacted]"
    if isinstance(value, dict):
        return {k: redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    if isinstance(value, str):
        value = URL.sub(lambda m: safe_url(m.group(0)), value)
        return SECRET_VALUE.sub("[redacted]", value)
    return value


def log(event: str, stream=None, **fields) -> dict:
    record = {"ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
              "event": event, **redact(fields)}
    print(json.dumps(record, ensure_ascii=False, default=str), file=stream or sys.stdout, flush=True)
    return record
