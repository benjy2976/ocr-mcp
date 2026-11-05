# 0002. Un servicio HTTP con OAuth 2.1 obligatorio, también en uso local

- **Estado:** aceptada, sin implementar
- **Fecha:** 2026-11-05
- **Decidió:** Walther Aguirre

> **Hoy:** el repo todavía no tiene código.

## Contexto

MCP admite dos transportes. En el **local (stdio)**, el cliente del agente
lanza el servidor como un proceso en la misma máquina. En el **remoto
(Streamable HTTP)**, el servidor corre como un servicio y los agentes se
conectan por la red. La especificación de MCP define la autorización con
OAuth 2.1 solo para el transporte HTTP.

El autor usa el servidor en su propia máquina. Cualquiera que clone el repo
debe poder ponerlo en línea sin reescribirlo, y el autor quiere una sola forma
de conectarse y de controlar quién accede.

## Decisión

1. **Solo Streamable HTTP.** No hay modo stdio. El servidor corre siempre como
   un servicio permanente, por ejemplo en un contenedor.
2. **OAuth 2.1 obligatorio en toda petición MCP**, según la especificación de
   autorización de MCP:
   - el servidor es un servidor de recursos y publica sus metadatos de recurso
     protegido;
   - una petición sin token válido recibe `401`, con un `WWW-Authenticate` que
     apunta a esos metadatos;
   - el servidor de autorización viene incluido (decisión 0006).
3. **Igual para todos.** El autor lo corre en su máquina, escuchando en
   `127.0.0.1`. Quien lo publique pone un proxy inverso con TLS delante y
   configura la URL pública.
4. **Valida el encabezado `Origin`**, como pide la especificación contra el
   DNS rebinding.

## Alternativas descartadas

- **stdio para uso local y OAuth solo en línea.** Dejaría dos formas de
  conectarse y un uso local sin control de acceso. El autor prefirió una sola.
- **Tokens estáticos por usuario en un encabezado.** No funcionan con los
  conectores web de los asistentes, y obligan a copiar el token en la
  configuración de cada cliente.
- **Un servidor de autorización externo** (Keycloak, Google, GitHub). Es
  pesado para una herramienta pequeña y depende de cuentas externas. Como el
  servidor es un servidor de recursos estándar, puede adoptarse más adelante
  (`docs/INICIATIVAS.md`).

## Consecuencias

- El uso local también pasa por el inicio de sesión: una vez por cliente, en el
  navegador.
- Los clientes que no soportan OAuth en servidores MCP por HTTP no pueden
  conectarse.
- Como el servidor no ve el disco del usuario, los archivos viajan por enlace
  (decisión 0003).
- Las pruebas cubren el flujo OAuth completo y el `401`.

## Evidencia

Commit inicial del repo.
