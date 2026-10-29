"""Audita los registros locales y vuelve a calcular las calificaciones, sin llamar al modelo.

El CLI mantiene utilidades para listar recursos aun sin servidores registrados.
Solo se excluyen del conteo de consultas las respuestas exactamente vacías de esas listas.
"""
import csv
import hashlib
import json
from pathlib import Path

from evaluar import AQUI, calificar, descubrimiento_vacio


def main():
    with (AQUI / "preguntas.csv").open(encoding="utf-8", newline="") as f:
        preguntas = {q["id"]: q for q in csv.DictReader(f)}
    for experimento, nombre in [("base", "resultados.csv"), ("sin_abstencion", "resultados_sin_abstencion.csv")]:
        archivo = AQUI / nombre
        with archivo.open(encoding="utf-8", newline="") as f:
            filas = list(csv.DictReader(f))
        for fila in filas:
            caso = f"{fila['modo']}_{fila['id']}"
            evidencia = AQUI / "evidencia_evaluacion" / experimento / f"{caso}.json"
            r = json.loads(evidencia.read_text(encoding="utf-8"))
            raw = (AQUI / "salidas" / "evaluacion" / experimento / f"{caso}.jsonl").read_bytes()
            llamadas, vacios = [], []
            for linea in raw.decode("utf-8").splitlines():
                try:
                    e = json.loads(linea)
                except ValueError:
                    continue
                item = e.get("item", {})
                if e.get("type") == "item.completed" and item.get("type") == "mcp_tool_call":
                    registro = {k: item.get(k) for k in ("server", "tool", "arguments", "status")}
                    if descubrimiento_vacio(item):
                        registro["resultado"] = json.loads(item["result"]["content"][0]["text"])
                        vacios.append(registro)
                    else:
                        llamadas.append(registro)
            # Corregimos únicamente la clasificación de listas vacías del primer lote.
            problemas = [p for p in r["problemas"] if p != "El modo memoria intentó utilizar un MCP."]
            if fila["modo"] == "memoria" and llamadas:
                problemas.append("El modo memoria intentó utilizar un MCP.")
            r.update(llamadas_mcp=llamadas, descubrimientos_sin_datos=vacios,
                     sha256_eventos=hashlib.sha256(raw).hexdigest(), problemas=problemas,
                     resultado="error tecnico" if problemas else calificar(r["respuesta"], preguntas[fila["id"]]))
            evidencia.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
            fila.update(llamadas_mcp=len(llamadas), descubrimientos_vacios=len(vacios),
                        resultado=r["resultado"], error=" | ".join(problemas))
        with archivo.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(filas[0])); w.writeheader(); w.writerows(filas)
        for modo in dict.fromkeys(r["modo"] for r in filas):
            seleccion = [r for r in filas if r["modo"] == modo]
            print(experimento, modo, {x: sum(r["resultado"] == x for r in seleccion)
                  for x in ["acierta", "se equivoca", "no sabe", "error tecnico"]})


if __name__ == "__main__":
    main()
