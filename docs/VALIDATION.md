# Estado de validación

Validación actualizada el 2026-10-07. No representa validación de los requisitos de
la prueba, todavía desconocidos.

Las puertas de calidad de la base y las comprobaciones de esta revisión pasan;
las pruebas PostgreSQL utilizan exclusivamente una instancia temporal aislada.

| Componente | Evidencia |
| --- | --- |
| Backend | Ruff, formato, mypy estricto en 39 archivos, 213 pruebas incluidas 15 PostgreSQL |
| Sandbox e importador/paquete/publicación | Ruff, formato, mypy estricto y 77 pruebas |
| Helpers de despliegue | 28 pruebas offline de configuración, rutas y ejecución privada |
| Frontend | ESLint con tipos/hooks/a11y, Prettier, TypeScript strict, 93 pruebas y build |
| Dependencias web | npm audit: 0 vulnerabilidades en la comprobación del frontend |
| Configuración | JSON válido; Compose local y producción; proxy Vercel tipado |
| Claude/Spec Kit | Claude Code 2.1.286, specify-cli 1.0.7; 10 skills instalados |
| Paridad | 20 artefactos compatibles sin cambios; AGENTS.md manual preservado |

Total comprobado: **411 pruebas aprobadas** entre las puertas anteriores sin cambios
y las suites afectadas de esta revisión, incluidas 213 pruebas backend con PostgreSQL
temporal y 93 frontend. Las 15 de PostgreSQL se activan con
`LUMEN_TEST_DATABASE_URL` apuntando exclusivamente a una base temporal loopback
`lumen_test`; cada prueba crea y elimina su propio schema aleatorio. Nunca apuntar
esa variable a la base de la empresa. La base anterior de 214 pruebas también
se verificó desde un clon descargado del repositorio público con Python 3.12.3
en backend y sandbox. La comprobación actual utiliza Python 3.11.15 en backend
y 3.12 en sandbox; las 140 pruebas del backend anterior también pasaron en un entorno
aislado con Python 3.12.3. Docker apunta a Python 3.12. Mypy utiliza
objetivo 3.12 para interpretar los stubs PEP 695 de NumPy, manteniendo el código
compatible con Python 3.11 mediante Ruff. Los 15 casos actuales también pasaron en
PostgreSQL 16 local efímero, cerrado y eliminado al terminar; la conexión productiva
previamente validada sigue siendo PostgreSQL 18.6. Existe una advertencia externa de deprecación
de TestClient/httpx en cada suite Python; no impide los resultados.

## Publicación y configuración de este workspace

Comprobación del 2026-10-07, 04:51 UTC: web, documentación y Swagger productivos
responden HTTP 200. La API activa sigue en modo Anthropic con Haiku 4.5; todavía
no declara `document_reading` ni `customer_management`, y OpenAPI no ofrece GET de
contenido. Publicar la API actualizada sigue pendiente de una sesión SSH autenticada:
el VPS responde `Permission denied (publickey,password)` y el socket anterior expiró.

Se prepararon `.env.production` y `.env.vercel` privados, usando exclusivamente
las variables requeridas de la configuración de despliegue existente, sin imprimir
valores ni modificar el `.env` de desarrollo. Permisos `0600` y exclusión por Git
verificados. No se transfirieron credenciales a GitHub, Vercel cliente o Fedora.
El backend del VPS conserva su archivo privado externo; las variables del proxy
se configuran en el servidor de Vercel y el proxy HTTPS.
Una conexión de sólo lectura usando el nuevo `.env.production` confirmó PostgreSQL
18.6, TLS 1.3 con verificación completa y existencia del schema dedicado. No se
crearon ni modificaron cuentas, tablas, sesiones o documentos en esa comprobación.
La configuración privada también pasó `deploy-vercel.py check`; el origen HTTPS
devolvió 403 sin su secreto de servidor y 200 con él. Una llamada mínima autorizada
al proveedor autenticó la clave del backend y devolvió respuesta con
`claude-haiku-4-5-20251001` (14 tokens de entrada y 5 de salida), sin enviar corpus
ni imprimir secretos. Esta llamada no sustituye el smoke del chat tras actualizar
el contenedor productivo.

