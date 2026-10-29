"""Servidor MCP del BCRP. Empiecen aquí: buscar_series ya funciona; completen los TODO hasta que pasen las pruebas.

    uv run pytest                                           # el contrato: las 8 pruebas deben pasar
    uv run server.py                                        # el servidor, por stdio
    claude mcp add --scope project bcrp -- uv run server.py # conectarlo a Claude Code

Las cuentas las hace Python, no el modelo: así cada cifra sale de una llamada que se puede repetir.
"""
import json
import math
import re
import time
import unicodedata
from datetime import date
from functools import cache
from pathlib import Path
from statistics import fmean

import httpx
import pandas as pd
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

AQUI = Path(__file__).parent
CATALOGO = AQUI / "datos" / "catalogo_bcrp.csv"
URL_CATALOGO = "https://estadisticas.bcrp.gob.pe/estadisticas/series/metadata"
API = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"
SOLO_LECTURA = {"readOnlyHint": True, "openWorldHint": True}

mcp = FastMCP("bcrp", instructions=(
    "Series oficiales del Banco Central de Reserva del Perú (BCRP). Primero busca el código con buscar_series; "
    "luego usa resumen para variaciones, promedios y extremos, y serie para los datos. No calcules a mano: "
    "cita siempre el código de la serie y el periodo."))


def _sin_tildes(s):
    return unicodedata.normalize("NFD", str(s).lower()).encode("ascii", "ignore").decode()


@cache
def catalogo():
    """El catálogo oficial: 17 mil series en unos 7 MB. Se baja una vez y queda en datos/."""
    if not CATALOGO.exists():
        CATALOGO.parent.mkdir(exist_ok=True)
        r = httpx.get(URL_CATALOGO, timeout=120)
        r.raise_for_status()
        CATALOGO.write_text(r.content.decode("latin-1"), encoding="utf-8")
    df = pd.read_csv(CATALOGO, sep=";", dtype=str).fillna("")
    df = df.rename(columns={"Código de serie": "codigo", "Categoría de serie": "categoria", "Grupo de serie": "grupo",
                            "Nombre de serie": "nombre", "Frecuencia": "frecuencia",
                            "Fecha de actualización": "actualizada", "Fecha de inicio": "inicio"})
    df["texto"] = (df.categoria + " " + df.grupo + " " + df.nombre).map(_sin_tildes)
    return df


def _ficha(codigo):
    fila = catalogo().query("codigo == @codigo")
    if fila.empty:
        raise ToolError(f"No existe el código de serie {codigo!r}. Búsquenlo con buscar_series.")
    f = fila.iloc[0]
    return {"codigo": f.codigo, "nombre": f"{f.grupo} - {f.nombre}", "categoria": f.categoria,
            "frecuencia": f.frecuencia, "inicio": f.inicio, "actualizada": f.actualizada}


@mcp.tool(annotations=SOLO_LECTURA)
def buscar_series(texto: str, frecuencia: str | None = None, limite: int = 10) -> list[dict]:
    """Busca series del BCRP por palabras: todas deben aparecer en la categoría, el grupo o el nombre.

    Ejemplos: "ipc 12 meses", "tipo de cambio interbancario venta", "reservas internacionales netas",
    "tasa de referencia", "cobre precio". frecuencia: "Diaria", "Mensual", "Trimestral" o "Anual".
    Devuelve el código, el nombre completo, la frecuencia y desde cuándo hay datos. Si no hay resultados,
    prueben con menos palabras.
    """
    df = catalogo()
    m = pd.Series(True, index=df.index)
    for palabra in _sin_tildes(texto).split():
        m &= df.texto.str.contains(re.escape(palabra))
    if frecuencia:
        m &= df.frecuencia.str.lower() == frecuencia.lower()
    # primero las series vigentes y, entre ellas, las de nombre más corto (las más generales)
    sel = df[m]
    orden = sel.assign(vieja=sel.actualizada < "2025", largo=(sel.grupo + sel.nombre).str.len())
    return [_ficha(c) for c in orden.sort_values(["vieja", "largo"]).head(limite).codigo]


# TODO 1 · serie(codigo, desde, hasta) -> {"codigo", "nombre", "frecuencia", "datos": [{"periodo", "valor"}], "fuente"}
#   La API se llama así: f"{API}/{codigo}/json/{desde}/{hasta}" y responde
#   {"config": {...}, "periods": [{"name": "Ene.2025", "values": ["0.81"]}, ...]}
#   - Fechas que pide la API: 2025-1 (mensual y trimestral), 2025-01-15 (diaria), 2025 (anual).
#   - Nombres que devuelve: "Ene.2025" (mensual), "01.Oct.26" (diaria), "T1.25" (trimestral), "2025" (anual).
#     Setiembre viene como "Set". Devuelvan el periodo como "2025-01", "2026-10-01", "2025-T1" o "2025".
#   - Salten los valores "n.d." y usen la frecuencia de _ficha(codigo) para saber qué formato pedir.
#   - Si recibe muchos pedidos seguidos, la API responde una página HTML en vez de JSON: esperen unos segundos y
#     reintenten (y guarden en caché lo que ya bajaron).
#   - Un código que no existe debe dar un ToolError que diga el código.

