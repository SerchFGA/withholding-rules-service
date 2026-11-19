# Plan de implementación: servicio de reglas de retención

Fecha: 2026-11-19. Presupuesto del ejercicio: 6 horas, 1.500 líneas de código de producción,
README de una página. Fuente de requisitos: `Rules.md`.

## 1. Lo verificado (2026-11-19)

| Hecho | Cómo se comprobó |
|---|---|
| IRS Pub. 15, Pub. 505 y Rev. Proc. 2023-34 están vivos | Descarga real, HTTP 200 |
| Los tres PDF tienen texto en todas sus páginas | PyMuPDF: 59, 48 y 27 páginas, ninguna vacía |
| Extraer el texto es casi instantáneo | 0,22 s, 0,19 s y 0,05 s |
| La Pub. 15 es la edición 2026; el Rev. Proc. solo cubre 2023 a 2025 | Texto extraído |
| DIAN Res. 238 está viva: HTML de 29 KB, ISO-8859-1, una tabla, `$52.374`, UVT | Descarga real |
| El "30 %" no aparece en la Pub. 15 y solo en una página de la 505 (p. 28) | Búsqueda en el texto |
| El 24 % de retención de respaldo sí aparece (Pub. 15, pp. 2 y 9) | Búsqueda en el texto |
| La URL de Ontario del enunciado no entrega el PDF | Cuatro intentos automáticos y prueba manual en navegador |
| Un filtro simple por palabras clave no reduce páginas (54 de 59, 43 de 48) | Conteo sobre el texto |

| canada.ca no responde a clientes automáticos desde esta máquina: ni su página de inicio ni ningún PDF (irs.gov responde en 0,5 s) | Seis intentos con dos programas, todos colgados hasta el tiempo límite |

| El documento vigente de Ontario es `t4032-on-1-26e.pdf` (con guiones): 16 páginas, todas con texto, "Effective January 1, 2026" | Descargado a mano por el usuario y leído con PyMuPDF |
| El VPS de Hostinger del usuario sí puede bajar el PDF de Ontario | `curl` desde el VPS: HTTP 200, 496.744 bytes, el mismo tamaño que la copia manual |

**No verificado:** los tiempos y el costo reales de la IA. El despliegue en Easypanel. La calidad de la extracción de
las tablas de Ontario (solo se comprobó que hay texto).

## 2. Decisiones

Todas son **decisión mía sin confirmar** salvo las marcadas como confirmadas.