Fedora: la copia solicitada es `~/Documentos/repos/SoftopPrueba`. El alias `fedora`
no resuelve en este entorno; falta un host/usuario SSH accesible. El helper y la
guía usan esa ruta y conservan checkouts existentes. Sintaxis, ayuda y nueve casos
sintéticos de destino pasaron; no equivalen a una instalación real en el portátil.

## Servicios reales locales

- Lector de documentos: API protegida por rol admin, contenido completo persistente
  en nuevas cargas y migración aditiva compatible con la estructura anterior. Las
  213 pruebas backend incluyen lectura, whitespace, reinicio, reconstrucción,
  rollback, borrado y permisos; 93 frontend verifican el contrato y Markdown seguro.
- Chromium con API real y datos sintéticos: Markdown con títulos, listas, tablas,
  código y enlaces; vista de texto completo; documentos previos con aviso de
  reconstrucción; apertura con foco/desplazamiento, cierre, error y reintento,
  borrado del documento abierto. Escritorio 1440 px y móvil 390/320 px, sin overflow
  horizontal, HTML ejecutable, imágenes remotas ni errores JavaScript.
- Un segundo smoke sintético verificó cancelación de lecturas, cambio entre dos
  documentos sin respuestas obsoletas, retorno del foco y API anterior sin GET de
  contenido. Revisión independiente: 25 pruebas frontend y seis backend dirigidas,
  sin bloqueantes confirmados ni acceso al corpus privado.
- La API del entorno LAN ya declara `features.document_reading: true`; su UI
  carga sin errores. Activar el lector en Vercel sigue pendiente de publicar la API
  actualizada en el VPS con una conexión SSH autenticada. El frontend verifica la
  capacidad antes de habilitar la lectura, manteniendo carga y borrado en APIs anteriores.

- Gestión de clientes: 205 pruebas backend con PostgreSQL temporal y 68 frontend.
  Se verificaron autorización, rol fijo, campos públicos, conservación de la sesión
  admin y snapshots coherentes ante un alta entre el conteo y la lectura de filas.
- Legibilidad: Chromium con datos sintéticos en 36 vistas entre 320 y 1440 px;
  sin errores ni desbordes de página, ningún texto menor de 12 px en esas vistas y
  contraste mínimo medido de 5,82:1. Clientes se verificó además en escritorio/móvil.
- Navegación: una única lista de secciones por rol/capacidad, sin barra de pestañas
  duplicada ni referencias ARIA huérfanas. Chromium verificó escritorio/móvil,
  controles cerrados inertes, apertura/cierre por botón y Escape, ciclo de foco,
  restauración tras seleccionar y cambio de breakpoint; sin desbordes ni errores JS.
  El helper de foco se comparte con Ayuda. Se eliminaron estilos huérfanos y los
  falsos controles de selector de empresa, conservando una sola indicación de conexión.
- Producción: la cuenta indicada por el dueño obtuvo el rol admin mediante una
  transferencia transaccional desde la cuenta técnica inicial, conservando cuentas,
  contraseñas, conversaciones y sesiones. Una sesión aislada de comprobación confirmó
  permisos, ingesta de Markdown y recuperación del contenido; sesión y documento
  temporales se eliminaron al finalizar, sin cambiar el corpus existente.
- La nueva API de clientes aún requiere publicación en el VPS tras renovar su SSH.
  El frontend consulta la capacidad declarada por la API antes de mostrar Clientes.

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

## Despliegue real verificado

