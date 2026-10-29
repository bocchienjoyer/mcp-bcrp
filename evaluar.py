"""Evalúa diez preguntas con el mismo modelo de OpenAI vía Codex.

uv run --frozen evaluar.py
uv run --frozen evaluar.py --experimento sin_abstencion

Cada pregunta usa una sesión efímera en una carpeta vacía. La configuración personal,
terminal, apps, plugins, web e historial se excluyen; solo se agrega bcrp en modo mcp.
Las respuestas de referencia no se envían al modelo. Usa la sesión de ChatGPT de Codex.
"""
import argparse
import csv
import json
import math
import os
import shutil
import subprocess
import tempfile
import time
import tomllib
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

AQUI = Path(__file__).parent
ABSTENCION = "Si no puedes saberlo con certeza, pon valor null: no estimes.\n"
INSTRUCCION = ("Responde la pregunta en la unidad solicitada y con el esquema JSON indicado.\n" + ABSTENCION +
    "En fuente indica de dónde sale la cifra y los enlaces, si los consultaste.\n"
    "Si la pregunta compara metales, valor es la variación porcentual del ganador; ganador es cobre, plata u oro; "
    "desde y hasta son las fechas comparadas en YYYY-MM-DD. En las otras preguntas, ganador, desde y hasta son null.\n"
    "No leas archivos locales ni uses terminal, otras apps o búsqueda web. "
    "Puedes usar las herramientas de consulta que estén habilitadas para esta llamada.\n\n")


def configuracion_bcrp():
    carpeta = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    c = tomllib.loads((carpeta / "config.toml").read_text(encoding="utf-8"))
    if "bcrp" not in c.get("mcp_servers", {}):
        raise SystemExit("Registra primero bcrp en Codex; consulta docs/CONEXION.md.")
    return c["mcp_servers"]["bcrp"]


def calificar(respuesta, pregunta):
    valor = respuesta.get("valor")
    if valor is None:
        return "no sabe"
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor):
        return "respuesta invalida"
    acierto = abs(valor - float(pregunta["verdad"])) <= float(pregunta["tolerancia"])
    if pregunta.get("tipo") == "comparacion":
        acierto &= str(respuesta.get("ganador") or "").strip().lower() == pregunta["ganador"]
        acierto &= respuesta.get("desde") == pregunta["desde"] and respuesta.get("hasta") == pregunta["hasta"]
    return "acierta" if acierto else "se equivoca"


def comando(args, modo, servidor, carpeta, salida):
    cli = shutil.which("codex")
    if not cli:
        raise RuntimeError("No se encontró Codex CLI en PATH.")
    cmd = [cli, "exec", "--ignore-user-config", "--ephemeral", "--skip-git-repo-check", "--sandbox", "read-only",
           "--json", "--model", args.modelo, "--output-schema", str(AQUI / "evaluacion" / "esquema_respuesta.json"),
           "-o", str(salida), "-C", str(carpeta)]
    opciones = {"features.shell_tool": False, "features.unified_exec": False, "features.apps": False,
        "features.plugins": False, "features.multi_agent": False, "features.multi_agent_v2": False,
        "features.skill_search": False, "features.skip_host_skill_discovery": True,
        "web_search": "disabled", "model_reasoning_effort": args.esfuerzo, "project_doc_max_bytes": 0}
    if modo == "mcp":
        opciones.update({"mcp_servers.bcrp.command": servidor["command"],
            "mcp_servers.bcrp.args": servidor.get("args", []), "mcp_servers.bcrp.required": True,
            "mcp_servers.bcrp.startup_timeout_sec": 45, "mcp_servers.bcrp.tool_timeout_sec": 240})
        for clave, valor in servidor.get("env", {}).items():
            opciones[f"mcp_servers.bcrp.env.{clave}"] = valor
        if servidor.get("cwd"):
            opciones["mcp_servers.bcrp.cwd"] = servidor["cwd"]
    for clave, valor in opciones.items():
        cmd += ["-c", f"{clave}={json.dumps(valor, ensure_ascii=False)}"]
    return cmd + ["-"]


