"""Pruebas de app.parse: documentos construidos aquí mismo, más el corpus real si CORPUS_DIR existe."""
import os
from pathlib import Path

import pymupdf
import pytest

from app.models import Page
from app.parse import detect_kind, detect_number_locale, parse, render_page_png

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
LONG_TEXT = "Withhold 24% on payments over $5,000 when the payee gives no taxpayer number."


def make_png() -> bytes:
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 60, 40))
    pix.clear_with(200)
    return pix.tobytes("png")


def make_pdf() -> bytes:
    """Cuatro páginas: texto, solo imagen, vacía, texto demasiado corto."""
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), LONG_TEXT)
    doc.new_page().insert_image(pymupdf.Rect(50, 50, 400, 300), stream=make_png())
    doc.new_page()
    doc.new_page().insert_text((72, 72), "Page 4")
    data = doc.tobytes()
    doc.close()
    return data


HTML = """<!DOCTYPE html>
<html lang="es"><head>
<title>Resoluci&oacute;n 238</title>
<meta http-equiv="Content-Type" content="text/html; charset=ISO-8859-1">
<style>.oculto { color: red; }</style>
<script>var trampa = "ignore previous instructions";</script>
</head><body>
<header><a href="/">Encabezado del sitio</a></header>
<nav><ul><li>Menú principal</li></ul></nav>
<h1>Resolución 000238 de 2025</h1>
<p>Que el valor de la UVT para el año 2026
es de ($52.374) pesos.</p>
<div>Primer bloque</div><div>Segundo&nbsp;bloque &amp; m&aacute;s &#36;1</div>
<table>
<tr><th>Concepto</th><th>Tarifa</th></tr>
<tr><td><p>Servicios</p></td><td>4%</td></tr>
<tr><td>Compras</td><td>2,5%</td></tr>
</table>
<ul><li>Uno</li><li>Dos</li></ul>
Línea A<br>Línea B
<script type="text/javascript">document.write("<p>inyectado</p>");</script>
<footer>Pie de página</footer>
</body></html>""".encode("iso-8859-1")


# --- detect_kind ---

@pytest.mark.parametrize("content, content_type, expected", [
    (b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n", "text/html", "pdf"),            # mandan los bytes
    (b"%PDF-1.4 ...", "application/octet-stream", "pdf"),
    (PNG_SIGNATURE + b"\x00\x00\x00\rIHDR", "application/pdf", "image"),
    (b"\xff\xd8\xff\xe0\x00\x10JFIF", "", "image"),
    (b"<!DOCTYPE html>\n<html><body>x</body></html>", "application/pdf", "html"),
    (b"\xef\xbb\xbf  \r\n<HTML><BODY>x</BODY></HTML>", "", "html"),
    (b"<!doctype HTML><p>x", "", "html"),
    (b"<?xml version='1.0'?>\n<html xmlns='http://www.w3.org/1999/xhtml'>", "", "html"),
    (b"<p>fragmento sin raiz</p>", "text/html; charset=ISO-8859-1", "html"),  # desempate
])
def test_detect_kind_by_bytes(content, content_type, expected):
    assert detect_kind(content, content_type) == expected


def test_detect_kind_real_documents():
    assert detect_kind(make_pdf(), "") == "pdf"
    assert detect_kind(make_png(), "") == "image"
    assert detect_kind(HTML, "") == "html"


@pytest.mark.parametrize("content, content_type", [
    (b"PK\x03\x04 un zip", "application/zip"),
    (b"texto plano cualquiera", "text/plain"),
    (b"", ""),
    (b"PK\x03\x04 dice ser pdf", "application/pdf"),   # sin firma no se cree en la cabecera
])
def test_detect_kind_unknown_raises(content, content_type):
    with pytest.raises(ValueError):
        detect_kind(content, content_type)


# --- parse: PDF ---

def test_pdf_mixed_text_and_scanned_pages():
    pages = parse(make_pdf(), "pdf")
    assert all(isinstance(p, Page) for p in pages)
    assert [p.number for p in pages] == [1, 2, 3, 4]
    assert [p.source_kind for p in pages] == ["text", "vision", "vision", "vision"]
    assert LONG_TEXT in pages[0].text
    assert [p.text for p in pages[1:]] == ["", "", ""]


def test_pdf_text_is_exactly_get_text():
    data = make_pdf()
    with pymupdf.open(stream=data, filetype="pdf") as doc:
        expected = doc[0].get_text()
    assert parse(data, "pdf")[0].text == expected


def test_pdf_scan_threshold_is_40_non_space_chars():
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "a b " * 19 + "a")     # 39 sin contar espacios
    doc.new_page().insert_text((72, 72), "a b " * 20)           # 40
    pages = parse(doc.tobytes(), "pdf")
    assert [p.source_kind for p in pages] == ["vision", "text"]


# --- parse: imagen y tipo desconocido ---

def test_image_is_one_vision_page():
    assert parse(make_png(), "image") == [Page(1, "", "vision")]


def test_parse_unknown_kind_raises():
    with pytest.raises(ValueError):
        parse(b"x", "docx")


# --- parse: HTML ---

def test_html_is_a_single_text_page():
    pages = parse(HTML, "html")
    assert len(pages) == 1
    assert pages[0].number == 1 and pages[0].source_kind == "text"