El 7 de octubre de 2026 se publicó
[Humanizar IA](https://humanizar-ai-agent.vercel.app), con
[documentación pública](https://humanizar-ai-agent.vercel.app/docs) y
[Swagger](https://humanizar-ai-agent.vercel.app/api/docs) bajo el mismo origen.

- Vercel: build de producción READY, Node 22, frontend compilado desde sus fuentes.
  El rewrite agrega el secreto del proxy sólo en el servidor; el origen directo
  rechaza con 403 las peticiones que no lo incluyen.
- VPS: API y sandbox Docker saludables. API en loopback; sandbox no root, filesystem
  de lectura, sin mounts de host, capacidades eliminadas y red interna. Preset
  `python --version` ejecutado realmente, más calculadora y consulta MCP.
- PostgreSQL 18.6: TLS 1.3 con CA y hostname verificados desde la imagen de API.
  Schema exclusivo `lumen`, seis tablas del proyecto y exactamente un administrador
  inicial provisionado por stdin privado. Bootstrap protegido y token rotado.
- Claude Haiku: conversación SSE real en 5.6 segundos, herramienta de búsqueda,
  fuente de Humanizar y uso de tokens distinto de cero. Otra conversación real
  se visualizó en Chromium con recomendaciones, fuentes y trazas.
- Reinicio controlado del contenedor API: historial PostgreSQL conservado y refresh
  de la sesión anterior válido. Logout revocó la familia y refresh devolvió 401.
  Cliente registrado con rol customer, sin acceso a documentación/tools admin ni
  conversaciones ajenas.
- Chromium desktop y móvil: login, historial recuperado desde la barra lateral al
  recargar, logout, `/docs`, Swagger y OpenAPI. Cookie Secure/HttpOnly comprobada;
  respuestas de autenticación sin cache. Sin errores JavaScript ni overflow
  horizontal. Los bundles descargados no contienen las credenciales privadas.

Capturas y resúmenes de ejecución quedan sólo en `artifacts/`, excluidos de Git y
del paquete source. Las credenciales de operación se entregan en un archivo privado
del VPS, separado del checkout. La instalación en Fedora no se acredita aquí:
requiere identificar su usuario/host SSH y ejecutarla en el portátil.

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

La revisión de despliegue cubrió configuración de Vercel sin secretos serializados,
validación TLS y URL PostgreSQL, preservación de schemas ajenos, locks de sesiones
e idempotencia. Bootstrap con dos procesos independientes creó exactamente un
administrador. Se corrigieron parámetros vacíos/duplicados y puertos inválidos antes
de construir la conexión. Los helpers requieren secretos de JWT y bootstrap para
producción. La publicación real se registra por separado del inventario automatizado.

## Pendientes y límites

- El daemon Docker del entorno local no responde. Las pruebas PostgreSQL utilizaron
  un contenedor temporal aislado en el VPS, accesible sólo por un túnel loopback.
  Los builds y el sandbox productivo se verifican en el VPS durante el despliegue.
- CI definido en `.github/workflows/quality.yml`: dependencias fijadas, controles
  locales, auditoría de paths, Gitleaks, PostgreSQL temporal e integración Docker.
  El runner remoto no inició por bloqueo de facturación de la cuenta GitHub;
  el workflow no cuenta como validación remota aprobada. Las 378 pruebas locales
  y el smoke Docker/Vercel real se registran de forma independiente.
- El clon público no contiene una credencial: cada instalación configura su propia
  clave privada. Los controles automatizados del ciclo, errores y presupuestos
  utilizan proveedores simulados; las llamadas reales locales se registran arriba.
- Qdrant remoto no probado; modo local persistente comprobado.
- PDF requiere texto extraíble, sin OCR. SQLite local o PostgreSQL remoto conservan
  cuentas, sesiones, historial y solicitudes; Qdrant persiste en un volumen del VPS.
- El hosting público utiliza Vercel para React y un VPS para FastAPI/sandbox.
  Procedimiento y variables documentados en [DEPLOYMENT.md](DEPLOYMENT.md).
  Fedora dispone de un helper de preparación; ejecutar en el equipo real requiere
  su acceso SSH y la autenticación interactiva local de Claude Code.
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
realiza el integrador después de completar los gates. El escaneo de Git es una
comprobación distinta de la verificación del hosting y sus servicios.

Para repetir: `make setup`, `make check`, `make dev`. Para terminal real, activa
Docker y usa `make docker` o el override local de `make dev`. Para Anthropic,
configura una credencial propia únicamente en el `.env` privado del backend y
reinicia la API. La interfaz y el contrato HTTP no permiten introducir claves.
