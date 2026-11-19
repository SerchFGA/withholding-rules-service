# Índice del proyecto

Última actualización: 2026-11-19.

La puerta de entrada. Dice qué hay en cada documento y en cada sección, para ir directo a la
que hace falta sin leer lo demás. El índice describe; no sustituye: las reglas y las
decisiones se leen en su documento. `PROGRESO.md` dice en qué va el proyecto; este archivo
dice dónde está cada cosa.

## 1. Cómo usarlo

1. Busca el tema en la sección 4. Si no está, recorre los resúmenes de la sección 3.
2. Abre solo la sección que el índice señala.
3. Si vas a cambiar algo, revisa antes la sección 5: dice qué más hay que tocar.
4. Al terminar, actualiza este índice en el mismo cambio (resumen de la sección, fecha y una
   línea en la sección 6) y corre `python .claude/hooks/verificar.py`.

## 2. Mapa del proyecto

| Lugar | Qué es | Se publica |
|---|---|---|
| `CLAUDE.md` | Reglas de trabajo del repositorio | No |
| `INDICE.md` | Este archivo | No |
| `PROGRESO.md` | Bitácora: estado actual, siguiente paso, pendientes, decisiones | No |
| `EN-CURSO.md` | El proceso en marcha. Lo escribe la skill `en-curso`; git lo ignora | No |
| `EN-CURSO-historial.md` | Los procesos cerrados. Solo se lee si se pide | No |
| `.claude/` | Skill `en-curso`, el verificador (`hooks/verificar.py`) y los hooks (`settings.json`) | No |
| `Rules.md` | El enunciado de la prueba. No se edita | No |
| `PLAN.md` | Plan de implementación | No |
| `eval/notas/` | Lectura del corpus: un archivo por documento (`p15`, `p505`, `rp2334`, `t4032`, `dian`) con reglas, citas, casos difíciles y consultas candidatas | No |
| `app/` | Código de producción. `models.py` es el contrato entre módulos | Sí |
| `tests/` | Pruebas, una por módulo | No |
| `Dockerfile`, `requirements.txt`, `.env.example` | Imagen del servicio, dependencias y variables necesarias (sin valores) | Sí |
| `static/`, `scripts/`, `README.md` | Todavía no existen. Se crean según `PLAN.md` §5 | Ver `CLAUDE.md` |

## 3. Documentos

### `Rules.md` (el enunciado)

- **The situation**: el cliente, el orquestador ajeno y qué debe producir el servicio.
- **Your corpus**: los cinco documentos oficiales obligatorios.
- **Build**: los cuatro endpoints.
- **The v1 contract**: la forma fija del JSON de `/v1/resolve`.
- **The hard rules**: las tres reglas en código y la política del cliente.
- **Seven requirements**: R1 a R7.
- **Deliver four things**: URL y repositorio, `make verify`, README, set de evaluación, y
  las cinco líneas finales. Topes de líneas y documentación.
- **How we grade**: pesos de la calificación y la llamada con el sexto documento.
- **Four things that will cost you**: sustituir, sembrar, afirmar sin correr, construir de
  más.

### `PLAN.md`

- **1. Lo verificado (2026-11-19)**: qué se comprobó con los documentos reales y qué falta.
- **2. Decisiones**: D1 a D23, con la alternativa descartada de cada una.
- **3. Arquitectura**: flujo de la ingesta, flujo del resolve y tablas.
- **4. Reparto de líneas (tope 1.500)**: presupuesto por archivo.
- **5. Orden de trabajo**: pasos 0 a 8, con verificación y tiempo de cada uno.
- **6. Interfaz (inglés y español)**: las cuatro partes de la página.
- **7. Registro y datos sensibles (R7)**: qué se registra, qué se minimiza, qué nunca.
- **8. Riesgos y pendientes**: riesgos conocidos y qué hacer con cada uno.
- **9. Despliegue en el VPS**: los cinco pasos en Hostinger y Easypanel, y quién hace cada uno.
- **10. Supuestos que se declaran en el README**: clave de la API, `payee_type` y Ontario.

## 4. Dónde vive cada tema

| Tema | Dónde |
|---|---|
| Requisitos R1 a R7 | `Rules.md`, «Seven requirements» |
| Contrato del JSON | `Rules.md`, «The v1 contract»; campos nuevos en `PLAN.md` §2 (D11) |
| Reglas duras y política del cliente | `Rules.md`, «The hard rules»; orden de evaluación en `PLAN.md` §3 |
| Decisiones técnicas y alternativas | `PLAN.md` §2 |
| Qué se hace primero | `PLAN.md` §5 |
| Presupuesto de líneas | `PLAN.md` §4 |
| Estado de los cinco documentos del corpus | `PLAN.md` §1 |
| Qué reglas trae cada documento y qué no dice | `eval/notas/` |
| Registro y redacción de datos | `PLAN.md` §7 |
| Reglas de trabajo y prohibiciones | `CLAUDE.md` |
| En qué va el proyecto | `PROGRESO.md` |

## 5. Qué más tocar si cambia algo

| Si cambia | Toca también |
|---|---|
| Una decisión de `PLAN.md` §2 | `PROGRESO.md` (tabla de decisiones) y, al final, el README |
| Una sección `##` de `PLAN.md` | Su viñeta en la sección 3 de este índice |
| La estructura de carpetas | El mapa del `CLAUDE.md` y la sección 2 de este índice |
| Un comando nuevo | La sección «Comandos» del `CLAUDE.md` |
| El reparto de líneas | `PLAN.md` §4 |
| Un campo del contrato | `PLAN.md` §2 (D11), las pruebas de contrato y el README |

## 6. Registro de cambios

| Fecha | Qué cambió |
|---|---|
| 2026-11-19 | `PLAN.md` §2 gana D17 a D23 tras leer el corpus. Empieza el código: `app/` y `tests/` |
| 2026-11-19 | Nueva carpeta `eval/notas/` con la lectura del corpus (paso 0) |
| 2026-11-19 | Alojamiento decidido: VPS con Easypanel y SQLite en todos lados (D6, D7). `PLAN.md` gana §9 «Despliegue en el VPS»; los supuestos pasan a §10 |
| 2026-11-19 | `PLAN.md` §1: Ontario comprobado en su dirección vigente y descargable desde el VPS |
| 2026-11-19 | `PLAN.md` §9 pasa de preguntas a supuestos declarados en el README; §1 y §8 anotan el bloqueo de canada.ca |
| 2026-11-19 | Arranque del proyecto con `/iniciar-proyecto`: reglas, índice, bitácora, `en-curso` y verificador. `PLAN.md` creado |
