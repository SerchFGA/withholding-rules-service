"""R7: nada sensible llega al registro, y lo necesario para reconstruir una decisión sí."""
import io
import json

from app.logs import log, redact, safe_url


def emit(**fields):
    stream = io.StringIO()
    log("test", stream=stream, **fields)
    return stream.getvalue()


def test_exact_amount_is_redacted():
    line = emit(amount="12000", query={"amount": 12000, "amount_band": "10000-99999"})
    assert "12000" not in line.replace("10000-99999", "")
    assert json.loads(line)["query"]["amount_band"] == "10000-99999"


def test_document_thresholds_are_kept():
    # El umbral sale del documento público y hace falta para reconstruir la decisión.
    line = emit(thresholds_applied=[{"rule_id": 3, "min_amount": "5000", "satisfied": True}])
    assert json.loads(line)["thresholds_applied"][0]["min_amount"] == "5000"


def test_secrets_are_redacted_by_key_and_by_value():
    line = emit(api_key="sk-ant-abc123", x_ingest_key="hunter2", authorization="Bearer zzz",
                note="la clave es sk-ant-api03-XYZ_9 y Bearer abc.def")
    for secret in ("sk-ant", "hunter2", "zzz", "abc.def"):
        assert secret not in line


def test_urls_lose_query_string_and_credentials():
    assert safe_url("https://user:pw@example.gov/a/b.pdf?token=1#x") == "https://example.gov/a/b.pdf"
    line = emit(detail="fallo en https://example.gov/doc.pdf?amount=12000&key=abc ahora")
    assert "amount=12000" not in line and "key=abc" not in line
    assert "https://example.gov/doc.pdf" in line


def test_nested_structures_are_cleaned():
    cleaned = redact({"steps": [{"token": "t", "result": "ok"}], "n": 3})
    assert cleaned == {"steps": [{"token": "[redacted]", "result": "ok"}], "n": 3}


def test_log_line_is_json_with_timestamp_and_event():
    record = json.loads(emit(request_id="abc"))
    assert record["event"] == "test" and record["request_id"] == "abc" and "ts" in record
