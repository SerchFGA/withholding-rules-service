"""Registro del proceso en marcha: qué se está haciendo, qué pasos terminaron y cuál quedó
a medias. Lo usa la skill `en-curso` y el hook SessionStart de .claude/settings.json.

    python .claude/skills/en-curso/en_curso.py estado
    python .claude/skills/en-curso/en_curso.py iniciar "T-103 Base inicial" --repo plataforma
    python .claude/skills/en-curso/en_curso.py paso "Migración de parámetros"
    python .claude/skills/en-curso/en_curso.py paso 4            # empieza el pendiente 4
    python .claude/skills/en-curso/en_curso.py hecho --nota "pgTAP pasa"
    python .claude/skills/en-curso/en_curso.py hecho 4 --nota "..."
    python .claude/skills/en-curso/en_curso.py pendiente "Exportar PDF"
    python .claude/skills/en-curso/en_curso.py bloqueado 4 --nota "falta la cuenta"
    python .claude/skills/en-curso/en_curso.py bloqueado "Sentry" --nota "falta la cuenta"
    python .claude/skills/en-curso/en_curso.py cerrar --nota "commit abc123"
    python .claude/skills/en-curso/en_curso.py historial 3       # sin número, todo

Dos archivos en la raíz del proyecto:
  - EN-CURSO.md: solo el proceso activo. Siempre es corto. Git lo ignora.
  - EN-CURSO-historial.md: los procesos cerrados, el más reciente arriba. Solo se agrega.

`estado` imprime lo último en pocas líneas y nunca abre el historial. Un paso `en curso`
sin hora de fin al abrir una sesión nueva es donde se cortó la anterior.

La variable EN_CURSO_DIR cambia la carpeta de los dos archivos, para probar sin tocar los
reales.

Carriles: con dos sesiones trabajando en paralelo, cada una lleva su
proceso activo en su archivo. El carril `a` es EN-CURSO.md; otro carril, EN-CURSO-<letra>.md.
Se elige con `--carril b` en cualquier comando, o con la variable EN_CURSO_CARRIL. El
historial es uno solo para todos y se escribe con un candado. `estado --todos` imprime todos
los carriles: lo usa el hook de inicio de sesión.

    python .claude/skills/en-curso/en_curso.py paso "Plan de la pantalla" --carril b
    python .claude/skills/en-curso/en_curso.py estado --todos
"""
import argparse
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

RAIZ = Path(os.environ.get("EN_CURSO_DIR") or Path(__file__).resolve().parents[3])
HISTORIAL = RAIZ / "EN-CURSO-historial.md"
CANDADO = RAIZ / "EN-CURSO-historial.lock"
CARRIL = re.compile(r"^[a-z]$")
ARCHIVO_CARRIL = re.compile(r"^EN-CURSO-([a-z])\.md$")


def archivo_de(carril):
    return RAIZ / ("EN-CURSO.md" if carril == "a" else "EN-CURSO-%s.md" % carril)


# El carril de este comando: lo fija main(). Por omisión, el `a`.
CARRIL_ACTIVO = "a"
ACTIVO = archivo_de(CARRIL_ACTIVO)


def cabecera(carril):
    titulo = "# En curso" if carril == "a" else "# En curso (carril %s)" % carril
    return """%s

El proceso en marcha, paso por paso. Lo escribe `.claude/skills/en-curso/en_curso.py`: no
se edita a mano, se usa la skill `en-curso`. Los procesos cerrados están en
`EN-CURSO-historial.md`.

## Proceso activo

""" % titulo
CABECERA_HISTORIAL = """# Historial de procesos

Los procesos cerrados, el más reciente arriba. Lo escribe la skill `en-curso` al cerrar
un proceso. Solo se agrega: no se edita ni se borra.
"""
TABLA = "| # | Paso | Inicio | Fin | Estado | Nota |\n|---|---|---|---|---|---|\n"
FILA = re.compile(r"^\|\s*(\d+)\s*\|(.*)\|\s*$")
# `estado` es un resumen: recorta lo largo. El texto completo queda en el archivo.
LIMITE_LISTA = 6
LARGO_PASO = 60
LARGO_NOTA = 100


