# Preparación y adaptación en 20 minutos

## Antes de la prueba

1. Abre la web y crea tu administrador. Prepara una credencial Anthropic propia.
   Configura `ANTHROPIC_API_KEY` en el `.env` privado del backend, reinicia la API
   y verifica una respuesta con el modo Anthropic visible.
2. Ejecuta `make setup`, `make check`, `make dev` y una consulta con fuentes.
3. Abre `make claude` (Claude Code >=2.1.280). Comprueba `/mcp` y los diez skills
   `/speckit-*`; puedes cambiar el modelo con `CLAUDE_CODE_MODEL`.
   Claude Code desarrolla la solución; el agente de la web atiende consultas de clientes
   mediante la API de Anthropic y el modelo configurado en el backend.
4. Si el entorno permite Docker, ejecuta `make docker` y prueba `python --version`
   en Herramientas. Sin Docker, el chat, la búsqueda y la calculadora siguen funcionando.
5. Decide si necesitas embeddings semánticos y descarga el modelo antes, siguiendo
   RAG.md. No gastes tiempo de la prueba descargando dependencias conocidas.
6. Confirma las reglas del evaluador: uso de una base preparada, internet, proveedor
   y formato de entrega. Sus reglas determinan qué partes puedes reutilizar.

## Minutos 0–3: convertir el ZIP en requisitos

Con el servidor local funcionando:

```bash
uv run --project backend --extra semantic python scripts/import-material.py '/ruta/requisitos.zip' --no-upload
```

Consulta `--help` para las opciones disponibles. El importador conserva material
sanitizado bajo `material/`, no ejecuta código y separa el trabajo de importación
del contenido del repositorio. Evita subir al conocimiento del agente consignas,
rúbricas, secretos o código de evaluación: solo documentos con hechos de empresa.
El comando anterior guarda el material para inspección sin subirlo al corpus. Tras
leerlo, carga únicamente los documentos empresariales desde la UI. También puedes
subir un ZIP que contenga exclusivamente documentos de la empresa.

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

- Marca y descripción: configuración backend y `.env` local.
- Información empresarial: reemplazar documentos de demostración por el material
  real, `SEED_DEMO=false`, limpiar/cambiar `KNOWLEDGE_DIR` y usar un `DATA_DIR` nuevo.
  No mezclar empresas ni corpus. Inicia sesión como administrador para subir archivos.
- Tono y reglas: prompt de sistema del agente; mantener la regla de fuentes.
- Una nueva herramienta: registro backend + esquema de entrada + prueba del camino
  exitoso y del límite relevante. Si usa terminal, crear un preset seguro en sandbox.
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
