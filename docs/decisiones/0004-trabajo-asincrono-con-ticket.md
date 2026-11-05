# 0004. Trabajo asíncrono con el patrón del ticket

- **Estado:** aceptada, sin implementar
- **Fecha:** 2026-11-05
- **Decidió:** Walther Aguirre

> **Hoy:** el repo todavía no tiene código.

## Contexto

El OCR de un PDF escaneado tarda de segundos a decenas de minutos según sus
páginas. Los clientes MCP cortan una llamada a herramienta que tarda demasiado,
y un agente que consulta el estado sin pausa gasta turnos.

## Decisión

- `ocr_submit` toma un PDF ya subido por enlace, o una URL permitida
  (decisión 0003), comprueba la cuota (decisión 0007), crea el trabajo en el
  core y **responde enseguida**
  con su `job_id` (el ticket), su estado y el número de páginas.
- `ocr_status` acepta `wait_seconds` (de 0 a 50) y **espera del lado del
  servidor**, en tramos cortos, hasta que el trabajo termina o se agota el
  tiempo. Envía notificaciones de progreso donde el cliente las muestre.
- La `idempotency_key` del core es el SHA-256 del archivo más los artefactos
  pedidos y el usuario (decisión 0006). Reenviar el mismo PDF con el mismo
  pedido no repite el OCR ni consume cuota de nuevo.
- La primitiva de tareas largas de MCP (*tasks*, experimental) se adopta solo
  cuando los clientes que se usen la soporten; hasta entonces rige el ticket.

## Alternativas descartadas

- **Una sola herramienta que espera hasta el final.** Con documentos largos
  supera el tiempo máximo de una llamada, y el agente pierde el resultado.
- **Consulta sin espera del lado del servidor.** El agente tendría que repetir
  la llamada muchas veces y gastaría turnos y contexto.

## Consecuencias

- El agente necesita al menos dos llamadas: enviar y consultar.
- Si el uso lo pide, una herramienta que encadene enviar, esperar y leer las
  primeras páginas puede agregarse sin cambiar este patrón (iniciativa en
  `docs/INICIATIVAS.md`).

## Evidencia

Commit inicial del repo.
