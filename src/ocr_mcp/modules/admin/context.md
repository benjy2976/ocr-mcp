# Contexto: `admin`

## Propósito

El panel `/admin`, mínimo (decisiones 0006 y 0007): crear y borrar claves,
fijar sus cuotas, ver su uso, configurar el modo público y mostrar cómo se
conectan los clientes.

## Alcance y límites

- Incluye: la sesión del admin (`session.py`) y las rutas y plantillas del
  panel (`routes.py`, `templates/`).
- No incluye: roles, varios admins, edición de usuarios ni nada más.
- Dependencias funcionales: `access` (claves), `quotas` (límites y modo
  público) y `jobs` (uso y estadísticas).

## Actores y permisos

| Actor | Puede | No puede | Evidencia |
| --- | --- | --- | --- |
| Admin (usuario y contraseña del entorno) | Todo lo del panel | Ver una clave después de crearla | `test_creating_a_key_shows_it_once_with_client_examples` |
| Cualquier otro | Ver la página de inicio de sesión | Cambiar nada, aunque conozca las rutas | `test_forms_without_the_csrf_token_do_nothing` |

## Reglas

1. La contraseña del admin viene del entorno solo como hash scrypt
   (`ocr-mcp hash-password`); usuario y contraseña se comparan en tiempo
   constante y fallan con el mismo mensaje.
2. Cinco intentos fallidos por dirección en diez minutos bloquean con `429`.
   Prueba: `test_admin_login_attempts_are_limited`.
3. La sesión es una cookie `HttpOnly`, `SameSite=Strict`, con ruta `/admin` y
   `Secure` detrás de TLS; dura ocho horas. Prueba:
   `test_the_session_cookie_is_protected`.
4. Todo formulario lleva el token CSRF de la sesión; sin él, no cambia nada.
5. Borrar una clave revoca sus tokens de inmediato; sus trabajos quedan sin
   dueño, pero los conteos se conservan.
6. Las estadísticas solo muestran conteos (documentos, páginas, bytes, estados
   y la serie de 30 días).

## Flujo e integraciones

Iniciar sesión → panel (claves con su uso de hoy y del mes, nueva clave, modo
público) → detalle de una clave (uso, cuota, borrar) → ejemplos de integración
con la URL `<OCR_MCP_PUBLIC_URL>/mcp` ya puesta. Contrato: `docs/api.md`.

## Errores esperables y recuperación

| Situación | Comportamiento | Recuperación |
| --- | --- | --- |
| Límite inválido (negativo, texto) | Vuelve con el error en la página | Corregir el valor |
| Modo público sin límite de páginas | Se rechaza | Fijar al menos uno |
| Sesión vencida | Vuelve a pedir credenciales | Iniciar sesión |

## Pruebas mínimas

`tests/modules/admin/test_panel.py`.