def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def limpia(texto):
    # Una celda de tabla no admite barras ni saltos de línea.
    return " ".join((texto or "").replace("|", "/").split())


def leer():
    """Devuelve el proceso activo como diccionario, o None si no hay."""
    if not ACTIVO.exists():
        return None
    proceso = {"nombre": None, "repo": "", "inicio": "", "pasos": []}
    for linea in ACTIVO.read_text(encoding="utf-8").splitlines():
        fila = FILA.match(linea)
        if fila:
            celdas = [c.strip() for c in fila.group(2).split("|")]
            celdas += [""] * (5 - len(celdas))
            proceso["pasos"].append(
                {
                    "n": int(fila.group(1)),
                    "paso": celdas[0],
                    "inicio": celdas[1],
                    "fin": celdas[2],
                    "estado": celdas[3],
                    "nota": celdas[4],
                }
            )
        elif linea.startswith("**") and linea.rstrip().endswith("**"):
            proceso["nombre"] = linea.strip().strip("*")
        elif linea.startswith("- Repositorio:"):
            proceso["repo"] = linea.split(":", 1)[1].strip()
        elif linea.startswith("- Inicio:"):
            proceso["inicio"] = linea.split(":", 1)[1].strip()
    return proceso if proceso["nombre"] else None


def tabla(pasos):
    return TABLA + "".join(
        "| %d | %s | %s | %s | %s | %s |\n"
        % (p["n"], p["paso"], p["inicio"], p["fin"], p["estado"], p["nota"])
        for p in pasos
    )


def guardar(proceso):
    if proceso is None:
        cuerpo = "Ninguno.\n"
    else:
        cuerpo = "**%s**\n\n%s- Inicio: %s\n\n%s" % (
            proceso["nombre"],
            "- Repositorio: %s\n" % proceso["repo"] if proceso["repo"] else "",
            proceso["inicio"],
            tabla(proceso["pasos"]),
        )
    ACTIVO.write_text(cabecera(CARRIL_ACTIVO) + cuerpo, encoding="utf-8", newline="\n")


def falla(mensaje):
    print("en-curso: " + mensaje, file=sys.stderr)
    sys.exit(1)


def activo_o_falla():
    proceso = leer()
    if proceso is None:
        falla('no hay proceso activo. Empieza uno con: iniciar "nombre"')
    return proceso


def abierto(proceso):
    return next((p for p in proceso["pasos"] if p["estado"] == "en curso"), None)


def por_numero(proceso, n):
    paso = next((p for p in proceso["pasos"] if p["n"] == n), None)
    if paso is None:
        falla("no existe el paso %d." % n)
    return paso


def nuevo(proceso, texto, estado, nota="", inicio=""):
    paso = {
        "n": max((p["n"] for p in proceso["pasos"]), default=0) + 1,
        "paso": limpia(texto),
        "inicio": inicio,
        "fin": "",
        "estado": estado,
        "nota": limpia(nota),
    }
    proceso["pasos"].append(paso)
    return paso


def recorta(texto, largo):
    return texto if len(texto) <= largo else texto[: largo - 1].rstrip() + "…"


def corto(paso, largo=None):
    return "%d. %s" % (paso["n"], recorta(paso["paso"], largo) if largo else paso["paso"])


def cmd_estado(args):
    global ACTIVO, CARRIL_ACTIVO
    if not args.todos:
        estado_de_uno()
        return
    carriles = ["a"] + sorted(
        m.group(1) for m in (ARCHIVO_CARRIL.match(f.name) for f in RAIZ.glob("EN-CURSO-*.md")) if m)
    for carril in carriles:
        ACTIVO, CARRIL_ACTIVO = archivo_de(carril), carril
        if len(carriles) > 1:
            print("[carril %s]" % carril)
        estado_de_uno()


