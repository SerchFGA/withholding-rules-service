"""Registro estructurado con redacción. Una línea JSON por evento, a la salida estándar.

Frontera (R7): aquí nunca entra un monto exacto, una clave ni una URL con parámetros. Quien
llama entrega el monto ya reducido a un rango (resolve.amount_band); este módulo además
limpia todo lo que reciba, por si alguien se equivoca.
"""
import json
import re
import sys
from datetime import datetime, timezone
from urllib.parse import urlsplit

# "amount" a secas es el monto del pago (confidencial). Los umbrales del documento
# (min_amount, flat_amount) y el rango (amount_band) son públicos o ya minimizados.
SENSITIVE_KEY = re.compile(r"key|token|secret|authorization|password|credential|^amount$", re.I)
SECRET_VALUE = re.compile(r"sk-ant-[\w-]+|Bearer\s+\S+", re.I)
URL = re.compile(r"https?://[^\s\"'<>]+")


def safe_url(url: str) -> str:
    """La URL sin usuario, sin parámetros y sin fragmento."""
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.hostname or ''}{parts.path}"


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