MESES = {nombre: numero for numero, nombre in enumerate(
    ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "set", "oct", "nov", "dic"), 1)}
MESES["sep"] = 9


def _fecha_consulta(periodo, frecuencia):
    """Devuelve la fecha uniforme para nosotros y la fecha que acepta el BCRP."""
    if frecuencia == "Diaria":
        normal = date.fromisoformat(periodo).isoformat()
        return normal, normal
    if frecuencia == "Mensual":
        anio, mes = map(int, re.fullmatch(r"(\d{4})-(\d{1,2})", periodo).groups())
        normal = date(anio, mes, 1).strftime("%Y-%m")
        return normal, f"{anio}-{mes}"
    if frecuencia == "Trimestral":
        anio, trimestre = re.fullmatch(r"(\d{4})-T?([1-4])", periodo).groups()
        return f"{anio}-T{trimestre}", f"{anio}-{trimestre}"
    if frecuencia == "Anual" and re.fullmatch(r"\d{4}", periodo) and int(periodo) > 0:
        return periodo, periodo
    raise ValueError("frecuencia o periodo no reconocido")


def _anio_bcrp(texto, desde, hasta):
    """Cuando el banco abrevia el año, lo ubicamos dentro del rango solicitado."""
    if len(texto) == 4:
        return int(texto)
    candidatos = [anio for anio in range(int(desde[:4]), int(hasta[:4]) + 1)
                  if anio % 100 == int(texto)]
    if len(candidatos) != 1:
        raise ValueError(f"el año abreviado {texto!r} es ambiguo para ese rango")
    return candidatos[0]


def _periodo_bcrp(nombre, frecuencia, desde, hasta):
    """Traduce, por ejemplo, Mar.2025 a 2025-03 y 01.Oct.26 a 2026-10-01."""
    if frecuencia == "Anual":
        return str(int(nombre))
    if frecuencia == "Trimestral":
        trimestre, anio = re.fullmatch(r"T([1-4])\.(\d{2}|\d{4})", nombre).groups()
        return f"{_anio_bcrp(anio, desde, hasta)}-T{trimestre}"
    partes = nombre.split(".")
    anio = _anio_bcrp(partes[-1], desde, hasta)
    mes = MESES[partes[-2].lower()]
    dia = int(partes[0]) if frecuencia == "Diaria" else 1
    normal = date(anio, mes, dia).isoformat()
    return normal if frecuencia == "Diaria" else normal[:7]


def _descargar_serie(codigo, desde_api, hasta_api):
    """Reutiliza descargas y reintenta si el banco devuelve HTML o falla temporalmente."""
    url = f"{API}/{codigo}/json/{desde_api}/{hasta_api}"
    archivo = CATALOGO.parent / f"{codigo}_{desde_api}_{hasta_api}.json"
    if archivo.exists():
        try:
            contenido = json.loads(archivo.read_text(encoding="utf-8"))
            if isinstance(contenido.get("periods"), list):
                return contenido, url
        except (ValueError, AttributeError):
            pass  # Una copia incompleta se vuelve a descargar.

    for intento in range(3):
        try:
            respuesta = httpx.get(url, timeout=60, follow_redirects=True)
            respuesta.raise_for_status()
            contenido = respuesta.json()
            if not isinstance(contenido, dict) or not isinstance(contenido.get("periods"), list):
                raise ValueError("la respuesta no contiene una lista de periodos")
        except (httpx.HTTPError, ValueError) as error:
            if intento == 2:
                raise ToolError(f"El BCRP no respondió con datos para {codigo}. Fuente: {url}") from error
            time.sleep(intento + 1)
        else:
            archivo.parent.mkdir(exist_ok=True)
            archivo.write_text(json.dumps(contenido, ensure_ascii=False), encoding="utf-8")
            return contenido, url


