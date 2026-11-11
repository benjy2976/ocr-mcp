# Procedimientos

Comandos reproducibles para preparar, probar y validar el repo. Todos se
ejecutan desde la raíz del repo. Antes de ejecutar comandos, el protocolo de
`AGENTS.md` pide declarar su propósito y alcance
(`docs/memoria-viva/resource-efficiency.md`).

## Preparar el entorno

Precondición: Python 3.11 o posterior (`docs/entorno.md`).

```bash
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

Éxito: `.venv/bin/pytest --version` responde sin error.

## Pruebas y lint

```bash
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check src tests
```

Las pruebas no necesitan un core real, red ni GPU: usan el core simulado
(`tests/fakes/core.py`). `tests/test_architecture.py` comprueba las reglas de
organización del código.

## Arrancar el servidor en la propia máquina

Precondiciones: un `ocr-core` accesible y el token de este servidor registrado
en él (`README.md`, "Requisitos").

```bash
cp .env.example .env
.venv/bin/ocr-mcp hash-password        # pegar el resultado en OCR_MCP_ADMIN_PASSWORD_HASH
# completar OCR_CORE_TOKEN y revisar OCR_CORE_URL en .env
.venv/bin/ocr-mcp serve --env-file .env
```

Éxito: `curl http://127.0.0.1:18040/health` responde
`{"status": "ok", …}` y `http://127.0.0.1:18040/admin` muestra el inicio de
sesión del panel. Después, crear una clave en el panel y conectar un cliente
(`docs/integracion-con-clientes.md`).

## Arrancar con Docker

```bash
cp .env.example .env                    # completar como arriba
docker compose up -d --build
curl http://127.0.0.1:18040/health
```

Dentro del contenedor, `127.0.0.1` es el propio contenedor: `OCR_CORE_URL` debe
apuntar a una dirección del core alcanzable desde él (por ejemplo, el nombre
del servicio en una red de Docker compartida). El estado queda en el volumen
`ocr-mcp-data`; respaldarlo conserva las claves y el uso.

## Publicar en una red local

Para que las máquinas de una red usen el servidor. OAuth exige HTTPS fuera de
`127.0.0.1`, así que el servidor sirve HTTPS por sí mismo (decisión 0008). En
los ejemplos, el equipo tiene la IP `192.0.2.10`; se reemplaza por la real.
Claude Desktop y claude.ai no sirven en una red local: se conectan desde la
nube del proveedor.

### 1. Certificado con una CA local

Una vez, en el equipo del servidor y en una carpeta fuera del repo:

```bash
mkdir -p ~/ocr-mcp-tls && cd ~/ocr-mcp-tls && umask 077
# CA local: su certificado (ca.crt) se instala en cada cliente; ca.key no sale de aquí.
openssl req -x509 -newkey rsa:3072 -sha256 -days 3650 -nodes \
  -keyout ca.key -out ca.crt -subj "/CN=ocr-mcp CA local"
# Certificado del servidor para su IP (y su nombre, si la red tiene DNS).
openssl req -newkey rsa:2048 -sha256 -nodes \
  -keyout servidor.key -out servidor.csr -subj "/CN=192.0.2.10"
printf "subjectAltName=IP:192.0.2.10,DNS:ocr-mcp.lan\nextendedKeyUsage=serverAuth\n" > servidor.ext
openssl x509 -req -in servidor.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -days 825 -sha256 -extfile servidor.ext -out servidor.crt
```

Si la organización tiene su propia CA, se usa un certificado emitido por ella y
este paso se omite.

### 2. Configuración

En el `.env` del servidor:

```bash
OCR_MCP_HOST=0.0.0.0
OCR_MCP_PORT=18040
OCR_MCP_PUBLIC_URL=https://192.0.2.10:18040
OCR_MCP_TLS_CERT=/ruta/a/ocr-mcp-tls/servidor.crt
OCR_MCP_TLS_KEY=/ruta/a/ocr-mcp-tls/servidor.key
```

Todos los clientes usan exactamente la URL de `OCR_MCP_PUBLIC_URL` (la misma IP
o el mismo nombre que figura en el certificado): el servidor rechaza peticiones
MCP dirigidas a otro nombre. Los tokens emitidos con la URL anterior dejan de
valer, porque están atados a ella; las claves de acceso siguen sirviendo, así
que cada cliente vuelve a iniciar sesión con su misma clave.

