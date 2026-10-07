import { ChevronDown, Terminal } from 'lucide-react';
import { ActionConfirmation, actionProposal, useConfirmedAction } from '../requests/actions';
import { toolLabel } from '../tools/toolSchema';
import type { ToolTrace } from '../../shared/api/types';

export function Trace({ trace }: { trace: ToolTrace }) {
  const proposal = actionProposal(trace);
  const confirmed = useConfirmedAction(trace.id);
  return (
    <details className={`trace-detail ${proposal ? 'trace-proposal' : ''}`} open={!!proposal}>
      <summary>
        <span className={`trace-status ${trace.status}`}>
          <Terminal size={14} />
        </span>
        <span>
          {proposal
            ? confirmed
              ? 'Solicitud registrada'
              : 'Pendiente de confirmar'
            : toolLabel(trace.tool)}
        </span>
        <span className="trace-time">{trace.duration_ms} ms</span>
        <ChevronDown size={13} />
      </summary>
      <div className="trace-body">
        {proposal ? (
          <ActionConfirmation trace={trace} />
        ) : (
          <>
            <div className="mini-label">Entrada</div>
            <pre>{JSON.stringify(trace.input, null, 2)}</pre>
            <div className="mini-label">
              {trace.status === 'error' ? 'Error de ejecución' : 'Resultado'}
            </div>
            <pre>{trace.output}</pre>
          </>
        )}
      </div>
    </details>
  );
}
