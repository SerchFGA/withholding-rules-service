# Usa el Python del entorno virtual si existe; si no, python3.
PYTHON ?= $(firstword $(wildcard .venv/bin/python .venv/Scripts/python.exe) python3)

.PHONY: verify test run

# Base vacia, ingesta real de los cinco documentos, pruebas y set de evaluacion.
# Necesita ANTHROPIC_API_KEY en el entorno o en .env.
verify:
	$(PYTHON) scripts/verify.py

test:
	$(PYTHON) -m pytest -q

run:
	$(PYTHON) -m uvicorn app.main:app --port 8000 --no-access-log