### 3. Abrir el puerto

- **Linux:** permitir el puerto 18040 en el firewall del equipo (por ejemplo,
  `sudo ufw allow 18040/tcp`).
- **Windows con WSL2 en modo NAT** (WSL tiene su propia IP interna, que se ve
  con `hostname -I` dentro de WSL y cambia al reiniciar): en PowerShell como
  administrador, reenviar el puerto y abrirlo en el firewall:

  ```powershell
  $wsl = (wsl hostname -I).Split(" ")[0]
  netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=18040 connectaddress=$wsl connectport=18040
  New-NetFirewallRule -DisplayName "ocr-mcp" -Direction Inbound -Protocol TCP -LocalPort 18040 -Action Allow
  ```

  El reenvío se repite tras cada reinicio de WSL (con el `netsh … add` de
  nuevo, que reemplaza el anterior) y se retira con
  `netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=18040`.
  Con el reenvío, el servidor ve todas las conexiones como del propio equipo:
  el límite de intentos por dirección se vuelve compartido.
- **Windows 11 con WSL2 en modo reflejado** (`networkingMode=mirrored` en
  `.wslconfig`): no hace falta el reenvío, solo la regla del firewall.

### 4. Arrancar y comprobar

```bash
.venv/bin/ocr-mcp serve --env-file .env
# desde otra máquina de la red, con el ca.crt copiado:
curl --cacert ca.crt https://192.0.2.10:18040/health
```

### 5. Conectar cada cliente

1. Copiar `ca.crt` a la máquina y confiar en él:
   - Claude Code y otros clientes de Node.js: `export NODE_EXTRA_CA_CERTS=/ruta/a/ca.crt`
     antes de abrirlos (por ejemplo, en el perfil de la shell);
   - el navegador, para la página de la clave: importar `ca.crt` como autoridad
     de confianza en el sistema o en el navegador.
2. Agregar el servidor con su URL, por ejemplo
   `claude mcp add --transport http ocr https://192.0.2.10:18040/mcp`, e iniciar
   sesión con una clave creada en `https://192.0.2.10:18040/admin`.

El panel `/admin` queda accesible desde toda la red: lo protegen la contraseña
del admin y el límite de intentos. Con una contraseña larga y la red de
confianza, alcanza; si no, conviene limitar el puerto en el firewall a las
máquinas que lo necesitan.

### Con Docker

El mismo resultado, con el servidor en un contenedor que arranca solo con
Docker. Lo propio de cada equipo va en `docker-compose.override.yml`, junto a
`docker-compose.yml`; ese archivo no se versiona (`.gitignore`) y Compose lo
aplica solo. Ejemplo, con el certificado del paso 1 y el core en otra red de
Docker del mismo equipo:

```yaml
services:
  ocr-mcp:
    user: "1000:1000"                 # dueño de los datos y del certificado en el equipo
    environment:
      OCR_CORE_URL: http://<nombre-del-core>:8000
      OCR_MCP_PUBLIC_URL: https://192.0.2.10:18040
      OCR_MCP_TLS_CERT: /tls/servidor.crt
      OCR_MCP_TLS_KEY: /tls/servidor.key
    ports: !override
      - "0.0.0.0:18040:18040"
    volumes: !override
      - ./datos:/data                 # o el volumen ocr-mcp-data
      - /ruta/a/ocr-mcp-tls:/tls:ro
    networks: [default, core]
networks:
  core:
    external: true
    name: <red-del-core>
```

```bash
docker compose up -d --build
curl --cacert /ruta/a/ocr-mcp-tls/ca.crt https://192.0.2.10:18040/health
```

- El `.env` sigue siendo la base; `environment` del override manda sobre él.
  Dentro del contenedor, `127.0.0.1` es el propio contenedor: el core se
  alcanza por su nombre en la red de Docker que comparten.
- Con **Docker Desktop** (Windows o macOS), el puerto publicado queda en la IP
  del equipo: no hace falta el reenvío del paso 3, solo la regla del firewall si
  Windows no la crea. Con Docker dentro de WSL2 sin Docker Desktop, el reenvío
  sigue siendo necesario.
- El contenedor ve las conexiones como de Docker, así que el límite de intentos
  por dirección se comparte entre todos los clientes.
