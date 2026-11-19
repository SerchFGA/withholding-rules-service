"""Pruebas del resolve: reglas duras, umbral, política del cliente y registro (R1, R4, R6, R7)."""
import json
from decimal import Decimal

import pytest

from app.models import REVIEW_REASONS, Query, Rule
from app.resolve import amount_band, resolve

VERSION = "sha256:abc"
UNKNOWN = {"withholding_applies": None, "rate": None, "basis": None}
NO_WITHHOLDING = {"withholding_applies": False, "rate": "0.0000", "basis": "none"}
CONTRACT_FIELDS = ["contract_version", "query", "outcome", "requires_human_review",
                   "review_reasons", "provenance", "rules_version"]


def D(value):
    return None if value is None else Decimal(str(value))


def rule(id=1, rate="0.2400", flat=None, min_amount=None, inclusive=False, year=2026,
         kind="rate", condition="unconditional", source_kind="text"):
    return Rule(id=id, source_url=f"https://example.test/doc{id}.pdf", jurisdiction="US-FED",
                payment_type="services", tax_year=year, kind=kind, condition=condition,
                rate=D(rate), flat_amount=D(flat), min_amount=D(min_amount),
                threshold_inclusive=inclusive, page=10 + id, quote=f"quote {id}",
                source_kind=source_kind)


def query(amount="12000", payee=None, year=2026):
    return Query(payment_type="services", amount=Decimal(amount), jurisdiction="US-FED",
                 tax_year=year, payee_type=payee)


def run(rules, amount="12000", payee=None, year=2026, events=None):
    """Resuelve y comprueba las invariantes que valen para toda respuesta."""
    resp, record = resolve(query(amount, payee, year), rules, VERSION, events or [])
    assert list(resp)[:7] == CONTRACT_FIELDS
    assert resp["requires_human_review"] is bool(resp["review_reasons"])
    assert all(reason in REVIEW_REASONS for reason in resp["review_reasons"])
    assert len(set(resp["review_reasons"])) == len(resp["review_reasons"])
    if resp["outcome"]["withholding_applies"] is None:
        assert resp["requires_human_review"] is True
    assert resp["decision_trace"] and all(set(s) == {"step", "result"} for s in resp["decision_trace"])
    return resp, record


def policy_core(resp):
    return {k: resp["policy_outcome"][k] for k in ("withholding_applies", "rate", "basis")}


def cited(resp):
    return [(p["source_url"], p["page"], p["quote"]) for p in resp["provenance"]]


def test_government_never_withholds():
    resp, _ = run([rule()], payee="government")
    assert resp["outcome"] == NO_WITHHOLDING
    assert policy_core(resp) == NO_WITHHOLDING
    assert resp["requires_human_review"] is False
    assert resp["provenance"] == []


def test_government_wins_over_everything():
    rules = [rule(1, rate="0.3700", condition="requires_missing_tin", source_kind="vision"),
             rule(2, rate="0.2400"), rule(3, kind="unsupported_table", rate=None, year=2027)]
    for year in (2026, 2025):
        resp, _ = run(rules, amount="5000000", payee="government", year=year)
        assert resp["outcome"] == NO_WITHHOLDING
        assert policy_core(resp) == NO_WITHHOLDING
        assert resp["review_reasons"] == [] and resp["provenance"] == []


def test_non_resident_without_rule_withholds_minimum():
    resp, _ = run([], payee="non_resident")
    expected = {"withholding_applies": True, "rate": "0.3000", "basis": "percent_of_payment"}
    assert resp["outcome"] == expected and policy_core(resp) == expected
    assert resp["review_reasons"] == [] and resp["provenance"] == []


def test_non_resident_raises_document_rate_to_minimum():
    resp, _ = run([rule(rate="0.2400")], payee="non_resident")
    assert resp["outcome"]["rate"] == "0.3000" and resp["policy_outcome"]["rate"] == "0.3000"
    assert resp["outcome"]["withholding_applies"] is True


def test_non_resident_keeps_higher_document_rate():
    resp, _ = run([rule(rate="0.3700")], payee="non_resident")
    assert resp["outcome"]["rate"] == "0.3700" and resp["policy_outcome"]["rate"] == "0.3700"
    assert cited(resp) == [("https://example.test/doc1.pdf", 11, "quote 1")]


