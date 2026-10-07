import {
  BookOpen,
  CircleDot,
  Code2,
  Database,
  FileCheck2,
  Hammer,
  LayoutGrid,
  Link2,
  Network,
  ShieldCheck,
  Workflow,
  Wrench,
} from 'lucide-react';

/** Page order: the index, the section numbers and presentation mode all follow this list. */
export const sections = [
  { id: 'vision', label: 'El proyecto', icon: <BookOpen size={15} /> },
  { id: 'recursos', label: 'Recursos y enlaces', icon: <Link2 size={15} /> },
  { id: 'capacidades', label: 'Qué tiene', icon: <LayoutGrid size={15} /> },
  { id: 'proceso', label: 'Cómo se hizo', icon: <Hammer size={15} /> },
  { id: 'arquitectura', label: 'Arquitectura', icon: <Network size={15} /> },
  { id: 'agente', label: 'Cómo responde el agente', icon: <Workflow size={15} /> },
  { id: 'datos', label: 'Conocimiento y persistencia', icon: <Database size={15} /> },
  { id: 'seguridad', label: 'Acceso y seguridad', icon: <ShieldCheck size={15} /> },
  { id: 'herramientas', label: 'Herramientas e integraciones', icon: <Wrench size={15} /> },
  { id: 'calidad', label: 'Calidad y evidencia', icon: <FileCheck2 size={15} /> },
  { id: 'estado', label: 'Estado y límites', icon: <CircleDot size={15} /> },
  { id: 'empezar', label: 'Ejecutar en local', icon: <Code2 size={15} /> },
] as const;
export type SectionId = (typeof sections)[number]['id'];
export const sectionIds: readonly SectionId[] = sections.map((section) => section.id);

export function sectionNumber(id: SectionId): string {
  return String(sectionIds.indexOf(id) + 1).padStart(2, '0');
}

export function sectionLabel(id: SectionId): string {
  return sections.find((section) => section.id === id)?.label ?? id;
}
