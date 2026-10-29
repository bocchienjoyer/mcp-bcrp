# ¿Ayuda un MCP a responder preguntas económicas con cifras verificables?

Evaluación del proyecto de clase adaptado de Claude Code a OpenAI mediante Codex. Referencia principal: [presentación de clase](https://claude.ai/artifact/B9W8izJCRr6qsTLwbMXqcT). El [repositorio del curso](https://github.com/d2cml-ai/Data-Science-Python/tree/main/sessions/04-mcp-claude-code) aportó el servidor inicial, las ocho pruebas y ocho preguntas.

## Resultado principal

Con el mismo modelo y las mismas diez preguntas, memoria acertó **1/10** y el MCP acertó **9/10** según la referencia fijada. La discrepancia del MCP corresponde a una pregunta ambigua del cobre: consultó la cotización LME en lugar del precio de exportación que esperaba la referencia del curso. Se conserva esa calificación, sin sustituirla por la consulta aclarada.

| Condición | Aciertos | Discrepancias | No sabe | Fallos técnicos | Segundos medios |
|---|---:|---:|---:|---:|---:|
| Memoria · base | 1/10 | 0 | 9 | 0 | 18.34 |
| MCP · base | 9/10 | 1 | 0 | 0 | 29.22 |
| Memoria · sin instrucción de abstenerse | 2/10 | 0 | 8 | 0 | 17.41 |

![Resultados y variaciones de los metales](grafico.png)

## Cómo se hizo la comparación

- Modelo: **gpt-6.1-sol**, el configurado en este equipo; esfuerzo **low** en todas las llamadas.
- Las ocho preguntas originales se conservaron y se agregaron dos comparaciones propuestas por el estudiante.
- Cada pregunta abrió una sesión efímera en una carpeta temporal vacía. No se adjuntaron esta conversación, el código, las referencias ni los archivos de resultados al contexto del modelo.
- Se ignoró la configuración personal en cada ejecución y se desactivaron shell, apps, plugins, subagentes y búsqueda web. Solo el brazo MCP recibió el servidor bcrp. Las respuestas esperadas nunca se enviaron al modelo.
- El CLI conserva utilidades administrativas para listar recursos. Algunas sesiones sin MCP las usaron y recibieron listas exactamente vacías; se registran como descubrimientos sin datos, no como consultas a fuentes. La auditoría comprueba su contenido y rechaza cualquier acceso a fuentes no permitido.
- La condición base pidió responder null si no había certeza. En ambos brazos se utilizó la misma instrucción y el mismo esquema de respuesta. Una abstención es distinta de un fallo técnico.
- Se exigió una consulta de cifras al MCP para considerar válida una respuesta numérica de ese brazo. Las comparaciones debían acertar el metal, el porcentaje y las dos fechas.
- Los tiempos incluyen arranque del CLI y del MCP, solicitudes y generación de la respuesta. Las consultas pueden reutilizar la caché local; no son una medida de latencia de red en frío.
- Corrida base: 20 llamadas. Experimento adicional: 10 llamadas de memoria. Diagnóstico aclarado: 1 llamada MCP. Las llamadas de preparación no forman parte de los resultados.
- Resultados completos: [base](resultados.csv), [experimento](evaluacion/resultados_sin_abstencion.csv), [metadatos](evaluacion/ejecucion.json) y [evidencias por respuesta](evaluacion/evidencias/). Los registros brutos permanecen en salidas/, excluida de Git.

## Las dos preguntas propias

### metales_2026

Según las cotizaciones internacionales diarias del BCRP, entre el cierre del 31 de diciembre de 2025 y el 27 de octubre de 2026, ¿cuál subió más en porcentaje: el cobre, la plata o el oro? Indica el metal ganador, su variación porcentual y las fechas comparadas.

**Referencia:** Cobre, **16.96 %** acumulado.

| Metal | Variación acumulada |
|---|---:|
| Cobre | +16.96 % |
| Plata | -23.72 % |
| Oro | -6.00 % |

Se compara el valor final con el inicial: `(final / inicial - 1) × 100`. Es crecimiento acumulado entre fechas, no promedio de precios ni tasa anualizada.

### metales_10anios

Según las cotizaciones internacionales diarias del BCRP, entre el 27 de octubre de 2016 y el 27 de octubre de 2026, ¿cuál tuvo el mayor crecimiento porcentual: el cobre, la plata o el oro? Indica el metal ganador, su variación porcentual y las fechas comparadas.

**Referencia:** Oro, **220.64 %** acumulado.

| Metal | Variación acumulada |
|---|---:|
| Cobre | +206.35 % |
| Plata | +207.99 % |
| Oro | +220.64 % |

Se compara el valor final con el inicial: `(final / inicial - 1) × 100`. Es crecimiento acumulado entre fechas, no promedio de precios ni tasa anualizada.

## Verificación independiente en la web del BCRP

Las referencias se comprobaron en tablas **HTML públicas del BCRP**, sin importar server.py ni llamar al MCP. Se conservaron los valores visibles, enlaces, fecha de consulta y SHA-256 de cada página en [fuentes.json](verificacion/fuentes.json), [referencias originales](verificacion/referencias_verificadas.csv) y [precios de metales](verificacion/metales_verificados.csv). El programa [scripts/verificar_referencias.py](scripts/verificar_referencias.py) permite repetir la comprobación. Las copias HTML quedan locales, fuera de Git.

Dos comprobaciones concretas de las nuevas preguntas:

| Serie | Fecha | Valor visible | Unidad | Tabla web |
|---|---|---:|---|---|
| PD04701XD | 2026-10-27 | 663.38 | centavos de US$/libra | [BCRP](https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PD04701XD-PD04702XD-PD04704XD/html/2026-10-27/2026-10-27) |
| PD04704XD | 2016-10-27 | 1,266.25 | US$/onza troy | [BCRP](https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PD04701XD-PD04702XD-PD04704XD/html/2016-10-27/2016-10-27) |

Las tablas redondean los valores; por eso las tolerancias permiten diferencias de presentación. Las ocho cifras originales quedaron dentro de las tolerancias del curso. El PBI se muestra como 3,4 en la tabla anual; la coma es decimal. Para las dos comparaciones se usa una tolerancia de 0.05 puntos porcentuales.

## Qué acertó y qué no

| Pregunta | Referencia | Memoria base | MCP base |
|---|---:|---|---|
| ipc_set26 | 4.5487 | No sabe (no sabe) | 4.5487 (acierta) |
| ipc_dic25 | 1.5088 | No sabe (no sabe) | 1.5088 (acierta) |
| ipc_mar25 | 0.8102 | 0.8100 (acierta) | 0.8102 (acierta) |
| referencia_set26 | 4.2500 | No sabe (no sabe) | 4.2500 (acierta) |
| tc_15oct26 | 3.4282 | No sabe (no sabe) | 3.4282 (acierta) |
| rin_ago26 | 96,517.9000 | No sabe (no sabe) | 96,517.9058 (acierta) |
| cobre_ago26 | 689.7000 | No sabe (no sabe) | 651.4515 (se equivoca) |
| pbi_2025 | 3.4306 | No sabe (no sabe) | 3.4306 (acierta) |
| metales_2026 | cobre: 16.96 % | No sabe (no sabe) | 16.9626 (acierta) |
| metales_10anios | oro: 220.64 % | No sabe (no sabe) | 220.6421 (acierta) |

### La discrepancia del cobre

La pregunta original dice «precio promedio del cobre», sin especificar exportación o LME. El modelo eligió **PN01652XM**, cotización promedio LME, y devolvió **651.45** centavos de US$/libra. La referencia espera **PN38784BM**, precio de exportación, con **689.70**. Ambas son series oficiales.

La [tabla alternativa LME](https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PN01652XM/html/2026-8/2026-8) muestra 651 redondeado; la herramienta conserva mayor precisión. La [tabla de exportación](https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PN38784BM/html/2026-8/2026-8) muestra 689.70. El fallo frente a la referencia no se debió a una cifra inventada, sino a la selección de un indicador distinto bajo una pregunta ambigua.

Se hizo una única consulta diagnóstica cambiando la pregunta a «precio promedio de EXPORTACIÓN del cobre». Respondió **689.698759925968**, que sí coincide con la referencia. Está en [evaluacion/resultados_diagnostico.csv](evaluacion/resultados_diagnostico.csv) y tiene evidencia separada. No reemplaza la corrida base ni eleva su puntuación.

## Experimento adicional: quitar la instrucción de abstenerse

Al retirar únicamente la frase que pide null si no sabe, memoria pasó de 1 a 2 aciertos, con 8 abstenciones y 0 errores numéricos. Preguntas cuya calificación cambió: ipc_dic25. La variación observada no permite atribuir una mejora general a quitar esa instrucción: también puede influir la variabilidad de generación. Este experimento se limitó a memoria, donde interesa observar la conducta sin fuentes externas.

## Alcance y limitaciones

Son diez preguntas elegidas para este ejercicio, con una ejecución por pregunta y condición. No se estima una precisión universal ni se comparan familias de modelos. Las cotizaciones son las publicadas por el BCRP, no precios bursátiles en tiempo real. Las referencias y las descargas tienen una fecha de corte y pueden cambiar por revisiones estadísticas. El uso de una caché debe considerarse al interpretar los tiempos.

## Conclusión

El acceso al MCP elevó los aciertos de 1/10 a 9/10 en esta muestra. Permitió recuperar cifras recientes y hacer comparaciones con fuentes y fechas verificables. La conexión no elimina la necesidad de elegir bien el indicador: el caso del cobre muestra esa limitación. Un MCP resulta útil cuando se necesita consultar reiteradamente la misma fuente estructurada y repetir cálculos; aquí no se evaluó un brazo de búsqueda web, por lo que no se afirma que supere a la web.

## Reproducir

```powershell
uv sync --frozen
uv run --frozen pytest -q
uv run --frozen scripts/verificar_referencias.py
uv run --frozen evaluar.py
uv run --frozen evaluar.py --experimento sin_abstencion --modos memoria
uv run --frozen scripts/auditar_resultados.py
uv run --frozen scripts/generar_informe.py
```

La configuración de Codex debe tener registrado bcrp; consulta [la guía de conexión](docs/CONEXION.md). Para regenerar solo el informe y la figura con esta corrida basta el último comando; no consume nuevas llamadas al modelo.
