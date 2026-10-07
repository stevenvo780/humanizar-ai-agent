# Instalar en otra laptop

La aplicación no requiere Claude Code para arrancar. El desarrollo con Claude Code
requiere su propia instalación y autenticación; ninguna sesión se distribuye en Git.
`config/env.example` es la copia pública que pueden leer los agentes. El bootstrap
usa `.env.example` para crear la configuración local; nunca sustituye una existente.

## Herramientas necesarias

| Herramienta | Versión y uso |
| --- | --- |
| Git, Bash y GNU Make | Clonar y ejecutar los comandos de proyecto |
| uv | 0.11.21 o posterior; versión comprobada 0.11.21 |
| Node.js y npm | Node.js 22 o posterior; comprobado con 22.22.3 y npm 10.9.8 |
| Python | uv prepara 3.12; `LUMEN_PYTHON=3.13 make setup` selecciona otra versión compatible |
| Docker con Compose | Opcional para el terminal aislado y el stack completo |
| Claude Code | Opcional; >=2.1.280 para Opus 5.5, comprobado con 2.1.286 |

Instala uv siguiendo [sus instrucciones oficiales](https://docs.astral.sh/uv/getting-started/installation/)
y Node.js desde [Node.js](https://nodejs.org/en/download). En Windows utiliza WSL2
con una distribución Linux. Los scripts del sandbox y del importador usan límites
Linux: para esas funciones se recomienda Linux/WSL2. macOS no tiene todos esos
límites y no se presenta como un entorno completamente verificado.

## Clon limpio

```bash
git clone --branch dev https://github.com/stevenvo780/humanizar-ai-agent.git
cd humanizar-ai-agent
make setup
make dev
```

`make setup` comprueba versiones, sincroniza los locks backend/sandbox, ejecuta
`npm ci` y prepara los pesos multilingües. Solo crea `.env` si no existe; conserva
su contenido y no lo imprime. También inicializa el puntero local de Spec Kit
si falta. Las cuentas y datos se crean al utilizar la aplicación, no al clonar.
La primera ejecución puede descargar Python y pesos del modelo; necesita internet.

Para instalar dependencias sin preparar pesos:

```bash
bash scripts/bootstrap.sh --skip-model-download
```

Esto no convierte la aplicación a modo offline. Configura `EMBEDDING_PROVIDER=hash`
localmente para omitir la inferencia semántica, o prepara los pesos antes de arrancar.
El modo hash es léxico y se identifica como tal. Consulta `--help` para las opciones.

La web usa http://127.0.0.1:5173 y la API http://127.0.0.1:8000. Swagger y OpenAPI
están bajo `/api/docs` y `/api/openapi.json`; también funcionan desde el proxy web.
Para otra máquina de tu red, `make lan` publica la web en las interfaces del host:
abre `http://<IP-LAN-del-host>:5173`. Usa redes de confianza y configura HTTPS antes
de desplegar fuera del entorno local. El sandbox nunca se ejecuta directamente en el host.

## Claude Code y Spec Kit

Instala y autentica Claude Code siguiendo [la documentación oficial](https://code.claude.com/docs/en/quickstart).
`make setup` no instala ni autentica ese CLI. Después:

```bash
make claude
# Otra selección para esa sesión:
make claude CLAUDE_CODE_MODEL=opus
```

El valor preparado es `claude-opus-5-5`. La disponibilidad efectiva depende de
tu cuenta/proveedor; confirma el modelo en `/model`. El modelo de la web permanece
independiente y se configura en el entorno privado del backend.

Los diez skills de Spec Kit ya están versionados. Para administrar la CLI fijada:

```bash
make speckit
specify version
make speckit-check
```

`make speckit` instala únicamente `specify-cli==1.0.7` mediante uv, bajo tu usuario.
No ejecutes `specify init --here` sobre el clon: ya tiene el scaffolding necesario.
La selección de feature y el flujo de adaptación están en [SPECKIT.md](SPECKIT.md).

## Datos propios

Crea tu administrador desde la web. Configura una credencial Anthropic propia
en el `.env` privado del backend y reinicia la API si vas a usar Haiku.
No existen credenciales predeterminadas ni formularios web para introducir claves.
Las pruebas automatizadas simulan el proveedor; no validan tu cuenta de Anthropic.
`make check` ejecuta los controles del proyecto. [VALIDATION.md](VALIDATION.md)
separa la evidencia registrada de Docker, Anthropic y otros pendientes.

## Separar local y producción

| Entorno | Configuración y persistencia |
| --- | --- |
| Laptop local | `.env` privado del backend; `DATABASE_URL` vacío usa SQLite. Los datos viven en el `DATA_DIR` local. |
| Preparación de producción | `.env.production` privado, ignorado por Git y modo `0600`. No reemplaza `.env` ni se carga automáticamente. |
| Preparación de Vercel | `.env.vercel` privado, ignorado por Git y modo `0600`; contiene únicamente la configuración del proxy y no se publica. |
| Runtime VPS | Archivo externo `/opt/humanizar-ai-agent/production.env`; PostgreSQL remoto con schema dedicado `lumen` y TLS completo. Documentos y Qdrant continúan en `/data` persistente. |
| Vercel | Sólo configuración del proxy: `API_ORIGIN` y `ORIGIN_SECRET` gestionados en servidor. Ninguna clave Anthropic, URL PostgreSQL o secreto JWT. |

No copiar archivos privados completos, bases de datos, volúmenes, cookies,
sesiones de agentes o credenciales de otra instalación al clonar. Cada entorno
local puede tener su propio administrador y corpus. Pasar de SQLite a PostgreSQL
selecciona otro almacén; no migra automáticamente cuentas o conversaciones.
Preservar los secretos existentes en el VPS durante las actualizaciones y los
backups. [DEPLOYMENT.md](DEPLOYMENT.md) describe el alta inicial y
[OPERATIONS.md](OPERATIONS.md) describe actualización y recuperación.

## Equipo Fedora previsto

El destino solicitado es `~/Documentos/repos/SoftopPrueba`. Al 2026-10-07 faltan
usuario e IP del equipo; la instalación remota no se ha ejecutado ni validado.
Seguir [FEDORA.md](FEDORA.md) con el operador del equipo. Para un destino vacío:

```bash
mkdir -p "$HOME/Documentos/repos"
git clone --branch dev https://github.com/stevenvo780/humanizar-ai-agent.git \
  "$HOME/Documentos/repos/SoftopPrueba"
cd "$HOME/Documentos/repos/SoftopPrueba"
make setup
make check
make dev
```

Si el directorio ya contiene un checkout, conservar sus cambios y configuración;
no borrar ni sobrescribirlo para repetir la instalación. Descargar el código
público no copia el acceso de producción. Instalar y autenticar Claude Code en
ese equipo mediante el canal privado del dueño; no trasladar historiales ni
ajustes de sesión desde otro runtime.
