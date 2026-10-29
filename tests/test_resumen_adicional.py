"""Casos límite de resumen. Complementan las ocho pruebas originales del curso."""
import asyncio

import pytest
from fastmcp import Client

import server


def consultar(monkeypatch, valores):
    datos = [{"periodo": f"2025-{mes:02}", "valor": valor}
             for mes, valor in enumerate(valores, 1)]

    def serie_de_prueba(codigo, desde, hasta):
        return {"codigo": codigo, "nombre": "Indicador de prueba", "frecuencia": "Mensual",
                "datos": datos, "fuente": "https://example.org/datos-de-prueba"}

    monkeypatch.setattr(server, "serie", serie_de_prueba)

    async def ejecutar():
        async with Client(server.mcp) as cliente:
            respuesta = await cliente.call_tool(
                "resumen", {"codigo": "PRUEBA", "desde": "2025-01", "hasta": f"2025-{len(valores):02}"})
            return respuesta.data

    return asyncio.run(ejecutar())


def test_resumen_conserva_fuente_y_distingue_cambio_de_porcentaje(monkeypatch):
    r = consultar(monkeypatch, [10, 15, 20])
    assert r["cambio"] == 10
    assert r["variacion_pct"] == 100
    assert r["promedio"] == {"valor": 15, "desde": "2025-01", "hasta": "2025-03"}
    assert r["primero"] == r["minimo"] == {"periodo": "2025-01", "valor": 10}
    assert r["ultimo"] == r["maximo"] == {"periodo": "2025-03", "valor": 20}
    assert r["cantidad"] == 3
    assert r["fuente"] == "https://example.org/datos-de-prueba"


def test_resumen_con_inicio_cero_no_inventa_un_porcentaje(monkeypatch):
    r = consultar(monkeypatch, [0, 5, 10])
    assert r["variacion_pct"] is None
    assert r["cambio"] == 10
    assert r["promedio"]["valor"] == 5


def test_resumen_con_una_sola_observacion(monkeypatch):
    r = consultar(monkeypatch, [7])
    assert r["cantidad"] == 1
    assert r["cambio"] == r["variacion_pct"] == 0
    assert r["primero"] == r["ultimo"] == r["maximo"] == r["minimo"]
    assert r["promedio"]["valor"] == 7


def test_resumen_con_descenso_y_extremos_empatados(monkeypatch):
    r = consultar(monkeypatch, [20, 5, 20, 5])
    assert r["cambio"] == -15
    assert r["variacion_pct"] == pytest.approx(-75)
    assert r["maximo"]["periodo"] == "2025-01"
    assert r["minimo"]["periodo"] == "2025-02"
