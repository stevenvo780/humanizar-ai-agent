import { createContext, useContext, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { CheckCheck, LoaderCircle, Send, ShieldCheck } from 'lucide-react';
import { api, errorMessage } from '../../shared/api/api';
import type { ToolTrace } from '../../shared/api/types';

interface Proposal {
  tool: 'create_demo_request' | 'create_support_ticket';
  input: Record<string, unknown>;
  message: string;
}

const fieldLabels: Record<string, string> = {
  name: 'Nombre',
  email: 'Correo',
  company: 'Empresa',
  interest: 'Producto',
  needs: 'Necesidad',
  subject: 'Asunto',
  description: 'Descripción',
};

function requestReceipt(output: string): { id: string; status: string } | null {
  try {
    const data: unknown = JSON.parse(output);
    if (
      !data ||
      typeof data !== 'object' ||
      !('request' in data) ||
      !data.request ||
      typeof data.request !== 'object'
    )
      return null;
    const request = data.request;
    if (
      !('id' in request) ||
      typeof request.id !== 'string' ||
      !('status' in request) ||
      typeof request.status !== 'string'
    )
      return null;
    return { id: request.id, status: request.status };
  } catch {
    return null;
  }
}

export function actionProposal(trace: ToolTrace): Proposal | null {
  try {
    const data: unknown = JSON.parse(trace.output);
    if (
      !data ||
      typeof data !== 'object' ||
      !('requires_confirmation' in data) ||
      data.requires_confirmation !== true ||
      !('action' in data) ||
      !data.action ||
      typeof data.action !== 'object'
    )
      return null;
    const action = data.action;
    if (
      !('tool' in action) ||
      (action.tool !== 'create_demo_request' && action.tool !== 'create_support_ticket') ||
      !('input' in action) ||
      !action.input ||
      typeof action.input !== 'object' ||
      Array.isArray(action.input)
    )
      return null;
    return {
      tool: action.tool,
      input: action.input as Record<string, unknown>,
      message:
        'message' in data && typeof data.message === 'string'
          ? data.message
          : 'Revisa los datos y confirma para registrar la solicitud.',
    };
  } catch {
    return null;
  }
}

interface ActionState {
  results: Record<string, ToolTrace>;
  pending: string[];
  errors: Record<string, string>;
  confirm: (trace: ToolTrace) => Promise<void>;
}
const ActionContext = createContext<ActionState | null>(null);

export function useConfirmedAction(id: string): boolean {
  return !!useContext(ActionContext)?.results[id];
}

export function ActionsProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<Record<string, ToolTrace>>({});
  const [pending, setPending] = useState<string[]>([]);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const inFlight = useRef(new Set<string>());
  async function confirm(trace: ToolTrace): Promise<void> {
    const proposal = actionProposal(trace);
    if (!proposal || results[trace.id] || inFlight.current.has(trace.id)) return;
    inFlight.current.add(trace.id);
    setPending((current) => [...current, trace.id]);
    setErrors((current) => ({ ...current, [trace.id]: '' }));
    try {
      const result = await api.confirmAction(proposal.tool, proposal.input, trace.id);
      if (result.status === 'error') throw new Error(result.output);
      setResults((current) => ({ ...current, [trace.id]: result }));
      window.dispatchEvent(new Event('lumen-requests-changed'));
    } catch (err) {
      setErrors((current) => ({ ...current, [trace.id]: errorMessage(err) }));
    } finally {
      inFlight.current.delete(trace.id);
      setPending((current) => current.filter((id) => id !== trace.id));
    }
  }
  return (
    <ActionContext.Provider value={{ results, pending, errors, confirm }}>
      {children}
    </ActionContext.Provider>
  );
}

export function ActionConfirmation({ trace }: { trace: ToolTrace }) {
  const state = useContext(ActionContext);
  const proposal = actionProposal(trace);
  if (!proposal || !state) return null;
  const result = state.results[trace.id];
  const receipt = result ? requestReceipt(result.output) : null;
  const pending = state.pending.includes(trace.id);
  return (
    <div className="action-confirmation">
      <div className="action-confirmation-label">
        <ShieldCheck size={15} />
        <strong>{result ? 'Solicitud registrada' : 'Tu confirmación es necesaria'}</strong>
      </div>
      <p>{proposal.message}</p>
      <dl>
        {Object.entries(proposal.input).map(([key, value]) => (
          <div key={key}>
            <dt>{fieldLabels[key] ?? key.replaceAll('_', ' ')}</dt>
            <dd>{typeof value === 'string' ? value : JSON.stringify(value)}</dd>
          </div>
        ))}
      </dl>
      {result ? (
        <div className="action-success">
          <CheckCheck size={16} />
          <span>Registrada en Mis solicitudes. No se enviaron mensajes externos.</span>
          {receipt && (
            <dl>
              <div>
                <dt>Identificador de solicitud</dt>
                <dd>#{receipt.id}</dd>
              </div>
              <div>
                <dt>Estado</dt>
                <dd>{receipt.status === 'received' ? 'Recibida' : receipt.status}</dd>
              </div>
            </dl>
          )}
        </div>
      ) : (
        <button
          className="primary-button"
          disabled={pending}
          onClick={() => void state.confirm(trace)}
        >
          {pending ? <LoaderCircle className="spin" size={15} /> : <Send size={14} />}
          {pending
            ? 'Registrando…'
            : proposal.tool === 'create_demo_request'
              ? 'Confirmar solicitud de demo'
              : 'Confirmar ticket de soporte'}
        </button>
      )}
      {state.errors[trace.id] && (
        <p className="action-error" role="alert">
          {state.errors[trace.id]}
        </p>
      )}
    </div>
  );
}
