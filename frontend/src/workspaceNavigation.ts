import { BookOpen, ClipboardList, Sparkles, Users, WandSparkles } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { WorkspaceSection } from './types';

export interface WorkspaceNavigationItem {
  id: WorkspaceSection;
  label: string;
  icon: LucideIcon;
}

export function workspaceNavigation({
  isAdmin,
  customerManagement,
}: {
  isAdmin: boolean;
  customerManagement: boolean;
}): readonly [WorkspaceNavigationItem, ...WorkspaceNavigationItem[]] {
  return [
    { id: 'assistant', label: 'Asistente', icon: Sparkles },
    {
      id: 'requests',
      label: isAdmin ? 'Solicitudes de clientes' : 'Mis solicitudes',
      icon: ClipboardList,
    },
    ...(isAdmin
      ? [
          { id: 'knowledge', label: 'Documentación', icon: BookOpen } as const,
          ...(customerManagement
            ? [{ id: 'customers', label: 'Clientes', icon: Users } as const]
            : []),
          { id: 'tools', label: 'Herramientas', icon: WandSparkles } as const,
        ]
      : []),
  ];
}
