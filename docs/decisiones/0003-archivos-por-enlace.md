# 0003. Los archivos viajan por enlace: subida de un solo uso y descarga que vence

- **Estado:** vigente
- **Fecha:** 2026-11-05
- **Decidió:** Walther Aguirre

## Contexto

El servidor es un servicio HTTP (decisión 0002): no ve el disco de quien lo
usa, aunque corran en la misma máquina, porque normalmente está dentro de un
contenedor. Un PDF escaneado pesa de cientos de KB a cientos de MB, y un agente
le pasa datos a una herramienta como argumentos que el propio modelo genera.

## Decisión

1. **Entrada por enlace de subida.** `ocr_upload_link` entrega un enlace de un
   solo uso, que vence y pertenece al usuario que lo pidió. Sirve de dos
   formas:
   - un agente con terminal sube el archivo con un `PUT`
     (`curl -T documento.pdf <enlace>`);
   - una persona abre el enlace en el navegador y elige el archivo en un
     formulario.

   El servidor valida que sea un PDF, cuenta sus páginas y lo reenvía al core
   por partes, sin cargarlo completo en memoria.
2. **URL opcional.** `ocr_submit` acepta una URL solo si empieza por uno de los
   prefijos que configura quien opera el servidor. La lista está vacía por
   defecto, así que esa vía queda apagada y se evita que el servidor descargue
   direcciones internas (SSRF).
3. **Salida:**
   - el Markdown, por tramos de páginas, en la respuesta de la herramienta,
     cortado por las marcas de página del artefacto;
   - los artefactos (`pdf`, `text`, `md`), por enlaces de descarga que vencen y
     pertenecen al usuario.
4. **Nunca en base64 dentro de los argumentos, y nunca por rutas del disco del
   servidor.** Ninguna herramienta lee ni escribe rutas en nombre de un
   usuario.

## Alternativas descartadas

- **PDF en base64 dentro de los argumentos.** El modelo tendría que generar el
  archivo entero como texto: millones de tokens para un PDF grande, con costo,
  lentitud y riesgo de corrupción.
- **Ruta local.** Solo funciona si el servidor ve el mismo disco que el
  usuario, cosa que no ocurre con un contenedor ni en línea. Además, un agente
  engañado podría pedir que se lea cualquier archivo.
- **Descargar cualquier URL.** Permitiría usar el servidor para alcanzar
  direcciones internas de su red.

## Consecuencias

- El contenido del PDF no pasa por el modelo. Solo llega al proveedor del
  modelo el Markdown que el agente decide leer (regla de uso en el
  `README.md`).
- Con un cliente sin terminal, la persona abre el enlace y elige el archivo.
- La vigencia de los enlaces es configurable.

## Evidencia

Commit inicial del repo (diseño). Implementación: `src/ocr_mcp/modules/files/`;
pruebas en `tests/modules/files/test_links.py` y
`test_urls_are_accepted_only_from_configured_prefixes`
(`tests/modules/jobs/test_tools.py`).
