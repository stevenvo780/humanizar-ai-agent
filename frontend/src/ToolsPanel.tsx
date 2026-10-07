import { useState } from 'react';
import { ArrowUpRight, Code2, Layers3, Search, Terminal, WandSparkles } from 'lucide-react';
import type { ReactNode } from 'react';
import { toolLabel } from './toolSchema';
import { ToolInputForm } from './ToolInputForm';
import type { Health, ToolDefinition } from './types';

const icons = new Map<string, ReactNode>([
  ['calculate', <Code2 size={21} />],
  ['terminal', <Terminal size={21} />],
  ['search_knowledge', <Search size={21} />],
  ['mcp_company_info', <Layers3 size={21} />],
]);

export function ToolsPanel({
  tools,
  online,
  health,
}: {
  tools: ToolDefinition[];
  online: boolean;
  health: Health | null;
}) {
  const [selection, setSelection] = useState('calculate');
  const [running, setRunning] = useState(false);
  const definition = tools.find((tool) => tool.name === selection) ?? tools[0];
  return (
    <section className="workspace-page" aria-labelledby="tools-title">
      <div className="page-eyebrow">
        <WandSparkles size={15} /> ADMINISTRACIÓN · HERRAMIENTAS
      </div>
      <h1 id="tools-title">
        Una respuesta puede
        <br />
        <span>hacer mucho más.</span>
      </h1>
      <p className="page-intro">
        Prueba las herramientas que el asistente puede usar para ayudarte.
        <br className="desktop-break" /> Comprueba las integraciones y sus resultados reales.
      </p>
      <div className="tool-grid">
        {tools.map((tool) => (
          <button
            className={`tool-card ${definition?.name === tool.name ? 'selected' : ''}`}
            key={tool.name}
            aria-pressed={definition?.name === tool.name}
            disabled={running}
            onClick={() => setSelection(tool.name)}
          >
            <span className="tool-card-top">
              <span className="tool-icon">{icons.get(tool.name) ?? <Code2 size={21} />}</span>
              <span className={`tool-enabled ${tool.enabled ? '' : 'unavailable'}`}>
                <span
                  className={`status-dot ${tool.enabled ? '' : 'status-dot-offline'}`}
                  aria-hidden="true"
                />
                {tool.enabled ? 'Habilitada' : 'No disponible'}
              </span>
            </span>
            <strong>{toolLabel(tool.name)}</strong>
            <p>{tool.description}</p>
            <span className="tool-card-link">
              Explorar herramienta <ArrowUpRight size={14} />
            </span>
          </button>
        ))}
      </div>
      {!tools.length && (
        <div className="empty-state">
          <WandSparkles size={24} />
          <h3>Sin herramientas disponibles</h3>
          <p>La lista se actualizará cuando el servidor esté conectado.</p>
        </div>
      )}
      {definition && (
        <ToolInputForm
          key={definition.name}
          tool={definition}
          online={online}
          health={health}
          running={running}
          onRunning={setRunning}
        />
      )}
    </section>
  );
}
