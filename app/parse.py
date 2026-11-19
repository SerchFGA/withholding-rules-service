"""Convierte un documento descargado en texto por página. El contenido es dato, nunca instrucción."""
import codecs
import re
from html.parser import HTMLParser

import pymupdf

from app.models import Page

MIN_TEXT_CHARS = 40   # con menos caracteres visibles, la página se trata como escaneo
_SKIP = {"script", "style", "nav", "header", "footer"}
_BLOCK = {"p", "div", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6", "br", "table"}
_CELL = {"td", "th"}
_CHARSET = re.compile(rb"charset\s*=\s*[\"']?\s*([\w.:-]+)", re.I)
_AMOUNT = re.compile(r"[$€£]\s?(\d[\d.,]*\d)")
_DOT_THOUSANDS = re.compile(r"\d{1,3}(\.\d{3})+(,\d{1,2})?|\d+,\d{2}")
_COMMA_THOUSANDS = re.compile(r"\d{1,3}(,\d{3})+(\.\d{1,2})?|\d+\.\d{2}")


def detect_kind(content: bytes, content_type: str) -> str:
    """Decide por los primeros bytes; la cabecera Content-Type solo desempata."""
    head = content[:2048].lstrip(b"\xef\xbb\xbf \t\r\n")
    low = head.lower()
    if head.startswith(b"%PDF"):
        return "pdf"
    if head.startswith((b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff")):
        return "image"
    if b"<html" in low or b"<!doctype html" in low:
        return "html"
    if b"%PDF" in content[:1024]:   # algunos PDF traen basura antes de la firma
        return "pdf"
    if b"<" in head and content_type.split(";")[0].strip().lower() in ("text/html", "application/xhtml+xml"):
        return "html"
    raise ValueError("tipo de documento no reconocido")


def parse(content: bytes, kind: str) -> list[Page]:
    if kind == "image":
        return [Page(1, "", "vision")]
    if kind == "html":
        return [Page(1, _html_text(content), "text")]
    if kind != "pdf":
        raise ValueError(f"tipo de documento no admitido: {kind!r}")
    pages = []
    with pymupdf.open(stream=content, filetype="pdf") as doc:
        for number, pdf_page in enumerate(doc, start=1):
            text = pdf_page.get_text()   # sin limpiar: el validador de citas usa este mismo texto
            if sum(1 for char in text if not char.isspace()) < MIN_TEXT_CHARS:
                pages.append(Page(number, "", "vision"))
            else:
                pages.append(Page(number, text, "text"))
    return pages


def render_page_png(content: bytes, page_number: int, dpi: int = 110) -> bytes:
    """La página (desde 1) como PNG, para leer con visión una página escaneada."""
    with pymupdf.open(stream=content) as doc:
        if not 1 <= page_number <= len(doc):
            raise ValueError(f"la página {page_number} no existe")
        return doc[page_number - 1].get_pixmap(dpi=dpi).tobytes("png")


def detect_number_locale(pages: list[Page]) -> str:
    """Vota con los montos que llevan símbolo de moneda. Sin evidencia o en empate: comma_thousands."""
    dot = comma = 0
    for page in pages:
        for amount in _AMOUNT.findall(page.text):
            dot += bool(_DOT_THOUSANDS.fullmatch(amount))
            comma += bool(_COMMA_THOUSANDS.fullmatch(amount))
    return "dot_thousands" if dot > comma else "comma_thousands"


def _decode(content: bytes) -> str:
    """BOM, luego meta charset, luego UTF-8, y al final windows-1252."""
    if content.startswith(codecs.BOM_UTF8):
        return content[3:].decode("utf-8", errors="replace")
    declared = _CHARSET.search(content[:4096])
    try:
        name = codecs.lookup(declared.group(1).decode("ascii")).name if declared else None
    except LookupError:
        name = None
    if name in ("iso8859-1", "ascii"):
        name = "cp1252"   # como los navegadores: es un superconjunto y evita caracteres de control
    if name is None:
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            name = "cp1252"
    return content.decode(name, errors="replace")


class _TextExtractor(HTMLParser):
    """Junta el texto visible: un salto por bloque y las celdas de una fila separadas por ' | '."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0                 # profundidad dentro de script, style, nav, header, footer
        self.in_cell = False
        self.first_cell = True
        self.tables: list[tuple[bool, bool]] = []   # estado de la fila que contiene cada tabla anidada

    def _block(self, tag: str) -> None:
        # Dentro de una celda, un bloque no parte la fila; una tabla anidada sí empieza líneas nuevas.
        self.parts.append(" " if self.in_cell and tag != "table" else "\n")

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP:
            self.skip += 1
        elif self.skip:
            return
        elif tag in _CELL:
            self.parts.append("" if self.first_cell else " | ")
            self.in_cell, self.first_cell = True, False
        elif tag in _BLOCK:
            self._block(tag)
            if tag == "table":
                self.tables.append((self.in_cell, self.first_cell))
                self.in_cell = False
            elif tag == "tr":
                self.in_cell, self.first_cell = False, True

    def handle_endtag(self, tag):
        if tag in _SKIP:
            self.skip = max(0, self.skip - 1)
        elif self.skip:
            return
        elif tag in _CELL:
            self.in_cell = False
        elif tag in _BLOCK and tag != "br":
            if tag == "tr":
                self.in_cell = False
            self._block(tag)
            if tag == "table" and self.tables:
                self.in_cell, self.first_cell = self.tables.pop()

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data.replace("\n", " ").replace("\r", " "))


def _html_text(content: bytes) -> str:
    extractor = _TextExtractor()
    extractor.feed(_decode(content))
    extractor.close()
    lines = (" ".join(line.split()) for line in "".join(extractor.parts).split("\n"))
    return "\n".join(line for line in lines if line)
