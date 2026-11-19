"""make verify: base vacía, ingesta real de los cinco documentos, pruebas y set de evaluación.

Imprime una línea PASS o FAIL por requisito (R1 a R7) y la exactitud. La salida va en inglés
porque la leen los evaluadores. Necesita ANTHROPIC_API_KEY: la ingesta llama al modelo de
verdad, y aquí no hay respuestas guardadas (sería sembrar la demostración).
"""
import contextlib
import io
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Qué pruebas respaldan cada requisito (expresión sobre "archivo::nombre").
REQUIREMENTS = {
    "R1 control flow": r"test_resolve\.py::|test_api\.py::test_(hard_rules|resolve_rejects)",
    "R2 model claims": r"test_validate\.py::(?!.*inject)|test_api\.py::test_ingest_stores_only"
                       r"|test_extract\.py::test_(schema|request_uses|claims_are_not)",
    "R3 deadline": r"test_extract\.py::test_.*(deadline|no_retries|failing_group|refusal)"
                   r"|test_fetch\.py::test_.*(deadline|timeout)|test_api\.py::test_(expired|partially)",
    "R4 human review": r"test_resolve\.py::test_(no_rules|only_unsupported|other_tax_year|conflicting"
                       r"|unsupported_rule|conditions)|test_api\.py::test_missing_rate",
    "R5 untrusted input": r"inject|embedded_instruction|test_fetch\.py::test_rejects|page_text_travels"
                          r"|security_events",
    "R6 contract": r"test_api\.py::test_(reingest|resolve_returns_contract)"
                   r"|test_resolve\.py::test_(contract_fields|policy)",
    "R7 sensitive data": r"test_logs\.py::|test_api\.py::test_logs|exact_amount|api_key_never"
                         r"|error_message_has_no_query",
}


CANARY = "73519.37"


def say(text=""):
    print(text, file=sys.__stdout__, flush=True)


def run_tests(tmp):
    """Corre pytest y devuelve {"archivo::nombre": pasó}."""
    report = Path(tmp) / "junit.xml"
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                           f"--junitxml={report}"], cwd=ROOT, capture_output=True, text=True)
    say(proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else proc.stderr[-400:])
    if not report.exists():   # pytest no llegó a correr: faltan las dependencias
        say("Tests did not run. Install the dependencies first: pip install -r requirements-dev.txt")
        sys.exit(2)
    results = {}
    for case in ET.parse(report).getroot().iter("testcase"):
        name = f"{case.get('classname', '').split('.')[-1]}.py::{case.get('name')}"
        failed = any(child.tag in ("failure", "error") for child in case)
        skipped = any(child.tag == "skipped" for child in case)
        if not skipped:
            results[name] = not failed
    return results


def matches(expected, got):
    """Compara lo esperado con la respuesta; devuelve la lista de diferencias."""
    outcome, diffs = got["outcome"], []
    for field in ("withholding_applies", "rate", "basis"):
        if outcome[field] != expected[field]:
            diffs.append(f"{field}: expected {expected[field]!r}, got {outcome[field]!r}")
    if got["requires_human_review"] != expected["requires_human_review"]:
        diffs.append(f"requires_human_review: expected {expected['requires_human_review']}")
    if set(got["review_reasons"]) != set(expected["review_reasons"]):
        diffs.append(f"review_reasons: expected {expected['review_reasons']}, got {got['review_reasons']}")
    return diffs


def load_dotenv():
    """Lee .env si existe (nunca se versiona). Lo que ya está en el entorno manda."""
    env = ROOT / ".env"
    for line in env.read_text(encoding="utf-8").splitlines() if env.exists() else []:
        name, sep, value = line.partition("=")
        if sep and name.strip() and not name.startswith("#"):
            os.environ.setdefault(name.strip(), value.strip())


