# Cómo funciona nuestro ejercicio

La referencia principal es la [presentación de clase](https://claude.ai/artifact/B9W8izJCRr6qsTLwbMXqcT).
Los archivos iniciales vienen del [repositorio compartido](https://github.com/d2cml-ai/Data-Science-Python/tree/main/sessions/04-mcp-claude-code/proyecto),
versión `d13359d8536fe378d512e8a190c950688cb8889d`.
Estamos adaptando la conexión y la evaluación de Claude Code a Codex.

## Las piezas, en palabras simples

- **BCRP:** la institución que publica los datos económicos que consultamos.
- **Serie:** los valores de un mismo indicador a lo largo del tiempo. Por ejemplo, una cifra de inflación por mes.
- **Código:** el identificador que el banco asigna a cada serie.
- **API:** la dirección y las reglas que permiten pedir esos datos desde un programa.
- **Función:** instrucciones de Python que reciben información, realizan una tarea y devuelven un resultado.
- **Servidor MCP:** nuestro programa que ofrece funciones para que un asistente pueda utilizarlas.
- **Prueba:** una comprobación automática de que una parte del programa responde como pide el ejercicio.

## Paso que completamos: obtener una serie

`buscar_series` busca en el catálogo. `serie` obtiene los valores del indicador elegido.

Ejemplo: queremos la inflación mensual de Lima de enero a diciembre de 2025.

1. El catálogo identifica esa serie con el código `PN01271PM`.
2. A `serie` le entregamos ese código, `2025-01` como inicio y `2025-12` como final.
3. La función comprueba el código y prepara una consulta a la API del BCRP.
4. El banco devuelve una fila por mes.
5. La función ordena las filas, convierte las cifras de texto a números y uniforma las fechas.
6. Devuelve la lista con el nombre de la serie y el enlace que permite comprobarla.

En la consulta comprobada, marzo de 2025 devuelve `0.810159321766145`, aproximadamente **0.81 %**.
La [respuesta del BCRP](https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PN01271PM/json/2025-1/2025-12)
contiene los doce meses. Es inflación mensual, no inflación acumulada ni interanual.

Si falta una cifra, no se convierte en cero: se omite. Si el código no existe, se informa del error.
Las descargas se guardan en `datos/` para reutilizarlas; esa carpeta está excluida de Git.

## Qué comprobamos y qué falta

Las ocho pruebas originales dan **4 aprobadas y 4 pendientes**.
Ya pasan la búsqueda, la consulta mensual, la consulta diaria y el error por código inexistente.
También comprobamos consultas anuales y trimestrales mediante un cliente MCP de Python.

Faltan `resumen`, la herramienta propia, el recurso y el prompt. Después conectaremos el servidor al
asistente y evaluaremos las diez preguntas. Las pruebas actuales llaman al MCP desde Python;
la conexión para usarlo conversando todavía está pendiente.

La [documentación oficial del BCRP](https://estadisticas.bcrp.gob.pe/estadisticas/series/ayuda/api)
explica la dirección y los parámetros de las consultas.
