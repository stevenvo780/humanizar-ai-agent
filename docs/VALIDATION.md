# Estado de validación

Validación actualizada el 2026-10-07. No representa validación de los requisitos de
la prueba, todavía desconocidos.

`bash scripts/check.sh`: aprobado.

| Componente | Evidencia |
| --- | --- |
| Backend | Ruff, formato, mypy estricto en app y pruebas, 140 pruebas |
| Sandbox e importador/paquete/publicación | Ruff, formato, mypy estricto y 76 pruebas |
| Frontend | ESLint con tipos/hooks/a11y, Prettier, TypeScript strict, 25 pruebas y build |
| Dependencias web | npm audit: 0 vulnerabilidades en la comprobación del frontend |
| Configuración | JSON válido, Compose principal y override local válidos |
| Claude/Spec Kit | Claude Code 2.1.286, specify-cli 1.0.7; 10 skills instalados |
| Paridad | 20 artefactos compatibles sin cambios; AGENTS.md manual preservado |

Total actual: **241 pruebas aprobadas**. La base anterior de 214 pruebas también
se verificó desde un clon descargado del repositorio público con Python 3.12.3
en backend y sandbox. La comprobación actual utiliza Python 3.11.15 en backend
y 3.12 en sandbox; las 140 pruebas del backend también pasaron en un entorno
aislado con Python 3.12.3. Docker apunta a Python 3.12. Mypy utiliza
objetivo 3.12 para interpretar los stubs PEP 695 de NumPy, manteniendo el código
compatible con Python 3.11 mediante Ruff. Existe una advertencia externa de deprecación
de TestClient/httpx en cada suite Python; no impide los resultados.

## Servicios reales locales

- Anthropic autenticado con Haiku 4.5, respuesta de modelo
  `claude-haiku-4-5-20251001` en una llamada real. El backend local y su proxy web
  reportan modo `anthropic`; la credencial queda únicamente en configuración
  privada del backend, ignorada por Git y con permisos 0600.
- Ciclo real del agente comprobado con respuestas HTTP 200: consulta de identidad
  mediante `mcp_company_info` y consulta sobre Cauce mediante `search_knowledge`
  con una fuente recuperada. Las comprobaciones usaron cuentas y datos sintéticos
  aislados; ninguna sesión privada forma parte del repositorio.
- Clon público en una ruta nueva con espacios: `make setup`, `make speckit-check`
  y `make check` completos. El arranque real en Python 3.12 verificó administrador,
  registro de cliente, chat con fuentes semánticas de Humanizar, historial, refresh
  y logout. Datos sintéticos en una instancia temporal; servicios cerrados al terminar.
- Build de producción servido en navegador: acceso y `/docs` en móvil sin errores
  JavaScript ni overflow; `/docs` no realiza solicitudes de autenticación.
- Auditoría del 7 de octubre: build de producción con API y SQLite temporales,
  administrador con contraseña de seis caracteres, login, chat SSE, historial al
  recargar, logout y acceso posterior. Navegación por teclado en las pestañas de
  autenticación; desktop 1440x1000 y móvil 390x844 sin overflow ni errores JS.
  Sin formulario de claves ni solicitudes a rutas de configuración del proveedor.

- FastEmbed multilingüe descargado e inferencia de vectores de 384 dimensiones.
- Corpus activo: cinco resúmenes de Humanizar con URLs oficiales y fecha de consulta.
  La carga inicial es idempotente y usa datos separados del corpus anterior de Forma.
- SQLite persistente para cuentas, sesiones, chats y solicitudes.
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

Auditoría del 7 de octubre: corregidos y reproducidos independientemente el bloqueo
del event loop durante autenticación SQLite y la liberación prematura de permisos
al cancelar ingesta o búsqueda del chat. REST y SSE comparten un límite de llamadas
con 429 mientras un worker sigue ocupado. Se añadieron pruebas de desconexión SSE
real y heartbeat. En frontend se validan respuestas en runtime, se ignoran refresh
de sesiones anteriores y se cierra el lector SSE al recibir `done`.
Retirados formulario, tipos, CSS, rutas HTTP y prioridad SQLite para configurar Claude;
las filas legacy se conservan, se ignoran y no alteran el JWT persistente.
La auditoría de publicación rechaza directorios de entorno privados, sesiones Claude
con variaciones de mayúsculas y el puntero local de Spec Kit, incluido un índice Git real.

## Pendientes y límites

- El daemon Docker no responde. Compose y Dockerfiles están preparados; no se
  ejecutaron builds ni procesos de terminal del producto en este host.
- CI definido en `.github/workflows/quality.yml`: dependencias fijadas, controles
  locales, auditoría de paths, Gitleaks e integración Docker. El runner remoto no
  inició su ejecución; el workflow no cuenta como validación de Docker.
- El clon público no contiene una credencial: cada instalación configura su propia
  clave privada. Los controles automatizados del ciclo, errores y presupuestos
  utilizan proveedores simulados; las llamadas reales locales se registran arriba.
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

Publicación: repositorio público con historial independiente saneado; Gitleaks
no encontró secretos en los archivos ni en el historial publicado. No se incluyen
configuración privada, cuentas, datos de sesión, material del examen ni el
manifiesto local de paridad. El ZIP portable contiene también Nginx y excluye el
puntero local `.specify/feature.json`; el bootstrap lo recrea al instalar.

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
configura una credencial propia únicamente en el `.env` privado del backend y
reinicia la API. La interfaz y el contrato HTTP no permiten introducir claves.
