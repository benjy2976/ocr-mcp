# Integración con los clientes más habituales

> **Verificación por cliente.** Probado de punta a punta con el cliente MCP
> oficial de Python (OAuth y clave como token) y con `curl` (clave como token).
> Los ejemplos de Claude Code, Codex, VS Code y Cursor siguen su documentación
> y todavía no se comprobaron uno por uno. El panel `/admin` y la página
> `/public/key` los muestran con la URL del servidor ya puesta.

Hay dos formas de conectarse, con la misma clave de acceso (decisiones 0006 y
0009):

| Forma | Configuración del cliente | Cuándo usarla |
| --- | --- | --- |
| **Con inicio de sesión (OAuth)** | Solo la URL. En la primera conexión el cliente abre el navegador y la página pide la clave; después renueva sus tokens solo | Clientes con OAuth de MCP: es la recomendada, porque la clave no queda guardada en la configuración |
| **Con la clave como token** | La URL y el encabezado `Authorization: Bearer <clave>` | Clientes sin OAuth, agentes, scripts y entornos sin navegador |

La clave la entrega el admin desde `/admin`, o la obtiene cada uno en
`/public/key` si el modo público está encendido. Con la clave como token, la
clave queda guardada en la configuración del cliente: se trata como una
contraseña, y si se filtra, el admin la borra y deja de valer al instante.

En los ejemplos, `<URL>` es la URL pública del servidor más `/mcp`:

- en la máquina propia: `http://127.0.0.1:18040/mcp`;
- en línea: `https://ocr.ejemplo.org/mcp`.

## Obtener una clave pública

Con el modo público encendido, desde el navegador en `<URL pública>/public/key`,
o desde una terminal:

```bash
curl -X POST https://ocr.ejemplo.org/public/key
```

La respuesta trae la clave (`key`), la URL de `/mcp`, el encabezado listo para
copiar y la cuota. Cada dirección puede obtener un número limitado de claves por
día.

## Claude Code

Con inicio de sesión:

```bash
claude mcp add --transport http ocr <URL>
```

Dentro de Claude Code, `/mcp` muestra el servidor y abre el navegador para
iniciar sesión. Con `--scope project`, la configuración queda en el `.mcp.json`
del proyecto y la comparte el equipo; cada persona inicia sesión con su clave.

Con la clave como token:

```bash
claude mcp add --transport http ocr <URL> --header "Authorization: Bearer <clave>"
```

## Codex

Codex toma el token de una variable de entorno, que tiene que existir al
abrirlo (por ejemplo, `OCR_MCP_KEY` con la clave):

```bash
codex mcp add ocr --url <URL> --bearer-token-env-var OCR_MCP_KEY
```

O en `~/.codex/config.toml`:

```toml
[mcp_servers.ocr]
url = "<URL>"
bearer_token_env_var = "OCR_MCP_KEY"
```

Dentro de Codex, `/mcp` muestra los servidores activos.

## VS Code

En `.vscode/mcp.json` del proyecto, o en la configuración de usuario. Con
inicio de sesión basta la URL; VS Code pide autorizar y abre el navegador:

```json
{
  "servers": {
    "ocr": {
      "type": "http",
      "url": "<URL>"
    }
  }
}
```

Con la clave como token, VS Code la pide una vez y la guarda cifrada:

```json
{
  "servers": {
    "ocr": {
      "type": "http",
      "url": "<URL>",
      "headers": { "Authorization": "Bearer ${input:ocr-clave}" }
    }
  },
  "inputs": [
    { "type": "promptString", "id": "ocr-clave", "description": "Clave de ocr-mcp", "password": true }
  ]
}
```

## Cursor

En `~/.cursor/mcp.json`, o en `.cursor/mcp.json` del proyecto. Con inicio de
sesión basta la URL; con la clave como token, se agrega `headers`:

```json
{
  "mcpServers": {
    "ocr": {
      "url": "<URL>",
      "headers": { "Authorization": "Bearer <clave>" }
    }
  }
}
```

## Claude Desktop y claude.ai

Se agrega como conector personalizado, desde la configuración de conectores,
con la URL del servidor e inicio de sesión. Estos conectores se conectan desde
la nube del proveedor, así que **exigen una URL pública con HTTPS**: no
funcionan con `127.0.0.1`.

## Otros clientes y scripts

Sirve cualquier cliente MCP que soporte el transporte Streamable HTTP, con
OAuth o con un encabezado fijo. Para comprobar una clave sin cliente MCP:

```bash
curl -H "Authorization: Bearer <clave>" \
  -H "Accept: application/json, text/event-stream" \
  -H "Content-Type: application/json" <URL> \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"prueba","version":"1"}}}'
```

Una respuesta `200` con `ocr-mcp` en el cuerpo confirma la clave; `401`
indica que no es válida o fue borrada.

## Uso desde el agente

1. `ocr_upload_link` entrega un enlace de subida. Un agente con terminal sube
   el PDF con `curl -T documento.pdf <enlace>`; si no tiene terminal, la
   persona abre el enlace y elige el archivo.
2. `ocr_submit` crea el trabajo y devuelve su `job_id`.
3. `ocr_status` espera hasta 50 segundos por llamada a que termine.
4. `ocr_read_markdown` lee el resultado por tramos de páginas, y
   `ocr_artifact_links` entrega enlaces para descargar el PDF buscable, el texto
   JSONL o el Markdown.
