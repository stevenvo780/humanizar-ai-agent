# Vectores y recuperación

El valor de RAG es recuperar evidencia de la empresa y dársela al modelo para que
responda con fuentes. Se puede comprobar sin pagar llamadas al proveedor.

El modo `EMBEDDING_PROVIDER=hash` crea vectores léxicos deterministas, los guarda en
Qdrant y busca por similitud. No descarga pesos y es adecuado para probar el pipeline
sin red. No equivale a comprensión semántica neuronal: puede perder sinónimos,
paráfrasis y correspondencias entre idiomas.

El modo `fastembed` está seleccionado en `.env.example` y utiliza
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`: embeddings de 384
dimensiones para varios idiomas, incluido español. `make setup` instala el extra
semántico y prepara los pesos. Para instalarlo explícitamente:

```bash
uv sync --project backend --extra semantic --extra dev
```

Configura `EMBEDDING_PROVIDER=fastembed` y un DATA_DIR nuevo en `.env`, luego arranca
la API y sube el corpus. Consulta la configuración backend para el modelo concreto.
La primera inicialización requiere red, almacenamiento y tiempo para sus pesos.
El modo efectivo se informa en la API; compruébalo antes de mostrar una demo.

Si cambias el modelo, verifica que el backend reindexe el corpus; un DATA_DIR nuevo
ofrece una separación explícita entre pruebas. Para retirar documentos de demostración, usa la pantalla
de Conocimiento o inicia con `SEED_DEMO=false` y un directorio de datos limpio.

Con documentos reales, verifica preguntas directas, paráfrasis y datos ausentes.
Las citas sirven para evaluar el fragmento recuperado; un resultado de similitud
alto no garantiza por sí solo que la respuesta esté correctamente fundamentada.
