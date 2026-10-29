# Conectar el ejercicio a Codex

La [presentación de clase](https://claude.ai/artifact/B9W8izJCRr6qsTLwbMXqcT) pide conectar
BCRP y Fetch. En nuestra adaptación los registramos en Codex. La [documentación oficial](https://learn.chatgpt.com/docs/extend/mcp)
explica la configuración local y el reinicio de los servidores.

## Qué aporta cada conexión

- **bcrp:** nuestro programa, con las cuatro herramientas, el recurso y el prompt.
- **fetch:** el servidor de referencia del proyecto Model Context Protocol para leer páginas web.

## Repetir la instalación en otra computadora

Con Python, uv y Codex instalados, abre la carpeta del proyecto y ejecuta `uv sync --frozen`.
Después registra los servidores, sustituyendo la ruta por la carpeta de tu copia:

```powershell
codex mcp add bcrp --env PYTHONIOENCODING=utf-8 -- uv --directory "C:/ruta/a/mcp-bcrp" run --frozen server.py
codex mcp add fetch --env PYTHONIOENCODING=utf-8 -- uvx mcp-server-fetch==2026.10.28
codex mcp list
```

`codex-mcp.example.toml` muestra la configuración equivalente. No copies sobre la configuración
personal completa: conserva las otras conexiones y preferencias que ya tengas.
En este equipo registramos rutas absolutas al Python del proyecto y al uv local, de modo que
el arranque no dependa de haber agregado uv al PATH. Esas rutas personales no se publican.

`.mcp.json` conserva la configuración del recorrido original de Claude, para usar desde la
carpeta del proyecto con uv y uvx disponibles. Codex utiliza su configuración TOML.

## Comprobar la conexión

```powershell
uv run --frozen verificar_conexion.py
```

La comprobación inicia procesos nuevos por stdio usando la configuración de Codex:
lista las herramientas, lee la ficha del oro, obtiene el prompt, consulta un precio y usa
Fetch para leer la documentación de FastMCP. Guarda el resultado en
`salidas/conexion_verificada.json`, fuera de Git. No necesita una clave de OpenAI ni invoca un modelo.

## Activar las herramientas en la aplicación

En Configuración → Servidores MCP, busca `bcrp` y `fetch` y reinicia la conexión.
Después, en el chat, comprueba con `/mcp` qué servidores están disponibles, cuando ese menú
esté admitido por el cliente. La comprobación final será que el asistente llame a una
herramienta del servidor desde el chat. Haber guardado la configuración o haber ejecutado
el cliente de prueba no confirma por sí solo ese último paso.

Un chat alojado en ChatGPT web usa otra integración mediante plugins; no lee automáticamente
la configuración local de Codex. Comprueba siempre en qué cliente estás usando el ejercicio.