- `docker compose down` lo detiene; `restart: unless-stopped` lo vuelve a
  levantar con Docker.

## Detrás de un proxy o un Ingress

Con TLS en el proxy (un proxy inverso o un Ingress de Kubernetes), el servidor
corre en HTTP detrás y `OCR_MCP_PUBLIC_URL` es la URL `https` del proxy. Para
que los límites por dirección (intentos de inicio de sesión y claves públicas
por día) cuenten a cada cliente por separado, el servidor tiene que creer el
`X-Forwarded-For` del proxy:

```bash
OCR_MCP_TRUSTED_PROXIES=10.42.0.0/16    # rango de los pods del Ingress, o la IP del proxy
```

- Con `*` cree a cualquiera que le hable directo. Sirve si solo el proxy llega
  al puerto del servidor (en Kubernetes, un `Service` sin exponer).
- Sin la variable, el servidor arranca con un aviso y todos los clientes llegan
  con la IP del proxy: unos pocos intentos fallidos bloquean a todos, y las
  claves públicas del día se agotan para todos.
- El proxy tiene que ver la IP real del cliente. Si delante hay un balanceador
  con NAT, se configura para conservarla (por ejemplo, `externalTrafficPolicy:
  Local` en un `Service` de Kubernetes o el protocolo PROXY).
- El proxy enruta al servidor `/mcp`, `/.well-known/`, `/authorize`, `/token`,
  `/register`, `/revoke`, `/login`, `/public/key`, `/u/`, `/d/` y `/admin`, o
  directamente todo `/`.

Con Docker en el propio equipo (sección anterior) no hay proxy que agregue el
encabezado: la variable no cambia nada y el límite queda compartido.

## Términos prohibidos

El repo no puede contener nombres de instituciones, terceros, equipos ni rutas
de máquinas (`docs/convenciones.md`). La lista de términos vive **fuera del
repo**, un término por línea, para que el repo no los nombre ni siquiera en la
prueba:

```bash
OCR_MCP_RESTRICTED_TERMS_FILE=/ruta/fuera/del/repo/terminos.txt .venv/bin/pytest tests/test_restricted_terms.py
```

Sin la variable, la prueba se omite y lo informa. Antes de cada commit, quien
tenga la lista la corre.

## Validar la memoria

```bash
scripts/validate-project-memory
npx --no-install markdownlint-cli2 "**/*.md" "#.venv" "#planes"
```

- El validador se ejecuta directo, sin anteponer `python3`: el lanzador ya
  aísla el intérprete. Para un cambio pequeño, `--changed` o `--module`
  limitan el alcance; el modo completo y Markdownlint global se reservan para
  un hito candidato a commit (`AGENTS.md`, "Cierre obligatorio").
- Leer cobertura, confianza y evidencia de cada hallazgo, no solo el código de
  salida. `NOT_EVALUATED` no significa conformidad.
- `--no-install` usa la copia de `markdownlint-cli2` en la caché de `npx`. Sin
  ella, declarar la comprobación como no ejecutada.

## Obtener `ocr-core`

`ocr-core` se genera desde el repositorio `ocr-lab`, que contiene su fuente y
su empaquetado; su documentación explica cómo generar un release desde un tag.
Para conectarlo, el servidor necesita un token de cliente cuyo hash registre
quien opera el core (`README.md`, "Requisitos").

## Mantenimiento de memoria

Antes del cambio:

1. Leer `AGENTS.md`, el `context.md` de los módulos afectados y la fuente
   normativa de lo que se va a tocar.
2. Anotar las capacidades actuales que el cambio puede alterar.

Después del cambio:

1. Revisar el diff completo.
2. Evaluar la matriz de umbrales de `AGENTS.md` y crear o actualizar la fuente
   que corresponda.
3. Correr las pruebas del módulo y el validador con alcance.
4. En un hito candidato a commit, además: suite completa, validador sin
   alcance, Markdownlint global y la prueba de términos prohibidos.

## Actualizar el estándar de memoria

Se sigue el modo "Actualizar estándar" de `docs/memoria-viva/workflow.md`:
comparar la versión adoptada (`docs/guia_IA.md`) con la nueva, migrar por
artefacto sin perder las mejoras locales y registrar la nueva versión solo al
terminar y validar.
