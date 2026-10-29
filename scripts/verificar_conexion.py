"""Comprueba el arranque por stdio de BCRP y Fetch registrados en Codex.

    uv run --frozen scripts/verificar_conexion.py

No utiliza un modelo. Lanza los procesos configurados y guarda la comprobación
en salidas/conexion_verificada.json, una carpeta excluida de Git.
"""
import asyncio
import json
import os
import tomllib
from datetime import datetime, timezone
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport


def transporte(configuracion):
    return StdioTransport(command=configuracion["command"],
                          args=configuracion.get("args", []),
                          env=configuracion.get("env", {}),
                          cwd=configuracion.get("cwd"))


async def main():
    carpeta_codex = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    config = tomllib.loads((carpeta_codex / "config.toml").read_text(encoding="utf-8"))
    servidores = config.get("mcp_servers", {})
    if not all(nombre in servidores for nombre in ("bcrp", "fetch")):
        raise SystemExit("Primero registra bcrp y fetch en Codex. Consulta docs/CONEXION.md.")

    async with Client(transporte(servidores["bcrp"]), timeout=180) as cliente:
        herramientas = sorted(t.name for t in await cliente.list_tools())
        assert {"buscar_series", "serie", "resumen", "comparar_series"} <= set(herramientas)
        ficha = json.loads((await cliente.read_resource("bcrp://serie/PN38793BM"))[0].text)
        assert ficha["codigo"] == "PN38793BM"
        prompt = await cliente.get_prompt("informe", {"tema": "precio del oro en agosto de 2026"})
        assert prompt.messages
        datos = (await cliente.call_tool("serie", {
            "codigo": "PN38793BM", "desde": "2026-08", "hasta": "2026-08"})).data
        assert len(datos["datos"]) == 1 and datos["datos"][0]["periodo"] == "2026-08"

    async with Client(transporte(servidores["fetch"]), timeout=180) as cliente:
        assert "fetch" in {t.name for t in await cliente.list_tools()}
        url = "https://gofastmcp.com/llms.txt"
        respuesta = await cliente.call_tool("fetch", {"url": url, "max_length": 2000})
        texto = "\n".join(c.text for c in respuesta.content if hasattr(c, "text"))
        assert "FastMCP" in texto

    resultado = {"fecha_utc": datetime.now(timezone.utc).isoformat(),
                 "tipo_prueba": "cliente MCP por stdio; no es una llamada del asistente del chat",
                 "bcrp": {"herramientas": herramientas, "recurso": "correcto", "prompt": "correcto",
                          "consulta": datos},
                 "fetch": {"url": url, "lectura": "correcta"}}
    salida = Path(__file__).resolve().parents[1] / "salidas" / "conexion_verificada.json"
    salida.parent.mkdir(exist_ok=True)
    salida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(resultado, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
