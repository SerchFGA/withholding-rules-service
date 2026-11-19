"""Valida las afirmaciones del modelo: lo no validable se descarta. El texto fuente es dato (R2, R5)."""
import re
import unicodedata
from decimal import Decimal
from urllib.parse import urlsplit

from app.models import (CONDITIONS, HOST_COUNTRY, JURISDICTION_PATTERN, PAYMENT_TYPES,
                        RULE_KINDS, Page)

MIN_QUOTE_CHARS = 20
CONTEXT_CHARS = 150  # a cada lado de la cita: una ventana de 300
_CHARS = str.maketrans({"‘": "'", "’": "'", "‚": "'", "′": "'", "“": '"',
                        "”": '"', "„": '"', "″": '"', "ﬀ": "ff",
                        "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl"})
_DASHES = re.compile("[‐-―−­]")
# Solo entre letras: unir cifras a través de un guion fabricaría números.
_HYPHEN_BREAK = re.compile(r"([^\W\d_])-\s+(?=[^\W\d_])")
_YEAR = re.compile(r"(?<![\d$])(?:20\d\d|2100)(?!\d|[.,]\d)")
_WITHHOLDING = re.compile(r"withh|deduct|reten|contribution|premium")
_AMOUNT = re.compile(r"[0-9]+(?:\.[0-9]+)?")
_RATE = re.compile(r"[0-9]+(?:\.[0-9]{1,4})?")  # el contrato da cuatro decimales
_PERCENT = r"\s*(?:%|percent|per cent|por ciento)"
_INJECTION = {name: re.compile(pattern) for name, pattern in (
    ("ignore_instructions", r"\bignore (?:(?:all|any|the|your|these) )*(?:previous|prior|above|earlier)"
     r" (?:instructions|prompts?|rules)|\b(?:ignor|olvid|omit)[ae]\w* (?:todas )?(?:las |tus )?instrucciones"),
    ("disregard_instructions", r"\bdisregard (?:\w+ ){0,4}instructions"),
    ("role_override", r"\byou are now\b|\bahora eres\b|\beres ahora\b"),
    ("system_prompt", r"system prompt|prompt del? sistema"),
    ("report_no_withholding", r"\breport (?:that )?(?:there is )?no withholding"
     r"|\bno report\w+ (?:la |ninguna )?retenci[oó]n"))}


def normalize_text(s: str) -> str:
    """Misma forma para la cita y la página, aunque el PDF haya partido las líneas."""
    s = _DASHES.sub("-", unicodedata.normalize("NFC", s).translate(_CHARS))
    return re.sub(r"\s+", " ", _HYPHEN_BREAK.sub(r"\1", s)).strip().lower()


def document_years(pages: list[Page]) -> set[int]:
    """Años de cuatro cifras (2000 a 2100) que el documento menciona."""
    return {int(y) for page in pages for y in _YEAR.findall(page.text)}


def detect_injection(pages: list[Page]) -> list[dict]:
    """Registra instrucciones dirigidas a un modelo. Solo informa: no cambia nada."""
    events = []
    for page in pages:
        text = normalize_text(page.text)
        events += [{"page": page.number, "pattern": name,
                    "excerpt": text[max(0, m.start() - 40):][:160]}
                   for name, rx in _INJECTION.items() for m in rx.finditer(text)]
    return events


def _shape_ok(c) -> bool:
    if not isinstance(c, dict):
        return False
    texts = all(isinstance(c.get(k), str) for k in
                ("kind", "jurisdiction", "payment_type", "condition", "quote"))
    ints = all(type(c.get(k)) is int for k in ("tax_year", "page"))
    numbers = all(k in c and (c[k] is None or (isinstance(c[k], str) and rx.fullmatch(c[k])))
                  for k, rx in (("rate", _RATE), ("flat_amount", _AMOUNT), ("min_amount", _AMOUNT)))
    flag = c.get("threshold_inclusive")
    # Sin umbral la marca no significa nada: se admite nula y sale False.
    return texts and ints and numbers and (
        type(flag) is bool or (flag is None and c["min_amount"] is None))


