import {
  BookOpen,
  CircleDot,
  Code2,
  Database,
  FileCheck2,
  Network,
  ShieldCheck,
  Workflow,
  Wrench,
} from 'lucide-react';

export const REPOSITORY_URL = 'https://github.com/stevenvo780/humanizar-ai-agent';
export const REPOSITORY_SLUG = new URL(REPOSITORY_URL).pathname.slice(1);
export const sections = [
  { id: 'vision', label: 'El proyecto', icon: <BookOpen size={15} /> },
  { id: 'arquitectura', label: 'Arquitectura', icon: <Network size={15} /> },
  { id: 'agente', label: 'Cómo responde el agente', icon: <Workflow size={15} /> },
  { id: 'datos', label: 'Conocimiento y persistencia', icon: <Database size={15} /> },
  { id: 'seguridad', label: 'Acceso y seguridad', icon: <ShieldCheck size={15} /> },
  { id: 'herramientas', label: 'Herramientas e integraciones', icon: <Wrench size={15} /> },
  { id: 'calidad', label: 'Calidad y evidencia', icon: <FileCheck2 size={15} /> },
  { id: 'estado', label: 'Estado y límites', icon: <CircleDot size={15} /> },
  { id: 'empezar', label: 'Explorar el código', icon: <Code2 size={15} /> },
];