def estado_de_uno():
    proceso = leer()
    if proceso is None:
        print("En curso: ningún proceso activo.")
        return
    pasos = proceso["pasos"]
    hechos = [p for p in pasos if p["estado"] == "hecho"]
    print(
        "En curso: %s (%s), desde %s. %d de %d pasos hechos."
        % (proceso["nombre"], proceso["repo"] or "sin repositorio", proceso["inicio"],
           len(hechos), len(pasos))
    )
    paso = abierto(proceso)
    if paso:
        print(
            "PASO ABIERTO: %s, desde %s y sin hora de fin. Si la sesión es nueva, ahí se "
            "cortó la anterior: verifícalo antes de seguir." % (corto(paso), paso["inicio"])
        )
    if hechos:
        ultimo = hechos[-1]
        nota = ": " + recorta(ultimo["nota"], LARGO_NOTA) if ultimo["nota"] else ""
        print("Último hecho: %s (%s)%s" % (corto(ultimo, LARGO_PASO), ultimo["fin"], nota))
    for titulo, estado in (("Pendientes", "pendiente"), ("Bloqueados", "bloqueado")):
        lista = [p for p in pasos if p["estado"] == estado]
        if not lista:
            continue
        partes = [
            corto(p, LARGO_PASO)
            + (": " + recorta(p["nota"], LARGO_PASO) if estado == "bloqueado" and p["nota"] else "")
            for p in lista[:LIMITE_LISTA]
        ]
        if len(lista) > LIMITE_LISTA:
            partes.append("y %d más" % (len(lista) - LIMITE_LISTA))
        print("%s: %s" % (titulo, "; ".join(partes)))


def cmd_iniciar(args):
    proceso = leer()
    if proceso is not None:
        falla("ya hay un proceso activo (%s). Ciérralo antes con: cerrar" % proceso["nombre"])
    guardar({"nombre": limpia(args.texto), "repo": limpia(args.repo), "inicio": ahora(),
             "pasos": []})
    print("Proceso iniciado: %s" % limpia(args.texto))


def cmd_paso(args):
    proceso = activo_o_falla()
    paso = abierto(proceso)
    if paso:
        falla("el paso %s sigue en curso. Ciérralo antes con: hecho" % corto(paso))
    if args.texto.isdigit():
        paso = por_numero(proceso, int(args.texto))
        if paso["estado"] == "hecho":
            falla("el paso %s ya está hecho." % corto(paso))
        paso.update(estado="en curso", inicio=ahora(), fin="")
        if args.nota:
            paso["nota"] = limpia(args.nota)
    else:
        paso = nuevo(proceso, args.texto, "en curso", args.nota, ahora())
    guardar(proceso)
    print("En curso: %s" % corto(paso))


def cmd_hecho(args):
    proceso = activo_o_falla()
    paso = por_numero(proceso, args.numero) if args.numero else abierto(proceso)
    if paso is None:
        falla("no hay paso en curso. Di cuál con: hecho N")
    momento = ahora()
    paso.update(estado="hecho", inicio=paso["inicio"] or momento, fin=momento)
    if args.nota:
        paso["nota"] = limpia(args.nota)
    guardar(proceso)
    print("Hecho: %s" % corto(paso))


def cmd_pendiente(args):
    proceso = activo_o_falla()
    paso = nuevo(proceso, args.texto, "pendiente", args.nota)
    guardar(proceso)
    print("Pendiente: %s" % corto(paso))


def cmd_bloqueado(args):
    proceso = activo_o_falla()
    if args.texto.isdigit():
        paso = por_numero(proceso, int(args.texto))
        paso.update(estado="bloqueado", fin="")
        if args.nota:
            paso["nota"] = limpia(args.nota)
    else:
        paso = nuevo(proceso, args.texto, "bloqueado", args.nota)
    guardar(proceso)
    print("Bloqueado: %s" % corto(paso))