| # | Decisión | Alternativa descartada |
|---|---|---|
| D1 | Python 3.12 con FastAPI | TypeScript: peor ecosistema de PDF |
| D2 | Extracción al ingerir; el resolve no usa IA | RAG con vectores: resultados aproximados y IA en cada pregunta |
| D3 | PyMuPDF para PDF, analizador HTML para la DIAN, visión de Claude para páginas sin texto | Docling, Marker, OCR en la nube: pesados o con credenciales extra |
| D4 | API de Claude (`claude-opus-5-5`) con salida estructurada y vocabulario cerrado (confirmado: se puede usar la API) | Citations de la API: no se combina con salida estructurada |
| D5 | Páginas en grupos, todas las llamadas en paralelo, con el tiempo restante como límite | Proceso en serie: no cabe en 120 s |
| D6 | VPS propio (Hostinger) con Easypanel, en `https://withholding.pixanai.com`, desplegado desde GitHub con un `Dockerfile` (confirmado por el usuario) | Vercel: disco no persistente y sin comprobar que descargue de canada.ca. Cloudflare: 10 ms de CPU en plan gratis. Render: se duerme |
| D7 | SQLite en todos lados (local, `make verify` y producción), en un volumen persistente del VPS (confirmado por el usuario) | Postgres: un segundo motor sin necesidad |
| D8 | Parámetro opcional nuevo `payee_type` (`government`, `non_resident`, `resident`) en `/v1/resolve` | Sin él las reglas duras no se pueden evaluar |
| D9 | Si la tasa es desconocida: `withholding_applies: null`, `rate: null`, revisión obligatoria | Responder `false`: lo prohíbe R4 |
| D10 | Vencido el plazo: HTTP 504 con error explícito en el resolve; en la ingesta, documento marcado "parcial" | Devolver lo que haya como decisión: lo prohíbe R3 |
| D11 | Campos nuevos del contrato: `policy_outcome`, `policy_applied`, `security_events`, `decision_trace`, `request_id`. `outcome` queda como el resultado sin ajustar | Cambiar `outcome`: rompe al orquestador |
| D12 | `POST /v1/documents` exige una clave en cabecera | Abierto: cualquiera gasta la cuota de la IA |
| D13 | Regla de páginas escaneadas: toda regla salida de visión queda marcada para revisión | Confiar en lo que la IA dice haber leído |
| D14 | Gobierno gana sobre no residente si llegan a chocar | El enunciado no lo define |
| D15 | Interfaz: una sola página estática, sin framework, inglés y español | React o similar: gasta el límite de líneas |
| D16 | Ontario: usar la versión oficial vigente y declararlo en el README | Sustituir por otro documento: penalizado |
| D17 | `services` en `US-FED` responde 24 % citando la retención de respaldo, con revisión obligatoria y motivo `conditional_on_payee_tin` (confirmado por el usuario) | Copiar el ejemplo sin revisión: afirma más que el documento. Responder desconocido: contradice el único ejemplo del enunciado |
| D18 | Alcance: solo reglas de tasa fija con umbral opcional. Topes máximos, tramos que suman y rejillas se guardan como estructura no soportada y responden revisar (confirmado por el usuario) | Modelar tramos y topes: no cabe en 1.500 líneas ni en 6 horas |
| D19 | El validador exige, además de la cita literal, que la cita hable de retener, y normaliza guiones de corte, apóstrofos y saltos de línea | Solo cita literal: deja pasar el 24 % de un tramo de impuesto y el 30 % de impuesto estimado, que existen palabra por palabra |
| D20 | La jurisdicción no es una lista fija: se valida su forma y, si el dominio es conocido, el país. Así entra un sexto documento de otro país | Lista cerrada de tres: rompería en la prueba en vivo |
| D21 | Sin `payee_type` no hay motivo de revisión: se anota en `decision_trace` que las reglas de beneficiario no se evaluaron | Marcar revisión siempre: contradice el ejemplo del enunciado |
| D22 | Un intento de instrucción incrustada se registra en `security_events` y no cambia ni el resultado ni la bandera de revisión | Marcar revisión: sería dejar que el documento altere la respuesta |
| D23 | Si hay un documento leído a medias, toda respuesta sale con revisión y motivo `document_partially_read` | Responder como si estuviera completo: lo prohíbe R3 |

**Aviso sobre la interfaz:** el enunciado no la pide y castiga construir de más. Cuenta contra
las 1.500 líneas. Se limita a unas 250 líneas y se hace al final; si el tiempo no alcanza, es
lo primero que se recorta.

## 3. Arquitectura

```
INGESTA   POST /v1/documents
  descarga (plazo propio, solo https, sin IP privadas)
  → hash del contenido (si ya existe: se devuelve lo guardado, cero gasto de IA)
  → detectar tipo (PDF, HTML, imagen) y, por página, texto o escaneo
  → texto por página (PyMuPDF / HTML) o imagen de página (visión)
  → detector de instrucciones incrustadas (se registra, no cambia nada)
  → grupos de páginas a Claude en paralelo → afirmaciones estructuradas
  → validador en código (enums, cita literal, números dentro de la cita)
  → reglas válidas a la base; las inválidas se descartan y se cuentan

RESOLVE   GET /v1/resolve   (sin IA)
  validar parámetros → gobierno → no residente → buscar reglas → umbral
  → tasa o "desconocido" → política del cliente (resultado aparte) → JSON v1
```

