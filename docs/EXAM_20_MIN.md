# Preparación y adaptación en 20 minutos

## Antes de la prueba

La preparación de Fedora está en [FEDORA.md](FEDORA.md). El despliegue con frontend
Vercel, backend Docker y PostgreSQL está en [DEPLOYMENT.md](DEPLOYMENT.md). Para una
presentación sin red, deja `DATABASE_URL` vacío y usa SQLite local con datos propios;
configura por separado una clave privada si necesitas llamadas reales a Anthropic.

1. Ejecuta `make setup` (uv >=0.11.21) y `make check`. En Fedora exporta antes
   `FASTEMBED_CACHE_PATH=$HOME/.cache/fastembed`: `/tmp` es tmpfs y perdería el modelo.
2. Configura `ANTHROPIC_API_KEY` en el `.env` privado del backend, ejecuta `make dev`,
   abre la web, crea tu administrador y verifica una respuesta con fuentes en modo
   Anthropic visible. Reinicia la API tras cambiar `.env`.
3. Abre `make exam-claude` (Claude Code >=2.1.280): fija Spec Kit en la feature `002`.
   Comprueba `/mcp` y los diez skills `/speckit-*`; puedes cambiar el modelo con
   `CLAUDE_CODE_MODEL`.
   Claude Code desarrolla la solución; el agente de la web atiende consultas de clientes
   mediante la API de Anthropic y el modelo configurado en el backend.
   Prepara antes la sesión de búsqueda de [MCP](MCP.md) con `mcp-login`; la
   identidad pública no necesita login, pero el corpus protegido sí.
4. Si el entorno permite Docker, ejecuta `make docker` y prueba `python --version`
   en Herramientas. Sin Docker, el chat, la búsqueda y la calculadora siguen funcionando.
5. Decide si necesitas embeddings semánticos y descarga el modelo antes, siguiendo
   RAG.md. No gastes tiempo de la prueba descargando dependencias conocidas.
6. Confirma las reglas del evaluador: uso de una base preparada, internet, proveedor
   y formato de entrega. Sus reglas determinan qué partes puedes reutilizar.

## Minutos 0–3: convertir el ZIP en requisitos

Atajo: copia el material en `prueba-tecnica/` y ejecuta `/prueba-tecnica` en
`make exam-claude`. La skill sigue los pasos de esta guía hasta desplegar.

Con el servidor local funcionando:

```bash
uv run --project backend --extra semantic python scripts/import-material.py '/ruta/requisitos.zip' --no-upload
```

Antes, lista todos los nombres sin extraer con `python3 -I -m zipfile -l requisitos.zip`.
El importador informa por nombre los formatos que no convierte (YAML, SQL, imágenes,
código): léelos desde el ZIP original. Consulta `--help` para las opciones disponibles. El importador conserva material
sanitizado bajo `material/`, no ejecuta código y separa el trabajo de importación
del contenido del repositorio. Evita subir al conocimiento del agente consignas,
rúbricas, secretos o código de evaluación: solo documentos con hechos de empresa.
El comando anterior guarda el material para inspección sin subirlo al corpus. Tras
leerlo, carga únicamente los documentos empresariales desde la UI. También puedes
subir un ZIP que contenga exclusivamente documentos de la empresa.
La importación local es ahora el modo predeterminado; `--no-upload` sigue siendo
un alias explícito. `--upload` requiere un JWT administrativo privado en
`LUMEN_API_TOKEN` y sólo admite un origen HTTP numérico loopback. No pasar tokens
como argumentos ni subir consignas automáticamente. Los directorios de sesiones
y configuraciones privadas se excluyen antes de leer sus miembros; se redactan
los encabezados de autenticación en el material de texto.

Lee primero README, requisitos, rúbrica, ejemplos y archivos de entrada/salida.
Identifica cinco decisiones: proveedor, almacenamiento, herramientas requeridas,
interfaces y criterios de aceptación. Escribe una matriz breve:

| Requisito real | Implementación actual | Cambio mínimo | Comprobación |
| --- | --- | --- | --- |
| Respuestas sobre la empresa | Ingesta y Qdrant | Reemplazar corpus/configuración | Pregunta con fuente |
| Uso de herramientas | Registro compartido y tool loop | Agregar herramienta concreta | Ejecución registrada |
| Web y API Python | React + FastAPI | Adaptar campos o rutas | UI + Swagger |
| Persistencia vectorial | Qdrant local/remoto | Elegir embedding/URL | Reinicio y búsqueda |

