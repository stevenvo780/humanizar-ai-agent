# Auditoría de calidad y adaptación

Revisión del 7 de octubre de 2026. El proyecto prepara la prueba técnica de
Softop; Humanizar sigue siendo la empresa de ejemplo y su corpus actual.
Los requisitos del examen todavía no se conocen. La preparación permite cambiar
perfil, documentos y herramientas; no acredita resolver cualquier examen en
veinte minutos.

## Hallazgos y correcciones

| Hallazgo | Corrección | Evidencia de regresión |
| --- | --- | --- |
| Una herramienta exitosa admitía afirmaciones empresariales sin fuentes | Sin citas válidas, resultados deterministas pertinentes o falta de evidencia | `backend/tests/agent/test_agent.py`: identidad inventada después de calcular y cálculo mezclado con afirmaciones |
| ZIP podía incorporar sesiones o cabeceras de autenticación | Exclusión previa a lectura y redacción de Basic/Bearer/Proxy-Authorization | `scripts/tests/test_material.py`: sesiones, contenido no leído, cabeceras y JSON |
| El importador intentaba subir sin sesión | Importación local por defecto; `--upload` explícito con JWT y destino HTTP loopback numérico | Cero HTTP por defecto, rechazo previo al ZIP y errores 401/403 sin credenciales |
| MCP no tenía sesión con la API protegida | Login interactivo, sesión privada ligada al origen y renovación coordinada | `backend/tests/mcp/test_mcp_auth.py`: login, permisos, origen, renovación, fallos y archivos privados |
| Colecciones remotas competían entre corpus | Namespace persistente del corpus y modelo; reconstrucción sin borrar colecciones ajenas | `backend/tests/knowledge/test_storage.py`: dos corpus y embeddings; servidor remoto real pendiente |
| Otro perfil heredaba productos y enlaces de Humanizar | Perfil y catálogo configurables; valores de Humanizar sólo para su perfil | `backend/tests/business/test_company_configuration.py`, `frontend/src/shared/config/company.test.ts` |
| Catálogo y esquemas duplicados; argumentos vacíos para herramientas nuevas | Metadatos centrales compartidos con Claude/API y formularios derivados | `backend/tests/tools/test_tools.py`, `frontend/src/features/tools/toolSchema.test.ts` |
| Refresh con 429, 5xx o fallo de red cerraba la sesión | Conservar sesión ante errores temporales; distinguir rechazo de autenticación | `frontend/src/shared/api/auth.test.ts` |
| Finalización SSE sin anuncio accesible | Región de estado que anuncia sólo la respuesta completada | `frontend/src/features/chat/ChatAnnouncement.test.ts` y Chromium sintético |
| Campos `constructor`, `__proto__` o `toString` leían propiedades heredadas | Lectura propia con `Object.hasOwn` | Regresiones de omisión, obligatoriedad, POST y prototipo; revisión independiente |
| Una ruta larga ensanchaba las tarjetas de documentación a 320 px | Columnas acotadas y ajuste de texto en tarjetas de estado | Chromium en 320/390/1440 px sin desborde de página |
| Validación de Spec Kit modificaba la selección activa | Prerequisitos de sólo lectura y parche local separado del manifiesto upstream | Cuatro pruebas en `scripts/tests/test_speckit.py`, incluyendo bytes/mtime y hashes |
| Legibilidad y recuentos ambiguos o antiguos | Aceptación medible y trazabilidad a tareas y evidencia fechada | `specs/001-company-agent/spec.md`, `tasks.md`, [VALIDATION.md](VALIDATION.md) |

## Cambiar la base durante el examen

1. Importar el ZIP localmente y leer sus requisitos con
   [EXAM_20_MIN.md](EXAM_20_MIN.md). La importación no ejecuta material recibido.
2. Actualizar la feature del examen en `specs/002-exam-adaptation`; conservar
   `001-company-agent` como base. El chequeo no cambia la selección activa.
3. Configurar `COMPANY_NAME`, `COMPANY_DESCRIPTION`, `ASSISTANT_NAME`,
   `COMPANY_WEBSITE`, `COMPANY_SUGGESTED_QUESTIONS` y `COMPANY_PRODUCTS` en el
   entorno del backend. Los dos últimos son arrays JSON; `null` selecciona el
   ejemplo de Humanizar sólo para Humanizar y `[]` desactiva esas sugerencias
   o productos. Los documentos siguen siendo la evidencia de las respuestas.
4. Añadir cada herramienta en `backend/app/tools/definitions.py` y su ejecución
   validada en `backend/app/tools/registry.py`. El esquema admite string, number/integer,
   boolean y parámetros opcionales; por sí solo no concede ejecución ni permisos.
   Sin citas, el agente muestra el resultado determinista de cualquier herramienta
   que no esté en `FACT_TOOLS`. La consola admite campos simples; esquemas
   complejos requieren una interfaz explícita.
5. Ejecutar `make check`, validar los escenarios de la nueva feature y comprobar
   el navegador. El código nuevo debe pasar las mismas puertas que la base.

La sesión MCP de Claude Code se prepara según [MCP.md](MCP.md). Es independiente
de la clave del proveedor y no se copia entre máquinas.

## Límites de la evidencia

Las citas se validan y los resultados sin citas se restringen; una cita existente
no demuestra por sí sola que cada frase sea verdadera. La interfaz exige texto de
al menos 12 CSS px, contraste de 4,5:1, teclado y vistas de 320/390/1440 px; esto no
equivale a una certificación WCAG completa. El anuncio final sigue el criterio de
[mensajes de estado de W3C](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html).

Qdrant remoto tiene regresiones simuladas, sin despliegue real comprobado. El modo
local mantiene un worker; varios procesos requieren validar SQLite y coordinación
de ingesta. PDF no tiene OCR; las solicitudes no envían correo ni reservan agenda.
La terminal sigue limitada a presets del sandbox.

El namespace se aplica también al índice local. Al actualizar una instalación
anterior, SQLite conserva documentos y contenido, y el índice se reconstruye en
una colección nueva. Las colecciones anteriores se conservan; prever espacio para
ambas y tiempo de indexación antes de confirmar que la API está saludable.

Frontend y API se verifican por separado. La API auditada requiere SSH al VPS;
Fedora requiere host y usuario accesibles. Estado en [VALIDATION.md](VALIDATION.md)
y operación en [OPERATIONS.md](OPERATIONS.md).