def test_non_resident_wins_over_threshold_and_unknowns():
    below, _ = run([rule(min_amount="5000")], amount="100", payee="non_resident")
    assert below["outcome"]["withholding_applies"] is True and below["outcome"]["rate"] == "0.3000"
    unsupported, _ = run([rule(kind="unsupported_table", rate=None)], payee="non_resident")
    assert unsupported["outcome"]["rate"] == "0.3000" and unsupported["review_reasons"] == []
    other_year, _ = run([rule(kind="unsupported_cap", rate=None, year=2025)], payee="non_resident")
    assert other_year["outcome"]["rate"] == "0.3000"
    assert "no_rule_for_tax_year" not in other_year["review_reasons"]
    assert "unsupported_rule_structure" not in other_year["review_reasons"]


def test_exclusive_threshold_at_the_edge():
    rules = [rule(min_amount="5000", inclusive=False)]
    at_edge, _ = run(rules, amount="5000", payee="resident")
    assert at_edge["outcome"] == NO_WITHHOLDING and policy_core(at_edge) == NO_WITHHOLDING
    assert at_edge["requires_human_review"] is False
    assert cited(at_edge) == [("https://example.test/doc1.pdf", 11, "quote 1")]
    above, _ = run(rules, amount="5000.01")
    assert above["outcome"] == {"withholding_applies": True, "rate": "0.2400", "basis": "percent_of_payment"}


def test_inclusive_threshold_at_the_edge():
    rules = [rule(min_amount="5000", inclusive=True)]
    at_edge, _ = run(rules, amount="5000")
    assert at_edge["outcome"]["withholding_applies"] is True and at_edge["outcome"]["rate"] == "0.2400"
    below, _ = run(rules, amount="4999.99")
    assert below["outcome"] == NO_WITHHOLDING


def test_no_rules_is_unknown_never_false():
    for payee in (None, "resident"):
        resp, _ = run([], payee=payee)
        assert resp["outcome"] == UNKNOWN and policy_core(resp) == UNKNOWN
        assert resp["outcome"]["withholding_applies"] is not False
        assert resp["review_reasons"] == ["no_rate_in_publication"]
        assert resp["provenance"] == []


def test_only_unsupported_rules():
    rules = [rule(1, kind="unsupported_table", rate=None), rule(2, kind="unsupported_bracket", rate=None)]
    resp, _ = run(rules)
    assert resp["outcome"] == UNKNOWN and policy_core(resp) == UNKNOWN
    assert resp["review_reasons"] == ["unsupported_rule_structure"]
    assert [p["quote"] for p in resp["provenance"]] == ["quote 1", "quote 2"]


def test_other_tax_year_resolves_adjusted_to_latest():
    rules = [rule(1, rate="0.2200", year=2024), rule(2, rate="0.2400", year=2025)]
    resp, record = run(rules, year=2023)
    assert resp["outcome"] == UNKNOWN
    assert policy_core(resp) == {"withholding_applies": True, "rate": "0.2400", "basis": "percent_of_payment"}
    assert "no_rule_for_tax_year" in resp["review_reasons"]
    assert "tax_year_ambiguous_resolved_to_later" in resp["review_reasons"]
    assert "later_tax_year" in resp["policy_applied"]
    assert record["rule_ids"] == [2]


def test_same_year_rules_ignore_other_years():
    resp, _ = run([rule(1, rate="0.2400", year=2026), rule(2, rate="0.3700", year=2027)])
    assert resp["outcome"]["rate"] == "0.2400" and policy_core(resp) == resp["outcome"]
    assert resp["review_reasons"] == [] and resp["policy_applied"] == []


def test_most_specific_rule_wins():
    rules = [rule(1, rate="0.2200"), rule(2, rate="0.3700", min_amount="1000000")]
    high, _ = run(rules, amount="1500000")
    assert high["outcome"]["rate"] == "0.3700" and high["requires_human_review"] is False
    assert [p["quote"] for p in high["provenance"]] == ["quote 2"]
    low, _ = run(rules, amount="50000")
    assert low["outcome"]["rate"] == "0.2200"
    assert [p["quote"] for p in low["provenance"]] == ["quote 1"]


def test_conflicting_rates():
    resp, _ = run([rule(1, rate="0.2400"), rule(2, rate="0.2800")])
    assert resp["outcome"] == UNKNOWN and policy_core(resp) == UNKNOWN
    assert resp["review_reasons"] == ["conflicting_rules"]
    assert [p["quote"] for p in resp["provenance"]] == ["quote 1", "quote 2"]


def test_same_rate_from_several_rules():
    resp, _ = run([rule(1, rate="0.2400"), rule(2, rate="0.24")])
    assert resp["outcome"]["rate"] == "0.2400" and resp["requires_human_review"] is False
    assert [p["quote"] for p in resp["provenance"]] == ["quote 1", "quote 2"]