## Minutos 3–5: especificación y plan acotados

Copia `docs/EXAM_PROMPT.txt` en Claude Code e indica la ruta real del material.
Selecciona `002-exam-adaptation` siguiendo [SPECKIT.md](SPECKIT.md); la feature
`001-company-agent` conserva la base implementada. Las tareas de `002` están pendientes.
Puedes ejecutar `/speckit-specify` y `/speckit-plan` para una especificación y plan
breves. Si ya está clara la diferencia con la base, evita regenerar todo el proyecto.
Pide una lista de archivos concretos y comprueba que coincide con la rúbrica.

## Minutos 5–14: adaptación

Cambios habituales:

- Marca y descripción: `COMPANY_NAME`, `COMPANY_DESCRIPTION`, `ASSISTANT_NAME`,
  `COMPANY_WEBSITE`, `COMPANY_SUGGESTED_QUESTIONS` y `COMPANY_PRODUCTS` juntas en `.env`
  (sin `ASSISTANT_NAME` el asistente se llama "Lumen"). El título de la pestaña y la
  presentación `/docs` toman la identidad de la API. No hagas buscar y reemplazar de
  "Humanizar": `X-Requested-With: Humanizar`, el emisor JWT, `APPLICATION_ID` y los
  eventos `humanizar-*` son identificadores de protocolo entre backend y frontend.
- Información empresarial: reemplazar documentos de demostración por el material
  real, `SEED_DEMO=false`, limpiar/cambiar `KNOWLEDGE_DIR` y usar un `DATA_DIR` nuevo.
  No mezclar empresas ni corpus. Inicia sesión como administrador para subir archivos.
  `KNOWLEDGE_DIR` lee TXT, MD, PDF, DOCX, CSV y JSON del nivel superior una vez por
  nombre: si editas un archivo ya cargado, bórralo en la UI o usa otro `DATA_DIR`.
  En Docker `DATA_DIR` es siempre `/data`; para empezar de cero en local usa
  `docker compose down -v` (borra también cuentas y conversaciones de ese stack).
- Tono y reglas: prompt de sistema del agente; mantener la regla de fuentes.
- Una nueva herramienta: `ToolDefinition` en `backend/app/tool_definitions.py`
  (string, number/integer, boolean y `optional`) + rama en `ToolRegistry.run` de
  `backend/app/tools.py` + prueba del camino exitoso y del límite. Si la respuesta no
  cita fuentes, su resultado determinista se muestra sin tocar `agent.py`; las
  herramientas de hechos con fuentes van en `FACT_TOOLS`. Una escritura con
  confirmación además necesita `BUSINESS_WRITES`, `business.py`, los CHECK de
  `postgres.py` (con `DATA_DIR`/`DATABASE_SCHEMA` nuevos o migración), `ActionConfirmation`
  y `frontend/src/actions.tsx`. Si usa terminal, crear un preset en las tres listas
  (`sandbox/app/main.py`, `tool_definitions.py`, `frontend/src/toolSchema.ts`).
- Formato exigido: modelos Pydantic, contrato y cliente frontend juntos.
- Otra base vectorial/proveedor: adaptar la capa de recuperación o proveedor; no
  rehacer la interfaz sin necesidad.

Usa `/speckit-tasks` y `/speckit-implement` cuando ayuden a ejecutar ese alcance.
Pide a Claude terminar y verificar cada cambio; no aceptar un plan como entregable.

## Minutos 14–18: verificar comportamiento

1. Pregunta por un hecho que exista en los documentos; abre la fuente correcta.
2. Pregunta por un dato ausente; confirma que el asistente admite que falta información.
3. Ejecuta una herramienta requerida y revisa su resultado real.
4. Prueba un archivo de entrada real y la ruta de API exigida.
5. Ejecuta `make check` o los checks proporcionales si cambiaste un módulo acotado.

No cambies a modo demo para disimular un error de autenticación: comprueba el modo
visible, resuelve la clave local o documenta la limitación.

## Minutos 18–20: entregar

Escribe cómo arrancar, variables requeridas sin valores, decisiones tomadas y pruebas
ejecutadas. Ejecuta `make package` si piden ZIP; inspecciona el listado del archivo.
Entrega el formato indicado por el evaluador, sin credenciales ni corpus privado
que no autorice incluir. Explica la arquitectura con ARCHITECTURE.md.
