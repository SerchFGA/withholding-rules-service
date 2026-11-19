"""Decide una retención. Función pura: sin modelo, sin red, sin base de datos.

El orden de los pasos y las tres reglas duras viven aquí (R1). Un dato ausente es
"desconocido, revisar", nunca "no se retiene" (R4). El monto exacto no sale en la traza ni
en el registro (R7).
"""
from decimal import Decimal

from app.models import CONTRACT_VERSION, NON_RESIDENT_MIN_RATE, Query, Rule

_CONDITION_REASONS = {
    "requires_missing_tin": "conditional_on_payee_tin",
    "optional_method": "optional_withholding_method",
    "other_condition": "condition_not_evaluable",
}
# Motivos que la regla dura del no residente deja sin efecto cuando decide ella.
_SUPERSEDED_BY_HARD_RULE = ("no_rate_in_publication", "no_rule_for_tax_year", "unsupported_rule_structure")
_BANDS = ((Decimal(1000), "<1000"), (Decimal(10000), "1000-9999"), (Decimal(100000), "10000-99999"))


def amount_band(amount: Decimal) -> str:
    """Rango del monto para el registro: lo único del monto que se anota."""
    return next((label for limit, label in _BANDS if amount < limit), ">=100000")


def _out(applies, rate=None, basis=None, flat=None) -> dict:
    return {"applies": applies, "rate": rate, "basis": basis, "flat": flat}


def _unknown() -> dict:
    return _out(None)


def _no_withholding() -> dict:
    return _out(False, Decimal(0), "none")


def _public(o: dict, with_flat: bool = False) -> dict:
    """Forma del contrato: la tasa es texto con cuatro decimales."""
    rate = None if o["rate"] is None else format(o["rate"], ".4f")
    public = {"withholding_applies": o["applies"], "rate": rate, "basis": o["basis"]}
    if with_flat:
        public["flat_amount"] = None if o["flat"] is None else str(o["flat"])
    return public


def _doubts(rules: list[Rule]) -> list[str]:
    """Motivos de revisión por regla condicional o salida de una página escaneada."""
    found = []
    for r in rules:
        for x in (_CONDITION_REASONS.get(r.condition), "source_page_was_scanned" if r.source_kind == "vision" else None):
            if x and x not in found:
                found.append(x)
    return found


def _evaluate(amount: Decimal, rules: list[Rule], step, thresholds: list) -> tuple:
    """Pasos 3 a 9. Devuelve (sin ajustar, ajustado, motivos, citadas, elegidas, política)."""
    if not rules:
        step("rules_available", "none: unknown")
        return _unknown(), _unknown(), ["no_rate_in_publication"], [], [], []
    usable = [r for r in rules if r.kind == "rate" and (r.rate is not None or r.flat_amount is not None)]
    step("usable_rules", f"{len(usable)} of {len(rules)}")
    if not usable:
        unsupported = [r for r in rules if r.kind != "rate"]
        reason = "unsupported_rule_structure" if unsupported else "no_rate_in_publication"
        return _unknown(), _unknown(), [reason], unsupported, [], []
    # Una estructura no soportada junto a una tasa (un tope máximo, por ejemplo) no se
    # ignora en silencio: la tasa se devuelve, pero una persona debe mirarla.
    extra = [r for r in rules if r.kind != "rate"]
    flagged = ["unsupported_rule_structure"] if extra else []
    # Las reglas firmes deciden; las condicionales solo deciden si no hay ninguna firme.
    pool = [r for r in usable if r.condition == "unconditional"] or usable
    met, rivals = [], []
    for r in usable:  # paso 5, regla dura del umbral
        ok = r.min_amount is None or amount > r.min_amount or (amount == r.min_amount and r.threshold_inclusive)
        thresholds.append({"rule_id": r.id, "min_amount": None if r.min_amount is None else str(r.min_amount),
                           "inclusive": r.threshold_inclusive, "satisfied": ok})
        if ok:
            (met if r in pool else rivals).append(r)
    step("threshold", f"{len(met)} of {len(pool)} deciding rules satisfied")
    if not met:  # "no se retiene" apoyado en una regla dudosa, o con una condicional viva, no sale limpio
        return _no_withholding(), _no_withholding(), flagged + _doubts(pool + rivals), pool + rivals + extra, [], []
    chosen, ids = met, [r.id for r in met]
    if len({(r.rate, r.flat_amount) for r in chosen}) > 1:
        # Tasas distintas a la vez: no se supone que el tramo alto reemplace al bajo.
        step("selection", f"conflicting rules {ids}")
        return _unknown(), _unknown(), ["conflicting_rules"], chosen, [], []
    rate, flat = chosen[0].rate, chosen[0].flat_amount
    rivals = [r for r in rivals if (r.rate, r.flat_amount) != (rate, flat)]
    step("selection", f"rules {ids}, conditional rivals {[r.id for r in rivals]}")
    reasons = flagged + _doubts(chosen + rivals)  # paso 7: la tasa se devuelve igual, con revisión
    step("conditions", ",".join(reasons) or "unconditional")
    main = _out(True, rate, "percent_of_payment") if rate is not None else _out(True, None, "flat_amount", flat)
    step("unadjusted_outcome", main["basis"])
    policy, applied = main, []
    if rate is not None and flat is not None:  # paso 9: gana el que retenga más
        applied = ["higher_of_percent_or_flat"]
        if flat > rate * amount:
            policy = _out(True, None, "flat_amount", flat)
        step("client_policy", f"higher_of_percent_or_flat: {policy['basis']}")
    return main, policy, reasons, chosen + rivals + extra, chosen, applied


