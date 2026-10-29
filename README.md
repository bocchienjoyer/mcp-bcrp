# MCP del BCRP con OpenAI / Codex

Servidor MCP para consultar series oficiales del Banco Central de Reserva del Perú y evaluar si su acceso mejora las respuestas de un modelo.

La referencia principal es la [presentación de clase](https://claude.ai/artifact/B9W8izJCRr6qsTLwbMXqcT). Partimos del [repositorio del curso](https://github.com/d2cml-ai/Data-Science-Python/tree/main/sessions/04-mcp-claude-code) y adaptamos la conexión y la evaluación de Claude Code a OpenAI mediante Codex. Conservamos el [enunciado original](docs/ENUNCIADO_ORIGINAL.md).

## Resultados

| Condición | Aciertos | Discrepancias | No sabe |
|---|---:|---:|---:|
| Memoria, con instrucción de abstenerse | 1/10 | 0 | 9 |
| MCP del BCRP | 9/10 | 1 | 0 |
| Memoria, sin esa instrucción | 2/10 | 0 | 8 |

Usamos el mismo modelo `gpt-6.1-sol`, esfuerzo `low` y sesiones independientes. La discrepancia corresponde a una pregunta ambigua del cobre: el modelo eligió su cotización LME y la referencia esperaba el precio de exportación. Una consulta aclarada acertó; se conserva aparte, sin cambiar el 9/10.

- [Informe completo](informe.md), [diez preguntas](preguntas.csv) y [resultados base](resultados.csv).
- [Experimento adicional](evaluacion/resultados_sin_abstencion.csv), [diagnóstico](evaluacion/resultados_diagnostico.csv) y [evidencias por respuesta](evaluacion/evidencias/).
- [Referencias verificadas](verificacion/referencias_verificadas.csv) y [comparaciones de metales](verificacion/comparaciones.json), contrastadas con las tablas web del BCRP.

![Evaluación y comparaciones de metales](grafico.png)

## Instalar y usar

Requisitos: Python 3.11 o superior, uv, Codex CLI con una sesión iniciada e internet.

```powershell
git clone https://github.com/bocchienjoyer/mcp-bcrp.git
cd mcp-bcrp
uv sync --frozen
uv run --frozen pytest -q
```

Las ocho pruebas originales permanecen sin cambios. Con las 27 complementarias, pasan **35 pruebas**.

Sigue la [guía de conexión](docs/CONEXION.md) para registrar `bcrp` y `fetch` en Codex. La configuración de Claude se conserva en `.mcp.json`; su equivalente para Codex está en [este ejemplo](docs/codex-mcp.example.toml). La [guía sencilla](docs/GUIA.md) explica cómo funciona cada pieza.

Con el MCP activado, pregunta normalmente:

- ¿Cuánto está la plata hoy?
- ¿Qué subió más entre el cierre de 2025 y el 27 de octubre de 2026: cobre, plata u oro?
- ¿Cuál de esos tres creció más entre el 27 de octubre de 2016 y el 27 de octubre de 2026?

La respuesta debe incluir fecha, unidad, código y fuente. «Hoy» corresponde al último dato publicado por el BCRP, cuya fecha debe indicarse.

## Qué ofrece

`buscar_series` identifica indicadores; `serie` obtiene sus datos; `resumen` calcula cambios, promedio y extremos. Nuestra herramienta propia, **`comparar_series`**, compara variaciones porcentuales entre dos series usando fechas comunes y devuelve ambas fuentes. Incluimos el recurso `bcrp://serie/{codigo}` y el prompt `informe(tema)`.

## Organización

En la raíz quedan el servidor, el evaluador y los archivos principales de la entrega.

| Carpeta | Contenido |
|---|---|
| [docs/](docs/) | Conexión, guía sencilla, enunciado y figura vectorial. |
| [scripts/](scripts/) | Verificar referencias y conexión, auditar resultados y generar el informe. |
| [tests/](tests/) | Pruebas complementarias; `test_server.py` conserva las originales en la raíz. |
| [evaluacion/](evaluacion/) | Metadatos, esquema de respuesta, experimentos y evidencias. |
| [verificacion/](verificacion/) | Cifras y fuentes comprobadas independientemente en la web. |

Los entornos, datos descargados, registros brutos y copias HTML quedan excluidos de Git.

## Reproducir

Para regenerar el informe y la figura desde los resultados incluidos, sin nuevas llamadas al modelo:

```powershell
uv run --frozen scripts/generar_informe.py
```

El [informe](informe.md#reproducir) detalla cómo repetir la verificación y las evaluaciones. Una nueva evaluación consume uso del modelo y puede producir respuestas distintas.
