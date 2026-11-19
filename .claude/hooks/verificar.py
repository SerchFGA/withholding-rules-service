"""Comprueba que INDICE.md y los documentos de planeación no se hayan desfasado.

    python .claude/hooks/verificar.py            # todo; termina con código 1 si algo falla
    python .claude/hooks/verificar.py --hook     # modo hook de Claude Code (ver abajo)

Falla si:
  - una sección (encabezado ##) de un documento de la carpeta de planeación no está en
    INDICE.md, o el índice lista una que ya no existe;
  - un archivo de esa carpeta no aparece en INDICE.md;
  - hay una raya en la planeación o en los archivos de RAYAS_TAMBIEN;
  - queda un marcador de documento a medias (<!-- CONTINUA -->);
  - se cita un identificador de PREFIJOS que nadie define.
Avisa, sin fallar, de lo que sigue marcado «PENDIENTE DE DEFINIR».

En INDICE.md cada documento de la planeación tiene un bloque que empieza con un encabezado
que nombra el archivo (### `planeacion/01-requisitos.md`) y lista sus secciones como viñetas
«- **Título de la sección**: resumen». El título debe ser idéntico al del documento.

Un identificador se define donde abre una fila de tabla, un encabezado o un párrafo en
negrita. Escrito entre comillas invertidas (`RF-000`) es un ejemplo y no cuenta como cita.

Modo --hook: lo llama el hook PostToolUse de .claude/settings.json después de cada Edit o
Write. Lee de la entrada estándar el JSON del hook; si el archivo editado no es de los que
vigila, no hace nada. Solo revisa índice y rayas (lo que un cambio suelto puede romper) y, si
hay desfase, lo escribe en stderr y sale con código 2, que es como Claude Code le devuelve el
mensaje al agente.
"""
import json
import re
import sys
from pathlib import Path

# Lo que cambia de un proyecto a otro.
RAIZ = Path(__file__).resolve().parents[2]
PLANEACION = RAIZ / "planeacion"
INDICE = RAIZ / "INDICE.md"
RAYAS_TAMBIEN = ["INDICE.md", "CLAUDE.md", "PROGRESO.md", "PLAN.md", "README.md"]
PREFIJOS = ["RF", "RNF", "RN", "PQ", "ADR", "T"]  # vacío: no revisa identificadores

RAYA = "\u2014"  # la raya; escrita así para que este archivo no la contenga
PENDIENTE = "PENDIENTE DE DEFINIR"
_ALTERNATIVAS = "|".join(sorted(PREFIJOS, key=len, reverse=True))
CITA = re.compile(r"(?<![A-Za-z0-9_`/-])(%s)-(\d{2,3})(?![0-9A-Za-z_])" % _ALTERNATIVAS)
DEFINE = re.compile(r"^(?:\|\s*\**|#{2,5}\s+(?:\S+\s+)?\**|\*\*)(%s)-(\d{2,3})\b" % _ALTERNATIVAS)


def documentos():
    return sorted(PLANEACION.glob("*.md")) if PLANEACION.is_dir() else []


def lineas_fuera_de_codigo(path):
    en_codigo = False
    for n, ln in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
        if ln.startswith("```"):
            en_codigo = not en_codigo
            continue
        if not en_codigo:
            yield n, ln


def secciones(path):
    return [ln[3:].strip() for _, ln in lineas_fuera_de_codigo(path) if ln.startswith("## ")]


def bloques_del_indice(texto):
    """{nombre de archivo: [títulos listados]} a partir de los encabezados que nombran un .md."""
    bloques, actual = {}, None
    patron = re.compile(r"%s/([\w.-]+\.md)" % re.escape(PLANEACION.name))
    for ln in texto.split("\n"):
        if ln.startswith("#"):
            m = patron.search(ln)
            actual = m.group(1) if m else None
            if actual:
                bloques.setdefault(actual, [])
        elif actual:
            m = re.match(r"^- \*\*(.+?)\*\*", ln)
            if m:
                bloques[actual].append(m.group(1).strip())
    return bloques


