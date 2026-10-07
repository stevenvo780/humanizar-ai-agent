import { describe, expect, it } from 'vitest';
import { workspaceNavigation } from './workspaceNavigation';

describe('workspace navigation visibility', () => {
  it('keeps customer navigation limited to personal sections even with admin capabilities enabled', () => {
    const items = workspaceNavigation({ isAdmin: false, customerManagement: true });
    expect(items.map((item) => item.id)).toEqual(['assistant', 'requests']);
    expect(items.find((item) => item.id === 'requests')?.label).toBe('Mis solicitudes');
  });

  it('shows document and tool administration while hiding unsupported customer management', () => {
    const items = workspaceNavigation({ isAdmin: true, customerManagement: false });
    expect(items.map((item) => item.id)).toEqual(['assistant', 'requests', 'knowledge', 'tools']);
    expect(items.find((item) => item.id === 'requests')?.label).toBe('Solicitudes de clientes');
  });

  it('provides each enabled administrator section once', () => {
    const items = workspaceNavigation({ isAdmin: true, customerManagement: true });
    expect(items.map((item) => item.id)).toEqual([
      'assistant',
      'requests',
      'knowledge',
      'customers',
      'tools',
    ]);
    expect(new Set(items.map((item) => item.id)).size).toBe(items.length);
  });
});
