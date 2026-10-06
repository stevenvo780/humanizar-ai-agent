# Estado de validación

Validación realizada el 2026-10-06. No representa validación de los requisitos de
la prueba, todavía desconocidos.

`bash scripts/check.sh`: aprobado.

| Componente | Evidencia |
| --- | --- |
| Backend | Ruff, formato, mypy estricto y 127 pruebas |
| Sandbox e importador/paquete/publicación | Ruff, formato, mypy estricto y 71 pruebas |
| Frontend | ESLint con tipos/hooks/a11y, Prettier, TypeScript strict, 16 pruebas y build |
| Dependencias web | npm audit: 0 vulnerabilidades en la comprobación del frontend |
| Configuración | JSON válido, Compose principal y override local válidos |
| Claude/Spec Kit | Claude Code 2.1.286, specify-cli 1.0.7; 10 skills instalados |
| Paridad | 20 artefactos compatibles sin cambios; AGENTS.md manual preservado |

Total: **214 pruebas aprobadas**. Python backend ejecutó en 3.11.15 y sandbox en
3.12.3; Docker apunta a Python 3.12. Existe una advertencia externa de deprecación
de TestClient/httpx en cada suite Python; no impide los resultados.

## Servicios reales locales

- FastEmbed multilingüe descargado e inferencia de vectores de 384 dimensiones.
- Corpus activo: cinco resúmenes de Humanizar con URLs oficiales y fecha de consulta.
  La carga inicial es idempotente y usa datos separados del corpus anterior de Forma.
- SQLite persistente para cuentas, sesiones, chats, configuración cifrada y solicitudes.
- Horario, precios e integraciones se validaron con el corpus ficticio anterior;
  CEO y facturación anual ausentes producen respuesta sin fuentes inventadas.
- Calculadora: 21% de 4500 = 945; total con IVA = 5445.
- MCP: handshake, catálogo y company_info por stdio/HTTP sobre la misma API. Búsqueda
  se validó antes de habilitar auth; el MCP sin sesión recibe ahora 401 en búsqueda.
- Chromium: chat SSE, fuentes expandibles, calculadora, MCP, upload ZIP y eliminación
  de documento completos; cero errores JavaScript.
- Chromium con autenticación y una BD aislada: primer admin, JWT, refresh al recargar,
  historial, confirmación de ticket y bandeja admin, registro de cliente y aislamiento
  de conversaciones/solicitudes; cero errores JS y sin overflow en móvil.
- Acceso a la web por el proxy local verificado. No se crearon cuentas fijas en la
  instancia del usuario; el primer acceso permite crear su propio administrador.
- Desktop 1512x982 y mobile 390x844 inspeccionados; sin overflow horizontal.
- ZIP sintético: README/rúbrica separados del documento empresarial.
- OpenAPI exportado en `docs/openapi.json`.
- Swagger y OpenAPI devuelven 200 desde el proxy web, sin llamadas de autenticación
  inesperadas, errores JavaScript ni overflow en la comprobación de navegador.

Capturas locales en `artifacts/`: desktop, mobile, chat, conocimiento y herramientas.
Se excluyen del ZIP source para mantenerlo portable y libre de datos de sesión.

## Revisión independiente

Veredicto aprobado dentro del alcance revisado. Se corrigieron y revalidaron:
numeración de citas, sanitización antes de emitir respuesta, cancelación SSE con
cola llena, reconciliación al cambiar embeddings, credenciales en JSON/CSV y parser
PDF con límites y streams anidados. El revisor no modificó código.
La ampliación auth se revisó de manera independiente: aislamiento SSE, bootstrap
concurrente, permisos y JWT; corregidas y revalidadas las carreras de logout/refresh,
verificación de proveedor y el reinicio del rate limit mediante login exitoso.

## Pendientes y límites

- El daemon Docker no responde. Compose y Dockerfiles están preparados; no se
  ejecutaron builds ni procesos de terminal del producto en este host.
- Modo demo activo: sin llamada real a Anthropic con credencial nueva. El ciclo
  nativo de herramientas, errores y presupuestos se probó con proveedor simulado.
- Qdrant remoto no probado; modo local persistente comprobado.
- PDF requiere texto extraíble, sin OCR. El historial autenticado persiste en SQLite.
- Hosting público de la web queda fuera de esta base local. Autenticación multiusuario
  con roles ya está implementada y comprobada. SQLite se utiliza como BD relacional.
- Las solicitudes se registran localmente; no hay envío externo ni reserva de agenda.

## Archivos y repetición

Código en `backend/app`, `frontend/src` y `sandbox/app`; pruebas por módulo y en
`scripts/tests`. Locks en los proyectos backend/sandbox y frontend. Arranque y
adaptación en `scripts`, `compose.yaml`, `compose.local.yaml`, `Makefile`, `CLAUDE.md`,
`.mcp.json` y `.claude/skills`. Spec inicial en `specs/001-company-agent` y constitución
en `.specify`.

Spec Kit: 22 archivos instalados coinciden con sus manifiestos de versión 1.0.7,
los 10 skills tienen nombres válidos, seis referencias locales requeridas resuelven
y los scripts Bash pasan verificación de sintaxis. `specify version` y `specify check`
se ejecutaron; el análisis de la baseline no encontró conflictos críticos.
Ver [la selección de features y auditoría](SPECKIT.md).

Portabilidad: `make setup` y `make speckit-check` pasaron en una copia limpia de
fuentes reubicada, con espacios en la ruta, Python 3.12.3 y sin copiar entornos,
dependencias instaladas, configuración local o datos. Los caches de paquetes/pesos
del host estaban disponibles; se preparó FastEmbed de 384 dimensiones.
La CLI `specify-cli==1.0.7` se instaló desde PyPI y se ejecutó en directorios
temporales aislados, sin sustituir herramientas globales.

El [repositorio público](https://github.com/stevenvo780/humanizar-ai-agent) dispone
de código fuente preparado con CI, escaneo de publicación y exclusión
de configuración local, datos y sesiones. El escaneo final y la publicación los
realiza el integrador después de completar los gates; no acreditan hosting de la web.

Para repetir: `make setup`, `make check`, `make dev`. Para terminal real, activa
Docker y usa `make docker` o el override local de `make dev`. Para Anthropic,
configura una credencial propia desde Conexión Claude o únicamente en `.env` local.