def _rate_in(text: str, rate: Decimal) -> bool:
    """El porcentaje ("24%", "6.2 percent") o el decimal ("0.0595") como número completo."""
    percent = format((rate * 100).normalize(), "f")
    fraction = format(rate, "f").partition(".")[2].rstrip("0")
    forms = [percent.replace(".", "[.,]") + ("0*" if "." in percent else "(?:[.,]0+)?") + _PERCENT]
    if fraction and rate < 1:
        forms.append(rf"0?[.,]{fraction}0*(?!\d|\s*%)")
    return re.search(rf"(?<![\d.,])(?:{'|'.join(forms)})", text) is not None


def _amount_in(text: str, value: Decimal, number_locale: str) -> bool:
    """El monto como número completo, con o sin separador de miles; ignora ".00"."""
    sep, dec = (r"\.", ",") if number_locale == "dot_thousands" else (",", r"\.")
    whole, _, fraction = format(value.normalize(), "f").partition(".")
    body = f"{sep}?".join(f"{int(whole):,}".split(","))
    tail = f"{dec}{fraction}0*" if fraction else f"(?:{dec}0+)?"
    return re.search(rf"(?<![\d.,]){body}{tail}(?![.,]?\d)", text) is not None


def validate_claim(claim: dict, pages: dict[int, Page], doc_years: set[int],
                   number_locale: str, source_url: str) -> tuple[dict | None, str | None]:
    """Devuelve (regla, None) o (None, motivo). La primera comprobación que falla decide."""
    c = claim
    if not _shape_ok(c):
        return None, "malformed_claim"
    if (c["kind"] not in RULE_KINDS or c["payment_type"] not in PAYMENT_TYPES
            or c["condition"] not in CONDITIONS):
        return None, "unknown_vocabulary"
    host = (urlsplit(source_url if "://" in source_url else "//" + source_url).hostname or "").lower()
    country = next((v for k, v in HOST_COUNTRY.items() if host == k or host.endswith("." + k)), None)
    if not re.fullmatch(JURISDICTION_PATTERN, c["jurisdiction"]) or (
            country and c["jurisdiction"][:2] != country):
        return None, "jurisdiction_mismatch"
    page = pages.get(c["page"])
    if page is None:
        return None, "page_not_in_document"
    # Una página de visión no tiene texto contra el cual comparar: se omiten 5, 7 y lo textual de 8.
    has_text = page.source_kind != "vision"
    quote = normalize_text(c["quote"])
    if has_text:
        body = normalize_text(page.text)
        at = body.find(quote)
        if len(quote) < MIN_QUOTE_CHARS or at < 0:
            return None, "quote_not_in_source"
    if c["tax_year"] not in doc_years:
        return None, "tax_year_not_in_document"
    if has_text and not _WITHHOLDING.search(
            body[max(0, at - CONTEXT_CHARS):at + len(quote) + CONTEXT_CHARS]):
        return None, "not_a_withholding_statement"
    rate, flat, low = (None if c[k] is None else Decimal(c[k])
                       for k in ("rate", "flat_amount", "min_amount"))
    if c["kind"] == "rate" and rate is None and flat is None:
        return None, "rate_missing"
    if (rate is not None and not (0 < rate <= 1 and (not has_text or _rate_in(quote, rate)))) or (
            has_text and not all(v is None or _amount_in(quote, v, number_locale) for v in (flat, low))):
        return None, "number_not_in_quote"
    rule = {k: c[k] for k in ("jurisdiction", "payment_type", "tax_year", "kind", "condition",
                              "flat_amount", "min_amount", "page", "quote")}
    return {**rule, "rate": None if rate is None else format(rate, ".4f"),
            "threshold_inclusive": bool(c["threshold_inclusive"]), "source_kind": page.source_kind}, None
