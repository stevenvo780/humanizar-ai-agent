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
4. Pregunta al asistente por un dato del documento y abre la fuente recuperada.

El servidor procesa e indexa el contenido en Qdrant persistente. Los documentos
amplían la información consultable de la empresa; no se ejecutan como instrucciones.
La UI muestra el límite por archivo y los errores u omisiones del importador.
Eliminar un documento requiere una confirmación y elimina también sus fragmentos.

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
