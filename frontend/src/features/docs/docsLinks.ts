/** Public links shown on the technical page. Only public URLs: no hosts, IPs or settings. */
// The GitHub repository keeps its original (legacy) name: renaming it would break deployments.
export const REPOSITORY_URL = 'https://github.com/stevenvo780/humanizar-ai-agent';
export const REPOSITORY_BRANCH = 'dev';
export const REPOSITORY_SLUG = new URL(REPOSITORY_URL).pathname.slice(1);
export const PUBLIC_APP_URL = 'https://softop-ai-agent.vercel.app';
export const API_DOCS_PATH = '/api/docs';
export const OPENAPI_PATH = '/api/openapi.json';

/** The technical exam endpoint: public, at the API root, proxied by the same origin. */
export const EXAM_ENDPOINT_URL = `${PUBLIC_APP_URL}/preguntar`;
export const EXAM_CURL = [
  `curl -X POST ${EXAM_ENDPOINT_URL} \\`,
  "  -H 'Content-Type: application/json' \\",
  `  -d '{"pregunta": "¿Cómo hago una devolución?"}'`,
].join('\n');

/** Every repository file the page links to; a unit test checks that each one exists. */
export const REPOSITORY_FILES = [
  'README.md',
  'docs/ARCHITECTURE.md',
  'docs/API_CONTRACT.md',
  'docs/DEPLOYMENT.md',
  'docs/OPERATIONS.md',
  'docs/VALIDATION.md',
  'docs/QUALITY.md',
  'docs/SPECKIT.md',
  'docs/EXAM_20_MIN.md',
  'docs/EXAM_RECIPES.md',
  'docs/RAG.md',
  'docs/MCP.md',
  'docs/ADMIN.md',
  'docs/FEDORA.md',
  '.specify/memory/constitution.md',
  'specs/001-company-agent/spec.md',
  'specs/001-company-agent/plan.md',
  'specs/001-company-agent/tasks.md',
  'specs/001-company-agent/analysis.md',
  'specs/001-company-agent/checklists/requirements-quality.md',
  'specs/002-exam-adaptation/spec.md',
  'specs/002-exam-adaptation/tasks.md',
  'specs/002-exam-adaptation/research.md',
  'specs/002-exam-adaptation/quickstart.md',
  'softop-rag/README.md',
] as const;
export type RepositoryFile = (typeof REPOSITORY_FILES)[number];

export function repositoryFile(path: RepositoryFile): string {
  return `${REPOSITORY_URL}/blob/${REPOSITORY_BRANCH}/${path}`;
}

export type ResourceIcon = 'live' | 'code' | 'docs' | 'spec';
export interface ResourceLink {
  label: string;
  detail: string;
  href: string;
  path?: RepositoryFile;
}
export interface ResourceGroup {
  id: string;
  title: string;
  description: string;
  icon: ResourceIcon;
  links: readonly ResourceLink[];
}

function file(path: RepositoryFile, label: string, detail: string): ResourceLink {
  return { label, detail, href: repositoryFile(path), path };
}

export const resourceGroups: readonly ResourceGroup[] = [
  {
    id: 'en-vivo',
    title: 'Producto en vivo',
    description: 'La aplicación publicada y el contrato de su API.',
    icon: 'live',
    links: [
      {
        label: 'Aplicación pública',
        detail: 'Asistente Softop desplegado en Vercel',
        href: PUBLIC_APP_URL,
      },
      {
        label: 'API · Swagger',
        detail: 'Referencia interactiva en /api/docs',
        href: API_DOCS_PATH,
      },
      { label: 'OpenAPI JSON', detail: 'Contrato en /api/openapi.json', href: OPENAPI_PATH },
    ],
  },
  {
    id: 'codigo',
    title: 'Código en GitHub',
    description: `Repositorio público ${REPOSITORY_SLUG}, rama ${REPOSITORY_BRANCH}.`,
    icon: 'code',
    links: [
      {
        label: 'Repositorio',
        detail: `Código completo · rama ${REPOSITORY_BRANCH}`,
        href: `${REPOSITORY_URL}/tree/${REPOSITORY_BRANCH}`,
      },
      {
        label: 'Commits',
        detail: `Historial de la rama ${REPOSITORY_BRANCH}`,
        href: `${REPOSITORY_URL}/commits/${REPOSITORY_BRANCH}`,
      },
      { label: 'Issues', detail: 'Seguimiento público', href: `${REPOSITORY_URL}/issues` },
    ],
  },
  {
    id: 'documentacion',
    title: 'Documentación técnica',
    description: 'Cada decisión, procedimiento y evidencia, en el repositorio.',
    icon: 'docs',
    links: [
      file('README.md', 'README', 'Arranque, variables y comandos'),
      file('docs/ARCHITECTURE.md', 'Arquitectura', 'Componentes y flujos'),
      file('docs/API_CONTRACT.md', 'Contrato de la API', 'Rutas, SSE y errores'),
      file('docs/DEPLOYMENT.md', 'Despliegue', 'Vercel, Docker y PostgreSQL'),
      file('docs/OPERATIONS.md', 'Operaciones', 'Runbook, backups y restauración'),
      file('docs/VALIDATION.md', 'Validación', 'Evidencia y comprobaciones'),
      file('docs/QUALITY.md', 'Calidad', 'Hallazgos y regresiones'),
      file('docs/SPECKIT.md', 'Spec Kit', 'Flujo y selección de features'),
      file('docs/EXAM_20_MIN.md', 'Examen en 20 minutos', 'Guion de adaptación'),
      file('docs/EXAM_RECIPES.md', 'Recetas verificadas', 'Endpoint RAG, API externa, proveedor'),
      file('docs/RAG.md', 'RAG', 'Vectores y recuperación'),
      file('docs/MCP.md', 'MCP', 'Servidor autenticado'),
      file('docs/ADMIN.md', 'Administración', 'Cuentas, roles y clientes'),
      file('softop-rag/README.md', 'Entrega softop-rag', 'POST /preguntar independiente'),
    ],
  },
  {
    id: 'spec-kit',
    title: 'Artefactos de Spec Kit',
    description: '001 es la base implementada; 002 adapta la base al enunciado de Softop.',
    icon: 'spec',
    links: [
      file('.specify/memory/constitution.md', 'Constitución', 'Principios del proyecto'),
      file('specs/001-company-agent/spec.md', '001 · Especificación', 'Requisitos de la base'),
      file('specs/001-company-agent/plan.md', '001 · Plan', 'Arquitectura y decisiones'),
      file('specs/001-company-agent/tasks.md', '001 · Tareas', 'Trabajo trazable'),
      file('specs/001-company-agent/analysis.md', '001 · Análisis', 'Coherencia entre artefactos'),
      file(
        'specs/001-company-agent/checklists/requirements-quality.md',
        '001 · Checklist',
        'Calidad de los requisitos',
      ),
      file('specs/002-exam-adaptation/spec.md', '002 · Especificación', 'POST /preguntar con RAG'),
      file('specs/002-exam-adaptation/tasks.md', '002 · Tareas', 'Trabajo del enunciado'),
      file('specs/002-exam-adaptation/research.md', '002 · Research', 'Requisito → archivos'),
      file('specs/002-exam-adaptation/quickstart.md', '002 · Quickstart', 'Escenarios Q0–Q10'),
    ],
  },
];

/** Opens off-page links in a new tab without giving the new page access to this one. */
export const EXTERNAL_LINK = { target: '_blank', rel: 'noopener noreferrer' } as const;