def revisar_indice(errores):
    if not INDICE.exists():
        errores.append("INDICE.md no existe en la raíz.")
        return
    texto = INDICE.read_text(encoding="utf-8")
    bloques = bloques_del_indice(texto)
    for doc in documentos():
        if doc.name not in bloques:
            errores.append("INDICE.md no tiene bloque para %s/%s." % (PLANEACION.name, doc.name))
            continue
        reales, listadas = secciones(doc), bloques[doc.name]
        for s in reales:
            if s not in listadas:
                errores.append("INDICE.md: falta la sección «%s» de %s." % (s, doc.name))
        for s in listadas:
            if s not in reales:
                errores.append("INDICE.md: lista «%s» en %s y esa sección ya no existe." % (s, doc.name))
    if PLANEACION.is_dir():
        for p in PLANEACION.iterdir():
            if p.is_file() and p.name not in texto:
                errores.append("INDICE.md no menciona %s/%s." % (PLANEACION.name, p.name))


def revisar_rayas(errores, avisos, archivos):
    for p in archivos:
        if not p.exists():
            continue
        for n, ln in enumerate(p.read_text(encoding="utf-8").split("\n"), 1):
            if RAYA in ln:
                errores.append("%s:%d tiene una raya." % (p.name, n))
            if re.search(r"<!--\s*CONTINUA\s*-->", ln):
                errores.append("%s:%d tiene un marcador de documento a medias." % (p.name, n))
            if PENDIENTE in ln:
                avisos.append("%s:%d sigue %s." % (p.name, n, PENDIENTE))


def revisar_identificadores(errores):
    if not PREFIJOS:
        return
    definidos, primera_cita = set(), {}
    for doc in documentos():
        for n, ln in lineas_fuera_de_codigo(doc):
            m = DEFINE.match(ln)
            if m:
                definidos.add("%s-%s" % m.groups())
            for pre, num in CITA.findall(ln):
                primera_cita.setdefault("%s-%s" % (pre, num), "%s:%d" % (doc.name, n))
    for ident in sorted(primera_cita):
        if ident not in definidos:
            errores.append("%s se cita en %s y nadie lo define." % (ident, primera_cita[ident]))


def vigilados():
    return documentos() + [RAIZ / nombre for nombre in RAYAS_TAMBIEN]


def modo_hook():
    try:
        dato = json.load(sys.stdin)
        texto = dato.get("tool_input", {}).get("file_path") or ""
        ruta = Path(texto).resolve()
        rel = ruta.relative_to(RAIZ)
    except Exception:
        return 0
    if not texto or not rel.parts:
        return 0
    en_planeacion = rel.parts[0] == PLANEACION.name
    if not en_planeacion and rel.as_posix() not in RAYAS_TAMBIEN:
        return 0
    errores, avisos = [], []
    if INDICE.exists() and (en_planeacion or rel.name == INDICE.name):
        revisar_indice(errores)
    if ruta.suffix == ".md":
        revisar_rayas(errores, avisos, [ruta])
    if not errores:
        return 0
    sys.stderr.write(
        "El cambio a %s dejó desfasado el proyecto. Corrige antes de seguir:\n- "
        % rel.as_posix() + "\n- ".join(errores[:20]) + "\n"
    )
    return 2


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    if "--hook" in sys.argv:
        sys.exit(modo_hook())
    errores, avisos = [], []
    revisar_indice(errores)
    revisar_rayas(errores, avisos, vigilados())
    revisar_identificadores(errores)
    for a in avisos:
        print("aviso:", a)
    for e in errores:
        print("ERROR:", e)
    print("%d errores, %d avisos." % (len(errores), len(avisos)))
    sys.exit(1 if errores else 0)


if __name__ == "__main__":
    main()