def main():
    load_dotenv()
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        say("make verify needs ANTHROPIC_API_KEY in the environment: ingesting the five documents\n"
            "calls the model for real. Example:  ANTHROPIC_API_KEY=sk-ant-... make verify\n"
            "No key is stored in this repository, the image or any prompt.")
        return 2
    corpus = json.loads((ROOT / "eval" / "corpus.json").read_text(encoding="utf-8"))
    cases = json.loads((ROOT / "eval" / "cases.json").read_text(encoding="utf-8"))
    live = {name: [] for name in REQUIREMENTS}   # fallos de las comprobaciones en vivo
    checked = {"R2 model claims", "R3 deadline", "R6 contract", "R7 sensitive data"}   # las que tienen una
    corpus_failures = []

    # En Windows SQLite puede seguir con el archivo abierto al salir: no es un fallo de la prueba.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        say("== 1/3 Tests ==")
        tests = run_tests(tmp)

        say("\n== 2/3 Ingest five documents from an empty database (live network and model) ==")
        ingest_key = secrets.token_hex(16)
        os.environ.update(DATABASE_PATH=str(Path(tmp) / "verify.db"), INGEST_KEY=ingest_key)
        from fastapi.testclient import TestClient
        from app.main import app
        client, logs = TestClient(app), io.StringIO()
        headers = {"X-Ingest-Key": ingest_key}
        with contextlib.redirect_stdout(logs):   # los logs del servicio se revisan al final
            if client.get("/health").json()["documents"] != 0:
                live["R6 contract"].append("database was not empty at start")
            for doc in corpus:
                started = time.monotonic()
                resp = client.post("/v1/documents", json={"source_url": doc["source_url"]}, headers=headers)
                took, body = time.monotonic() - started, resp.json()
                say(f"  {doc['id']:7} http={resp.status_code} status={body.get('status', body.get('error'))}"
                    f" pages={body.get('pages')} rules={body.get('rules_stored')}"
                    f" rejected={sum((body.get('claims_rejected') or {}).values())} {took:5.1f}s")
                if took > 120:
                    live["R3 deadline"].append(f"{doc['id']} took {took:.0f}s")
                if resp.status_code == 504 or body.get("status") == "partial":
                    live["R3 deadline"].append(f"{doc['id']} not fully read: {body.get('status', body.get('error'))}")
                elif resp.status_code != 200:   # la red o el sitio, no un requisito del servicio
                    corpus_failures.append(f"{doc['id']}: {body.get('error')} {body.get('detail', '')}".strip())
            before = client.get("/v1/rules").json()["total"]
            if before == 0:   # sin una sola regla validada no hay nada que demostrar
                live["R2 model claims"].append("no rule was extracted and validated from any document")
            again = client.post("/v1/documents", json={"source_url": corpus[0]["source_url"]}, headers=headers).json()
            after = client.get("/v1/rules").json()["total"]
            if not again.get("cached") or again.get("model_calls") != 0 or before != after:
                live["R6 contract"].append("re-ingesting the same URL duplicated rows or model spend")
            say(f"  re-ingest {corpus[0]['id']}: cached={again.get('cached')} model_calls={again.get('model_calls')}"
                f" rules {before} -> {after}")

            say(f"\n== 3/3 Evaluation set ({len(cases)} queries) ==")
            passed = 0
            for case in cases:
                resp = client.get("/v1/resolve", params=case["query"])
                diffs = [f"http {resp.status_code}"] if resp.status_code != 200 else matches(case["expected"], resp.json())
                passed += not diffs
                say(f"  {'PASS' if not diffs else 'FAIL'}  {case['id']}" + ("" if not diffs else "  <- " + "; ".join(diffs)))

            # Un monto que no puede coincidir con ningún umbral ni rango: si aparece, es una fuga.
            client.get("/v1/resolve", params=dict(cases[0]["query"], amount=CANARY))

        text = logs.getvalue()
        leaks = [what for what, found in (
            ("API key", key in text), ("ingest key", ingest_key in text),
            ("query string", re.search(r"[?&]amount=", text)),
            ("exact amount", CANARY.split(".")[0] in text)) if found]
        if leaks:
            live["R7 sensitive data"].append("found in logs: " + ", ".join(leaks))
        if '"event": "decision"' not in text:
            live["R7 sensitive data"].append("no decision record in logs")

    say("\n== Result ==")
    ok = True
    for name, pattern in REQUIREMENTS.items():
        mine = {t: good for t, good in tests.items() if re.search(pattern, t)}
        failed = [t for t, good in mine.items() if not good] + live[name]
        good = bool(mine) and not failed
        ok = ok and good
        note = "; ".join(live[name]) or ("live check ok" if name in checked else "no live check")
        say(f"{name:20} {'PASS' if good else 'FAIL'}  ({sum(mine.values())}/{len(mine)} tests; {note})")
    ok = ok and not corpus_failures
    say(f"{'Corpus':20} {'PASS' if not corpus_failures else 'FAIL'}  ({len(corpus) - len(corpus_failures)}/{len(corpus)}"
        f" documents downloaded and ingested" + ("" if not corpus_failures else "; " + "; ".join(corpus_failures)) + ")")
    say(f"{'Accuracy':20} {passed}/{len(cases)} = {100 * passed / len(cases):.1f}% of evaluation queries match"
        " the expected answer (informative: it does not change the exit code)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
