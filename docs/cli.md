# Contrato CLI

Fuente normativa del comando `ocr-mcp`, que instala `pyproject.toml`
(`[project.scripts]`) y vive en `src/ocr_mcp/__main__.py`. También se puede
ejecutar como `python -m ocr_mcp`.

## Convenciones transversales

- Los mensajes de error van a la salida de errores, en español y con el prefijo
  `ocr-mcp:`; nunca incluyen secretos.
- Código `0`: éxito. Código `2`: configuración o entrada inválidas.

## Índice de comandos

| Comando | Propósito | Efectos |
| --- | --- | --- |
| `ocr-mcp serve` (o `ocr-mcp`) | Arranca el servidor | Abre el puerto y crea o migra la base en `OCR_MCP_DATA_DIR` |
| `ocr-mcp hash-password` | Genera el hash de la contraseña del admin | Solo escribe el hash en la salida |

## `ocr-mcp serve`

### Sintaxis

```bash
ocr-mcp serve [--env-file RUTA]
```

| Nombre | Requerido | Default | Descripción |
| --- | --- | --- | --- |
| `--env-file` | No | — | Archivo `KEY=VALOR` que se carga antes de leer el entorno. No pisa variables ya definidas; acepta comentarios con `#` y comillas alrededor del valor |

Lee la configuración de `docs/entorno.md`, aplica las migraciones pendientes y
sirve en `OCR_MCP_HOST:OCR_MCP_PORT` con uvicorn (`--proxy-headers`, para
conocer la dirección real del cliente detrás de un proxy). Con
`OCR_MCP_TLS_CERT` y `OCR_MCP_TLS_KEY` sirve HTTPS directamente (decisión 0008).

| Código | Significado | Acción |
| --- | --- | --- |
| `0` | El servidor se detuvo normalmente | — |
| `2` | Falta una variable, un valor es inseguro o no se pudo leer `--env-file` | Corregir según el mensaje |

## `ocr-mcp hash-password`

Pide la contraseña dos veces sin mostrarla y escribe en la salida estándar el
hash para `OCR_MCP_ADMIN_PASSWORD_HASH` (scrypt con sal). La contraseña
necesita al menos 12 caracteres.

```bash
ocr-mcp hash-password
# Contraseña del admin: ••••••••••••
# Repítela: ••••••••••••
# scrypt$16384$8$1$…
```

| Código | Significado |
| --- | --- |
| `0` | Hash escrito |
| `2` | Contraseña corta o las dos no coinciden |

## Pruebas que respaldan el contrato

`tests/test_cli.py`.