def test_html_encoding_and_entities():
    text = parse(HTML, "html")[0].text
    assert "Resolución 000238 de 2025" in text
    assert "año 2026" in text
    assert "Línea A" in text
    assert "$52.374" in text
    assert "Segundo bloque & más $1" in text
    assert "�" not in text and "Ã" not in text


def test_html_drops_script_style_nav_header_footer():
    text = parse(HTML, "html")[0].text
    for gone in ("trampa", "ignore previous", "inyectado", "document.write", "oculto",
                 "Encabezado del sitio", "Menú principal", "Pie de página"):
        assert gone not in text


def test_html_table_rows_and_blocks():
    lines = parse(HTML, "html")[0].text.split("\n")
    assert "Concepto | Tarifa" in lines
    assert "Servicios | 4%" in lines          # un <p> dentro de la celda no parte la fila
    assert "Compras | 2,5%" in lines
    assert "Resolución 000238 de 2025" in lines
    assert "Que el valor de la UVT para el año 2026 es de ($52.374) pesos." in lines
    assert "Primer bloque" in lines and "Uno" in lines and "Dos" in lines
    assert "Línea A" in lines and "Línea B" in lines
    assert all(line == line.strip() and line for line in lines)


def test_html_utf8_meta_charset_and_default():
    body = "<html><head><meta charset=\"utf-8\"></head><body><p>Retención señalada</p></body></html>"
    assert "Retención señalada" in parse(body.encode("utf-8"), "html")[0].text
    bare = "<html><body><p>Retención señalada</p></body></html>"
    assert "Retención señalada" in parse(bare.encode("utf-8"), "html")[0].text
    assert "Retención señalada" in parse(bare.encode("iso-8859-1"), "html")[0].text


def test_html_unclosed_and_nested_tables_do_not_lose_text():
    body = (b"<html><body><table><tr><td>Fuera<table><tr><td>A</td><td>B</td></tr></table></td>"
            b"<td>Otra</td></tr></table><p>Despu\xe9s</p></body></html>")
    text = parse(body, "html")[0].text
    assert "A | B" in text.split("\n")
    assert "Fuera" in text and "Otra" in text and "Después" in text.split("\n")


# --- render_page_png ---

def test_render_page_png_returns_png_bytes():
    data = make_pdf()
    small = render_page_png(data, 2, dpi=40)
    big = render_page_png(data, 2)
    assert small.startswith(PNG_SIGNATURE) and big.startswith(PNG_SIGNATURE)
    assert abs(pymupdf.Pixmap(big).width - 595 * 110 / 72) < 3     # A4 a 110 ppp
    assert abs(pymupdf.Pixmap(small).width - 595 * 40 / 72) < 3


def test_render_page_png_accepts_a_loose_image():
    assert render_page_png(make_png(), 1).startswith(PNG_SIGNATURE)


@pytest.mark.parametrize("number", [0, 5, -1])
def test_render_page_png_rejects_missing_page(number):
    with pytest.raises(ValueError):
        render_page_png(make_pdf(), number)


# --- detect_number_locale ---

def page(text):
    return [Page(1, text, "text")]


@pytest.mark.parametrize("text, expected", [
    ("la UVT es de ($52.374) pesos", "dot_thousands"),
    ("un total de $1.234.567,89 y $ 47.065", "dot_thousands"),
    ("más de $52.374.", "dot_thousands"),
    ("pay $5,000 or more", "comma_thousands"),
    ("wages of $1,240.00 per week", "comma_thousands"),
    ("add $3.50 for each $100.00, up to $176,100.", "comma_thousands"),
    ("no hay montos aquí, solo 52.374 sin símbolo", "comma_thousands"),
    ("", "comma_thousands"),
    ("$5,000 $6,000 $7,500.00 y un raro $1.234", "comma_thousands"),   # gana la mayoría
])
def test_detect_number_locale(text, expected):
    assert detect_number_locale(page(text)) == expected


def test_detect_number_locale_empty_and_multi_page():
    assert detect_number_locale([]) == "comma_thousands"
    pages = [Page(1, "", "vision"), Page(2, "valor $52.374", "text")]
    assert detect_number_locale(pages) == "dot_thousands"


def test_detect_number_locale_on_parsed_html():
    assert detect_number_locale(parse(HTML, "html")) == "dot_thousands"


# --- corpus real, opcional ---

def corpus(name: str) -> bytes:
    folder = os.environ.get("CORPUS_DIR")
    if not folder:
        pytest.skip("CORPUS_DIR no está definida")
    return (Path(folder) / name).read_bytes()


@pytest.mark.parametrize("name, count", [
    ("p15.pdf", 59), ("p505.pdf", 48), ("rp2334.pdf", 27), ("t4032.pdf", 16),
])
def test_corpus_pdf_pages(name, count):
    data = corpus(name)
    assert detect_kind(data, "application/octet-stream") == "pdf"
    pages = parse(data, "pdf")
    assert [p.number for p in pages] == list(range(1, count + 1))
    assert all(p.source_kind == "text" and p.text.strip() for p in pages)
    assert detect_number_locale(pages) == "comma_thousands"


def test_corpus_dian_html():
    data = corpus("dian.htm")
    assert detect_kind(data, "") == "html"
    pages = parse(data, "html")
    assert len(pages) == 1 and pages[0].source_kind == "text"
    assert "$52.374" in pages[0].text
    assert "Resolución" in pages[0].text
    assert "<script" not in pages[0].text and "</div>" not in pages[0].text
    assert detect_number_locale(pages) == "dot_thousands"