def cmd_cerrar(args):
    proceso = activo_o_falla()
    paso = abierto(proceso)
    if paso:
        falla("el paso %s sigue en curso. Márcalo antes con: hecho, o bloqueado %d"
              % (corto(paso), paso["n"]))
    entrada = "## %s a %s: %s\n\n" % (proceso["inicio"], ahora(), proceso["nombre"])
    if proceso["repo"]:
        entrada += "- Repositorio: %s\n" % proceso["repo"]
    if args.nota:
        entrada += "- Cierre: %s\n" % limpia(args.nota)
    sin_hacer = [p for p in proceso["pasos"] if p["estado"] != "hecho"]
    if sin_hacer:
        entrada += "- Quedó sin hacer: %s\n" % "; ".join(corto(p) for p in sin_hacer)
    if CARRIL_ACTIVO != "a":
        entrada += "- Carril: %s\n" % CARRIL_ACTIVO
    entrada += "\n" + tabla(proceso["pasos"])

    with Candado():
        previo = HISTORIAL.read_text(encoding="utf-8") if HISTORIAL.exists() else CABECERA_HISTORIAL
        corte = re.search(r"^## ", previo, flags=re.M)
        if corte:
            texto = previo[: corte.start()] + entrada + "\n" + previo[corte.start():]
        else:
            texto = previo.rstrip("\n") + "\n\n" + entrada
        HISTORIAL.write_text(texto, encoding="utf-8", newline="\n")
    guardar(None)
    print("Cerrado y pasado al historial: %s" % proceso["nombre"])


class Candado:
    """El historial lo comparten los carriles: dos `cerrar` a la vez no se pisan. Crear el
    archivo con O_EXCL es atómico; uno de más de 30 segundos quedó de un corte y se quita."""

    def __enter__(self):
        for _ in range(100):
            try:
                os.close(os.open(CANDADO, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
                return self
            except FileExistsError:
                try:
                    if time.time() - CANDADO.stat().st_mtime > 30:
                        CANDADO.unlink()
                        continue
                except FileNotFoundError:
                    continue
                time.sleep(0.1)
        falla("otro carril está escribiendo el historial. Si nadie está cerrando, borra %s"
              % CANDADO.name)

    def __exit__(self, *_):
        try:
            CANDADO.unlink()
        except FileNotFoundError:
            pass


def cmd_historial(args):
    if not HISTORIAL.exists():
        print("El historial está vacío.")
        return
    entradas = re.split(r"(?m)^(?=## )", HISTORIAL.read_text(encoding="utf-8"))[1:]
    if not entradas:
        print("El historial está vacío.")
        return
    elegidas = entradas[: args.numero] if args.numero else entradas
    print("".join(elegidas).rstrip("\n"))
    if len(elegidas) < len(entradas):
        print("\n(%d de %d procesos; sin número se imprime todo)" % (len(elegidas), len(entradas)))


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    global ACTIVO, CARRIL_ACTIVO
    comun = argparse.ArgumentParser(add_help=False)
    comun.add_argument("--carril", default=os.environ.get("EN_CURSO_CARRIL") or "a")
    analizador = argparse.ArgumentParser(description="Registro del proceso en marcha.")
    sub = analizador.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("estado", parents=[comun])
    p.add_argument("--todos", action="store_true")
    p.set_defaults(fn=cmd_estado)

    p = sub.add_parser("iniciar", parents=[comun])
    p.add_argument("texto")
    p.add_argument("--repo", default="")
    p.set_defaults(fn=cmd_iniciar)

    for nombre, fn in (("paso", cmd_paso), ("pendiente", cmd_pendiente),
                       ("bloqueado", cmd_bloqueado)):
        p = sub.add_parser(nombre, parents=[comun])
        p.add_argument("texto")
        p.add_argument("--nota", default="")
        p.set_defaults(fn=fn)

    p = sub.add_parser("hecho", parents=[comun])
    p.add_argument("numero", nargs="?", type=int)
    p.add_argument("--nota", default="")
    p.set_defaults(fn=cmd_hecho)

    p = sub.add_parser("cerrar", parents=[comun])
    p.add_argument("--nota", default="")
    p.set_defaults(fn=cmd_cerrar)

    p = sub.add_parser("historial", parents=[comun])
    p.add_argument("numero", nargs="?", type=int)
    p.set_defaults(fn=cmd_historial)

    args = analizador.parse_args()
    if not CARRIL.match(args.carril):
        falla("el carril es una letra minúscula: a, b, ...")
    CARRIL_ACTIVO, ACTIVO = args.carril, archivo_de(args.carril)
    args.fn(args)


if __name__ == "__main__":
    main()
