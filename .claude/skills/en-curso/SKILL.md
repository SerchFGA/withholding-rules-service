---
name: en-curso
description: |
  Registro breve del proceso en marcha en este proyecto: qué se está haciendo, qué pasos
  terminaron y cuál quedó a medias, con historial de los procesos cerrados. Úsala SIEMPRE
  al empezar o retomar un trabajo de más de un paso (una tarea T-000, un cambio que cruza
  varios archivos, una instalación), al empezar y al terminar cada paso, antes de algo
  que puede cortar la sesión (instalar, reiniciar, un comando largo) y al cerrar el
  trabajo. También cuando el usuario diga "en qué íbamos", "qué proceso estaba", "qué
  quedó a medias", "se reinició", "se cortó", "registra esto", "historial de procesos" o
  "qué se hizo antes".
allowed-tools:
  - Bash
  - PowerShell
---

# en-curso: el proceso en marcha

Todo se hace con un script, desde la raíz del proyecto. No abras `EN-CURSO.md` ni
`EN-CURSO-historial.md` con Read, y no los edites a mano.

```bash
python .claude/skills/en-curso/en_curso.py <comando>
```

| Comando | Qué hace |
|---|---|
| `estado` | Lo último, en pocas líneas. Es lo único que se consulta al retomar |
| `iniciar "T-003 Registro con correo" --repo app` | Abre un proceso |
| `paso "Qué voy a hacer"` | Abre un paso, con la hora. `paso 4` empieza el pendiente 4 |
| `hecho --nota "cómo se verificó"` | Cierra el paso abierto. `hecho 4` cierra el 4 |
| `pendiente "Qué falta"` | Anota un paso por hacer |
| `bloqueado 4 --nota "qué lo detiene"` | Marca un paso, o crea uno nuevo si se le da texto |
| `cerrar --nota "commit abc123"` | Pasa el proceso al historial y deja el activo vacío |
| `historial 3` | Los últimos 3 procesos cerrados. Sin número, todos |
| `--carril b` | En cualquier comando: el proceso de ese carril (abajo). `estado --todos` imprime todos |

## Reglas

1. **Al retomar, `estado` y nada más.** El hook de inicio de sesión ya lo imprime. No leas
   el historial para saber dónde vas.
2. **`paso` antes de empezar, `hecho` al terminar.** En el momento, no al final: lo que se
   anota después de un corte ya no sirve. Una línea por paso, sin detalle de más.
3. **Un `PASO ABIERTO` en una sesión nueva es donde se cortó la anterior.** Verifícalo
   antes de seguir. No lo marques hecho sin comprobarlo.
4. **Antes de algo que puede tumbar la sesión**, deja con `pendiente` lo que sigue.
5. **`cerrar` cuando el proceso termina.** Lo que quede sin hacer se anota solo en el
   historial. Lo que importa de fondo (decisiones, pendientes del proyecto) va a
   `PROGRESO.md` con la skill `bitacora`, que es aparte.
6. **El historial solo si se pide.** Y entonces `historial N` antes que el archivo entero.

## Varias sesiones en paralelo

Si dos sesiones trabajan a la vez, cada una lleva su carril: el `a` escribe en
`EN-CURSO.md` y cualquier otro en `EN-CURSO-<letra>.md`. La sesión del carril `b` agrega
`--carril b` a **todos** sus comandos (o define `EN_CURSO_CARRIL=b`); sin eso escribiría en
el proceso del otro. El historial es uno solo, con el carril anotado. El hook de inicio corre
`estado --todos`: cada sesión mira el suyo y no toca el del otro.

## Después de un corte

1. `git status`: qué quedó a medio editar o sin commit.
2. `python .claude/hooks/verificar.py`: que el índice y la redacción sigan al día.
3. Cuando existan (paso 1 del plan): las pruebas del proyecto y, si el paso lo requiere, el
   servidor local. Los comandos exactos están en la sección «Comandos» del `CLAUDE.md`.
4. Si el paso cortado llamaba a la API de Claude o descargaba un documento, comprueba en la
   base local si el documento quedó marcado como parcial antes de repetir la ingesta.

Revisa a mano el paso abierto y ciérralo con `hecho --nota "..."`.
