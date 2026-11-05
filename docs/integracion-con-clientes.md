# Integración con los clientes más habituales

> **Previsto.** El servidor todavía no existe. Estos ejemplos se verifican con
> cada cliente al implementarlo, y el panel `/admin` los muestra con la URL del
> servidor ya puesta (decisión 0006).

En todos los clientes el procedimiento es el mismo, porque el acceso es por
OAuth 2.1 (decisión 0002):

1. El admin crea una clave de acceso para el usuario en `/admin` y se la entrega
   por un canal seguro.
2. El usuario agrega el servidor a su cliente con **solo la URL**, sin tokens en
   la configuración.
3. En la primera conexión, el cliente abre el navegador y la página pide la
   clave. Desde ahí, el cliente renueva sus tokens solo.

En los ejemplos, `<URL>` es la URL pública del servidor más `/mcp`:

- en la máquina propia: `http://127.0.0.1:18040/mcp`;
- en línea: `https://ocr.ejemplo.org/mcp`.

## Claude Code

```bash
claude mcp add --transport http ocr <URL>
```

Dentro de Claude Code, `/mcp` muestra el servidor y abre el navegador para
iniciar sesión. Con `--scope project`, la configuración queda en el `.mcp.json`
del proyecto y la comparte el equipo; cada persona inicia sesión con su clave.

## VS Code

En `.vscode/mcp.json` del proyecto, o en la configuración de usuario:

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

Al iniciar el servidor desde la vista de MCP, VS Code pide autorizar y abre el
navegador.

## Cursor

En `~/.cursor/mcp.json`, o en `.cursor/mcp.json` del proyecto:

```json
{
  "mcpServers": {
    "ocr": {
      "url": "<URL>"
    }
  }
}
```

## Claude Desktop y claude.ai

Se agrega como conector personalizado, desde la configuración de conectores,
con la URL del servidor. Estos conectores se conectan desde la nube del
proveedor, así que **exigen una URL pública con HTTPS**: no funcionan con
`127.0.0.1`.

## Otros clientes

Sirve cualquier cliente MCP que soporte el transporte Streamable HTTP y la
autorización OAuth de la especificación de MCP. Los que solo aceptan un token
fijo en un encabezado no pueden conectarse.

## Uso desde el agente

1. `ocr_upload_link` entrega un enlace de subida. Un agente con terminal sube
   el PDF con `curl -T documento.pdf <enlace>`; si no tiene terminal, la
   persona abre el enlace y elige el archivo.
2. `ocr_submit` crea el trabajo y devuelve su `job_id`.
3. `ocr_status` espera hasta 50 segundos por llamada a que termine.
4. `ocr_read_markdown` lee el resultado por tramos de páginas, y
   `ocr_artifact_links` entrega enlaces para descargar el PDF buscable, el texto
   JSONL o el Markdown.