@mcp.tool(annotations=SOLO_LECTURA)
def serie(codigo: str, desde: str, hasta: str) -> dict:
    """Consulta valores oficiales de una serie del BCRP entre dos periodos, incluidos ambos.

    Primero usa buscar_series para elegir el código y conocer su frecuencia y unidad.
    Fechas: YYYY-MM-DD para Diaria, YYYY-MM para Mensual, YYYY-T1 a YYYY-T4 para
    Trimestral y YYYY para Anual. Ejemplo: codigo="PN01271PM", desde="2025-01",
    hasta="2025-12". Omite valores no disponibles y devuelve fechas, cifras y la URL
    exacta de la fuente. Cita siempre el nombre, el periodo y la unidad de la serie.
    """
    # 1. Buscamos la ficha: identifica el indicador y si sus valores son diarios, mensuales, etc.
    ficha = _ficha(codigo)
    frecuencia = ficha["frecuencia"]
    try:
        inicio, desde_api = _fecha_consulta(desde, frecuencia)
        fin, hasta_api = _fecha_consulta(hasta, frecuencia)
    except (ValueError, AttributeError) as error:
        raise ToolError(f"Fechas inválidas para {codigo} ({frecuencia}): {desde!r}, {hasta!r}.") from error
    if inicio > fin:
        raise ToolError(f"Para {codigo}, desde debe ser anterior o igual a hasta.")

    # 2. Pedimos los datos al banco (o recuperamos una descarga idéntica).
    contenido, url = _descargar_serie(codigo, desde_api, hasta_api)

    # 3. Convertimos cada fila en una fecha uniforme y un número que Python pueda usar.
    datos = []
    for fila in contenido["periods"]:
        try:
            valor_original = fila["values"][0]
            if valor_original is None or str(valor_original).strip().lower() in {"", "n.d.", "n.d"}:
                continue
            valor = float(valor_original)
            if not math.isfinite(valor):
                continue
            periodo = _periodo_bcrp(fila["name"], frecuencia, inicio, fin)
        except (ValueError, KeyError, IndexError, TypeError, AttributeError) as error:
            raise ToolError(f"El BCRP devolvió una fila con formato inesperado para {codigo}. Fuente: {url}") from error
        if inicio <= periodo <= fin:
            datos.append({"periodo": periodo, "valor": valor})
    if not datos:
        raise ToolError(f"No hay valores disponibles para {codigo} entre {desde} y {hasta}. Fuente: {url}")

    # 4. Entregamos los valores junto con la identificación y la fuente para poder verificarlos.
    return {"codigo": codigo, "nombre": ficha["nombre"], "frecuencia": frecuencia,
            "datos": sorted(datos, key=lambda fila: fila["periodo"]), "fuente": url}

# TODO 2 · resumen(codigo, desde, hasta): primero, ultimo, cambio, variacion_pct, promedio, maximo y minimo
#   (los tres últimos con su periodo). Úsenla para que el modelo nunca haga cuentas a mano.


@mcp.tool(annotations=SOLO_LECTURA)
def resumen(codigo: str, desde: str, hasta: str) -> dict:
    """Calcula un resumen de una serie del BCRP en el rango solicitado.

    Úsala para preguntar cuánto cambió un indicador, su promedio, máximo o mínimo.
    Recibe las mismas fechas que serie. Devuelve primero y último con sus periodos;
    cambio = último - primero; variacion_pct = cambio / primero * 100; promedio
    aritmético de los valores disponibles con el rango observado; máximo y mínimo
    con su periodo (si hay empate, el primero). Incluye la cantidad de valores y
    la URL de la fuente. Si el primer valor es cero, variacion_pct es null porque
    no se puede dividir entre cero. En una serie expresada en %, cambio se mide
    en puntos porcentuales; variacion_pct mide el cambio relativo de esa tasa.
    Este resumen no calcula inflación acumulada ni anualiza tasas.
    """
    # 1. Reutilizamos serie: ella se encarga de consultar al banco y ordenar las fechas.
    resultado = serie(codigo, desde, hasta)
    datos = resultado["datos"]
    primero, ultimo = datos[0], datos[-1]

    # 2. Python hace las cuentas usando las cifras completas, sin redondearlas antes.
    cambio = ultimo["valor"] - primero["valor"]
    variacion = cambio / primero["valor"] * 100 if primero["valor"] != 0 else None
    promedio = fmean(fila["valor"] for fila in datos)

    # 3. Conservamos las fechas y la fuente para que cada resultado se pueda comprobar.
    return {
        "codigo": resultado["codigo"], "nombre": resultado["nombre"],
        "frecuencia": resultado["frecuencia"], "cantidad": len(datos),
        "primero": primero, "ultimo": ultimo,
        "cambio": cambio, "variacion_pct": variacion,
        "promedio": {"valor": promedio, "desde": primero["periodo"], "hasta": ultimo["periodo"]},
        "maximo": max(datos, key=lambda fila: fila["valor"]),
        "minimo": min(datos, key=lambda fila: fila["valor"]),
        "fuente": resultado["fuente"],
    }


# TODO 3 · Una herramienta suya, bien descrita. Ideas:
#   - comparar_paises con la API del Banco Mundial, que tampoco pide clave:
#     https://api.worldbank.org/v2/country/PER;CHL;COL/indicator/NY.GDP.MKTP.KD.ZG?format=json&date=2015:2025
#   - correlacion(codigo_a, codigo_b, desde, hasta)
#   - grafico(codigo, desde, hasta) que guarde un PNG en salidas/ y devuelva la ruta

# TODO 4 · Un recurso, por ejemplo la plantilla bcrp://serie/{codigo} con la ficha de la serie.

# TODO 5 · Un prompt, por ejemplo informe(tema) que pida citar el código y el periodo de cada cifra.


if __name__ == "__main__":
    mcp.run()