Tablas: `documents` (URL, hash, estado, versión del modelo), `pages` (texto, origen: texto o
visión), `rules` (jurisdicción, tipo de pago, año, umbral, tasa, monto fijo, base, página,
cita), `events` (registro de decisiones). `rules_version` es el sha256 de las reglas válidas
ordenadas.

## 4. Reparto de líneas (tope 1.500)

| Archivo | Qué hace | Líneas |
|---|---|---|
| `app/main.py` | Endpoints, plazo de 120 s, errores | 170 |
| `app/db.py` | SQLite y esquema | 80 |
| `app/fetch.py` | Descarga segura, detección de tipo | 90 |
| `app/parse.py` | PDF, HTML, páginas escaneadas, números por país | 150 |
| `app/extract.py` | Llamadas a Claude en paralelo, esquema cerrado | 170 |
| `app/validate.py` | Validación de afirmaciones, detector de inyección | 120 |
| `app/resolve.py` | Reglas duras, política, contrato | 190 |
| `app/logs.py` | Registro estructurado y redacción | 80 |
| `static/index.html` | Interfaz bilingüe | 250 |
| **Total** | | **1.300** |

Fuera del conteo: `tests/`, `eval/`, `scripts/verify.py`, `Makefile`, `Dockerfile`.

## 5. Orden de trabajo

La prueba se escribe antes que el código. Una prueba que falla no se cambia para que pase.

| Paso | Qué | Cómo se verifica | Tiempo |
|---|---|---|---|
| 0 | Resolver Ontario; leer los cinco documentos y fijar el vocabulario (jurisdicciones, tipos de pago) | Lista escrita con página y cita de cada regla esperada | 40 min |
| 1 | Esqueleto, `/health`, base de datos, `Dockerfile` y despliegue mínimo en Easypanel | `https://withholding.pixanai.com/health` responde con certificado válido; desde el contenedor se descargan los cinco documentos; la base sobrevive a un redespliegue | 35 min |
| 2 | Resolve con reglas duras y política, sobre reglas de prueba | Pruebas: gobierno, no residente, umbral, tasa ausente, año ambiguo, porcentaje contra monto fijo | 60 min |
| 3 | Descarga, detección de tipo y extracción de texto | Pruebas con los documentos reales: páginas, números colombianos, idempotencia | 45 min |
| 4 | Extracción con Claude en paralelo y validador | Pruebas: cita inventada se descarta, enum inválido se descarta, reingesta sin gasto | 60 min |
| 5 | Plazo de 120 s, inyección, registro y redacción | Pruebas: plazo vencido da error explícito; documento de prueba con instrucción incrustada no cambia la respuesta y queda registrado; ningún monto ni clave en el registro | 40 min |
| 6 | Set de evaluación (20 casos o más) y `make verify` | Sale una línea por R1 a R7 y la exactitud, desde base vacía | 40 min |
| 7 | Interfaz bilingüe | Revisión manual en inglés y español, en ancho de teléfono | 25 min |
| 8 | README de una página, diagrama C4 en Mermaid, cinco líneas finales | Todos los enlaces abren | 25 min |

Suma: unas 6 horas y 10 minutos. No hay margen: si algo se atrasa, se recorta el paso 7 y
luego el camino de visión, que se declara "diseñado, no ejercitado".

## 6. Interfaz (inglés y español)

Una página en `/`, sin dependencias. Selector de idioma arriba (recuerda la elección).

1. **Consultar:** formulario con listas cerradas (jurisdicción, tipo de pago, tipo de
   beneficiario), monto y año. Sin texto libre.
2. **Resultado:** tarjeta con la decisión en grande (se retiene, no se retiene, o revisar),
   el resultado sin ajustar y el ajustado lado a lado, los motivos de revisión en lenguaje
   llano, y cada cita con su documento, página y enlace.
