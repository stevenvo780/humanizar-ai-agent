# Administración y cuentas de clientes

La aplicación está en [humanizar-ai-agent.vercel.app](https://humanizar-ai-agent.vercel.app).
Los clientes se registran en la pantalla de acceso y disponen de conversaciones y
solicitudes privadas. El registro público siempre crea una cuenta de cliente.
Existe un único administrador; el servidor comprueba su rol en cada petición.
La interfaz actual permite listar y crear clientes, además de gestionar documentos;
no incluye cambio de roles, borrado de cuentas ni recuperación de contraseña.

## Acceso del administrador

Entra con el acceso privado custodiado por el operador. No hay cuentas ni
contraseñas predeterminadas. La contraseña admite entre 6 y 128 caracteres; usa
una contraseña propia y evita compartir tu sesión administrativa con clientes.

El primer administrador de producción se provisiona mediante el CLI privado del
contenedor, antes de abrir el servicio al público. El bootstrap HTTP está protegido
por un token del servidor; no introducir ese token en el frontend. En una
instalación local nueva sin ese token puedes crear el administrador desde la web.
El [runbook](OPERATIONS.md) contiene el comando de provisionamiento. Si ya hay
administrador, no recrearlo ni regenerar JWT para intentar recuperar el acceso.

Las sesiones usan JWT de corta duración y una cookie de refresh privada. Cerrar
sesión revoca la familia de esa sesión. No copiar tokens, cookies o respuestas
autenticadas al chat, a informes o a comandos visibles.

## Ampliar la información del asistente

1. Entra con tu cuenta de administrador y abre **Documentación**.
2. Pulsa **Añadir documentos**, selecciona uno o varios `.md`, o arrástralos al área
   de carga. También se aceptan TXT, PDF, DOCX, CSV, JSON y ZIP de documentos.
3. Espera la confirmación y comprueba el archivo en la biblioteca.
4. Pulsa el **nombre del documento**, junto al icono de libro, para consultar su
   contenido. El lector ofrece una vista Markdown y otra con el texto, además de
   estados de carga y errores.
5. Pregunta al asistente por un dato del documento y abre la fuente recuperada.

El servidor procesa e indexa el contenido en Qdrant persistente. Los documentos
amplían la información consultable de la empresa; no se ejecutan como instrucciones.
La UI muestra el límite por archivo y los errores u omisiones del importador.
Eliminar un documento requiere una confirmación y elimina también sus fragmentos.

Las nuevas cargas conservan el texto extraído completo en la base de conocimiento;
el lector no descarga el binario original del archivo.
Los documentos anteriores sólo guardaban fragmentos: el lector los reconstruye
en orden y avisa de que el formato puede diferir. **Texto original** identifica
el texto extraído guardado al importar; **Texto recuperado** identifica una
reconstrucción de fragmentos. Puedes volver a subir el `.md` original para guardar
su texto extraído completo, sin depender de esa reconstrucción. El importador
puede normalizar el archivo; conserva el original fuera de la aplicación si
necesitas preservar sus bytes exactos.
La lectura está protegida por el rol administrador, igual que la carga y el borrado.
El botón de lectura se habilita cuando la API declara
`features.document_reading: true`; una API anterior permite seguir cargando y
eliminando documentos mientras se actualiza el servidor.
La activación en la instancia publicada se registra en [VALIDATION.md](VALIDATION.md).

## Crear cuentas desde administración

La sección **Clientes** aparece cuando `/api/health` declara
`features.customer_management: true`. Una API anterior mantiene el registro público
y la administración de documentos, sin mostrar una opción que todavía no soporta.

En **Clientes**, introduce nombre, correo y una contraseña inicial de al menos seis
caracteres, y pulsa **Crear cliente**. El correo se normaliza y no puede duplicar
una cuenta existente. El alta crea exclusivamente un cliente, mantiene tu sesión
de admin y no envía correos. Entrega el acceso por un canal privado autorizado;
la aplicación no implementa invitaciones ni cambio de contraseña del cliente.
La lista está paginada y muestra nombre, correo y fecha; no muestra contraseñas,
hashes, tokens ni conversaciones privadas.

Sólo el administrador puede listar o crear clientes. Una petición sin sesión
recibe 401; una cuenta de cliente recibe 403. El rol de una cuenta creada aquí
siempre es `customer`; no existe una opción para crear otro administrador.

## Configuración y solicitudes

La clave Anthropic y el modelo se configuran exclusivamente en el entorno privado
del backend. La interfaz no pide ni guarda esa clave. La configuración Vercel del
proxy y las credenciales PostgreSQL también corresponden al operador; no se envían
al navegador. Una carga de documentos amplía el conocimiento recuperable, pero
no cambia el proveedor, las credenciales ni las instrucciones del sistema.

Las solicitudes se almacenan en la aplicación. Su creación no demuestra un envío
de correo ni una reserva en un calendario externo. Revisa su estado y realiza el
seguimiento comercial por los canales de la empresa.

## Estado de publicación al 2026-10-07

Frontend en Vercel y API del VPS publicados en `9ac20b0` el 2026-10-07: `/api/health`
declara `customer_management` y `document_reading`, así que **Clientes** y el lector
están activos. El procedimiento está en [OPERATIONS.md](OPERATIONS.md). Hasta entonces los botones dependen de los flags
que declare el servidor existente, por lo que pueden no aparecer. El estado
verificable está en [VALIDATION.md](VALIDATION.md) y [OPERATIONS.md](OPERATIONS.md).
