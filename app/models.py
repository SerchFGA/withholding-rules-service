"""Vocabulario cerrado y tipos compartidos: el contrato entre módulos. Sin modelo ni red."""
import time
from dataclasses import dataclass, field
from decimal import Decimal

CONTRACT_VERSION = "1.0"
REQUEST_BUDGET_SECONDS = 120.0
MAX_PAGES = 300   # tope por documento: acota el gasto de modelo de una sola ingesta
PIPELINE_VERSION = "2"   # sube al cambiar el prompt o el validador: obliga a releer los documentos

# Un documento nuevo puede traer otra jurisdicción: se valida la forma (país ISO y subdivisión
# opcional) y, si el dominio es conocido, que el país coincida.
JURISDICTION_PATTERN = r"^[A-Z]{2}(-[A-Z0-9]{2,4})?$"
HOST_COUNTRY = {"irs.gov": "US", "canada.ca": "CA", "dian.gov.co": "CO"}
PAYEE_TYPES = ("government", "non_resident", "resident")
PAYMENT_TYPES = (
    "services", "wages", "supplemental_wages", "gambling_winnings",
    "pension_nonperiodic", "pension_periodic", "eligible_rollover_distribution",
    "unemployment_compensation", "sick_pay", "interest", "dividends",
    "social_security_tax", "medicare_tax", "cpp_contribution", "ei_premium", "other",
)

# Qué tipo de regla encontró el modelo. Solo "rate" se resuelve; lo demás va a revisión.
RULE_KINDS = ("rate", "unsupported_cap", "unsupported_bracket", "unsupported_table")
# De qué depende la regla. Todo lo que no sea "unconditional" obliga a revisión humana.
# "qualified": firme, pero su cita trae una salvedad ("certain kinds", "unless you choose").
CONDITIONS = ("unconditional", "qualified", "requires_missing_tin", "optional_method", "other_condition")
FIRM_CONDITIONS = ("unconditional", "qualified")   # deciden; las demás solo si no hay ninguna firme

NON_RESIDENT_MIN_RATE = Decimal("0.3000")  # regla dura del enunciado, no sale del corpus

# Motivos de revisión: lista cerrada, se devuelven tal cual en review_reasons.
REVIEW_REASONS = (
    "no_rate_in_publication", "no_rule_for_tax_year", "tax_year_ambiguous_resolved_to_later",
    "conditional_on_payee_tin", "optional_withholding_method", "condition_not_evaluable",
    "conflicting_rules", "unsupported_rule_structure", "source_page_was_scanned",
    "payee_type_not_provided", "document_partially_read", "source_not_on_allowlist",
)


@dataclass(frozen=True)
class Page:
    number: int          # desde 1; un HTML sin páginas es una sola página 1
    text: str
    source_kind: str     # "text" (capa de texto) o "vision" (página escaneada)


@dataclass(frozen=True)
class Rule:
    """Una regla ya validada. Solo existe si pasó por app.validate."""
    id: int
    source_url: str
    jurisdiction: str
    payment_type: str
    tax_year: int
    kind: str                     # RULE_KINDS
    condition: str                # CONDITIONS
    rate: Decimal | None          # 0.2400 = 24 %
    flat_amount: Decimal | None
    min_amount: Decimal | None    # umbral: por debajo no se retiene
    threshold_inclusive: bool     # True: "at least X"; False: "more than X"
    page: int
    quote: str
    source_kind: str = "text"


@dataclass(frozen=True)
class Query:
    payment_type: str
    amount: Decimal
    jurisdiction: str
    tax_year: int
    payee_type: str | None = None


class DeadlineExceeded(Exception):
    pass


@dataclass
class Deadline:
    """El plazo de la petición. Se crea al llegar y se pasa a cada llamada."""
    expires_at: float
    clock: object = field(default=time.monotonic, repr=False)

    @classmethod
    def start(cls, seconds=REQUEST_BUDGET_SECONDS, clock=time.monotonic):
        return cls(expires_at=clock() + seconds, clock=clock)

    def remaining(self) -> float:
        return max(0.0, self.expires_at - self.clock())

    def check(self) -> None:
        if self.remaining() <= 0:
            raise DeadlineExceeded()
