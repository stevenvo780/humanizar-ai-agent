# Despliegue reproducible

Instancia publicada: [web](https://softop-ai-agent.vercel.app),
[documentación](https://softop-ai-agent.vercel.app/docs),
[API](https://softop-ai-agent.vercel.app/api/docs) y el endpoint de la prueba
`POST https://softop-ai-agent.vercel.app/preguntar`. Los resultados observados
de login, Haiku, TLS, sandbox y persistencia están en [VALIDATION.md](VALIDATION.md).

**Estado al 2026-10-07:** el frontend publicado está disponible en
Vercel; la revisión y comprobaciones vigentes están en [VALIDATION.md](VALIDATION.md).
Frontend y API publicados en `9ac20b0` el 2026-10-07, tras un backup coordinado de
PostgreSQL y `/data`; la salud HTTPS declara gestión de clientes y lectura de documentos.
En Fedora, el portátil Fedora 44 ya contiene el checkout en `~/Documentos/repos/SoftopPrueba` (enlace simbólico a un disco de datos); con uv 0.11.21, `make setup` y `make check` pasaron allí el 2026-10-07.
El operador preparó `.env.production` y `.env.vercel` privados, modo `0600` e
ignorados por Git, preservando `.env` local. Su comprobación de sólo lectura
confirmó PostgreSQL 18.6, TLS 1.3 y el schema dedicado; no actualizó la API ni
modificó cuentas o contenido.
El procedimiento de actualización, backup y recuperación está en
[OPERATIONS.md](OPERATIONS.md); las tareas de la interfaz están en
[ADMIN.md](ADMIN.md).

El proyecto Vercel está conectado al repositorio GitHub con rama de producción
`dev`. Un push a esa rama actualiza el frontend; el backend se actualiza por
separado en el VPS mediante pull y el helper de Compose, después del backup.
El lector de documentos necesita la API actualizada: `/api/health` debe declarar
`features.document_reading: true`; la sección **Clientes** requiere
`features.customer_management: true`. La migración añade `document_contents` a la
base de conocimiento SQLite, conservando la tabla histórica de documentos,
los fragmentos y los vectores. No modifica el schema PostgreSQL. La UI mantiene
la carga y el borrado disponibles mientras un servidor anterior todavía no declara
esa capacidad.
GitHub Actions permanece definido, pero su runner no inicia por un bloqueo de
facturación de la cuenta. El despliegue y las pruebas reales registrados no
dependen de atribuir éxito a ese workflow.

El frontend se publica en Vercel y conserva llamadas del navegador a `/api` en el
mismo origen. La API FastAPI y el sandbox se ejecutan en un VPS mediante
`compose.production.yaml`. PostgreSQL remoto almacena cuentas, sesiones y
solicitudes; Qdrant en modo local, documentos y los archivos privados existentes
permanecen en el volumen `/data` del VPS. Se usa un único worker de API por la persistencia local
de Qdrant. Este documento describe el procedimiento; la publicación y las
comprobaciones reales de cada entorno requieren evidencia de ese despliegue.

En la instancia preparada, el checkout está en `/opt/humanizar-ai-agent/repo`,
el entorno privado en `/opt/humanizar-ai-agent/production.env` y el acceso del
administrador en `/opt/humanizar-ai-agent/operator-access.json`. Los dos archivos
privados pertenecen al operador y tienen permisos `0600`; no se publican ni se
incorporan al ZIP. La configuración del proxy también queda fuera del checkout.

**Nombres heredados de infraestructura.** El repositorio GitHub
`stevenvo780/humanizar-ai-agent`, el proyecto Vercel `humanizar-ai-agent`, el proyecto
Compose `humanizar-ai-agent` con su volumen `humanizar-ai-agent_knowledge` y las rutas
`/opt/humanizar-ai-agent/...` conservan el nombre de la primera empresa de ejemplo.
Renombrarlos rompería el despliegue o separaría el volumen de datos; no identifican a la
empresa configurada, que es Softop. El dominio público es `softop-ai-agent.vercel.app`.

## Fuente y desarrollo

```bash
git clone --branch dev https://github.com/stevenvo780/humanizar-ai-agent.git lumen
cd lumen
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
| `API_ORIGIN` | Vercel, configuración de despliegue | Origen público HTTPS de la API, sin ruta, usuario, query ni fragmento. Preparación local en `.env.vercel` privado. |
| `ORIGIN_SECRET` | Vercel protegido y proxy privado del VPS | Autoriza el tráfico del rewrite; nunca tiene prefijo `VITE_`. |
| `ANTHROPIC_API_KEY` | API, archivo privado | Clave del proveedor; `auto` sin clave usa demo, `anthropic` exige una clave. |
| `LLM_MODE` / `ANTHROPIC_MODEL` | API | `auto`, `demo` o `anthropic`; el modelo web es independiente de Claude Code. |
| `DATABASE_URL` | API, archivo privado | PostgreSQL remoto con `sslmode=verify-full&sslrootcert=system`. |
| `DATABASE_SCHEMA` | API | Schema exclusivo `lumen`, sin modificar tablas de otros proyectos. |
| `JWT_SECRET` | API, archivo privado | Obligatorio en producción, al menos 32 caracteres; mantenerlo estable. |
| `AUTH_BOOTSTRAP_TOKEN` | API, archivo privado | Obligatorio en producción, al menos 32 caracteres; protege el bootstrap HTTP mediante `X-Bootstrap-Token`. |
| `CORS_ORIGINS` | API | Array JSON de los orígenes HTTPS exactos del frontend. |
| `COMPANY_NAME` / `COMPANY_DESCRIPTION` / `ASSISTANT_NAME` | API | Perfil público: `Softop`, descripción derivada de las FAQ y `Asistente Softop`. |
| `COMPANY_WEBSITE` | API | Enlace público opcional HTTP(S), sin credenciales. Vacío para Softop. |
| `COMPANY_SUGGESTED_QUESTIONS` / `COMPANY_PRODUCTS` | API | Arrays JSON; `null` usa valores genéricos y `[]` los desactiva. Softop usa cuatro preguntas de las FAQ y `[]` productos. |
| `KNOWLEDGE_DIR` | API | Corpus inicial `knowledge/softop`. Añade los archivos que falten por nombre; no borra documentos que ya estén en `/data`. |
| `LUMEN_PRODUCTION_ENV` | Helper/Compose | Ruta absoluta del archivo privado externo al checkout. |
| `LUMEN_API_PORT` | Helper/Compose | Puerto loopback de la API, por defecto `8087`. |

En el entorno de trabajo, `.env` conserva la instalación local SQLite. El operador
puede preparar `.env.production` como copia privada ignorada por Git, modo `0600`,
con las variables aprobadas de producción; no se carga automáticamente ni se usa
como archivo de Compose dentro del checkout. El runtime del VPS consume el archivo
externo `/opt/humanizar-ai-agent/production.env`. Vercel recibe solamente las
variables de su proxy, preparadas en `.env.vercel` privado, no el archivo del backend.
El helper Vercel recibe variables de proceso y no carga ese archivo automáticamente.
No leer ni imprimir estos archivos durante una revisión de código, publicación o
prueba automatizada.

La sesión MCP de desarrollo se prepara por separado con el
[CLI de login privado](MCP.md); no forma parte del entorno Vercel ni se transfiere
al portátil. El inventario de correcciones está en [QUALITY.md](QUALITY.md).

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
cd /opt/humanizar-ai-agent/repo
# Sólo para una instalación nueva; conservar el archivo privado existente.
if [ ! -e /opt/humanizar-ai-agent/production.env ]; then
  install -m 600 config/production.env.example /opt/humanizar-ai-agent/production.env
fi
# Completar la plantilla en un editor privado antes de validar o arrancar.
python3 scripts/deploy-vps.py check --env-file /opt/humanizar-ai-agent/production.env
python3 scripts/deploy-vps.py up --env-file /opt/humanizar-ai-agent/production.env
python3 scripts/deploy-vps.py status --env-file /opt/humanizar-ai-agent/production.env
```

El proyecto Compose `humanizar-ai-agent` (nombre heredado) da nombres propios a sus contenedores,
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
export LUMEN_PRODUCTION_ENV=/opt/humanizar-ai-agent/production.env
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
`npm ci` y build `npm run build`. `frontend/vercel.ts` genera los rewrites `/api` y
`/preguntar` hacia `API_ORIGIN` y agrega a ambos el header privado mediante una referencia
de despliegue a `ORIGIN_SECRET`. El valor no debe aparecer en código, `dist`, variables `VITE_*`
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
de solicitudes, los presets y `POST /preguntar` sin sesión. Comprobar que JS y `dist` no contienen credenciales,
que Swagger `/api/docs` y OpenAPI `/api/openapi.json` siguen el mismo origen, y que
el backend conserva los datos tras recrear el contenedor. Un HTTP 200 no demuestra
una llamada real a Anthropic: registrar esa comprobación por separado si se realiza.

## Backup, restauración y rollback

Antes de actualizar, obtener una copia coordinada de PostgreSQL y `/data`, además
de preservar la configuración privada estable. PostgreSQL contiene cuentas,
sesiones, conversaciones y solicitudes; la base de conocimiento sigue en SQLite
y Qdrant dentro del volumen. Copiar únicamente PostgreSQL no conserva los documentos.

El [runbook de operaciones](OPERATIONS.md) contiene los comandos completos para:

1. Verificar revisión, árbol Git limpio y configuración privada.
2. Detener la API, volcar el schema `lumen` y copiar `/data`, con reinicio incluso
   si falla la copia. El sandbox puede permanecer activo.
3. Avanzar mediante `git fetch` y `git merge --ff-only`, validar la revisión y
   ejecutar `deploy-vps.py check/up/status`.
4. Comprobar HTTPS, bootstrap cerrado y flags de clientes/lector, sin publicar
   respuestas autenticadas ni hacer una llamada de pago como parte del health.
5. Volver a una revisión compatible desde un worktree separado, conservando el
   mismo proyecto Compose, el volumen, PostgreSQL y los secretos de autenticación.
6. Ensayar restauración en una base y volumen nuevos antes de sustituir los activos.

Usar un servicio libpq privado con TLS verificado para `pg_dump`/`pg_restore`;
no poner credenciales en argumentos. Guardar backups fuera del checkout, con
permisos privados y cifrado. No copiar Qdrant mientras otro proceso lo tenga abierto.
No arrancar dos APIs sobre el mismo volumen local ni usar `down -v`, borrar schemas
o regenerar JWT para hacer rollback. Una migración futura requiere su propia
revisión de compatibilidad; la tabla aditiva del lector conserva la estructura
histórica de documentos.
