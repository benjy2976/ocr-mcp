# 0008. TLS directo en el servidor para publicarlo en una red local

- **Estado:** vigente
- **Fecha:** 2026-11-06
- **Decidió:** Walther Aguirre

## Contexto

La decisión 0002 prevé publicar el servidor detrás de un proxy inverso con
TLS. Para una red local (una oficina, un laboratorio o una casa) eso agrega una
pieza más que instalar y operar. OAuth y el SDK de MCP exigen HTTPS en
cualquier dirección que no sea `127.0.0.1`, `localhost` o `[::1]`.

## Decisión

1. El servidor puede servir HTTPS por sí mismo: con `OCR_MCP_TLS_CERT` y
   `OCR_MCP_TLS_KEY`, `ocr-mcp serve` arranca uvicorn con ese certificado. Las
   dos variables van juntas, deben apuntar a archivos existentes y exigen que
   `OCR_MCP_PUBLIC_URL` use `https`.
2. Sin esas variables, todo sigue como en la decisión 0002: HTTP en
   `127.0.0.1`, o un proxy con TLS delante para publicarlo.
3. El certificado lo elige quien publica: el de una CA de su organización o el
   de una CA local creada para la red. El procedimiento está en
   `docs/procedimientos.md`, "Publicar en una red local".

## Alternativas descartadas

- **Exigir siempre un proxy inverso.** Es lo adecuado en internet, pero en una
  red local es una pieza más sin beneficio proporcional.
- **Permitir HTTP en la red local.** OAuth y el SDK lo rechazan, y los tokens y
  las claves viajarían en claro por la red.

## Consecuencias

- Cada máquina cliente tiene que confiar en la CA del certificado. Los clientes
  basados en Node.js, como Claude Code, la toman de `NODE_EXTRA_CA_CERTS`.
- Detrás de un reenvío de puertos (por ejemplo, el de Windows hacia WSL2), el
  servidor ve la dirección del reenvío y no la del cliente, así que el límite de
  intentos por dirección se vuelve compartido entre todos los clientes.
- Los conectores de Claude Desktop y claude.ai siguen sin poder usarlo: se
  conectan desde la nube del proveedor.

## Evidencia

Implementación en `src/ocr_mcp/config.py` y `src/ocr_mcp/__main__.py`; prueba
`test_tls_needs_both_files_and_an_https_public_url`. Prueba manual el
2026-11-06: con una CA local de prueba, un cliente que confía en ella obtiene
`/health` y metadatos con `issuer` en `https`; uno que no confía es rechazado y
el HTTP plano deja de responder en ese puerto.
