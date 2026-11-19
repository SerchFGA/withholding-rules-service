# Progreso · Servicio de reglas de retención (prueba Auxis)

## Estado actual
Código completo y probado con red y modelo simulados: 278 pruebas pasan. Producción: 1.450
líneas de 1.500 (`app/` 1.202, `static/` 248). Nada se ha ejercitado todavía contra la API de
Claude ni está desplegado.

## Siguiente paso
Paso 6 de `PLAN.md` §5, primera corrida real: con `ANTHROPIC_API_KEY` en `.env`, correr
`make verify` (o `./.venv/Scripts/python scripts/verify.py`) y ajustar el prompt o el
validador según lo que Claude extraiga de verdad.

## Pendientes
- **Clave de la API.** Falta que el usuario cree `.env` con `ANTHROPIC_API_KEY`. Sin ella no
  corre la ingesta real ni `make verify`. La extracción y la transcripción (`app/extract.py`)
  son hasta entonces «diseñado, no ejercitado».
- **Interfaz sin ver en navegador.** `static/index.html` se probó con un DOM simulado y contra
  el servidor real, pero nadie la ha visto: aspecto, ancho de teléfono, modo oscuro y
  teclado quedan sin comprobar. Falta abrirla (con permiso del usuario) o que la mire él.
- **Caso de umbral dudoso.** La Pub. 505 p. 12 dice que bajo 5.000 USD en juego puede haber
  retención de respaldo. Si Claude extrae esa regla, los casos `us-gambling-just-below-threshold`
  y `us-gambling-exactly-at-threshold` de `eval/cases.json` fallarán. Decidir entonces qué manda.
- **Despliegue en Easypanel.** Sin hacer. Pasos en `PLAN.md` §9; los de Hostinger y Easypanel
  los hace el usuario.
- **README.** Sin escribir (paso 8). Debe declarar: la clave de la API, `payee_type`, el cambio
  de URL de Ontario, que canada.ca bloquea a algunos clientes, el servidor propio, los tres
  riesgos de `app/fetch.py` (DNS, HTML mal formado, proxy) y las cinco líneas finales (las
  reglas duras no tienen respaldo en el corpus; ver `eval/notas/`).
- **Revisión del diff posterior a los arreglos.** La revisión independiente se hizo antes de
  los arreglos; falta una segunda pasada sobre la punta antes de entregar.
- **Horas ya gastadas.** No se ha llevado la cuenta del presupuesto de 6 horas.

## Decisiones
| Fecha | Decisión | Por qué |
|---|---|---|
| 2026-11-19 | Sin zonas delicadas declaradas en `CLAUDE.md` | Lo eligió el usuario. R7 se cubre en «Lo que nunca se hace» |
| 2026-11-19 | Los cambios entran directo a la rama principal, en commits pequeños | Lo eligió el usuario: trabaja solo y hay 6 horas |
| 2026-11-19 | La planeación es solo `PLAN.md`, sin carpeta `planeacion/` | Lo eligió el usuario: es una prueba corta |
| 2026-11-19 | Se puede usar la API de Claude | Lo confirmó el usuario |
| 2026-11-19 | Se incluye una interfaz bilingüe (inglés y español) | Lo pidió el usuario. El enunciado no la pide y cuenta contra las 1.500 líneas |
| 2026-11-19 | No se pregunta a los evaluadores: la clave de la API de Claude y `payee_type` se explican en el README | Lo decidió el usuario |
| 2026-11-19 | Se mantiene el corpus de cinco documentos; Ontario con la versión oficial vigente y nota en el README | Lo decidió el usuario |
| 2026-11-19 | Alojamiento en el VPS de Hostinger con Easypanel, en `withholding.pixanai.com`, y SQLite en todos lados (D6, D7) | Lo decidió el usuario: es el único host donde se comprobó la descarga de los cinco documentos |
| 2026-11-19 | `services` responde 24 % con revisión (D17) y el alcance es tasa fija con umbral (D18) | Lo decidió el usuario tras ver los informes del corpus |
| 2026-11-19 | Un «no se retiene» sin `payee_type` pide revisión (`payee_type_not_provided`); corrige D21 para ese caso: **decisión mía sin confirmar** | Lo señaló la revisión independiente; un dato ausente no cuenta contra la retención (R4) |
| 2026-11-19 | El año de la política solo puede ser posterior al consultado; con reglas solo anteriores, desconocido: **decisión mía sin confirmar** | Lo señaló la revisión: el campo afirmaba «año posterior» usando uno anterior |
| 2026-11-19 | Las páginas escaneadas se transcriben y luego se validan como las demás; la regla sale marcada para revisión: **decisión mía sin confirmar** | La revisión mostró que antes se aceptaban sin validar (R2) |
| 2026-11-19 | D19 a D23 de `PLAN.md` §2: **decisión mía sin confirmar** | Salen de los hallazgos del corpus; hacían falta para repartir el trabajo entre agentes |
| 2026-11-19 | Repositorio de GitHub privado: **decisión mía sin confirmar** | Incluye el enunciado de la prueba; se abre o se comparte al entregar |
| 2026-11-19 | D1 a D16 de `PLAN.md` §2, salvo las de arriba: **decisión mía sin confirmar** | Propuestas del agente a partir de lo verificado; el usuario pidió seguir con el plan |
| 2026-11-19 | `git init` con rama `main`, sin commits: **decisión mía sin confirmar** | El entregable es un repositorio y `.gitignore` lo necesita |

## Bitácora
### 2026-11-19
- Hecho: lectura y explicación del enunciado; investigación de opciones de extracción y de
  alojamiento; descarga y prueba de cuatro documentos del corpus; `PLAN.md`.
- Hecho: paso 0 (lectura del corpus con tres agentes), pasos 1 a 5 del plan con cuatro
  agentes en paralelo, set de evaluación de 28 casos, `make verify`, interfaz bilingüe.
- Hecho: revisión independiente del código (12 hallazgos) y sus arreglos, cada uno con
  su prueba. Repositorio privado `SerchFGA/withholding-rules-service`, 14 commits.
- Hecho: arranque con `/iniciar-proyecto`. Quedaron `CLAUDE.md`, `INDICE.md`, este archivo, la skill `en-curso`, el verificador y los hooks.
