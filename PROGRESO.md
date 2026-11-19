# Progreso · Servicio de reglas de retención (prueba Auxis)

## Estado actual
Enunciado entendido, plan escrito (`PLAN.md`) y reglas del proyecto puestas. No hay código
todavía. Cuatro de los cinco documentos del corpus se descargaron y se probaron con PyMuPDF;
el de Ontario se movió: la versión vigente es `t4032-on-1-26e.pdf` y está comprobada (16 páginas con texto).

## Siguiente paso
Paso 0 de `PLAN.md` §5: leer los cinco documentos para
fijar el vocabulario cerrado (jurisdicciones y tipos de pago) y los casos del set de
evaluación.

## Pendientes
- **Despliegue en Easypanel.** Sin hacer. Los pasos están en `PLAN.md` §9; los de Hostinger
  y Easypanel los hace el usuario. Falta además crear el repositorio en GitHub.
- **Costo y tiempo reales de la extracción con Claude.** No medidos. Se miden en el paso 4.
- **Horas ya gastadas.** No se ha llevado la cuenta del presupuesto de 6 horas. Falta que
  el usuario diga cuánto cuenta lo hecho hasta ahora.

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
| 2026-11-19 | D1 a D16 de `PLAN.md` §2, salvo las de arriba: **decisión mía sin confirmar** | Propuestas del agente a partir de lo verificado; el usuario pidió seguir con el plan |
| 2026-11-19 | `git init` con rama `main`, sin commits: **decisión mía sin confirmar** | El entregable es un repositorio y `.gitignore` lo necesita |

## Bitácora
### 2026-11-19
- Hecho: lectura y explicación del enunciado; investigación de opciones de extracción y de
  alojamiento; descarga y prueba de cuatro documentos del corpus; `PLAN.md`.
- Hecho: arranque con `/iniciar-proyecto`. Quedaron `CLAUDE.md`, `INDICE.md`, este archivo, la skill `en-curso`, el verificador y los hooks.
