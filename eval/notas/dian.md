# dian: DIAN Resolución 000238 de 2025 (jurisdicción `CO`)

Fuente analizada: `text/dian.txt` (627 líneas, viene de HTML, primera línea `===== HTML (sin paginas) =====`).
Convención de citas: `[sin página] «texto»`. Cada «...» es una subcadena exacta de UNA línea del texto extraído. Como referencia interna, el cuerpo de la norma está entre las líneas 292 y 358 del archivo de texto.

## 1. Qué es y qué año fiscal cubre

Resolución de la DIAN del 15 de diciembre de 2025 que **fija el valor de la Unidad de Valor Tributario (UVT) para el año 2026**. Es una norma de un solo artículo de fondo.

- [sin página] «RESOLUCIÓN 000238 DE 2025»
- [sin página] «(diciembre 15)»
- [sin página] «Diario Oficial No. 53.338 de 17 de diciembre de 2025»
- Epígrafe: [sin página] «para fijar el valor de la Unidad de Valor Tributario (UVT) aplicable para el año 2026.»
- Artículo de fondo: [sin página] «"Artículo 1.2.1 . Valor de la Unidad de Valor Tributario (UVT). Fijar en cincuenta y dos mil trescientos setenta y cuatro pesos ($52.374) el valor de la Unidad de Valor Tributario -UVT que regirá durante el año 2026".»

Año fiscal: **2026**. La resolución es "de 2025" (año de expedición) y el valor rige en 2026: es el mismo patrón que el Rev. Proc. 2023-34 (nombre con un año, cifras para el siguiente).

Vigencia formal: [sin página] «ARTÍCULO 3o. VIGENCIA. La presente resolución rige a partir del día siguiente a la fecha de su publicación.» Publicada el 17 de diciembre de 2025, o sea que la resolución está vigente desde diciembre de 2025, pero el valor que fija es para 2026. Un extractor puede leer aquí un año ambiguo (2025 o 2026). El texto del artículo 1.2.1 es inequívoco: 2026.

## 2. Reglas explícitas

**Una sola, y no es una tasa de retención: es un valor de referencia.**

| Campo | Valor |
|---|---|
| Tipo propuesto | `uvt_reference_value` (no es un tipo de pago; dudoso si cabe en el vocabulario cerrado del servicio) |
| Año | 2026 |
| Tasa | ninguna |
| Umbral | ninguno |
| Monto | 52374 pesos colombianos por 1 UVT (escrito `$52.374`, el punto es separador de miles) |
| Base | valor de referencia (ni `percent_of_payment` ni `flat_amount` de retención ni `bracket`) |
| Página | sin página |
| Cita | [sin página] «"Artículo 1.2.1 . Valor de la Unidad de Valor Tributario (UVT). Fijar en cincuenta y dos mil trescientos setenta y cuatro pesos ($52.374) el valor de la Unidad de Valor Tributario -UVT que regirá durante el año 2026".» |

El mismo valor aparece una segunda vez en los considerandos: [sin página] «certificó el cálculo del valor actualizado de la Unidad de Valor Tributario (UVT) para el año 2026, en cincuenta y dos mil trescientos setenta y cuatro pesos ($52.374).» Conviene citar el artículo (parte resolutiva), no el considerando.

El valor en letras ("cincuenta y dos mil trescientos setenta y cuatro") permite confirmar que `$52.374` es 52374 y no 52,374 con decimales.

## 3. Casos difíciles

**a) Qué fija exactamente.** Solo el valor en pesos de la UVT para 2026. La UVT es la unidad en la que otras normas expresan sus umbrales: [sin página] «Que el Estatuto Tributario en su artículo 868 establece la Unidad de Valor Tributario UVT como la medida de valor que permite ajustar los valores contenidos en las disposiciones relativas a los impuestos y obligaciones administrados por la Unidad Administrativa Especial Dirección de Impuestos y Aduanas Nacionales (DIAN).» Las tarifas y las bases mínimas de retención en UVT están en el Estatuto Tributario y sus decretos, que NO forman parte de este documento ni del corpus.

