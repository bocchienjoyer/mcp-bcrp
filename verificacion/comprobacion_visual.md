# Contraste de las tablas en el navegador

El 28 de octubre de 2026 (America/Bogota) se abrieron las tablas HTML del BCRP en un navegador
y se leyeron sus filas visibles, además de la extracción independiente con verificar_referencias.py.

| Fecha visible | Cobre (cUS$/libra) | Plata (US$/onza troy) | Oro (US$/onza troy) |
|---|---:|---:|---:|
| 27Oct16 | 216.54 | 17.65 | 1266.25 |
| 27Oct26 | 663.38 | 54.36 | 4060.13 |

Fuentes abiertas:

- [27 de octubre de 2016](https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PD04701XD-PD04702XD-PD04704XD/html/2016-10-27/2016-10-27).
- [27 de octubre de 2026](https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PD04701XD-PD04702XD-PD04704XD/html/2026-10-27/2026-10-27).

Las columnas se identificaron por su nombre completo: cobre de Londres, plata H. Harman y oro de Londres.
Los valores visibles coinciden con metales_verificados.csv. La URL del navegador termina en
`/series/diarias/` después de cargar la tabla, pero las fechas y las tres columnas se conservan en la vista.
