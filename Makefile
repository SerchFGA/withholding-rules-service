PYTHON ?= python

.PHONY: verify test run

# Base vacia, ingesta real de los cinco documentos, pruebas y set de evaluacion.
# Necesita ANTHROPIC_API_KEY en el entorno.
verify:
	$(PYTHON) scripts/verify.py

test:
	$(PYTHON) -m pytest -q

run:
	$(PYTHON) -m uvicorn app.main:app --port 8000 --no-access-log