**b) No contiene ninguna tasa de retención.** Verificado por búsqueda exacta: `retenci` 0 coincidencias, `tarifa` 0, `base` 0, `exen` 0, `no residente` 0.

**c) El único porcentaje es una trampa.** El signo `%` aparece una sola vez y es la variación del IPC usada para reajustar la UVT, no una tarifa: [sin página] «fue de 5.17%.» (subcadena del considerando del DANE). Un extractor que busque "un porcentaje" devolverá 0.0517 como tasa de retención de `CO`, con cita literal válida y significado falso.

**d) Dos convenciones numéricas en el mismo texto.** `$52.374` usa punto como separador de miles (son 52374). `5.17%` usa punto como separador decimal (son 5,17 por ciento). `Diario Oficial No. 53.338` usa punto de miles y no es dinero. Una regla única de "el punto es miles" o "el punto es decimal" rompe uno de los tres. Sugerencia: tratar como miles solo el patrón `$` + grupos de exactamente tres dígitos.

**e) El valor de la UVT no es un umbral.** La regla dura "monto por debajo del umbral que dice la publicación: no retener" no se dispara con este documento. 52374 es el valor de una unidad, no un mínimo de retención. Un pago de 50.000 pesos NO queda "bajo el umbral".

**f) Año.** `2025` aparece 17 veces (fecha, números de otras resoluciones, oficios) y `2026` 5 veces. El conteo por frecuencia daría 2025. También aparecen 2024, 2021, 2019, 2018 y 2011 en los considerandos. El rango del IPC viene además en orden invertido: [sin página] «en el periodo comprendido entre el 1 de octubre de 2025 y el 1 de octubre de 2024, fue de 5.17%.»

**g) Sustituye un artículo de otra resolución.** Modifica la Resolución 000227 de 2025: [sin página] «ARTÍCULO 1o. SUSTITUCIÓN DEL ARTÍCULO 1.2.1. DEL TÍTULO 2 DE LA PARTE 1 DE LA RESOLUCIÓN NÚMERO 000227 DE 2025, ÚNICA EN MATERIA TRIBUTARIA, ADUANERA Y CAMBIARIA.» El valor de UVT de 2025 no está en este texto.

## 4. Lo que el documento NO dice

- Ninguna tarifa de retención en la fuente para ningún concepto (servicios, honorarios, compras, arrendamientos, pagos al exterior).
- Ninguna base mínima en UVT ni en pesos a partir de la cual se retiene.
- Nada sobre tipo de beneficiario (entidad pública, residente, no residente).
- El valor de la UVT de 2025 o de años anteriores (solo dice que la disposición anterior «conserva su vigencia» para obligaciones de esos periodos, sin dar la cifra).
- Qué IVA, ICA o autorretención aplican.

Para cualquier consulta de `CO` la respuesta desde este documento es "desconocido, revisar". Nunca "no se retiene".

## 5. Calidad de la extracción

