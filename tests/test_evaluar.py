"""Evita confundir abstenciones, errores de formato y aciertos de las comparaciones."""
import pytest

from evaluar import calificar, descubrimiento_vacio


@pytest.mark.parametrize("valor,esperado", [(None, "no sabe"), (0, "se equivoca"),
    (4.55, "acierta"), (4.7, "se equivoca"), ("4.55", "respuesta invalida"),
    (True, "respuesta invalida"), (float("nan"), "respuesta invalida")])
def test_calificar_valores_y_abstenciones(valor, esperado):
    assert calificar({"valor": valor}, {"verdad": "4.5487", "tolerancia": "0.05"}) == esperado


@pytest.mark.parametrize("cambios", [{"ganador": "plata"}, {"desde": "2026-01-01"},
    {"hasta": "2026-10-26"}, {"valor": 220.64}])
def test_comparacion_exige_ganador_valor_y_periodo(cambios):
    pregunta = {"tipo": "comparacion", "verdad": "16.96", "tolerancia": "0.05",
                "ganador": "cobre", "desde": "2025-12-31", "hasta": "2026-10-27"}
    respuesta = {"valor": 16.96, "ganador": "cobre", "desde": "2025-12-31", "hasta": "2026-10-27"}
    assert calificar(respuesta, pregunta) == "acierta"
    respuesta.update(cambios)
    assert calificar(respuesta, pregunta) == "se equivoca"


@pytest.mark.parametrize("contenido,esperado", [('{"resources":[]}', True),
    ('{"resources":[{"uri":"datos://precio"}]}', False), ('{}', False), ('no es JSON', False)])
def test_discovery_solo_es_inocuo_si_no_devuelve_datos(contenido, esperado):
    item = {"server": "codex", "tool": "list_mcp_resources", "result": {"content": [{"text": contenido}]}}
    assert descubrimiento_vacio(item) is esperado
