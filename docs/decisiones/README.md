# Registro de decisiones

Cada archivo registra una decisión que alguien podría cuestionar más adelante:
qué se decidió, por qué, qué alternativas se descartaron y qué consecuencias
tiene. Antes de cambiar algo que una decisión vigente gobierna, hay que leerla.
Las decisiones de Walther Aguirre, responsable del proyecto, no las reabre un
agente por su cuenta.

## Índice

| # | Decisión | Estado |
|---|---|---|
| [0001](0001-cliente-generico-que-solo-recibe-y-entrega-trabajos.md) | Un cliente genérico de `ocr-core` que solo recibe y entrega trabajos | aceptada, sin implementar |
| [0002](0002-servicio-http-con-oauth-obligatorio.md) | Un servicio HTTP con OAuth 2.1 obligatorio, también en uso local | aceptada, sin implementar |
| [0003](0003-archivos-por-enlace.md) | Los archivos viajan por enlace: subida de un solo uso y descarga que vence | aceptada, sin implementar |
| [0004](0004-trabajo-asincrono-con-ticket.md) | Trabajo asíncrono con el patrón del ticket | aceptada, sin implementar |
| [0005](0005-sin-limites-propios-por-defecto.md) | Sin límites propios por defecto; manda el límite del core | aceptada, sin implementar |
| [0006](0006-claves-de-acceso-oauth-y-panel-de-admin.md) | Acceso con una clave por usuario, OAuth 2.1 incluido y un panel mínimo de admin | aceptada, sin implementar |
| [0007](0007-cuotas-modo-publico-y-estadisticas.md) | Cuotas por clave, modo público opcional y estadísticas de uso | aceptada, sin implementar |

## Reglas

- Un archivo por decisión: `NNNN-<slug>.md`, numerado en orden de registro.
- **No se editan** salvo para corregir erratas o cambiar el estado. Si el
  criterio cambia, se registra una decisión nueva y la anterior pasa a
  `reemplazada por NNNN`.
- **Estados:**
  - `vigente`: rige y el sistema ya la cumple;
  - `aceptada, sin implementar`: está decidida, pero el sistema **todavía no**
    la cumple. Lleva al principio un aviso con lo que hace hoy el sistema.
    Cuando se implementa, pasa a `vigente`;
  - `reemplazada por NNNN`;
  - `retirada`.
- **Decidió:** quien tomó la decisión. Si fue una propuesta técnica, quien la
  aprobó.
- La evidencia se cita por commit, tag o documento vigente, nunca por un plan
  de trabajo.

## Formato

```markdown
# NNNN. <decisión en una frase>

- **Estado:** vigente
- **Fecha:** AAAA-MM-DD
- **Decidió:** <nombre>

## Contexto
## Decisión
## Alternativas descartadas
## Consecuencias
## Evidencia
```
