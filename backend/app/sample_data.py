from app.ingestion import ParsedDocument

DEMO_DOCUMENTS = [
    ParsedDocument(
        "forma-empresa.md",
        "Forma es una empresa ficticia para esta demostración. Forma es una plataforma SaaS de "
        "operaciones para equipos y pequeñas empresas. Fue fundada en 2019 y tiene su sede en "
        "Madrid, España. Centraliza tareas, procesos y colaboración. Los datos y precios de este "
        "corpus son ilustrativos, no una oferta comercial real.",
    ),
    ParsedDocument(
        "forma-precios.md",
        "Precios de Forma (ejemplo). Plan Starter: 29 euros al mes por equipo. Plan Equipo: "
        "79 euros al mes por equipo. Plan Enterprise: precio a medida, contactar con ventas. "
        "La prueba gratuita dura 14 días y no requiere tarjeta de crédito. Los planes se pueden "
        "cancelar al final del período mensual. Los importes no incluyen IVA.",
    ),
    ParsedDocument(
        "forma-soporte.md",
        "Soporte de Forma. Horario: lunes a viernes de 09:00 a 18:00, zona horaria UTC+2. "
        "Canal de soporte: soporte@forma.example. La atención Enterprise se acuerda en el "
        "contrato. El equipo de soporte ayuda con altas, permisos, importaciones e integraciones.",
    ),
    ParsedDocument(
        "forma-integraciones.md",
        "Integraciones disponibles en Forma: Slack, Notion y Google Workspace. Slack permite "
        "notificaciones de tareas. Notion permite enlazar documentación. Google Workspace "
        "conecta el calendario y los documentos del equipo. La configuración se hace desde "
        "Ajustes > Integraciones por una persona administradora.",
    ),
    ParsedDocument(
        "forma-primeros-pasos.md",
        "Primeros pasos con Forma: crear el espacio de trabajo, invitar al equipo, elegir una "
        "plantilla de operaciones e importar las tareas existentes mediante un archivo CSV. "
        "Los roles son administrador, editor y lector. Solo el administrador gestiona "
        "facturación e integraciones. Los lectores pueden consultar pero no modificar tareas.",
    ),
]
