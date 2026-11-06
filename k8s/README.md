# Manifiestos de Kubernetes — Servidor OCR MCP

Manifiestos para el despliegue del servidor **ocr-mcp** en el clúster institucional (`namespace: ocr-service`).

## Estructura de Manifiestos

| Archivo | Recurso | Función |
| :--- | :--- | :--- |
| `01-secret.yaml` | `Secret` | Token de conexión con `ocr-core` (`OCR_CORE_TOKEN`) y hash scrypt de la contraseña admin (`OCR_MCP_ADMIN_PASSWORD_HASH`). |
| `01-secret.example.yaml` | `Secret (Plantilla)` | Plantilla sin credenciales para control de versiones. |
| `02-configmap.yaml` | `ConfigMap` | URLs públicas, endpoints internos y usuario admin. |
| `03-pvc.yaml` | `PVC` | Almacenamiento persistente Longhorn (10 Gi) para SQLite (`/data/ocr-mcp.sqlite3`) y archivos temporales. |
| `04-deployment.yaml` | `Deployment` | Despliegue de `ryuk89/ocr-mcp:latest` con usuario no-root `10001:10001`, sondas `/health` y réplica única. |
| `05-service.yaml` | `Service` | Servicio ClusterIP en puerto `18040`. |
| `06-ingress.yaml` | `Ingress` | Exposición HTTPS con TLS de Let's Encrypt y buffers apagados para streaming SSE. |
| `kustomization.yaml` | `Kustomization` | Despliegue agrupado con `kubectl apply -k .`. |

## Despliegue

```bash
# 1. Aplicar en el clúster
kubectl apply -k k8s/

# 2. Verificar estado
kubectl get pods -n ocr-service -l app.kubernetes.io/name=ocr-mcp -w
```