3. **Reglas:** tabla filtrable de las reglas extraídas.
4. **Documentos:** lista de documentos ingeridos con su estado, y caja para ingerir una URL
   (pide la clave de D12).

Los estados "revisar" y "error" se distinguen por texto e icono, no solo por color.

## 7. Registro y datos sensibles (R7)

- **Se registra:** identificador de petición, jurisdicción, tipo de pago, año, resultado de
  cada regla, umbral aplicado, identificadores de las reglas usadas, versión del modelo,
  hash de reglas, tiempos.
- **Se minimiza:** el monto se guarda como rango y como resultado de la comparación con el
  umbral, nunca el valor exacto.
- **Nunca:** claves, cadenas de conexión, cabeceras de autorización, URL con parámetros de
  consulta.
- La frontera: el monto exacto solo existe en memoria durante la petición.

## 8. Riesgos y pendientes

| Riesgo | Qué hacer |
|---|---|
| El corpus trata sobre todo de nómina; muchas consultas de "servicios" darán "desconocido, revisar" | Es el comportamiento correcto (R4). El set de evaluación debe incluir esos casos. Material para las cinco líneas finales |
| `make verify` necesita una clave de la IA en la máquina del evaluador | Se documenta en el README (ver §10) |
| canada.ca bloquea a clientes automáticos desde la máquina local | El VPS sí lo descarga (comprobado). Las pruebas locales de Ontario usan una copia en disco; `make verify` en la máquina del evaluador puede toparse con el mismo bloqueo: se declara en el README |
| Límite de peticiones por minuto de la API al paralelizar | Tope de llamadas simultáneas configurable |
| El contrato no tiene forma de decir "desconocido" sin usar `null` | D9, y se menciona en las cinco líneas finales |
| En Windows no hay `make` | `make verify` solo llama a `python scripts/verify.py`, que también corre directo |

## 9. Despliegue en el VPS

Los pasos en paneles los hace el usuario; el agente prepara el `Dockerfile` y dice qué valor
va en cada campo. El agente no toca Hostinger ni Easypanel sin que se le pida.

1. Hostinger, DNS de `pixanai.com`: registro A `withholding` hacia la IP del VPS. No afecta
   a `www` ni a `devn8n`.
2. Easypanel: aplicación nueva desde el repositorio de GitHub, construida con el
   `Dockerfile`. No se tocan n8n ni NocoDB.
3. Dominio `withholding.pixanai.com` en la aplicación; Easypanel emite el certificado (ya
   lo hace para `devn8n.pixanai.com`).
4. Volumen persistente para el archivo de SQLite.
5. Variables de entorno en el panel: `ANTHROPIC_API_KEY` y la clave de ingesta (D12). Nunca
   en el repositorio ni en la imagen.

El enunciado dice "any free host". Se interpreta como permiso, no como prohibición de un
servidor propio, y el README lo dice en una línea.

## 10. Supuestos que se declaran en el README

Decidido por el usuario el 2026-11-19: no se pregunta a los evaluadores; se documenta.

1. **Clave de la API de Claude.** `make verify` necesita la variable de entorno
   `ANTHROPIC_API_KEY`. El README dice cómo definirla y que ninguna clave va en el
   repositorio. Si falta, `make verify` se detiene con un mensaje claro, no con un error
   críptico.
2. **`payee_type`.** El README explica que las reglas duras dependen del tipo de
   beneficiario, que el ejemplo del enunciado no lo trae y que por eso se agregó como
   parámetro opcional (`government`, `non_resident`, `resident`). Sin él, las reglas de
   gobierno y no residente no se evalúan y la respuesta lo dice en `decision_trace`.
3. **Ontario.** Se mantiene el corpus de cinco documentos. La URL del enunciado no entrega
   el PDF; se usa la versión oficial vigente y el README lo dice. Si el servidor tampoco
   puede descargarla, el README lo declara tal cual, con la evidencia, y ese documento
   queda como «no ingerido»: no se sustituye por otro.