@pytest.mark.parametrize("kwargs, reason", [
    ({"condition": "requires_missing_tin"}, "conditional_on_payee_tin"),
    ({"condition": "optional_method"}, "optional_withholding_method"),
    ({"condition": "other_condition"}, "condition_not_evaluable"),
    ({"source_kind": "vision"}, "source_page_was_scanned"),
])
def test_conditions_return_rate_with_review(kwargs, reason):
    resp, _ = run([rule(rate="0.2400", **kwargs)])
    assert resp["outcome"] == {"withholding_applies": True, "rate": "0.2400", "basis": "percent_of_payment"}
    assert resp["review_reasons"] == [reason] and resp["requires_human_review"] is True


def test_policy_flat_amount_wins_when_higher():
    resp, _ = run([rule(rate="0.1000", flat="500")], amount="1000")  # 100 contra 500
    assert resp["outcome"] == {"withholding_applies": True, "rate": "0.1000", "basis": "percent_of_payment"}
    assert resp["policy_outcome"] == {"withholding_applies": True, "rate": None,
                                      "basis": "flat_amount", "flat_amount": "500"}
    assert resp["policy_applied"] == ["higher_of_percent_or_flat"]
    assert resp["requires_human_review"] is False


def test_policy_percent_wins_when_higher():
    resp, _ = run([rule(rate="0.1000", flat="500")], amount="10000")  # 1000 contra 500
    assert resp["outcome"] == {"withholding_applies": True, "rate": "0.1000", "basis": "percent_of_payment"}
    assert resp["policy_outcome"] == {"withholding_applies": True, "rate": "0.1000",
                                      "basis": "percent_of_payment", "flat_amount": None}
    assert resp["policy_applied"] == ["higher_of_percent_or_flat"]


def test_flat_amount_only_rule():
    resp, _ = run([rule(rate=None, flat="75.50")])
    assert resp["outcome"] == {"withholding_applies": True, "rate": None, "basis": "flat_amount"}
    assert policy_core(resp) == resp["outcome"] and resp["policy_applied"] == []


def test_policy_outcome_equals_outcome_when_policy_changes_nothing():
    resp, _ = run([rule()])
    assert policy_core(resp) == resp["outcome"]
    assert resp["policy_outcome"]["flat_amount"] is None and resp["policy_applied"] == []


def test_contract_fields_and_query_echo():
    resp, _ = run([rule()])
    assert resp["contract_version"] == "1.0" and resp["rules_version"] == VERSION
    assert resp["query"] == {"payment_type": "services", "amount": 12000,
                             "jurisdiction": "US-FED", "tax_year": 2026}
    assert type(resp["query"]["amount"]) is int
    assert resp["provenance"] == [{"source_url": "https://example.test/doc1.pdf", "page": 11, "quote": "quote 1"}]
    for extra in ("policy_outcome", "policy_applied", "security_events", "decision_trace"):
        assert extra in resp
    json.dumps(resp)  # toda la respuesta es JSON puro
    decimal, _ = run([rule()], amount="12000.50", payee="resident")
    assert decimal["query"]["amount"] == 12000.5 and decimal["query"]["payee_type"] == "resident"


def test_exact_amount_never_in_record_or_trace():
    rules = [rule(1, rate="0.1000", flat="500", min_amount="600", inclusive=True),
             rule(2, rate="0.2400", year=2025)]
    for amount, payee in (("48313.77", None), ("48313.77", "non_resident"), ("48313", "resident"),
                          ("48313.77", "government")):
        for year in (2026, 2027):
            resp, record = run(rules, amount=amount, payee=payee, year=year)
            for blob in (json.dumps(record), json.dumps(resp["decision_trace"])):
                assert "48313" not in blob and "4831.3" not in blob  # ni el monto ni tasa*monto
            assert record["amount_band"] == "10000-99999"


def test_decision_record_contents():
    rules = [rule(1, rate="0.2200"), rule(2, rate="0.3700", min_amount="1000000")]
    resp, record = run(rules, amount="50000", payee="resident")
    assert set(record) == {"jurisdiction", "payment_type", "tax_year", "payee_type", "amount_band",
                           "rule_ids", "thresholds_applied", "steps", "outcome", "policy_outcome",
                           "review_reasons", "rules_version"}
    assert record["rule_ids"] == [1] and record["payee_type"] == "resident"
    assert record["thresholds_applied"] == [
        {"rule_id": 1, "min_amount": None, "inclusive": False, "satisfied": True},
        {"rule_id": 2, "min_amount": "1000000", "inclusive": False, "satisfied": False}]
    assert record["steps"] == resp["decision_trace"]
    assert record["outcome"] == resp["outcome"] and record["policy_outcome"] == resp["policy_outcome"]
    assert record["rules_version"] == VERSION and record["review_reasons"] == []
    json.dumps(record)


