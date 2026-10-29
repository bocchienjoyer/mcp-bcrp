"""Pruebas de la herramienta propia, sin modificar las ocho pruebas del curso."""
import asyncio

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

import server


def consultar(monkeypatch, valores_a, valores_b, frecuencias=("Mensual", "Mensual")):
    def ficha(codigo):
        return {"frecuencia": frecuencias[0 if codigo == "A" else 1]}

    def serie(codigo, desde, hasta):
        valores = valores_a if codigo == "A" else valores_b
        return {"codigo": codigo, "nombre": f"Indicador {codigo} (unidad propia)",
                "datos": [{"periodo": periodo, "valor": valor} for periodo, valor in valores.items()],
                "fuente": f"https://example.org/prueba/{codigo}"}

    monkeypatch.setattr(server, "_ficha", ficha)
    monkeypatch.setattr(server, "serie", serie)

    async def ejecutar():
        async with Client(server.mcp) as cliente:
            return (await cliente.call_tool("comparar_series", {
                "codigo_a": "A", "codigo_b": "B", "desde": "2025-01", "hasta": "2025-05"})).data

    return asyncio.run(ejecutar())


def test_compara_porcentajes_y_conserva_ambas_fuentes(monkeypatch):
    r = consultar(monkeypatch, {"2025-01": 100, "2025-02": 200},
                  {"2025-01": 1000, "2025-02": 1500})
    assert r["serie_a"]["variacion_pct"] == 100
    assert r["serie_b"]["variacion_pct"] == 50
    assert r["diferencia_variaciones_pp"] == 50
    assert r["mayor_variacion"] == "A"
    assert not r["empate"]
    assert r["serie_a"]["fuente"] == "https://example.org/prueba/A"
    assert r["serie_b"]["fuente"] == "https://example.org/prueba/B"


def test_alinea_las_fechas_antes_de_calcular(monkeypatch):
    r = consultar(monkeypatch, {"2025-01": 10, "2025-02": 20, "2025-03": 40, "2025-04": 80},
                  {"2025-02": 100, "2025-03": 120, "2025-04": 150, "2025-05": 200})
    assert r["periodo_comun"] == {"desde": "2025-02", "hasta": "2025-04"}
    assert r["observaciones_comunes"] == 3
    assert r["serie_a"]["variacion_pct"] == 300
    assert r["serie_b"]["variacion_pct"] == 50


def test_rechaza_una_sola_fecha_comun(monkeypatch):
    with pytest.raises(ToolError, match="dos periodos comunes"):
        consultar(monkeypatch, {"2025-01": 10, "2025-02": 20}, {"2025-02": 100, "2025-03": 200})


def test_rechaza_frecuencias_distintas(monkeypatch):
    with pytest.raises(ToolError, match="frecuencias distintas"):
        consultar(monkeypatch, {}, {}, frecuencias=("Mensual", "Anual"))


@pytest.mark.parametrize("inicio", [0, -10])
def test_rechaza_bases_no_positivas(monkeypatch, inicio):
    with pytest.raises(ToolError, match="inicial positivo para A"):
        consultar(monkeypatch, {"2025-01": inicio, "2025-02": 20}, {"2025-01": 100, "2025-02": 200})


def test_informa_empate(monkeypatch):
    r = consultar(monkeypatch, {"2025-01": 10, "2025-02": 20}, {"2025-01": 100, "2025-02": 200})
    assert r["empate"]
    assert r["mayor_variacion"] is None
    assert r["diferencia_variaciones_pp"] == 0


def test_si_ambas_bajan_identifica_la_caida_menor(monkeypatch):
    r = consultar(monkeypatch, {"2025-01": 100, "2025-02": 80}, {"2025-01": 100, "2025-02": 90})
    assert r["mayor_variacion"] == "B"
    assert r["serie_a"]["variacion_pct"] == -20
    assert r["serie_b"]["variacion_pct"] == -10
