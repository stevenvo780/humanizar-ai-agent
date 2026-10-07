# Operación de Lumen en producción

Este runbook se ejecuta por un operador autorizado. Los comandos de despliegue
actúan sobre el proyecto Compose `humanizar-ai-agent`; las comprobaciones públicas
no necesitan credenciales ni realizan llamadas de pago al modelo.

## Estado registrado el 2026-10-07

| Componente | Evidencia y estado |
| --- | --- |
| Frontend | [humanizar-ai-agent.vercel.app](https://humanizar-ai-agent.vercel.app), revisión `16e9ac2`, despliegue Vercel **READY**. |
| Fuente pública | [Repositorio GitHub](https://github.com/stevenvo780/humanizar-ai-agent), rama de producción `dev`. |
| Configuración privada | El operador preparó `.env.production` y `.env.vercel`, modo `0600` e ignorados por Git; `.env` local se conservó. |
| PostgreSQL | Comprobación de sólo lectura del operador: PostgreSQL **18.6**, **TLS 1.3** y schema dedicado existente. No se modificaron datos. |
| API del VPS | Gestión de clientes y lectura de documentos implementadas y probadas con datos aislados. El VPS ejecuta `0ecb292`; acceso SSH recuperado el 2026-10-07, **actualización pendiente**. |
| Capacidades de la UI | **Clientes** requiere `features.customer_management: true`; el lector requiere `features.document_reading: true`, declarados por la API real. |
| Fedora | `~/Documentos/repos/SoftopPrueba` presente; `make setup` y `make check` pasaron el 2026-10-07. |

Un frontend READY no actualiza el contenedor de la API. No registrar el despliegue
del backend como completado hasta comprobar su salud y sus capacidades por HTTPS.
La evidencia adicional está en [VALIDATION.md](VALIDATION.md); el procedimiento
inicial está en [DEPLOYMENT.md](DEPLOYMENT.md).

Checklist de esta actualización:

- [x] Frontend `16e9ac2` READY en Vercel.
- [x] Archivos privados preparados y `.env` local preservado por el operador.
- [x] PostgreSQL 18.6 y TLS 1.3 comprobados en una conexión de sólo lectura.
- [x] Recuperar el acceso SSH autorizado al VPS (2026-10-07).
- [ ] Validar la revisión candidata y completar el backup coordinado.
- [ ] Actualizar API con `check/up/status` y comprobar ambos flags por HTTPS.
- [ ] Confirmar lectura de documentos y gestión de clientes con la sesión admin.
- [ ] Ensayar restauración de los backups en un entorno aislado.
- [x] Preparar Fedora en el destino solicitado (make setup y make check, 2026-10-07).

## Rutas y configuración privada

| Ubicación | Responsabilidad |
| --- | --- |
| `/opt/humanizar-ai-agent/repo` | Checkout público del VPS; código, locks y Compose. |
| `/opt/humanizar-ai-agent/production.env` | Configuración privada que consume Compose; archivo regular del operador, modo `0600`, fuera del checkout. |
| `/opt/humanizar-ai-agent/operator-access.json` | Acceso administrativo privado del operador; modo `0600`, fuera del checkout. |
| `.env` del entorno de trabajo local | Configuración local del backend; se conserva para SQLite y desarrollo. |
| `.env.production` del entorno de trabajo local | Preparación privada de las variables de producción; ignorada por Git. No se carga automáticamente ni sustituye `.env`. |
| `.env.vercel` del entorno de trabajo local | Preparación privada del proxy Vercel; ignorada por Git, modo `0600`. No se incorpora al frontend ni se carga automáticamente por el helper. |
| Vercel y proxy HTTPS | `API_ORIGIN` y `ORIGIN_SECRET`, gestionados por el operador en sus destinos respectivos. |

El backend lee `.env` local o las variables de su proceso. En producción, Compose
inyecta el archivo externo indicado por `LUMEN_PRODUCTION_ENV`; el helper rechaza
un `--env-file` dentro del checkout. Trasladar solamente las variables aprobadas
para cada destino por un canal privado: no copiar el archivo completo al frontend,
a Vercel, al chat, a un ZIP o a Git. Ninguna variable secreta usa el prefijo `VITE_`.

Conservar `JWT_SECRET` estable y los archivos existentes de `/data`. No regenerar
el secreto JWT ni el archivo master durante un despliegue, bootstrap o rollback.
La clave Anthropic pertenece exclusivamente al entorno de la API; cambiarla
requiere recrear esa API. No existe un formulario web para guardarla.

## Qué debe respaldarse

Hay dos almacenes con funciones distintas:

- **PostgreSQL, schema `lumen`:** usuarios, sesiones, conversaciones, mensajes y
  solicitudes. La conexión de producción exige TLS `verify-full` y
  `sslrootcert=system`.
- **Volumen Compose `knowledge`, montado en `/data`:** `metadata.sqlite3`, texto
  extraído, fragmentos, Qdrant local y archivos privados existentes. PostgreSQL
  remoto no sustituye esta base de conocimiento.

El archivo externo de configuración y el acceso del operador también requieren
custodia y recuperación privadas. Mantener backups fuera del repositorio, en un
directorio `0700`, sin permisos para otros usuarios y con almacenamiento cifrado.
No incluirlos en artefactos públicos. Usar un solo worker de API y un solo proceso
que abra ese Qdrant local.

## Antes de actualizar

1. Confirmar acceso SSH, permisos del operador y espacio disponible. Si SSH falla,
   detener el procedimiento: no sustituir credenciales ni cambiar DNS como solución.
2. Validar la revisión candidata en un clon de desarrollo con `make setup` y
   `make check`; registrar el resultado y el SHA. Las pruebas simulan Anthropic.
   Las pruebas PostgreSQL requieren una base aislada; no apuntarlas a producción.
3. En el VPS, confirmar rama `dev`, árbol sin cambios locales y revisión actual.
   Si hay cambios, preservarlos y resolverlos antes de continuar.
4. Comprobar la configuración con el helper y obtener un backup recuperable.

```bash
cd /opt/humanizar-ai-agent/repo
git branch --show-current
git status --short
git rev-parse HEAD
python3 scripts/deploy-vps.py check \
  --env-file /opt/humanizar-ai-agent/production.env
python3 scripts/deploy-vps.py status \
  --env-file /opt/humanizar-ai-agent/production.env
```

`check` valida la forma del entorno y Compose, sin iniciar contenedores ni hacer
peticiones externas. No demuestra conectividad PostgreSQL, validez de una clave
Anthropic o funcionamiento de HTTPS. No usar `source production.env` ni imprimir
la configuración con `docker compose config` sin `--quiet`.

## Backup coordinado antes del despliegue

Preparar de forma privada un servicio libpq llamado `humanizar`, con autenticación
y TLS `verify-full` verificado. Proteger su archivo de servicio y su archivo de
contraseñas; no poner la URL o una contraseña en argumentos. Comprobar que `pg_dump` es compatible
con la versión del servidor: un cliente de una versión mayor anterior no puede
volcar un servidor más nuevo. El formato custom permite restauración con
`pg_restore`. [Referencia de pg_dump](https://www.postgresql.org/docs/current/app-pgdump.html).

El servicio libpq es un prerrequisito separado: el helper no lo crea a partir del
archivo de entorno. Antes de detener la API, confirmar en privado que apunta a la
misma base de producción y ejecutar este preflight, cuya salida se limita a versión,
TLS y existencia del schema:

```bash
pg_dump --version
PGSERVICE=humanizar PGCONNECT_TIMEOUT=10 psql --no-psqlrc \
  --set=ON_ERROR_STOP=1 --tuples-only --no-align \
  --command="SELECT current_setting('server_version'); SELECT ssl, version FROM pg_stat_ssl WHERE pid = pg_backend_pid(); SELECT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'lumen');"
```

Para el servidor 18.6 registrado, usar `pg_dump` de la versión mayor 18 o posterior.
Exigir TLS activo y schema existente; si falla conexión, permisos o versión, no
detener la API ni iniciar un backup. El estado TLS no sustituye la revisión privada
de `sslmode=verify-full` del servicio. No pasar `PGPASSWORD` en argumentos ni
imprimir variables, URLs o el archivo de servicio.

Este bloque detiene brevemente la API, obtiene ambas copias durante la misma pausa
y vuelve a arrancarla incluso si una copia falla. El sandbox permanece activo.
Ejecutarlo desde una sesión del operador con permiso sobre Docker y el directorio
privado; no hacerlo simultáneamente con otro despliegue o escritor de los datos.

```bash
(
  set -euo pipefail
  umask 077
  cd /opt/humanizar-ai-agent/repo
  export LUMEN_PRODUCTION_ENV=/opt/humanizar-ai-agent/production.env
  export COMPOSE_DISABLE_ENV_FILE=1
  LUMEN_BACKUP_ROOT="$HOME/.local/share/humanizar-backups"
  install -d -m 700 "$LUMEN_BACKUP_ROOT"
  LUMEN_BACKUP_DIR="$LUMEN_BACKUP_ROOT/$(date -u +%Y%m%dT%H%M%SZ)"
  mkdir "$LUMEN_BACKUP_DIR"
  git rev-parse HEAD > "$LUMEN_BACKUP_DIR/revision.txt"
  trap 'docker compose -p humanizar-ai-agent -f compose.production.yaml start api >/dev/null 2>&1 || { echo "Reinicio de API pendiente; revisar en privado." >&2; exit 1; }' EXIT
  docker compose -p humanizar-ai-agent -f compose.production.yaml stop --timeout 120 api
  PGSERVICE=humanizar pg_dump --schema=lumen --format=custom \
    --file="$LUMEN_BACKUP_DIR/postgres.dump"
  LUMEN_API_CONTAINER="$(docker compose -p humanizar-ai-agent -f compose.production.yaml ps -a -q api)"
  test -n "$LUMEN_API_CONTAINER"
  mkdir "$LUMEN_BACKUP_DIR/data"
  docker cp "$LUMEN_API_CONTAINER:/data/." "$LUMEN_BACKUP_DIR/data"
  chmod -R go-rwx "$LUMEN_BACKUP_DIR"
)
```

Si `docker cp` requiere permisos para conservar ownership, realizar esa operación
con el acceso administrativo autorizado; no conceder permisos amplios al volumen.
Registrar sólo la fecha, la revisión y el éxito de las copias, nunca su contenido.
Un backup no está validado hasta ensayar su restauración en un entorno aislado.
Guardar también la configuración privada mediante el mecanismo de custodia del
operador; no hacer un dump de variables al terminal.

## Obtener código, actualizar y comprobar

Con el backup completo y la revisión candidata ya validada, avanzar solamente por
fast-forward. La revisión obtenida debe coincidir con la que se probó; si aparece
otra, validar esa revisión antes de desplegar. No usar `reset`, `stash` ni un checkout
destructivo para ocultar cambios.

```bash
cd /opt/humanizar-ai-agent/repo
git fetch origin dev
git merge --ff-only origin/dev
git rev-parse HEAD
python3 scripts/deploy-vps.py check \
  --env-file /opt/humanizar-ai-agent/production.env
python3 scripts/deploy-vps.py up \
  --env-file /opt/humanizar-ai-agent/production.env
python3 scripts/deploy-vps.py status \
  --env-file /opt/humanizar-ai-agent/production.env
```

`up` construye las imágenes, recrea los servicios del proyecto y espera sus
healthchecks. Conserva el volumen y el schema PostgreSQL. Su éxito sólo confirma
la salud del stack; HTTPS se verifica por separado.
[Comportamiento de Compose up](https://docs.docker.com/reference/cli/docker/compose/up/).
No usar `make docker` para este despliegue: apunta al stack local.

```bash
curl --fail --silent --show-error http://127.0.0.1:8087/api/health
curl --fail --silent --show-error https://humanizar-ai-agent.vercel.app/api/health
curl --fail --silent --show-error https://humanizar-ai-agent.vercel.app/api/auth/status
curl --fail --silent --show-error --output /dev/null \
  https://humanizar-ai-agent.vercel.app/api/docs
curl --fail --silent --show-error --output /dev/null \
  https://humanizar-ai-agent.vercel.app/api/openapi.json
```

La salud pública de la nueva API debe incluir ambas capacidades a `true`.
`setup_required` debe ser `false` en la instalación provisionada. Comprobar desde
el navegador del administrador: login, listado **Clientes**, **Documentación** y
apertura de un documento autorizado. Revisar la indicación de texto original o
recuperado. Verificar refresh y logout sin copiar cookies, JWT o datos personales
a la evidencia. Una llamada de chat real consume el proveedor: ejecutarla sólo
cuando la comprobación de pago esté autorizada y registrarla aparte.

El proxy del VPS debe exigir su header privado de origen, preservar SSE y cookies
y pasar el protocolo HTTPS. Nunca enviar `ORIGIN_SECRET` en un comando curl visible.
La prueba desde Vercel usa el rewrite ya configurado. El puerto `8087` sigue
limitado a loopback; no abrirlo a Internet para solventar un error de proxy.

## Administrador y cambios de configuración

El CLI `create-admin` se utiliza sólo en una instalación sin administrador:

```bash
cd /opt/humanizar-ai-agent/repo
export LUMEN_PRODUCTION_ENV=/opt/humanizar-ai-agent/production.env
export COMPOSE_DISABLE_ENV_FILE=1
docker compose -p humanizar-ai-agent -f compose.production.yaml exec api \
  uv run --no-sync python -m app.manage create-admin
```

Solicita nombre, correo y contraseña de forma interactiva. `--stdin-json` permite
automatización mediante un objeto privado `{name,email,password}` por stdin; la
contraseña nunca va en argumentos y la salida no contiene un JWT. Si ya existe
administrador, no recrearlo ni cambiar secretos para intentar entrar. El bootstrap
HTTP requiere `X-Bootstrap-Token`; ese token no pertenece al frontend. Se puede
rotar el token de bootstrap tras provisionar, conservando `JWT_SECRET`.

Editar la configuración privada con un editor del operador y mantener sus permisos
`0600`. Después ejecutar `check`, `up` y el smoke público. No modificar `.env` local
para cambiar producción. Para rotar `ORIGIN_SECRET`, coordinar el proxy y Vercel y
volver a desplegar el frontend; no enviar a Vercel el entorno completo del backend.
Consultar [ADMIN.md](ADMIN.md) para las tareas disponibles en la interfaz.

## Rollback compatible y restauración

Un rollback de código conserva las cuentas, el schema y el volumen. Elegir una
revisión previamente validada que soporte el PostgreSQL y la autenticación actuales.
La lectura de documentos añade una tabla separada `document_contents`; mantiene
el esquema histórico de `documents` para permitir volver a una versión compatible.
Esto no garantiza compatibilidad de cualquier migración futura.

Crear un worktree separado con la revisión anterior registrada. Sustituir el
marcador por el SHA público validado; no usarlo literalmente:

```bash
cd /opt/humanizar-ai-agent/repo
LUMEN_ROLLBACK_REV='<SHA-validado-anterior>'
LUMEN_ROLLBACK_TREE="/opt/humanizar-ai-agent/releases/$LUMEN_ROLLBACK_REV"
mkdir -p /opt/humanizar-ai-agent/releases
git worktree add --detach "$LUMEN_ROLLBACK_TREE" "$LUMEN_ROLLBACK_REV"
cd "$LUMEN_ROLLBACK_TREE"
python3 scripts/deploy-vps.py check \
  --env-file /opt/humanizar-ai-agent/production.env
python3 scripts/deploy-vps.py up \
  --env-file /opt/humanizar-ai-agent/production.env --project humanizar-ai-agent --port 8087
python3 scripts/deploy-vps.py status \
  --env-file /opt/humanizar-ai-agent/production.env --project humanizar-ai-agent --port 8087
```

Usar el mismo proyecto Compose conserva su volumen; no arrancar un segundo proceso
sobre el Qdrant activo. Repetir el smoke HTTPS y registrar la revisión restaurada.
Si sólo se necesita detener el stack, `deploy-vps.py stop` conserva los datos.
No usar `down -v`, `docker volume rm`, borrar schemas ni cambiar el secreto JWT.
[Compose down y volúmenes](https://docs.docker.com/reference/cli/docker/compose/down/).

Restaurar un backup de datos primero en una base vacía y un volumen nuevo, con un
proyecto Compose y puerto separados. El servicio privado `humanizar_restore` debe
apuntar exclusivamente a la base de ensayo. Definir la ruta del backup privado
elegido; el bloque de backup anterior mantiene su variable dentro de una subshell:

```bash
LUMEN_RESTORE_BACKUP='<directorio-privado-del-backup>'
pg_restore --no-owner --no-acl --exit-on-error \
  --dbname='service=humanizar_restore' "$LUMEN_RESTORE_BACKUP/postgres.dump"
```

No usar `--clean` contra producción. Conservar ownership `10001:10001` en `/data`
y la configuración de autenticación de esa misma instalación. Validar restauración
en privado antes de cambiar un upstream; preservar la instalación activa hasta
terminar la comprobación. El ensayo de restauración no se da por ejecutado aquí.

## Diagnóstico y registro de evidencia

| Síntoma | Comprobación acotada |
| --- | --- |
| SSH no autentica | Resolver el acceso privado con el operador. El backend no se considera actualizado. |
| `check` falla | Revisar propiedad y modo `0600`, formato literal, TLS, schema y orígenes HTTPS en privado. No imprimir el archivo. |
| `up` falla | Ejecutar `status` y revisar logs privados del servicio afectado; comprobar CA, PostgreSQL, volumen y memoria. |
| Vercel responde 502 o 403 | Comprobar origen HTTPS y coherencia del header privado entre proxy y Vercel, sin exponerlo. |
| No aparece **Clientes** o el lector | Comprobar los flags del health público y la revisión del backend; un frontend nuevo no los inventa. |
| El modelo figura como `demo` | Revisar `LLM_MODE` y la presencia de una clave válida en el entorno backend, luego recrear API. El health no demuestra una llamada de pago. |
| 429 en login o chat | Esperar y reducir concurrencia; conservar autenticación y los límites. No reiniciar repetidamente para saltarlos. |

La API desactiva access logs y Compose rota los logs. Los diagnósticos del helper
se suprimen porque pueden contener configuración privada; revisarlos sólo en el
VPS y compartir un resumen sanitizado. No volcar `docker inspect`, el entorno del
proceso, archivos privados, respuestas autenticadas o cuerpos de documentos.

Para cerrar una operación, registrar fecha UTC, revisión frontend/backend,
resultado de backup, `check`, estado de servicios y smoke HTTPS, capacidades
observadas y cualquier pendiente. Registrar sesiones, credenciales o datos de
clientes nunca es necesario para demostrar el despliegue.
