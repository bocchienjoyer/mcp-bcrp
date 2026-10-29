"""Verifica cifras en tablas HTML del BCRP, sin importar ni usar nuestro MCP.

    uv run --frozen scripts/verificar_referencias.py

Guarda valores visibles, enlaces y huellas de las páginas. Las copias HTML son locales.
"""
import csv
import hashlib
import html
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

AQUI = Path(__file__).resolve().parents[1]
CARPETA = AQUI / "verificacion"
METALES = {"PD04701XD": "cobre", "PD04702XD": "plata", "PD04704XD": "oro"}


def tabla(codigos, desde, hasta, nombre):
    url = f"https://estadisticas.bcrp.gob.pe/estadisticas/series/api/{codigos}/html/{desde}/{hasta}"
    archivo = CARPETA / f"{nombre}.html"
    for intento in range(3):
        try:
            respuesta = httpx.get(url, timeout=90, follow_redirects=True)
            respuesta.raise_for_status()
            pagina = respuesta.content.decode("utf-8", errors="replace")
            filas = []
            for fila in re.findall(r"<tr\b[^>]*>(.*?)</tr>", pagina, re.S | re.I):
                celdas = [html.unescape(re.sub("<[^>]+>", " ", celda)).strip()
                          for celda in re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", fila, re.S | re.I)]
                if len(celdas) >= 2 and re.match(r"^\d|^[A-Za-z]{3}\.?\d", celdas[0]):
                    try:
                        # La tabla anual usa coma decimal; las otras pueden usar coma de miles.
                        numeros = [c.replace(",", ".") if "," in c and "." not in c
                                   else c.replace(",", "") for c in celdas[1:]]
                        valores = [float(c) for c in numeros]
                    except ValueError:
                        continue
                    filas.append({"etiqueta": celdas[0], "valores": valores})
            if not filas:
                raise ValueError("La página no contiene filas de datos numéricos.")
            archivo.write_text(pagina, encoding="utf-8")
            return {"url": url, "consultada_utc": datetime.now(timezone.utc).isoformat(),
                    "sha256_html": hashlib.sha256(respuesta.content).hexdigest(), "filas": filas}
        except (httpx.HTTPError, ValueError):
            if intento == 2:
                raise
            time.sleep(2 + intento)


def escribir_csv(nombre, filas):
    with (CARPETA / nombre).open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(filas[0]))
        escritor.writeheader()
        escritor.writerows(filas)


def main():
    CARPETA.mkdir(exist_ok=True)
    fuentes, metales = [], []
    codigos = "-".join(METALES)
    for fecha in ["2016-10-27", "2025-12-31", "2026-10-27"]:
        referencia = tabla(codigos, fecha, fecha, f"metales_{fecha}")
        assert len(referencia["filas"]) == 1
        for codigo, valor in zip(METALES, referencia["filas"][0]["valores"], strict=True):
            metales.append({"codigo": codigo, "metal": METALES[codigo], "fecha": fecha,
                            "valor_visible_tabla": valor, "fuente": referencia["url"]})
        fuentes.append(referencia)
        time.sleep(0.4)
    escribir_csv("metales_verificados.csv", metales)

    with (AQUI / "preguntas.csv").open(encoding="utf-8", newline="") as archivo:
        preguntas = list(csv.DictReader(archivo))[:8]
    comprobaciones = []
    for q in preguntas:
        periodo = q["periodo"]
        fecha_api = f"{periodo[:4]}-{int(periodo[5:])}" if len(periodo) == 7 else periodo
        referencia = tabla(q["serie"], fecha_api, fecha_api, q["id"])
        assert len(referencia["filas"]) == 1
        visible = referencia["filas"][0]["valores"][0]
        assert abs(visible - float(q["verdad"])) <= float(q["tolerancia"]), q["id"]
        comprobaciones.append({"id": q["id"], "codigo": q["serie"], "periodo": periodo,
                               "valor_visible_tabla": visible, "verdad_curso": q["verdad"],
                               "dentro_tolerancia": True, "fuente": referencia["url"]})
        fuentes.append(referencia)
        time.sleep(0.4)
    escribir_csv("referencias_verificadas.csv", comprobaciones)

    valores = {(f["metal"], f["fecha"]): f["valor_visible_tabla"] for f in metales}
    comparaciones = []
    for identificador, inicio in [("metales_2026", "2025-12-31"), ("metales_10anios", "2016-10-27")]:
        cambios = {metal: (valores[(metal, "2026-10-27")] / valores[(metal, inicio)] - 1) * 100
                   for metal in METALES.values()}
        ganador = max(cambios, key=cambios.get)
        comparaciones.append({"id": identificador, "desde": inicio, "hasta": "2026-10-27",
                              "ganador": ganador, "variacion_ganador_pct": cambios[ganador],
                              "variaciones_pct": cambios})
    (CARPETA / "fuentes.json").write_text(json.dumps(fuentes, ensure_ascii=False, indent=2), encoding="utf-8")
    (CARPETA / "comparaciones.json").write_text(json.dumps(comparaciones, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(comparaciones, ensure_ascii=True, indent=2))
    print("Las ocho cifras del curso coinciden con las tablas web dentro de sus tolerancias.")


if __name__ == "__main__":
    main()
