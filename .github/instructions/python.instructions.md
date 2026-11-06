---
applyTo: "src/**/*.py,tests/**/*.py,pyproject.toml"
---

# Instrucciones de la capa Python

Aplicar primero `AGENTS.md`. Este archivo contiene solo las reglas propias de la
capa; las transversales están en `docs/convenciones.md` y las de cada módulo en
su `context.md`.

## Alcance y límites

- Ruta principal: `src/ocr_mcp/`.
- Responsabilidad: el servicio completo (servidor MCP, OAuth, enlaces, panel y
  cliente del core). No hay otra capa.
- Límites: `app.py` compone; `modules/<módulo>/` contiene una capacidad;
  `shared/` no depende de ningún módulo; `config.py` es lo único que lee el
  entorno.

## Reglas específicas

- Python 3.11 o posterior, `from __future__ import annotations` y tipos en todas
  las firmas.
- El SDK es `mcp` 2.x (`mcp.server.mcpserver.MCPServer`). Antes de usar una API
  nueva del SDK, confirmarla en la versión instalada: entre versiones mayores
  cambian nombres (por ejemplo, `FastMCP` pasó a `MCPServer` y
  `structuredContent` a `structured_content`).
- Las herramientas lanzan `ToolError` con mensajes en español y nunca exponen
  secretos ni detalles internos. El usuario sale de
  `get_access_token().subject`.
- La base es SQLite de la biblioteca estándar: transacciones cortas con
  `Database.transaction()`, consultas con parámetros y cambios de esquema solo
  por migraciones nuevas en `src/ocr_mcp/migrations/`.
- Las rutas propias usan Starlette (`Route`) y se registran en `app.py` con
  `custom_route`; no pasan por OAuth, así que cada una se protege sola (secreto
  del enlace o sesión del admin).
- Las plantillas HTML viven en `templates/` del módulo, heredan de
  `src/ocr_mcp/shared/templates/base.html` y se renderizan con
  `shared.web.render`, que escapa el HTML y evita la caché.
- Las pruebas usan el core simulado (`tests/fakes/core.py`) y
  `httpx.ASGITransport`; las asíncronas llevan `pytestmark = pytest.mark.anyio`.
  Para invocar una herramienta con un usuario: `tests.conftest.as_user` y
  `app.state.mcp.call_tool`.

## Preflight adicional

- Identificar módulos y contratos afectados y leer sus `context.md`.
- Si cambia una ruta, revisar `docs/api.md`; si cambia el esquema,
  `docs/modelo-datos.md`; si cambia el comando, `docs/cli.md`.

## Validaciones de cierre

- Ejecutar: `.venv/bin/pytest` y `.venv/bin/ruff check . && .venv/bin/ruff format --check src tests`.
- Si un comando no puede ejecutarse, informar causa, riesgo y alternativa; no
  marcarlo como superado.
