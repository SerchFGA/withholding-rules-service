# Progreso · Servicio de reglas de retención (prueba Auxis)

## Estado actual
Desplegado y funcionando en `https://withholding.pixanai.com` (VPS con Easypanel). Los cinco
documentos se ingirieron ahí por el proceso real, desde base vacía, el 2026-11-19: 61 s en
total, 38 reglas, 25 de 27 casos del set de evaluación. Repositorio público. README escrito.
291 pruebas pasan. Producción: 1.478 líneas de 1.500.

## Siguiente paso
Segunda revisión independiente sobre la punta (código y README) y sus arreglos. Después,
ensayar la llamada en vivo: ingerir un documento nuevo desde la interfaz con la clave de ingesta.

## Pendientes
- **Segunda revisión independiente.** En curso o por lanzar. La primera fue antes de los
  arreglos y de los cambios de la corrida real.
- **Easypanel no redespliega solo.** Tras cada push hay que pulsar Deploy (o activar el
  despliegue automático). El volumen `withholding-data` conserva la base entre despliegues;
  falta comprobarlo con un redespliegue real.
- **Dos casos fallan en producción**, ambos con respuesta segura: `us-services-backup-withholding`
  (sale un motivo de revisión de más) y `us-supplemental-wages-optional-flat-rate`
  (`conflicting_rules`). La extracción varía entre corridas; está dicho en el README.
- **Ensayo de la llamada en vivo.** Falta probar la ingesta de un sexto documento desde la
  interfaz, idealmente uno escaneado, que es el camino «diseñado, no ejercitado».
- **El README va solo en inglés**, por el tope de una página: **decisión mía sin confirmar**
  (la regla del proyecto decía inglés y español).
- **Margen de líneas.** Quedan 22.
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
| 2026-11-19 | La regla firme decide y la condicional rival solo pide revisión; tasas distintas a la vez son conflicto, sin suponer que el tramo alto reemplaza al bajo: **decisión mía sin confirmar** | La ingesta real mostró que los tramos altos del corpus se aplican solo al excedente |
| 2026-11-19 | Una regla firme con un umbral cercano que no declara se descarta: **decisión mía sin confirmar** | El modelo citó la tasa y omitió el umbral de la frase siguiente: retenía de más sin aviso |
| 2026-11-19 | El set de evaluación cambia dos casos de juego entre 2.000 y 5.000 USD por uno bajo ambos umbrales (quedan 27): **decisión mía sin confirmar** | La publicación da dos umbrales para clases de juego que el vocabulario no separa; ninguna respuesta única era defendible |
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
- Hecho: repositorio público, despliegue en Easypanel (el usuario en los paneles), ingesta
  de los cinco documentos en producción y README.
- Hecho: primera corrida real contra Claude con la clave del usuario; cinco rondas de
  ajuste (prompt, validador, selección de reglas); `make verify` corre completo; interfaz
  vista en navegador en escritorio y teléfono.
- Hecho: paso 0 (lectura del corpus con tres agentes), pasos 1 a 5 del plan con cuatro
  agentes en paralelo, set de evaluación de 28 casos, `make verify`, interfaz bilingüe.
- Hecho: revisión independiente del código (12 hallazgos) y sus arreglos, cada uno con
  su prueba. Repositorio privado `SerchFGA/withholding-rules-service`, 14 commits.
- Hecho: arranque con `/iniciar-proyecto`. Quedaron `CLAUDE.md`, `INDICE.md`, este archivo, la skill `en-curso`, el verificador y los hooks.
