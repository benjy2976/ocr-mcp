# 0009. La clave de acceso vale como token Bearer y el modo público entrega claves sin OAuth

- **Estado:** vigente
- **Fecha:** 2026-11-09
- **Decidió:** Walther Aguirre

## Contexto

La decisión 0002 hizo obligatorio OAuth 2.1 en toda petición MCP y descartó
los tokens estáticos en un encabezado. En el uso real eso dejó fuera a los
clientes que no hacen el flujo OAuth de MCP o que no tienen navegador: un
agente que llama por HTTP recibe `401` y no puede seguir, aunque el modo
público (decisión 0007) esté encendido, porque ese modo solo ofrecía la clave
dentro de la página de inicio de sesión de OAuth.

Además, detrás de un proxy (por ejemplo, un Ingress de Kubernetes) el servidor
veía a todos los clientes con la IP del proxy, y los límites por dirección
(intentos de inicio de sesión y claves públicas por día) se volvían uno solo
para todos.

## Decisión

1. **Toda petición MCP sigue exigiendo una credencial**, que puede ser:
   - un token OAuth, como hasta ahora; o
   - la propia clave de acceso, en `Authorization: Bearer ocrk_…`.

   La clave identifica al mismo usuario que su token OAuth: mismas cuotas,
   estadísticas y aislamiento de trabajos. No vence sola; borrarla en el panel
   la revoca al instante.
2. **OAuth sigue disponible** y es la forma recomendada para los clientes que
   lo soportan: el usuario no guarda la clave en la configuración y los tokens
   vencen solos. Los conectores web de los asistentes solo usan OAuth.
3. **Modo público sin OAuth.** Con el modo público encendido, `/public/key`
   entrega una clave pública: una página para el navegador y JSON para scripts
   y agentes (`POST /public/key`). La página de inicio de sesión de OAuth la
   sigue ofreciendo. Las dos vías comparten el límite diario por dirección; la
   cuota pública y el tope global rigen igual.
4. **IP real detrás de un proxy.** El servidor toma la IP del cliente de
   `X-Forwarded-For` solo si el proxy figura en `OCR_MCP_TRUSTED_PROXIES` (IPs,
   rangos CIDR o `*`). Si la URL pública usa `https` sin TLS propio y la
   variable está vacía, avisa al arrancar.

Reemplaza el punto 2 de la decisión 0002 («OAuth 2.1 obligatorio en toda
petición MCP») y su alternativa descartada de tokens estáticos, y amplía el
punto 2 de la 0006 y el modo público de la 0007.

## Alternativas descartadas

- **Un endpoint anónimo, sin credencial** (`/public/mcp`). Cualquier cliente
  entraría sin pasos, pero las cuotas serían por sesión (se reinician al
  reconectar), el usuario perdería sus trabajos al perder la sesión y la GPU
  quedaría abierta a cualquiera que conozca la URL.
- **OAuth con aprobación automática en modo público.** Quita la página de
  inicio de sesión, pero sigue exigiendo un cliente con OAuth: no resuelve a
  los agentes ni a los scripts.

## Consecuencias

- La clave queda guardada en la configuración del cliente, como un token
  personal de larga vida: quien la vea la usa hasta que el admin la borre. La
  documentación lo advierte y recomienda OAuth cuando el cliente lo soporta.
- La clave viaja en cada petición: fuera de `127.0.0.1` exige HTTPS, que ya era
  obligatorio.
- Publicado detrás de un proxy, hay que configurar `OCR_MCP_TRUSTED_PROXIES`
  para que los límites por dirección funcionen.

## Evidencia

Implementación: `src/ocr_mcp/modules/access/oauth.py` (`_key_as_token`),
`src/ocr_mcp/modules/access/public_keys.py`, `src/ocr_mcp/config.py`
(`OCR_MCP_TRUSTED_PROXIES`) y `src/ocr_mcp/__main__.py`. Pruebas:
`tests/modules/access/test_key_as_token.py`,
`tests/modules/access/test_public_keys.py`, `tests/test_config.py` y
`tests/test_cli.py`. Prueba manual el 2026-11-09, contra un `ocr-core` 0.7.0
real y el servidor en `127.0.0.1`: `curl -X POST /public/key` entrega la clave
en JSON; con ella, `curl` y el cliente MCP oficial abren la sesión sin OAuth, y
el flujo completo (enlace de subida, envío, espera y lectura del Markdown) con
un PDF sintético termina bien; una clave inventada o la falta de credencial
reciben `401`.
