"""Regenera informe.md y grafico.png desde los resultados guardados, sin llamar al modelo."""
import csv
import json
from pathlib import Path
from statistics import fmean

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

AQUI = Path(__file__).parent


def leer_csv(nombre):
    with (AQUI / nombre).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def resumen(filas):
    return {"n": len(filas), "aciertos": sum(f["resultado"] == "acierta" for f in filas),
            "errores": sum(f["resultado"] == "se equivoca" for f in filas),
            "no_sabe": sum(f["resultado"] == "no sabe" for f in filas),
            "tecnicos": sum(f["resultado"] in {"error tecnico", "respuesta invalida"} for f in filas),
            "segundos": fmean(float(f["segundos"]) for f in filas)}


def numero(valor, decimales=2):
    return f"{float(valor):,.{decimales}f}" if valor not in (None, "") else "No sabe"


def main():
    base, extra = leer_csv("resultados.csv"), leer_csv("resultados_sin_abstencion.csv")
    preguntas = leer_csv("preguntas.csv")
    assert len(preguntas) == 10 and len(base) == 20 and len(extra) == 10
    assert not any(f["resultado"] in {"error tecnico", "respuesta invalida"} for f in base + extra)
    grupos = [("Memoria · base", [f for f in base if f["modo"] == "memoria"]),
              ("MCP · base", [f for f in base if f["modo"] == "mcp"]),
              ("Memoria · sin instrucción de abstenerse", extra)]
    estadisticas = [(nombre, resumen(filas)) for nombre, filas in grupos]
    metales = json.loads((AQUI / "verificacion_web/comparaciones.json").read_text(encoding="utf-8"))

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.spines.left": False, "figure.facecolor": "#ffffff"})
    fig = plt.figure(figsize=(13, 7.5), layout="constrained")
    cuadricula = fig.add_gridspec(2, 2, width_ratios=[1.25, 1])
    ax = fig.add_subplot(cuadricula[:, 0])
    etiquetas = ["Memoria\nBase", "MCP\nBase", "Memoria\nSin instrucción de abstenerse"]
    for i, (_, s) in enumerate(estadisticas):
        izquierda = 0
        for clave, color in [("aciertos", "#1565C0"), ("errores", "#D97706"), ("no_sabe", "#CBD5E1")]:
            n = s[clave]
            ax.barh(i, n, left=izquierda, color=color, height=.58)
            if n:
                ax.text(izquierda + n/2, i, str(n), ha="center", va="center",
                        weight="bold", color="white" if clave != "no_sabe" else "#243247", fontsize=13)
            izquierda += n
    ax.set(yticks=range(3), yticklabels=etiquetas, xlim=(0, 10), xticks=range(0, 11, 2),
           xlabel="Preguntas (10 por condición)", title="A. Respuestas frente a la referencia")
    ax.invert_yaxis()
    ax.legend(handles=[Patch(color="#1565C0", label="Acierto"), Patch(color="#D97706", label="Discrepancia"),
                       Patch(color="#CBD5E1", label="No sabe")], loc="lower left", bbox_to_anchor=(0, -.18), ncol=3,
              frameon=False)
    colores = {"cobre": "#B87333", "plata": "#8A99A6", "oro": "#D4A017"}
    for n, comparacion in enumerate(metales):
        a = fig.add_subplot(cuadricula[n, 1])
        orden = ["cobre", "plata", "oro"]
        valores = [comparacion["variaciones_pct"][m] for m in orden]
        a.barh(orden, valores, color=[colores[m] for m in orden], height=.55)
        a.axvline(0, color="#94A3B8", linewidth=.8)
        for j, valor in enumerate(valores):
            a.text(valor + (2 if valor >= 0 else -2), j, f"{valor:+.2f} %",
                   va="center", ha="left" if valor >= 0 else "right", weight="bold", fontsize=10)
        a.set_xlim((-40, 40) if n == 0 else (0, 280))
        a.invert_yaxis()
        a.set_xlabel("Variación acumulada (%)")
        a.set_title(("B. En 2026: 31 dic 2025 → 27 oct 2026" if n == 0 else
                     "C. Diez años: 27 oct 2016 → 27 oct 2026"), loc="left", fontsize=10, weight="bold")
    fig.suptitle("MCP del BCRP: evaluación y comparaciones de metales", fontsize=16, weight="bold")
    fig.supxlabel("OpenAI gpt-6.1-sol · esfuerzo low · una respuesta por pregunta y condición.\n"
                  "Paneles B–C: cálculos independientes con valores visibles en las tablas web del BCRP.", fontsize=9)
    fig.savefig(AQUI / "grafico.png", dpi=220, bbox_inches="tight")
    fig.savefig(AQUI / "grafico.svg", bbox_inches="tight")
    svg = AQUI / "grafico.svg"
    svg.write_text("\n".join(linea.rstrip() for linea in svg.read_text(encoding="utf-8").splitlines()) + "\n",
                   encoding="utf-8")
    plt.close(fig)

    m, c, e = [s for _, s in estadisticas]
    discrepancias = [r["id"] for r in base if r["modo"] == "mcp" and r["resultado"] == "se equivoca"]
    nota_discrepancias = (
        "La discrepancia del MCP corresponde a una pregunta ambigua del cobre: consultó la cotización LME "
        "en lugar del precio de exportación que esperaba la referencia del curso. Se conserva esa calificación, "
        "sin sustituirla por la consulta aclarada." if discrepancias == ["cobre_ago26"] else
        "No se registraron discrepancias del MCP frente a la referencia." if not discrepancias else
        "Discrepancias registradas del MCP: " + ", ".join(discrepancias) + ". Consulte las evidencias por respuesta.")
    cambios_extra = [q["id"] for q in preguntas if
        next(r["resultado"] for r in base if r["id"] == q["id"] and r["modo"] == "memoria") !=
        next(r["resultado"] for r in extra if r["id"] == q["id"])]
    lineas = ["# ¿Ayuda un MCP a responder preguntas económicas con cifras verificables?", "",
        "Evaluación del proyecto de clase adaptado de Claude Code a OpenAI mediante Codex. "
        "Referencia principal: [presentación de clase](https://claude.ai/artifact/B9W8izJCRr6qsTLwbMXqcT). "
        "El [repositorio del curso](https://github.com/d2cml-ai/Data-Science-Python/tree/main/sessions/04-mcp-claude-code) "
        "aportó el servidor inicial, las ocho pruebas y ocho preguntas.", "",
        "## Resultado principal", "",
        f"Con el mismo modelo y las mismas diez preguntas, memoria acertó **{m['aciertos']}/10** y el MCP "
        f"acertó **{c['aciertos']}/10** según la referencia fijada. " + nota_discrepancias, "",
        "| Condición | Aciertos | Discrepancias | No sabe | Fallos técnicos | Segundos medios |",
        "|---|---:|---:|---:|---:|---:|"]
    for nombre, s in estadisticas:
        lineas.append(f"| {nombre} | {s['aciertos']}/10 | {s['errores']} | {s['no_sabe']} | {s['tecnicos']} | {s['segundos']:.2f} |")
    lineas += ["", "![Resultados y variaciones de los metales](grafico.png)", "",
        "## Cómo se hizo la comparación", "",
        "- Modelo: **gpt-6.1-sol**, el configurado en este equipo; esfuerzo **low** en todas las llamadas.",
        "- Las ocho preguntas originales se conservaron y se agregaron dos comparaciones propuestas por el estudiante.",
        "- Cada pregunta abrió una sesión efímera en una carpeta temporal vacía. No se adjuntaron esta conversación, "
        "el código, las referencias ni los archivos de resultados al contexto del modelo.",
        "- Se ignoró la configuración personal en cada ejecución y se desactivaron shell, apps, plugins, subagentes "
        "y búsqueda web. Solo el brazo MCP recibió el servidor bcrp. Las respuestas esperadas nunca se enviaron al modelo.",
        "- El CLI conserva utilidades administrativas para listar recursos. Algunas sesiones sin MCP las usaron y "
        "recibieron listas exactamente vacías; se registran como descubrimientos sin datos, no como consultas a fuentes. "
        "La auditoría comprueba su contenido y rechaza cualquier acceso a fuentes no permitido.",
        "- La condición base pidió responder null si no había certeza. En ambos brazos se utilizó la misma instrucción "
        "y el mismo esquema de respuesta. Una abstención es distinta de un fallo técnico.",
        "- Se exigió una consulta de cifras al MCP para considerar válida una respuesta numérica de ese brazo. "
        "Las comparaciones debían acertar el metal, el porcentaje y las dos fechas.",
        "- Los tiempos incluyen arranque del CLI y del MCP, solicitudes y generación de la respuesta. "
        "Las consultas pueden reutilizar la caché local; no son una medida de latencia de red en frío.",
        "- Corrida base: 20 llamadas. Experimento adicional: 10 llamadas de memoria. Diagnóstico aclarado: 1 llamada MCP. "
        "Las llamadas de preparación no forman parte de los resultados.",
        "- Resultados completos: [base](resultados.csv), [experimento](resultados_sin_abstencion.csv), "
        "[metadatos](ejecucion.json) y [evidencias por respuesta](evidencia_evaluacion/). "
        "Los registros brutos permanecen en salidas/, excluida de Git.", "",
        "## Las dos preguntas propias", ""]
    for q in preguntas[8:]:
        comp = next(x for x in metales if x["id"] == q["id"])
        lineas += [f"### {q['id']}", "", q["pregunta"], "",
            f"**Referencia:** {comp['ganador'].capitalize()}, **{comp['variacion_ganador_pct']:.2f} %** acumulado.", "",
            "| Metal | Variación acumulada |", "|---|---:|"]
        for metal, valor in comp["variaciones_pct"].items():
            lineas.append(f"| {metal.capitalize()} | {valor:+.2f} % |")
        lineas += ["", "Se compara el valor final con el inicial: `(final / inicial - 1) × 100`. "
            "Es crecimiento acumulado entre fechas, no promedio de precios ni tasa anualizada.", ""]
    lineas += ["## Verificación independiente en la web del BCRP", "",
        "Las referencias se comprobaron en tablas **HTML públicas del BCRP**, sin importar server.py ni llamar "
        "al MCP. Se conservaron los valores visibles, enlaces, fecha de consulta y SHA-256 de cada página en "
        "[fuentes.json](verificacion_web/fuentes.json), [referencias originales](referencias_verificadas.csv) "
        "y [precios de metales](metales_verificados.csv). El programa [verificar_referencias.py](verificar_referencias.py) "
        "permite repetir la comprobación. Las copias HTML quedan locales, fuera de Git.", "",
        "Dos comprobaciones concretas de las nuevas preguntas:", "",
        "| Serie | Fecha | Valor visible | Unidad | Tabla web |", "|---|---|---:|---|---|"]
    precios = leer_csv("metales_verificados.csv")
    for codigo, fecha, unidad in [("PD04701XD", "2026-10-27", "centavos de US$/libra"),
                                 ("PD04704XD", "2016-10-27", "US$/onza troy")]:
        f = next(x for x in precios if x["codigo"] == codigo and x["fecha"] == fecha)
        lineas.append(f"| {codigo} | {fecha} | {numero(f['valor_visible_tabla'])} | {unidad} | [BCRP]({f['fuente']}) |")
    lineas += ["", "Las tablas redondean los valores; por eso las tolerancias permiten diferencias de presentación. "
        "Las ocho cifras originales quedaron dentro de las tolerancias del curso. El PBI se muestra como 3,4 "
        "en la tabla anual; la coma es decimal. Para las dos comparaciones se usa una tolerancia de 0.05 puntos porcentuales.", "",
        "## Qué acertó y qué no", "",
        "| Pregunta | Referencia | Memoria base | MCP base |", "|---|---:|---|---|"]
    for q in preguntas:
        rm = next(r for r in base if r["id"] == q["id"] and r["modo"] == "memoria")
        rc = next(r for r in base if r["id"] == q["id"] and r["modo"] == "mcp")
        referencia = numero(q["verdad"], 4)
        if q.get("ganador"):
            referencia = q["ganador"] + ": " + numero(q["verdad"]) + " %"
        lineas.append(f"| {q['id']} | {referencia} | {numero(rm['valor'], 4)} ({rm['resultado']}) | "
                      f"{numero(rc['valor'], 4)} ({rc['resultado']}) |")
    lineas += ["", "### La discrepancia del cobre", "",
        "La pregunta original dice «precio promedio del cobre», sin especificar exportación o LME. "
        "El modelo eligió **PN01652XM**, cotización promedio LME, y devolvió **651.45** centavos de US$/libra. "
        "La referencia espera **PN38784BM**, precio de exportación, con **689.70**. Ambas son series oficiales.", "",
        "La [tabla alternativa LME](https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PN01652XM/html/2026-8/2026-8) "
        "muestra 651 redondeado; la herramienta conserva mayor precisión. La "
        "[tabla de exportación](https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PN38784BM/html/2026-8/2026-8) "
        "muestra 689.70. El fallo frente a la referencia no se debió a una cifra inventada, sino a la selección de "
        "un indicador distinto bajo una pregunta ambigua.", "",
        "Se hizo una única consulta diagnóstica cambiando la pregunta a «precio promedio de EXPORTACIÓN del cobre». "
        "Respondió **689.698759925968**, que sí coincide con la referencia. Está en "
        "[resultados_diagnostico.csv](resultados_diagnostico.csv) y tiene evidencia separada. "
        "No reemplaza la corrida base ni eleva su puntuación.", "",
        "## Experimento adicional: quitar la instrucción de abstenerse", "",
        f"Al retirar únicamente la frase que pide null si no sabe, memoria pasó de {m['aciertos']} a {e['aciertos']} "
        f"aciertos, con {e['no_sabe']} abstenciones y {e['errores']} errores numéricos. "
        f"Preguntas cuya calificación cambió: {', '.join(cambios_extra) or 'ninguna'}. "
        "La variación observada no permite atribuir una mejora general a quitar esa instrucción: "
        "también puede influir la variabilidad de generación. Este experimento se limitó a memoria, donde interesa "
        "observar la conducta sin fuentes externas.", "",
        "## Alcance y limitaciones", "",
        "Son diez preguntas elegidas para este ejercicio, con una ejecución por pregunta y condición. "
        "No se estima una precisión universal ni se comparan familias de modelos. Las cotizaciones son las publicadas "
        "por el BCRP, no precios bursátiles en tiempo real. Las referencias y las descargas tienen una fecha de corte "
        "y pueden cambiar por revisiones estadísticas. El uso de una caché debe considerarse al interpretar los tiempos.", "",
        "## Conclusión", "",
        f"El acceso al MCP elevó los aciertos de {m['aciertos']}/10 a {c['aciertos']}/10 en esta muestra. "
        "Permitió recuperar cifras recientes y hacer comparaciones con fuentes y fechas verificables. "
        "La conexión no elimina la necesidad de elegir bien el indicador: el caso del cobre muestra esa limitación. "
        "Un MCP resulta útil cuando se necesita consultar reiteradamente la misma fuente estructurada y repetir "
        "cálculos; aquí no se evaluó un brazo de búsqueda web, por lo que no se afirma que supere a la web.", "",
        "## Reproducir", "", "```powershell", "uv sync --frozen", "uv run --frozen pytest -q",
        "uv run --frozen verificar_referencias.py", "uv run --frozen evaluar.py",
        "uv run --frozen evaluar.py --experimento sin_abstencion --modos memoria",
        "uv run --frozen auditar_resultados.py", "uv run --frozen generar_informe.py", "```", "",
        "La configuración de Codex debe tener registrado bcrp; consulta [CONEXION.md](CONEXION.md). "
        "Para regenerar solo el informe y la figura con esta corrida basta el último comando; no consume nuevas llamadas al modelo.", ""]
    (AQUI / "informe.md").write_text("\n".join(lineas), encoding="utf-8")
    print(json.dumps({nombre: s for nombre, s in estadisticas}, ensure_ascii=True, indent=2))
    print("Informe y figuras generados.")


if __name__ == "__main__":
    main()
