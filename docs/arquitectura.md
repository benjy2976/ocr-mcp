# Arquitectura

Describe el sistema implementado según las decisiones 0001 a 0007. Un cambio
de componentes o del flujo global se actualiza aquí en el mismo cambio.

## Resumen

`ocr-mcp` es un servicio HTTP que habla MCP con los agentes de IA y HTTP con
`ocr-core`. Recibe PDF por enlace, crea trabajos en el core, entrega el
Markdown por páginas y los artefactos por enlace. Controla quién lo usa (una
clave por usuario, con OAuth 2.1 o como token directo) y cuánto (cuotas), y
ofrece un panel mínimo de admin. No hace OCR y no conoce el almacenamiento de ningún otro sistema.

## Stack

| Pieza | Elección | Por qué |
| --- | --- | --- |
| Lenguaje | Python 3.11 o posterior | El SDK oficial de MCP y el resto del ecosistema del core |
| Servidor MCP y OAuth | SDK oficial `mcp` 2.x (`MCPServer`, Streamable HTTP y servidor de autorización incluido) | Sigue la especificación sin reimplementarla |
| HTTP | Starlette y uvicorn, que trae el SDK | Rutas propias junto a las del protocolo |
| Cliente del core | `httpx` | Subida y descarga por partes, asíncronas |
| PDF | `pypdf` | Validar el archivo y contar páginas antes de subir |
| Plantillas del panel y del inicio de sesión | `jinja2` | Escape automático del HTML |
| Estado | SQLite de la biblioteca estándar | Un solo archivo, sin servidor ni ORM |

Las versiones mínimas están en `pyproject.toml`; `mcp` se limita a `<3`
porque la 3.0 cambiará valores por defecto de la validación de tokens.

## Componentes y fronteras

```mermaid
flowchart LR
    agente["Agente de IA<br/>(Claude Code, VS Code, Cursor…)"]
    persona["Persona<br/>(navegador)"]
    admin["Admin<br/>(navegador)"]
    subgraph mcp["ocr-mcp"]
        access["access<br/>OAuth y claves"]
        jobs["jobs<br/>herramientas MCP"]
        files["files<br/>enlaces"]
        quotas["quotas<br/>cuotas y uso"]
        panel["admin<br/>panel /admin"]
        core["core<br/>cliente de ocr-core"]
        db[("SQLite")]
    end
    ocrcore["ocr-core"]

    agente -- "MCP + token OAuth o clave" --> jobs
    agente -- "inicio de sesión" --> access
    persona -- "subida o descarga" --> files
    admin --> panel
    jobs --> quotas
    jobs --> files
    jobs --> core
    files --> core
    core -- "HTTP + token del core" --> ocrcore
    access --> db
    jobs --> db
    files --> db
    quotas --> db
    panel --> access
    panel --> quotas
    panel --> jobs
```

| Componente | Responsabilidad | Frontera |
| --- | --- | --- |
| `access` | Servidor de autorización incluido, claves de acceso y página de inicio de sesión | Única fuente de identidad del usuario |
| `jobs` | Herramientas MCP, dueño de cada trabajo y Markdown por páginas | Habla con el core solo a través de `core` |
| `files` | Enlaces de subida y descarga, y URL de prefijos permitidos | Nunca lee ni escribe rutas del disco en nombre de un usuario |
| `quotas` | Cuotas por clave, modo público y estadísticas | Solo conteos, nunca nombres ni contenido |
| `admin` | Panel `/admin`: claves, cuotas, uso, modo público y ejemplos | Credenciales del admin desde el entorno |
| `core` | Cliente de `ocr-core`: token, `/meta`, subida, estado, artefactos y borrado | El único que conoce la API del core |

## Capas y dirección de dependencias

- `app.py` compone el servicio y es el único que conoce a todos los módulos.
- Un módulo usa a otro solo por su interfaz pública (`__init__.py` del
  módulo), nunca por sus archivos internos.
- `shared/` (base de datos, seguridad y utilidades web) no depende de ningún
  módulo.
- `config.py` lee y valida el entorno al arrancar; los módulos reciben su
  configuración, no leen variables por su cuenta.

## Mapa de carpetas

```text
src/ocr_mcp/
├── __main__.py      comando ocr-mcp (serve, hash-password)
├── app.py           composición del servicio
├── config.py        entorno validado al arrancar
├── shared/          db.py, security.py, web.py y templates/ (base y mensajes)
├── migrations/      SQL numerado
└── modules/         cada uno con su context.md
    ├── core/        client.py
    ├── quotas/      policy.py, public.py
    ├── access/      keys.py, oauth.py, login.py, templates/
    ├── files/       uploads.py, downloads.py, fetch.py, routes.py, templates/
    ├── jobs/        tools.py, ledger.py, markdown.py, rules.py
    └── admin/       session.py, routes.py, templates/
tests/               mismo orden que modules/, más fakes/core.py (el core simulado)
```

## Flujo global

```mermaid
sequenceDiagram
    participant A as Agente
    participant M as ocr-mcp
    participant C as ocr-core
    A->>M: ocr_upload_link
    M-->>A: enlace de un solo uso
    A->>M: PUT del PDF (o formulario en el navegador)
    A->>M: ocr_submit
    M->>M: valida PDF, cuenta páginas y comprueba la cuota
    M->>C: POST /jobs/upload (por partes, con token del core)
    C-->>M: job_id
    M-->>A: job_id, estado y páginas
    A->>M: ocr_status (espera hasta 50 s)
    M->>C: GET /jobs/{id}
    A->>M: ocr_read_markdown / ocr_artifact_links
    M->>C: GET /jobs/{id}/artifacts/{nombre}
    M-->>A: Markdown por páginas o enlaces de descarga
```

## Decisiones transversales

Las restricciones que gobiernan esta arquitectura están en
`docs/decisiones/README.md`: alcance (0001), transporte y OAuth (0002),
archivos (0003), trabajo asíncrono (0004), límites (0005), acceso y panel
(0006), cuotas (0007), TLS en una red local (0008) y clave como token con modo
público sin OAuth (0009).
