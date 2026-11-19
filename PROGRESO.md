# Progreso · Servicio de reglas de retención (prueba Auxis)

## Estado actual
Desplegado y funcionando en `https://withholding.pixanai.com` (VPS con Easypanel). Los cinco
documentos se ingirieron ahí por el proceso real, desde base vacía, el 2026-11-19: 61 s en
total, 38 reglas, 25 de 27 casos del set de evaluación. Repositorio público. README escrito.
291 pruebas pasan. Producción: 1.478 líneas de 1.500.

## Siguiente paso
El usuario pulsa Deploy en Easypanel para publicar los arreglos de la segunda revisión
(commit `12ba737`) y decide qué se queda en el repositorio público (ver pendientes). Después,
comprobar en producción y ensayar la ingesta de un sexto documento.

## Pendientes
- **Producción corre una versión anterior.** Los arreglos de la segunda revisión están en
  `main` pero no desplegados: falta pulsar Deploy. No hace falta reingerir (cambió el resolve,
  no la extracción). Al redesplegar se comprueba de paso que el volumen conserva la base.
- **Documentación interna en el repositorio público.** `CLAUDE.md`, `INDICE.md`, `PLAN.md`,
  `PROGRESO.md`, `EN-CURSO-historial.md`, `.claude/` y `eval/notas/` suman más de 2.000 líneas
  frente al tope de «una página de documentación», y `PLAN.md` nombra otro subdominio del
  usuario. La revisión propone sacarlos del repositorio (`git rm --cached`, se quedan en
  disco). Es decisión del usuario; el historial de git los conserva igual.
- **Etiqueta `condition` sin validar contra el texto.** Hay reglas guardadas como firmes cuya
  cita dice «unless you choose» o «certain kinds». Está declarado en el README y los seis
  casos afectados van con confianza media. El arreglo de fondo (palabras de salvedad en la
  cita impiden «firme») exige reingerir y cambiar esperados: sin decidir.
- **Densidad de `static/index.html`.** 112 de sus líneas pasan de 120 caracteres; un
  evaluador estricto puede decir que con formato normal se rebasa el tope de 1.500.
- **Ensayo de la llamada en vivo.** Falta ingerir un sexto documento desde la interfaz,
  idealmente escaneado y de otro país.
- **Margen de líneas.** Quedan 15 (1.485 de 1.500).
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
- Hecho: segunda revisión independiente (1 bloqueante y 8 que convenía arreglar) y sus
  arreglos, salvo los que son decisión del usuario.
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