def test_security_events_are_copied_without_changing_the_answer():
    events = [{"page": 3, "pattern": "ignore previous instructions", "source_url": "https://x.test"}]
    clean, _ = run([rule()])
    flagged, _ = run([rule()], events=events)
    assert flagged["security_events"] == events and clean["security_events"] == []
    for key in ("outcome", "policy_outcome", "requires_human_review", "review_reasons", "provenance"):
        assert flagged[key] == clean[key]


def test_missing_payee_type_is_traced_without_review():
    resp, _ = run([rule()])
    assert "payee_type" not in resp["query"]
    assert resp["review_reasons"] == []
    assert any("payee" in s["step"] and "not_provided" in s["result"] for s in resp["decision_trace"])


@pytest.mark.parametrize("amount, band", [
    ("0", "<1000"), ("999.99", "<1000"), ("1000", "1000-9999"), ("9999.99", "1000-9999"),
    ("10000", "10000-99999"), ("99999.99", "10000-99999"), ("100000", ">=100000"), ("5000000", ">=100000"),
])
def test_amount_band(amount, band):
    assert amount_band(Decimal(amount)) == band


def test_unsupported_rule_next_to_a_rate_forces_review():
    # Caso real: seguridad social 6.2 % y, aparte, su tope máximo. Ignorar el tope en
    # silencio retendría de más sin avisar a nadie.
    rules = [rule(1, rate="0.0620"), rule(2, kind="unsupported_cap", rate=None)]
    resp, _ = run(rules)
    assert resp["outcome"]["rate"] == "0.0620"
    assert resp["review_reasons"] == ["unsupported_rule_structure"]
    assert [p["quote"] for p in resp["provenance"]] == ["quote 1", "quote 2"]


def test_unsupported_rule_next_to_an_unmet_threshold_forces_review():
    rules = [rule(1, min_amount="50000"), rule(2, kind="unsupported_cap", rate=None)]
    resp, _ = run(rules, payee="resident")
    assert resp["outcome"] == NO_WITHHOLDING
    assert resp["review_reasons"] == ["unsupported_rule_structure"]


# Hallazgos de la revisión independiente (2026-11-19).

@pytest.mark.parametrize("kwargs, reason", [
    ({"condition": "other_condition"}, "condition_not_evaluable"),
    ({"condition": "requires_missing_tin"}, "conditional_on_payee_tin"),
    ({"source_kind": "vision"}, "source_page_was_scanned"),
])
def test_unmet_threshold_of_a_conditional_or_scanned_rule_still_needs_review(kwargs, reason):
    # "No se retiene" apoyado en una regla dudosa no puede salir limpio.
    resp, _ = run([rule(1, min_amount="999999999", **kwargs)], payee="resident")
    assert resp["outcome"] == NO_WITHHOLDING
    assert resp["review_reasons"] == [reason]


def test_only_earlier_years_is_unknown_and_never_called_later():
    # Con reglas solo de 2024, una consulta de 2026 no tiene "año posterior" al cual ir.
    resp, _ = run([rule(1, rate="0.2200", year=2024)], year=2026)
    assert resp["outcome"] == UNKNOWN and policy_core(resp) == UNKNOWN
    assert resp["review_reasons"] == ["no_rule_for_tax_year"]
    assert resp["policy_applied"] == [] and resp["provenance"] == []


def test_later_year_is_used_only_when_it_is_really_later():
    resp, _ = run([rule(1, rate="0.2200", year=2026), rule(2, rate="0.2400", year=2027)], year=2025)
    assert resp["outcome"] == UNKNOWN
    assert policy_core(resp)["rate"] == "0.2400" and resp["policy_applied"] == ["later_tax_year"]
    assert resp["review_reasons"] == ["no_rule_for_tax_year", "tax_year_ambiguous_resolved_to_later"]


def test_no_withholding_without_payee_type_needs_review():
    # Sin saber quién cobra no se pudo evaluar la regla del no residente: un dato ausente
    # no cuenta como evidencia contra la retención.
    rules = [rule(1, min_amount="5000")]
    resp, _ = run(rules, amount="100")
    assert resp["outcome"] == NO_WITHHOLDING and resp["review_reasons"] == ["payee_type_not_provided"]
    resp, _ = run(rules, amount="100", payee="resident")
    assert resp["outcome"] == NO_WITHHOLDING and resp["review_reasons"] == []
    resp, _ = run(rules, amount="6000")   # cuando sí se retiene, no hace falta el aviso
    assert resp["review_reasons"] == []