def _non_resident_floor(o: dict, amount: Decimal) -> dict:
    """Regla dura: siempre se retiene, con tasa mínima. Un fijo que ya retiene más se conserva."""
    if o["rate"] is None and o["flat"] is not None and o["flat"] >= NON_RESIDENT_MIN_RATE * amount:
        return o
    return _out(True, max(o["rate"] or Decimal(0), NON_RESIDENT_MIN_RATE), "percent_of_payment")


def resolve(query: Query, rules: list[Rule], rules_version: str, security_events: list[dict]) -> tuple[dict, dict]:
    """Devuelve (respuesta del contrato, registro de decisión para el log)."""
    trace: list[dict] = []
    thresholds: list[dict] = []

    def step(name: str, result: str) -> None:
        trace.append({"step": name, "result": result})

    main = policy = _no_withholding()
    reasons: list[str] = []
    cited: list[Rule] = []
    applied: list[str] = []
    payee = query.payee_type
    if payee is None:  # paso 11: sin tipo de beneficiario no se evalúan los pasos 1 y 10
        step("payee_hard_rules", "skipped: payee_type not_provided")
    if payee == "government":  # paso 1: gana sobre todo lo demás
        step("payee_government", "never withhold")
    else:
        if payee is not None:
            step("payee_government", "not government")
        year_rules = [r for r in rules if r.tax_year == query.tax_year]
        other_years = bool(rules) and not year_rules
        latest = max((r.tax_year for r in rules if r.tax_year > query.tax_year), default=None)
        fallback = other_years and latest is not None
        if fallback:  # paso 2: el ajustado usa el año posterior más reciente
            year_rules = [r for r in rules if r.tax_year == latest]
            step("tax_year", f"no rule for {query.tax_year}: adjusted outcome uses {latest}")
        else:
            step("tax_year", f"{len(year_rules)} rules for {query.tax_year}")
        main, policy, reasons, cited, chosen, applied = _evaluate(query.amount, year_rules, step, thresholds)
        if fallback:
            main = _unknown()
            reasons = ["no_rule_for_tax_year", "tax_year_ambiguous_resolved_to_later"] + reasons
            applied = ["later_tax_year"] + applied
        elif other_years:  # solo hay años anteriores: no hay año posterior al cual ir
            reasons = ["no_rule_for_tax_year"]
        if payee is None and _no_withholding() in (main, policy):
            # Sin saber quién cobra no se evaluó la regla del no residente: un dato ausente
            # no cuenta como evidencia contra la retención.
            reasons.append("payee_type_not_provided")
        if payee == "non_resident":  # paso 10: gana al umbral y a los "desconocido"
            if fallback or not chosen:
                reasons = [x for x in reasons if x not in _SUPERSEDED_BY_HARD_RULE]
            if not chosen:
                cited = []
            main = _non_resident_floor(main, query.amount)
            policy = _non_resident_floor(policy, query.amount)
            step("payee_non_resident", f"always withhold, minimum rate {NON_RESIDENT_MIN_RATE}")
        elif payee is not None:
            step("payee_non_resident", "not non_resident")
    outcome, policy_outcome = _public(main), _public(policy, with_flat=True)
    step("final", f"unadjusted {outcome['basis']}, adjusted {policy_outcome['basis']}, review {bool(reasons)}")

    echo = {"payment_type": query.payment_type,
            "amount": int(query.amount) if query.amount == query.amount.to_integral_value() else float(query.amount),
            "jurisdiction": query.jurisdiction, "tax_year": query.tax_year}
    if payee is not None:
        echo["payee_type"] = payee
    response = {
        "contract_version": CONTRACT_VERSION,
        "query": echo,
        "outcome": outcome,
        "requires_human_review": bool(reasons),
        "review_reasons": reasons,
        "provenance": [{"source_url": r.source_url, "page": r.page, "quote": r.quote} for r in cited],
        "rules_version": rules_version,
        "policy_outcome": policy_outcome,
        "policy_applied": applied,
        "security_events": list(security_events),
        "decision_trace": trace,
    }
    record = {
        "jurisdiction": query.jurisdiction, "payment_type": query.payment_type,
        "tax_year": query.tax_year, "payee_type": payee, "amount_band": amount_band(query.amount),
        "rule_ids": [r.id for r in cited], "thresholds_applied": thresholds, "steps": trace,
        "outcome": outcome, "policy_outcome": policy_outcome,
        "review_reasons": list(reasons), "rules_version": rules_version,
    }
    return response, record
