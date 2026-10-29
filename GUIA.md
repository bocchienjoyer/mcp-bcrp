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

## Paso que completamos: resumir una serie

`resumen` recibe el mismo código y las mismas fechas que `serie`. Primero llama a `serie`
para obtener los valores; después Python calcula el resumen. No necesita otra consulta
distinta al banco para hacer las cuentas.

Ejemplo inventado para entender las operaciones: tres valores, **10, 15 y 20**.

| Resultado | Cómo se obtiene | Valor del ejemplo |
|---|---|---|
| Primero y último | Tomamos el inicio y el final de la lista | 10 y 20 |
| Cambio | Último menos primero | 10 |
| Variación porcentual | Cambio dividido entre el primero, multiplicado por 100 | 100 % |
| Promedio | Sumamos los valores y dividimos entre cuántos hay | 15 |
| Máximo y mínimo | Buscamos el mayor y el menor | 20 y 10 |

El resultado incluye las fechas de los extremos y el rango del promedio, la cantidad de
valores disponibles y el enlace a la fuente. En caso de empate, se muestra la primera fecha.
Si el valor inicial es cero, la variación porcentual se devuelve como `null` (sin valor),
porque esa cuenta requeriría dividir entre cero.

El cambio y la variación porcentual son cosas diferentes. Si una tasa pasa de 2 % a 3 %,
sube **1 punto porcentual**; el aumento relativo de esa tasa es **50 %**. Esto no significa
que la inflación acumulada del periodo sea 50 %. El promedio es la media simple de las
observaciones disponibles, sin rellenar los datos ausentes con ceros.

## Qué comprobamos y qué falta

Las ocho pruebas originales dan **6 aprobadas y 2 pendientes**.
Ya pasan la búsqueda, la consulta mensual, la consulta diaria, el resumen y el error por código inexistente.
También pasa el requisito de cuatro herramientas: agregamos `comparar_series` como herramienta propia.
También comprobamos consultas anuales y trimestrales mediante un cliente MCP de Python.
Las cuatro pruebas complementarias de `test_resumen_adicional.py` pasan: verifican las cuentas,
el inicio en cero, una única observación y los extremos empatados. Las ocho pruebas originales
del curso permanecen sin cambios.

Las ocho pruebas complementarias de `test_comparar_adicional.py` pasan. Comprueban que se comparen
porcentajes con las mismas fechas, que se conserven las fuentes y que se manejen datos insuficientes,
frecuencias distintas, bases no positivas, empates y descensos.

Faltan el recurso y el prompt. Después conectaremos el servidor al
asistente y evaluaremos las diez preguntas. Las pruebas actuales llaman al MCP desde Python;
la conexión para usarlo conversando todavía está pendiente.

## Nuestra herramienta propia: comparar dos series

`comparar_series` responde preguntas como «¿cuál de estos dos precios subió más en porcentaje?».
Recibe dos códigos y las fechas de inicio y fin.

1. Comprueba que las dos series tengan la misma frecuencia: por ejemplo, ambas mensuales.
2. Llama a `serie` para obtener cada lista de datos.
3. Encuentra las fechas que aparecen en ambas listas. Necesita al menos dos.
4. Usa el primer y el último periodo compartidos para calcular las dos variaciones porcentuales.
5. Devuelve los valores, las fechas realmente usadas, las variaciones y las dos fuentes.

Esto permite comparar cambios aunque las unidades de los precios sean distintas. Ejemplo inventado:
si un precio pasa de 100 a 200, sube 100 %; si otro pasa de 1,000 a 1,500, sube 50 %.
El primero creció más en porcentaje. La comparación requiere valores iniciales positivos.
Si ambas series bajan, el resultado identifica la caída menor; si empatan, lo indica.

### Ejemplo real comprobado: enero a agosto de 2026

Elegimos las series mensuales de **precios de exportación** del BCRP. El nombre completo del
indicador es importante: el catálogo también contiene producción de cobre y oro y otras medidas.

| Indicador | Código | Enero | Agosto | Cambio relativo |
|---|---|---|---|---|
| Cobre (centavos de US$ por libra) | PN38784BM | 660.48 | 689.70 | +4.42 % |
| Oro (US$ por onza troy) | PN38793BM | 4,733.06 | 4,411.15 | -6.80 % |

Las cuentas usan las cifras completas; la tabla las redondea para facilitar su lectura.
La diferencia entre las variaciones es de 11.22 puntos porcentuales.
Fuentes: [cobre](https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PN38784BM/json/2026-1/2026-8)
y [oro](https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PN38793BM/json/2026-1/2026-8).

La [documentación oficial del BCRP](https://estadisticas.bcrp.gob.pe/estadisticas/series/ayuda/api)
explica la dirección y los parámetros de las consultas.
