# Administración y cuentas de clientes

Los clientes se registran en la pantalla de acceso y disponen de conversaciones y
solicitudes privadas. El registro público siempre crea una cuenta de cliente.
Existe un único administrador; el rol se consulta en la base de datos en cada
petición. Después de un cambio de rol basta recargar la página para renovar la UI.

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

Las nuevas cargas conservan el texto extraído completo en la base de conocimiento.
Los documentos anteriores sólo guardaban fragmentos: el lector los reconstruye
en orden y avisa de que el formato puede diferir. Puedes volver a subir el `.md`
original si necesitas conservar exactamente su contenido y formato.
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
caracteres. El alta crea exclusivamente un cliente, mantiene tu sesión de admin y
no envía correos. Comparte el acceso con el cliente por tu canal habitual.
La lista está paginada y muestra nombre, correo y fecha; no muestra contraseñas,
hashes, tokens ni conversaciones privadas.

El código y las pruebas están preparados. Publicar esta nueva API en el VPS sigue
pendiente de renovar su conexión SSH; el estado verificable está en
[VALIDATION.md](VALIDATION.md) y la tarea T015 de la base Spec Kit.