def descubrimiento_vacio(item):
    """Listar un registro vacío no proporciona cifras ni acceso a una fuente externa."""
    claves = {"list_mcp_resources": "resources", "list_mcp_resource_templates": "resourceTemplates"}
    if item.get("server") != "codex" or item.get("tool") not in claves:
        return False
    contenido = (item.get("result") or {}).get("content", [])
    try:
        return len(contenido) == 1 and json.loads(contenido[0]["text"]) == {claves[item["tool"]]: []}
    except (ValueError, KeyError, TypeError):
        return False


def preguntar(q, modo, args, servidor):
    inicio = time.perf_counter()
    nombre = f"{modo}_{q['id']}"
    lote = args.experimento + ("_diagnostico" if args.ids else "")
    raw = AQUI / "salidas" / "evaluacion" / lote
    raw.mkdir(parents=True, exist_ok=True)
    instruccion = INSTRUCCION if args.experimento == "base" else INSTRUCCION.replace(ABSTENCION, "")
    respuesta, llamadas, descubrimientos, problemas, uso = {}, [], [], [], {}
    try:
        with tempfile.TemporaryDirectory(prefix="bcrp_evaluacion_") as carpeta:
            salida = Path(carpeta) / "respuesta.json"
            proc = subprocess.run(comando(args, modo, servidor, Path(carpeta), salida),
                input=instruccion + q["pregunta"], capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=args.timeout)
            (raw / f"{nombre}.jsonl").write_text(proc.stdout, encoding="utf-8")
            (raw / f"{nombre}.stderr.txt").write_text(proc.stderr, encoding="utf-8")
            if proc.returncode:
                problemas.append(f"Codex terminó con código {proc.returncode}; revisa el registro local.")
            for linea in proc.stdout.splitlines():
                try:
                    evento = json.loads(linea)
                except json.JSONDecodeError:
                    continue
                item = evento.get("item", {})
                if item.get("type") == "mcp_tool_call" and evento.get("type") == "item.completed":
                    registro = {k: item.get(k) for k in ("server", "tool", "arguments", "status")}
                    if descubrimiento_vacio(item):
                        descubrimientos.append(registro)
                    else:
                        llamadas.append(registro)
                if item.get("type") in {"command_execution", "file_change", "web_search"}:
                    problemas.append("Se detectó una herramienta no permitida.")
                if evento.get("type") in {"turn.failed", "error"}:
                    problemas.append("Codex informó un fallo de ejecución.")
                if evento.get("type") == "turn.completed":
                    uso = evento.get("usage", {})
            if salida.exists():
                respuesta = json.loads(salida.read_text(encoding="utf-8"))
            else:
                problemas.append("No se produjo una respuesta estructurada.")
    except (OSError, subprocess.TimeoutExpired, ValueError) as error:
        problemas.append(f"{type(error).__name__}: {str(error)[:160]}")
    if modo == "memoria" and llamadas:
        problemas.append("El modo memoria intentó utilizar un MCP.")
    if modo == "mcp" and respuesta.get("valor") is not None:
        consultas = [c for c in llamadas if c["server"] == "bcrp" and
            c["tool"] in {"serie", "resumen", "comparar_series"} and c["status"] == "completed"]
        if not consultas:
            problemas.append("Falta una consulta de cifras del BCRP registrada para esta respuesta.")
    resultado = "error tecnico" if problemas else calificar(respuesta, q)
    segundos = round(time.perf_counter() - inicio, 2)
    evidencia = {"id": q["id"], "pregunta": q["pregunta"], "modelo": args.modelo, "esfuerzo": args.esfuerzo,
        "modo": modo, "experimento": args.experimento, "respuesta": respuesta, "llamadas_mcp": llamadas,
        "descubrimientos_sin_datos": descubrimientos,
        "uso": uso, "segundos": segundos, "resultado": resultado, "problemas": problemas}
    destino = AQUI / "evaluacion" / "evidencias" / lote
    destino.mkdir(parents=True, exist_ok=True)
    (destino / f"{nombre}.json").write_text(json.dumps(evidencia, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{args.experimento} | {modo:7} | {q['id']:18} | {resultado:16} | {segundos:.1f} s", flush=True)
    return {"id": q["id"], "modo": modo, "experimento": args.experimento, "modelo": args.modelo,
        "esfuerzo": args.esfuerzo, "verdad": q["verdad"], "valor": respuesta.get("valor"),
        "ganador_verdad": q.get("ganador", ""), "ganador": respuesta.get("ganador"),
        "desde": respuesta.get("desde"), "hasta": respuesta.get("hasta"), "unidad": respuesta.get("unidad", ""),
        "fuente": respuesta.get("fuente", ""), "segundos": segundos, "llamadas_mcp": len(llamadas),
        "descubrimientos_vacios": len(descubrimientos),
        "resultado": resultado, "error": " | ".join(problemas)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--modelo", default="gpt-6.1-sol")
    p.add_argument("--esfuerzo", default="low", choices=["low", "medium", "high", "xhigh"])
    p.add_argument("--modos", nargs="+", default=["memoria", "mcp"], choices=["memoria", "mcp"])
    p.add_argument("--experimento", default="base", choices=["base", "sin_abstencion"])
    p.add_argument("--preguntas", type=Path, default=AQUI / "preguntas.csv")
    p.add_argument("--ids", nargs="+", help="Diagnóstico; la entrega usa las diez preguntas.")
    p.add_argument("--paralelo", type=int, default=2)
    p.add_argument("--timeout", type=int, default=420)
    args = p.parse_args()
    with args.preguntas.open(encoding="utf-8", newline="") as archivo:
        preguntas = list(csv.DictReader(archivo))
    if args.ids:
        preguntas = [q for q in preguntas if q["id"] in args.ids]
    if not preguntas:
        raise SystemExit("No hay preguntas para evaluar.")
    servidor = configuracion_bcrp() if "mcp" in args.modos else None
    casos = [(q, modo) for q in preguntas for modo in args.modos]
    print(f"{len(casos)} llamadas independientes a OpenAI vía Codex; modelo {args.modelo}.", flush=True)
    resultados = []
    with ThreadPoolExecutor(max_workers=args.paralelo) as ex:
        futuros = [ex.submit(preguntar, q, modo, args, servidor) for q, modo in casos]
        for futuro in as_completed(futuros):
            resultados.append(futuro.result())
    orden = {q["id"]: i for i, q in enumerate(preguntas)}
    resultados.sort(key=lambda r: (orden[r["id"]], args.modos.index(r["modo"])))
    sufijo = "" if args.experimento == "base" else "_sin_abstencion"
    if args.ids:
        sufijo += "_diagnostico"
    carpeta_resultado = AQUI if not sufijo else AQUI / "evaluacion"
    carpeta_resultado.mkdir(exist_ok=True)
    with (carpeta_resultado / f"resultados{sufijo}.csv").open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(resultados[0]))
        escritor.writeheader(); escritor.writerows(resultados)
    meta = {"fecha_utc": datetime.now(timezone.utc).isoformat(), "modelo": args.modelo, "esfuerzo": args.esfuerzo,
        "experimento": args.experimento, "preguntas": len(preguntas), "llamadas": len(casos), "paralelo": args.paralelo,
        "codex_version": subprocess.run([shutil.which("codex"), "--version"], capture_output=True,
            text=True, encoding="utf-8").stdout.strip(),
        "aislamiento": "Sesiones efímeras en carpetas vacías, sin historial, shell, apps, plugins ni web; solo bcrp en modo mcp."}
    (AQUI / "evaluacion" / f"ejecucion{sufijo}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    for modo in args.modos:
        filas = [r for r in resultados if r["modo"] == modo]
        print(modo, {estado: sum(r["resultado"] == estado for r in filas)
            for estado in ["acierta", "se equivoca", "no sabe", "error tecnico", "respuesta invalida"]})
    if any(r["resultado"] == "error tecnico" for r in resultados):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
