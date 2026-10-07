# Despliegue reproducible

Instancia publicada: [web](https://humanizar-ai-agent.vercel.app),
[documentación](https://humanizar-ai-agent.vercel.app/docs) y
[API](https://humanizar-ai-agent.vercel.app/api/docs). Los resultados observados
de login, Haiku, TLS, sandbox y persistencia están en [VALIDATION.md](VALIDATION.md).

El proyecto Vercel está conectado al repositorio GitHub con rama de producción
`dev`. Un push a esa rama actualiza el frontend; el backend se actualiza por
separado en el VPS mediante pull y el helper de Compose, después del backup.
GitHub Actions permanece definido, pero su runner no inicia por un bloqueo de
facturación de la cuenta. El despliegue y las pruebas reales registrados no
dependen de atribuir éxito a ese workflow.

El frontend se publica en Vercel y conserva llamadas del navegador a `/api` en el
mismo origen. La API FastAPI y el sandbox se ejecutan en un VPS mediante
`compose.production.yaml`. PostgreSQL remoto almacena cuentas, sesiones y
solicitudes; Qdrant en modo local, documentos y el secreto generado permanecen en
el volumen `/data` del VPS. Se usa un único worker de API por la persistencia local
de Qdrant. Este documento describe el procedimiento; la publicación y las
comprobaciones reales de cada entorno requieren evidencia de ese despliegue.

En la instancia preparada, el checkout está en `/opt/humanizar-ai-agent/repo`,
el entorno privado en `/opt/humanizar-ai-agent/production.env` y el acceso del
administrador en `/opt/humanizar-ai-agent/operator-access.json`. Los dos archivos
privados pertenecen al operador y tienen permisos `0600`; no se publican ni se
incorporan al ZIP. La configuración del proxy también queda fuera del checkout.

## Fuente y desarrollo

```bash
git clone --branch dev https://github.com/stevenvo780/humanizar-ai-agent.git
cd humanizar-ai-agent
make setup
make dev
```

`make check` valida el proyecto. `make speckit` instala Specify CLI 1.0.7 y
`make speckit-check` comprueba la feature base. Para Fedora, usar
[FEDORA.md](FEDORA.md). Las dependencias de ejecución están en los lockfiles;
la instalación de producción no copia entornos virtuales de otro equipo.

Publicar únicamente código, pruebas, documentación, configuración de ejemplo,
lockfiles, CI y la integración pública Claude/Spec Kit. Excluir archivos privados
de entorno, datos, cargas, certificados privados, backups, `.git`, `.vercel`,
`node_modules`, `.venv`, ajustes locales e historiales de agentes. Antes de publicar,
usar la auditoría de rutas y el escaneo de secretos establecidos por el repositorio.

## Variables y sus destinos

| Variable | Destino | Uso |
| --- | --- | --- |
| `API_ORIGIN` | Vercel, configuración de despliegue | Origen público HTTPS de la API, sin ruta, usuario, query ni fragmento. |
| `ORIGIN_SECRET` | Vercel protegido y proxy privado del VPS | Autoriza el tráfico del rewrite; nunca tiene prefijo `VITE_`. |
| `ANTHROPIC_API_KEY` | API, archivo privado | Clave del proveedor; vacía permite el modo demo. |
| `LLM_MODE` / `ANTHROPIC_MODEL` | API | `auto`, `demo` o `anthropic`; el modelo web es independiente de Claude Code. |
| `DATABASE_URL` | API, archivo privado | PostgreSQL remoto con `sslmode=verify-full&sslrootcert=system`. |
| `DATABASE_SCHEMA` | API | Schema exclusivo `lumen`, sin modificar tablas de otros proyectos. |
| `JWT_SECRET` | API, archivo privado | Obligatorio en producción, al menos 32 caracteres; mantenerlo estable. |
| `AUTH_BOOTSTRAP_TOKEN` | API, archivo privado | Obligatorio en producción, al menos 32 caracteres; protege el bootstrap HTTP mediante `X-Bootstrap-Token`. |
| `CORS_ORIGINS` | API | Array JSON de los orígenes HTTPS exactos del frontend. |
| `LUMEN_PRODUCTION_ENV` | Helper/Compose | Ruta absoluta del archivo privado externo al checkout. |
| `LUMEN_API_PORT` | Helper/Compose | Puerto loopback de la API, por defecto `8087`. |

La plantilla pública está en
[config/production.env.example](../config/production.env.example). El archivo real
usa líneas literales `KEY=value`: sin `export`, comillas de shell, interpolación ni
valores multilínea. Docker Compose `format: raw` conserva caracteres como `$`.
Las contraseñas de la URL PostgreSQL deben estar codificadas para URL. El helper
exige Docker Compose **2.30 o posterior**, archivo regular propio con modo `0600`,
schema dedicado, ambos secretos de autenticación y TLS con validación completa.
La URL sólo admite las opciones `sslmode` y `sslrootcert`, una vez cada una, con puerto
válido de `1` a `65535` cuando se especifica. No imprime valores ni diagnósticos
que puedan contenerlos.

`verify-full` verifica la CA y que el hostname coincida con el certificado.
`sslrootcert=system` usa el almacén de confianza del cliente moderno. Para un
proveedor con CA privada hay que montar únicamente su certificado CA de lectura
y adaptar el helper/URL antes del despliegue; esta receta utiliza confianza del
sistema. [Referencia PostgreSQL](https://www.postgresql.org/docs/current/libpq-connect.html).

La imagen API instala las CA de Debian y configura `SSL_CERT_FILE` y
`SSL_CERT_DIR` con sus rutas de sistema. libpq incluido en `psycopg[binary]` puede
tener rutas OpenSSL diferentes; estas variables permiten usar `sslrootcert=system`
sin desactivar la verificación del certificado ni del hostname. Una conexión real
desde el contenedor confirmó TLS 1.3 con esta configuración.

## VPS

Instalar Docker Engine y Compose en el VPS mediante el procedimiento oficial de
su distribución. Usar un checkout público del proyecto; gestionar SSH y el acceso
administrativo de forma privada. Los scripts no solicitan ni transmiten contraseñas
SSH. No añaden un daemon, otro proxy global ni reglas DNS.

Crear el archivo privado fuera del repositorio; completar valores en un editor
local sin copiarlos al terminal, al chat o al historial:

```bash
install -d -m 700 "$HOME/.config/humanizar"
# Ejecutar sólo si no existe; no sobrescribir una configuración ya preparada.
if [ ! -e "$HOME/.config/humanizar/production.env" ]; then
  install -m 600 config/production.env.example "$HOME/.config/humanizar/production.env"
fi
python3 scripts/deploy-vps.py check --env-file "$HOME/.config/humanizar/production.env"
python3 scripts/deploy-vps.py up --env-file "$HOME/.config/humanizar/production.env"
python3 scripts/deploy-vps.py status --env-file "$HOME/.config/humanizar/production.env"
```

El proyecto Compose `humanizar-ai-agent` da nombres propios a sus contenedores,
redes y volumen. `--project` permite escoger otro nombre exclusivo, y `--port`
otro puerto libre. La API escucha en `127.0.0.1:8087`; una colisión hace fallar
Docker y debe resolverse eligiendo un puerto libre. El sandbox no publica puertos,
ni recibe credenciales ni monta sockets del host; usa una red interna,
filesystem de lectura, usuario no root, límites de procesos/memoria y presets.

Integrar el virtual host HTTPS de la API en el proxy existente. El proxy debe
validar `x-origin-secret` contra su configuración privada, pasar el protocolo HTTPS
al upstream y preservar streaming SSE y cookies. No registrar el header privado.
La receta activa `--proxy-headers --forwarded-allow-ips '*'` porque el puerto sólo
se expone en loopback y la red API es exclusiva. Mantener esa red reservada al
proyecto/proxy; si se comparte con contenedores no confiables, configurar la IP del
proxy explícitamente. No exponer el puerto `8087` directamente a Internet.

Verificar localmente `http://127.0.0.1:8087/api/health`, después el origen HTTPS por
el proxy y finalmente `/api/health` desde Vercel. Registrar sólo resultados públicos
de salud; el origen protegido debe rechazar peticiones sin autorización del proxy.
La configuración del proxy, su certificado, DNS y accesos reales se comprueban en
el entorno correspondiente, no se presuponen por la existencia de este archivo.

Antes de publicar o habilitar el frontend, crear el primer administrador desde
el CLI privado del contenedor, sin contraseña en argumentos:

```bash
export LUMEN_PRODUCTION_ENV="$HOME/.config/humanizar/production.env"
export COMPOSE_DISABLE_ENV_FILE=1
docker compose -p humanizar-ai-agent -f compose.production.yaml exec api \
  uv run --no-sync python -m app.manage create-admin
```

El CLI solicita los datos de forma interactiva; `--stdin-json` acepta un objeto
privado `{name,email,password}` generado en memoria por el operador, sin guardarlo
en un archivo público o incorporarlo a argumentos. La salida contiene sólo el estado
de creación, sin sesión ni JWT. También existe el bootstrap HTTP
del primer administrador protegido por `X-Bootstrap-Token`; no enviar el token en
URLs ni comandos con argumentos visibles. Tras provisionar el administrador,
rotar `AUTH_BOOTSTRAP_TOKEN` en el archivo privado y recrear la API; conservar
`JWT_SECRET` estable para las sesiones. Las
cuentas siguientes se registran como clientes; ninguna entrada de un modelo decide
el usuario o el rol. No hay endpoint para configurar la clave de Anthropic desde
el navegador.

Los dos secretos son obligatorios para `deploy-vps.py check/up`, incluso después
del bootstrap; `stop/status` siguen disponibles si se retiran credenciales.
El desarrollo local conserva el comportamiento de secreto generado cuando
`JWT_SECRET` está vacío. No hacer accesible una instalación nueva antes de confirmar
que el CLI creó el administrador y que el bootstrap HTTP ya está cerrado.

## Vercel

Configurar **Root Directory = `frontend`** en los ajustes del proyecto Vercel.
Invocar el CLI desde la **raíz del repositorio**, donde se guarda el enlace local
`.vercel/project.json`; Vercel aplica el Root Directory configurado y evalúa
`frontend/vercel.ts`. No ejecutar el deploy desde la subcarpeta `frontend`, porque
volvería a aplicar ese prefijo. Esta combinación sigue el procedimiento de
[monorepos de Vercel](https://vercel.com/docs/monorepos).
La `.vercelignore` de la raíz permite sólo el árbol frontend y después excluye
sus posibles archivos privados y de ejecución; deja fuera backend, sandbox,
`.env`, datos, material, artefactos, dependencias instaladas y estado de agentes.
Se conservan `frontend/vercel.ts`, `frontend/deployment`, fuentes y lock/config de
build. Revisar esta lista al añadir entradas públicas que el build necesite fuera
del frontend. El enlace local `.vercel` tampoco se publica.
El proyecto usa framework Vite, Node **22 o posterior**, instalación
`npm ci` y build `npm run build`. `frontend/vercel.ts` genera el rewrite `/api`
hacia `API_ORIGIN` y agrega el header privado mediante una referencia de despliegue
a `ORIGIN_SECRET`. El valor no debe aparecer en código, `dist`, variables `VITE_*`
ni solicitudes del navegador. La URL pública de la API puede ser visible.
La configuración programática se evalúa en el despliegue.
[Configuración Vercel](https://vercel.com/docs/project-configuration).

Instalar primero las dependencias frontend (`npm ci --prefix frontend`, o
`make setup`): el compilador local necesita `@vercel/config`. La allowlist raíz de
`.vercelignore` usa `/*` y `!frontend`: permite la carpeta antes de recorrerla y
después excluye configuración privada y archivos de ejecución. Una negación con
sólo `!frontend/` puede podar la carpeta y subir cero archivos.

Autenticar y vincular el CLI en el ordenador del operador. La versión comprobada
para este procedimiento es **54.4.1**; `npm exec` la ejecuta sin instalación global:

```bash
npm exec --yes --package=vercel@54.4.1 -- vercel login
npm exec --yes --package=vercel@54.4.1 -- vercel link
```

Suministrar `API_ORIGIN` y `ORIGIN_SECRET` al proceso por un canal privado del
operador, sin escribir valores de secreto en comandos, archivos públicos o chat.
El helper no lee ni crea archivos `.env` de frontend y no descarga secretos de
Vercel. `--check` sólo valida la forma local, sin probar acceso remoto:

```bash
python3 scripts/deploy-vercel.py --check
# Primer despliegue de preview, añade las variables del proyecto por stdin:
npm exec --yes --package=vercel@54.4.1 -- python3 scripts/deploy-vercel.py --configure-env
# Producción, con variables independientes para ese destino:
npm exec --yes --package=vercel@54.4.1 -- python3 scripts/deploy-vercel.py --production --configure-env
```

Si las variables ya están configuradas, omitir `--configure-env`. Para reemplazarlas
de forma deliberada, combinarlo con `--update-env`; antes coordinar el mismo secreto
en el proxy. Las entradas viajan como JSON por stdin a la API de variables de Vercel,
sin el prompt de rama que algunas versiones del CLI requieren para preview;
`ORIGIN_SECRET` se almacena como variable protegida. Los identificadores del proyecto
se obtienen del enlace local `.vercel/project.json`, sin leer credenciales del CLI.
El helper suprime logs de los comandos y no muestra secretos;
el operador consulta estado y URL en el dashboard privado. Si hay un fallo de build,
revisar los logs privados, sin pegarlos completos antes de sanitizarlos.
[CLI de variables Vercel](https://vercel.com/docs/cli/env).

Validar login/refresh/logout, streaming, recuperación con fuentes, la lista aislada
de solicitudes y los presets. Comprobar que JS y `dist` no contienen credenciales,
que Swagger `/api/docs` y OpenAPI `/api/openapi.json` siguen el mismo origen, y que
el backend conserva los datos tras recrear el contenedor. Un HTTP 200 no demuestra
una llamada real a Anthropic: registrar esa comprobación por separado si se realiza.

## Backup, restauración y rollback

Hacer backups privados de **ambas** capas antes de actualizar: PostgreSQL del schema
del proyecto y el volumen `/data` con documentos, Qdrant y material de autenticación.
Un backup de documentos puede contener datos personales. Mantenerlo fuera del
repositorio, con directorio `0700`, archivos `0600` y almacenamiento cifrado.

Para PostgreSQL usar un servicio de libpq configurado de forma privada
(`PGSERVICEFILE` y `.pgpass` propios, modo `0600`) con TLS verificado. El nombre de
servicio público no contiene credenciales:

```bash
umask 077
BACKUP_DIR="$HOME/.local/share/humanizar-backups/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$HOME/.local/share/humanizar-backups"
mkdir "$BACKUP_DIR"
PGSERVICE=humanizar pg_dump --schema=lumen --format=custom --file="$BACKUP_DIR/postgres.dump"
```

Para una copia coherente de Qdrant local, detener la API y copiar `/data` a un
directorio **nuevo**; el sandbox puede seguir activo. No copiar un Qdrant abierto:

```bash
export LUMEN_PRODUCTION_ENV="$HOME/.config/humanizar/production.env"
export COMPOSE_DISABLE_ENV_FILE=1
docker compose -p humanizar-ai-agent -f compose.production.yaml stop api
API_CONTAINER="$(docker compose -p humanizar-ai-agent -f compose.production.yaml ps -a -q api)"
mkdir "$BACKUP_DIR/data"
docker cp "$API_CONTAINER:/data/." "$BACKUP_DIR/data"
docker compose -p humanizar-ai-agent -f compose.production.yaml start api
```

Completar copia de PostgreSQL mientras la API está detenida cuando se requiera una
instantánea coordinada de las dos capas. Comprobar permisos y legibilidad del backup
de forma privada. Si la copia falla, arrancar la API igualmente antes de terminar.

Restaurar primero en una base de datos **nueva** con rol/schema dedicado y en un
volumen **nuevo** de un proyecto Compose separado:

```bash
pg_restore --no-owner --no-acl --exit-on-error \
  --dbname='service=humanizar_restore' "$BACKUP_DIR/postgres.dump"
```

El servicio privado `humanizar_restore` debe apuntar a esa base vacía;
no usar `--clean` ni sobrescribir la base activa.
Copiar `/data` al volumen vacío conservando ownership `10001:10001`, arrancar una API
aislada con otro puerto loopback y comprobar login, fuentes y solicitudes antes de
cambiar el upstream del proxy. No extraer backups no confiables ni mezclar un secreto
master de otra instalación. Guardar la instalación anterior hasta validar la nueva.

Para rollback de código, desplegar una revisión previamente validada en un checkout
separado y cambiar el upstream sólo después de su smoke; no hacer reset del árbol
de trabajo ni revertir datos. `python3 scripts/deploy-vps.py stop --env-file ...`
detiene sólo este proyecto y conserva los volúmenes. No ejecutar `down -v`, borrar
schemas o reemplazar backups existentes como parte de esta receta.
