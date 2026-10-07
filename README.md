# Lumen

Asistente de atención al cliente con información empresarial, interfaz React/TypeScript, API
FastAPI, recuperación en Qdrant, Claude Haiku, herramientas acotadas y MCP.
Preparado para adaptar documentos y requisitos de una prueba técnica.
El proyecto prepara la prueba de **Softop**; **Humanizar** se conserva como empresa
de ejemplo hasta que el dueño solicite cambiar la identidad y el material.

**Web publicada:** [Humanizar IA](https://humanizar-ai-agent.vercel.app) ·
[Documentación técnica](https://humanizar-ai-agent.vercel.app/docs) ·
[API Swagger](https://humanizar-ai-agent.vercel.app/api/docs).
Frontend Vercel, FastAPI y sandbox Docker en VPS, PostgreSQL con TLS y Qdrant
persistente. El administrador se provisiona por un canal privado; la web permite
registrar cuentas de clientes. Configuración y repetición en
[DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Arranque local

Requisitos: Git, Bash, GNU Make, uv 0.11.21 o posterior y Node.js 22 o posterior
con npm. Se recomienda Linux; en Windows utiliza WSL2. uv prepara Python 3.12
si no encuentra un intérprete compatible. La primera instalación necesita internet.

```bash
git clone https://github.com/stevenvo780/humanizar-ai-agent.git
cd humanizar-ai-agent
make setup
make dev
```

Abre **http://127.0.0.1:5173**. Swagger está en **http://127.0.0.1:5173/api/docs**;
el esquema está en **http://127.0.0.1:5173/api/openapi.json**. La API directa
usa los mismos paths bajo el puerto 8000.
La presentación técnica pública está en **http://127.0.0.1:5173/docs**, sin login:
arquitectura, ciclo del agente, datos, seguridad, herramientas y evidencia de calidad.
Consulta [portabilidad y dependencias](docs/PORTABILITY.md) para una instalación limpia.
La configuración inicial utiliza Humanizar y cinco resúmenes de fuentes públicas
oficiales en `backend/knowledge/humanizar`. Se cargan automáticamente sin duplicarse.
Sin una clave nueva, la aplicación funciona en modo demo extractivo, identificado
en pantalla. Ese modo verifica carga, recuperación y herramientas sin consumir API.

Al abrir la web crea tu primera cuenta de administrador. Las cuentas posteriores
son de clientes. El acceso usa JWT de 30 minutos y sesiones renovables revocables;
las contraseñas se guardan con Argon2 y el historial pertenece a cada cuenta.

Para usar Claude, configura `ANTHROPIC_API_KEY` en el `.env` privado del backend
con tu editor. El navegador no tiene un formulario ni rutas para guardar claves.
`LLM_MODE=auto` utiliza Anthropic cuando existe una clave; `LLM_MODE=anthropic`
exige una. Reinicia la API después de cambiar la configuración.
Las claves nunca se envían al navegador ni al sandbox.

Para acceder desde otra máquina de la LAN, usa `make lan` y abre
`http://<IP-LAN-del-host>:5173`. La web utiliza el proxy de Vite para consultar la API.
Si este workspace corre dentro de Docker, el host debe publicar o reenviar el
puerto 5173 del contenedor; su IP de bridge no equivale a la IP de la LAN.

## Docker

```bash
make setup
make docker
```

Abre **http://127.0.0.1:8080**. Compose levanta web, API y sandbox. Qdrant local
persiste en el volumen `knowledge`; la API usa un solo worker. El sandbox es
no privilegiado, tiene filesystem de solo lectura, límites de recursos y una
red interna. No recibe la clave de Anthropic, montajes del host ni Docker socket.
`make stop` detiene el stack sin borrar el volumen.

El daemon Docker debe estar activo. La ruta local permite preparar y usar el
chat aunque Docker no esté disponible; la herramienta terminal se identifica
como deshabilitada hasta conectar el sandbox.

## Lo que puedes probar

- Preguntar por Humanizar, Cauce, agentes de IA y productos; inspeccionar las fuentes.
- Crear cuentas de cliente, cerrar sesión y recuperar conversaciones desde la base de datos.
- Subir TXT, Markdown, PDF de texto, DOCX, JSON, CSV o ZIP desde Documentación como administrador.
- Probar calculadora, búsqueda, MCP y los presets de terminal disponibles.
  La búsqueda MCP utiliza una sesión propia preparada con el [CLI privado](docs/MCP.md).
- Recomendar productos según el proceso y preparar solicitudes de demo o soporte.
- Confirmar cada solicitud antes de guardarla; consultar su ID en Mis solicitudes.
- Revisar las solicitudes de clientes en la bandeja del administrador.
- Crear y listar clientes desde administración cuando la API declara esa capacidad;
  el alta conserva la sesión del administrador. Consulta [la guía](docs/ADMIN.md).
- Ver cada ejecución real de herramientas y los fragmentos recuperados.
- Iniciar una conversación nueva y revisar respuestas anteriores.

El modo Anthropic utiliza un ciclo de `tool_use`/`tool_result` limitado. El registro
de actividad muestra herramientas ejecutadas, no razonamiento interno del modelo.
El backend devuelve eventos SSE de estado y herramientas durante la ejecución;
la respuesta se emite después de sanear y ordenar sus fuentes.

## Recuperación vectorial

Qdrant funciona sin servidor adicional en modo persistente local. Puedes apuntar
`QDRANT_URL` a un servidor externo. La configuración preparada utiliza embeddings
semánticos multilingües de FastEmbed; `make setup` descarga sus pesos antes de la prueba.
El modo alternativo `hash` utiliza vectores léxicos de forma
determinista y sin descargas; no es una representación semántica neuronal.
La opción `fastembed` utiliza embeddings semánticos con un modelo descargable.
Consulta [las instrucciones de RAG](docs/RAG.md) antes de cambiar el proveedor.

SQLite guarda usuarios, sesiones, conversaciones, mensajes y solicitudes comerciales
en `DATA_DIR/application.sqlite3`. Documentos y vectores
persisten junto a esa base. No hay cuentas ni contraseñas predeterminadas.
Si configuras `DATABASE_URL`, esos registros relacionales se guardan en PostgreSQL
dentro de un schema dedicado; Qdrant y el corpus conservan su volumen persistente.
Las solicitudes son registros reales de esta aplicación; no envían notificaciones
ni confirman reuniones externas.

## Despliegue y portátil

La web se despliega en Vercel y envía `/api` al backend FastAPI por HTTPS. La API,
Qdrant y el sandbox se ejecutan en el VPS con Docker; PostgreSQL guarda los datos
relacionales. `ANTHROPIC_API_KEY`, `DATABASE_URL` y los secretos de autenticación
pertenecen al entorno privado del backend. Vercel utiliza `API_ORIGIN` y un secreto
del proxy; ninguna credencial utiliza el prefijo público `VITE_`.

[DEPLOYMENT.md](docs/DEPLOYMENT.md) describe las variables, aprovisionamiento,
comprobaciones, backups y repetición. [OPERATIONS.md](docs/OPERATIONS.md) reúne el
procedimiento de actualización y el estado de publicación por componente.
[FEDORA.md](docs/FEDORA.md) prepara la copia en
`~/Documentos/repos/SoftopPrueba`, Python, Node, Claude Code y Spec Kit para presentar
desde el portátil.

La configuración privada de este workspace se separa en `.env` para desarrollo,
`.env.production` para preparar la API productiva y `.env.vercel` para el proxy.
Los archivos tienen permisos `0600`, están ignorados y no se incluyen en Git ni
en el ZIP. El VPS consume su archivo externo `/opt/humanizar-ai-agent/production.env`;
no se sobrescriben sus secretos ni se regeneran claves de sesión durante una actualización.

Para adaptar otra empresa, cambia la identidad en `.env`, vacía `KNOWLEDGE_DIR`
y utiliza un `DATA_DIR` distinto, o apunta `KNOWLEDGE_DIR` a tus archivos Markdown/TXT.
Las rutas relativas de ese directorio se resuelven desde `backend/`.

## Claude Code y Spec Kit

```bash
make claude
```

Claude Code usa Opus 5.5 para desarrollar y adaptar la prueba. Se requiere
Claude Code 2.1.280 o posterior para ese modelo; aquí se verificó la versión 2.1.286.
Puedes elegir otro con `make claude CLAUDE_CODE_MODEL=opus` o con `/model`.
El alias `opus` y el ID `claude-opus-5-5` están documentados oficialmente en
[configuración de modelos](https://code.claude.com/docs/en/model-config).
El agente de la web
usa la API de Anthropic con su propio modelo configurable (Haiku por defecto).
El proyecto incluye `CLAUDE.md`, constitución, Spec Kit real y un servidor MCP
read-only configurado en `.mcp.json`. En Claude Code, `/mcp` permite aprobar e
inspeccionar la conexión local. La API debe estar arrancada para consultar datos.
Los diez skills oficiales de Spec Kit 1.0.7 vienen incluidos; no hace falta
regenerar el proyecto. [SPECKIT.md](docs/SPECKIT.md) documenta cada comando,
la auditoría y cómo seleccionar la feature de adaptación `002`.

Sigue [la guía de los 20 minutos](docs/EXAM_20_MIN.md) y copia
[el prompt de adaptación](docs/EXAM_PROMPT.txt) cuando llegue el ZIP real.
La base no puede anticipar requisitos todavía desconocidos: el objetivo es reducir
el trabajo inicial y dejar tiempo para resolver lo que realmente evalúen.

## Verificación y entrega

```bash
make check
make package
```

La verificación ejecuta lint, formato, tipos, pruebas y build. El paquete excluye
claves, dependencias instaladas, datos privados y sesiones locales.
El workflow de GitHub repite esos controles, revisa el historial con Gitleaks y
prepara un job de integración Docker. Su ejecución requiere un runner disponible;
la evidencia local y los límites pendientes se documentan por separado.
Consulta [la arquitectura](docs/ARCHITECTURE.md), [el contrato](docs/API_CONTRACT.md)
y [el estado de validación](docs/VALIDATION.md). La [auditoría y guía de adaptación](docs/QUALITY.md)
registra los hallazgos corregidos y los límites comprobados. La gestión de documentos y cuentas
se explica en [Administración](docs/ADMIN.md).

La implementación sigue las referencias oficiales de
[Spec Kit](https://github.com/github/spec-kit),
[Claude tool use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools),
[Qdrant Client](https://github.com/qdrant/qdrant-client) y
[MCP en Claude Code](https://code.claude.com/docs/en/mcp).
