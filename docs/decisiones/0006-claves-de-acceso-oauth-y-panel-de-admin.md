# 0006. Acceso con una clave por usuario, OAuth 2.1 incluido y un panel mínimo de admin

- **Estado:** vigente
- **Fecha:** 2026-11-05
- **Decidió:** Walther Aguirre

## Contexto

OAuth 2.1 es obligatorio (decisión 0002). Con OAuth, el cliente del agente
abre el navegador para que el usuario se identifique, y el servidor le emite
tokens que vencen solos. Hace falta decidir con qué se identifica cada usuario,
quién da y quita el acceso, y dónde se guarda ese estado.

## Decisión

1. **Servidor de autorización incluido**, en el mismo proceso que el servidor
   MCP:
   - código de autorización con PKCE, registro dinámico de clientes, metadatos
     del servidor de autorización, tokens de refresco y revocación;
   - tokens de acceso cortos (1 hora por defecto) y de refresco (30 días por
     defecto), ambos configurables.
2. **Una clave de acceso por usuario.** Es su identidad:
   - el admin la crea con un nombre y la ve una sola vez; el servidor solo
     guarda su hash;
   - en la primera conexión de cada cliente, el navegador muestra una página
     que pide la clave. Si es válida, OAuth emite tokens a nombre de ese
     usuario;
   - borrar la clave revoca de inmediato todos sus tokens.
3. **Panel `/admin`, mínimo:**
   - el usuario y la contraseña del admin vienen del `.env`
     (`OCR_MCP_ADMIN_USER` y `OCR_MCP_ADMIN_PASSWORD_HASH`, la contraseña solo
     como hash);
   - permite listar, crear y borrar claves, fijar su cuota y ver su uso
     (decisión 0007);
   - muestra ejemplos de integración con los clientes más habituales
     (`docs/integracion-con-clientes.md`);
   - no tiene roles, ni edición de usuarios, ni nada más.
4. **Estado en SQLite**, en `OCR_MCP_DATA_DIR`: claves, clientes OAuth, tokens,
   dueños de los trabajos, enlaces, cuotas y conteos de uso. Las claves y los
   tokens se guardan solo como hash.
5. **Trabajos aislados por usuario.** Ante el core, el servidor es un solo
   cliente (`mcp`). Por eso registra quién creó cada `job_id`, y un usuario
   solo ve sus trabajos: uno ajeno responde como si no existiera. La
   `idempotency_key` incluye al usuario, para que dos usuarios que suben el
   mismo PDF no compartan un trabajo.
6. **Defensas del inicio de sesión y del panel:**
   - intentos limitados por dirección;
   - comparación en tiempo constante;
   - errores genéricos, que no revelan si una clave existe;
   - protección CSRF en los formularios;
   - cookie de sesión del admin `HttpOnly`, `SameSite` y `Secure` detrás de
     TLS;
   - ni las claves ni los tokens se registran nunca.

## Alternativas descartadas

- **Usuario y contraseña por usuario.** El servidor tendría que guardar
  contraseñas de usuarios y ofrecer cambio y recuperación.
- **Tokens estáticos en un encabezado.** No funcionan con los conectores web
  (decisión 0002).
- **Claves en el `.env`.** El admin no podría crearlas ni borrarlas sin
  reiniciar el servidor.
- **Un token del core por usuario.** Obligaría a quien opera el core a
  registrar a cada usuario del MCP. El servidor MCP es la frontera.

## Consecuencias

- Hay un estado nuevo que respaldar: la base SQLite. Si se pierde, las claves y
  las sesiones dejan de valer y hay que emitir claves nuevas.
- La primera conexión de cada cliente exige abrir el navegador y pegar la
  clave.
- Los conectores web de los asistentes exigen una URL pública con HTTPS.

## Evidencia

Commit inicial del repo (diseño). Implementación: `src/ocr_mcp/modules/access/`
y `src/ocr_mcp/modules/admin/`; pruebas en
`tests/modules/access/test_oauth_flow.py`, `tests/modules/admin/test_panel.py` y
`test_a_user_never_sees_another_users_job_or_upload`.