- **Punto de miles: sale bien.** [sin página] «($52.374)» aparece 2 veces, idéntico. `52,374` y `52374` 0 coincidencias (el servicio debe convertir, el texto no lo trae convertido).
- **Acentos y eñes del cuerpo: salen bien** (RESOLUCIÓN, Artículo, Sustitúyase, año, Bogotá, Publíquese).
- **Mojibake solo en el pie de página del sitio** (no en la norma): [sin página] «Sede principal | Bogotá, Nivel Central, carrera 8 NÂ° 6C - 38» y [sin página] «57 601 794 8883 LÃ­nea Centro Nacional de Cobro». Curioso: la línea vecina [sin página] «57 601 489 9000 Línea de Contact Center atención de Impuestos» sale bien, así que el defecto parece venir del HTML original y no de la extracción (dudoso, no verifiqué el HTML).
- **Artefacto en la firma:** [sin página] «Carlos Emilio Betancourt Galeano002E» (un `002E`, código del punto, pegado al nombre).
- **Espacios espurios dentro de números y referencias:** [sin página] «Resolución número 00 0227 de 2025» (en otros lugares `000227`), [sin página] «Resolución número 000 007 de 2025», y «artículo 1.2.1 .» con espacio antes del punto (varias veces). Una búsqueda de `000227` no encuentra todas las menciones.
- **Mucho ruido de navegación:** de 627 líneas, unas 290 antes del título y unas 270 después de la firma son menú, pie, teléfonos y líneas en blanco. Los teléfonos son números largos que un extractor puede tomar por cifras: [sin página] «Conmutador Nivel central: PBX 601 4823294 / (+57)».
- **Sin tablas.** Todo es prosa, cada párrafo en una sola línea larga (bueno para citar; las citas largas no se parten).
- **Comillas rectas** (`"`) alrededor del artículo 1.2.1, incluidas en la línea. Si la cita se serializa en JSON hay que escaparlas.
- **Sin páginas:** el campo `page` del contrato (entero en el ejemplo) no tiene valor natural. Decisión pendiente del equipo: `null`, 1 o un ancla.
- No hay texto que parezca instrucción inyectada (`ignore` 0, `instruc` 0).

## 6. Consultas candidatas para el set de evaluación

| # | Consulta | Respuesta esperada | Respaldo |
|---|---|---|---|
| 1 | `payment_type=services, amount=12000000, jurisdiction=CO, tax_year=2026` | `withholding_applies`: desconocido (no `false`), `rate`: null, `requires_human_review=true`, motivo: la publicación fija el valor de la UVT y no contiene tarifa de retención | [sin página] «para fijar el valor de la Unidad de Valor Tributario (UVT) aplicable para el año 2026.»; `retenci` y `tarifa` 0 coincidencias |
| 2 | `payment_type=services, amount=50000, jurisdiction=CO, tax_year=2026` | Igual que la 1: desconocido y revisión. NO debe salir `withholding_applies=false` por "monto bajo el umbral": 52374 es el valor de 1 UVT, no un umbral de retención | [sin página] «"Artículo 1.2.1 . Valor de la Unidad de Valor Tributario (UVT). Fijar en cincuenta y dos mil trescientos setenta y cuatro pesos ($52.374) el valor de la Unidad de Valor Tributario -UVT que regirá durante el año 2026".» |
| 3 | `payment_type=services, amount=12000000, jurisdiction=CO, tax_year=2025` | Desconocido, `requires_human_review=true`, motivos: sin tarifa y el valor que fija es para 2026, no para 2025 (la resolución es "de 2025" pero rige para 2026) | Misma cita del artículo 1.2.1 («que regirá durante el año 2026») |
| 4 | `payment_type=services, amount=12000000, jurisdiction=CO, tax_year=2026, payee_type=government` | `withholding_applies=false`, `rate`: null, `requires_human_review=false`, motivo: regla dura de código (gobierno nunca retiene) | No sale del documento. Sin cita |
| 5 | `payment_type=services, amount=12000000, jurisdiction=CO, tax_year=2026, payee_type=non_resident` | `withholding_applies=true`, `rate=0.3000` (piso de la regla dura), `basis=percent_of_payment`. Dudoso si `requires_human_review=true` porque la publicación no da tasa: decisión del equipo | No sale del documento (`no residente` 0 coincidencias) |
| 6 | `payment_type=services, amount=12000000, jurisdiction=CO, tax_year=2026` con verificación negativa | La respuesta NO debe traer `rate=0.0517`. Si el pipeline extrajo una regla con tasa 5.17% para `CO`, es un falso positivo: ese porcentaje es la variación del IPC | [sin página] «fue de 5.17%.» |

Comprobación extra sobre `/v1/rules` (no es consulta de `resolve`): si se guarda la UVT, el valor debe ser 52374 (entero), año 2026, con la cita del artículo 1.2.1.
