import { useId, useMemo, useRef, useState } from 'react';
import type { SyntheticEvent } from 'react';
import { ArrowRight, LoaderCircle } from 'lucide-react';
import { api, errorMessage } from '../../shared/api/api';
import { toolFormModel, toolInput, toolLabel } from './toolSchema';
import type { ToolField } from './toolSchema';
import type { Health, ToolDefinition, ToolTrace } from '../../shared/api/types';

function Field({
  field,
  value,
  onChange,
  prefix,
}: {
  field: ToolField;
  value: string;
  onChange: (value: string) => void;
  prefix: string;
}) {
  const id = `${prefix}-${field.name}`;
  const descriptionId = field.description ? `${id}-help` : undefined;
  return (
    <div>
      <label htmlFor={id}>
        {field.label}
        {!field.required && <span className="field-optional"> · Opcional</span>}
      </label>
      {field.choices || field.type === 'boolean' ? (
        <select
          id={id}
          value={value}
          required={field.required}
          aria-describedby={descriptionId}
          onChange={(event) => onChange(event.target.value)}
        >
          <option value="">Selecciona una opción</option>
          {(field.choices ?? [true, false]).map((choice) => (
            <option key={String(choice)} value={String(choice)}>
              {typeof choice === 'boolean' ? (choice ? 'Sí' : 'No') : String(choice)}
            </option>
          ))}
        </select>
      ) : (
        <input
          id={id}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          required={field.required}
          aria-describedby={descriptionId}
          type={
            field.type === 'number' || field.type === 'integer'
              ? 'number'
              : field.name === 'email'
                ? 'email'
                : 'text'
          }
          step={field.type === 'integer' ? 1 : 'any'}
          min={field.minimum ?? undefined}
          max={field.maximum ?? undefined}
          minLength={field.minLength ?? undefined}
          maxLength={field.maxLength ?? undefined}
        />
      )}
      {field.description && (
        <p className="field-help" id={descriptionId}>
          {field.description}
        </p>
      )}
    </div>
  );
}

export function ToolInputForm({
  tool,
  online,
  health,
  running,
  onRunning,
}: {
  tool: ToolDefinition;
  online: boolean;
  health: Health | null;
  running: boolean;
  onRunning: (running: boolean) => void;
}) {
  const model = useMemo(() => toolFormModel(tool), [tool]);
  const [values, setValues] = useState<Record<string, string>>(() =>
    tool.name === 'calculate'
      ? { expression: '(120 + 80) * 2' }
      : tool.name === 'terminal'
        ? { command: 'pwd' }
        : {},
  );
  const [json, setJson] = useState('');
  const [writeConfirmed, setWriteConfirmed] = useState(false);
  const [result, setResult] = useState<ToolTrace | null>(null);
  const [error, setError] = useState('');
  const runningRef = useRef(false);
  const prefix = useId();
  const writeTool = tool.name === 'create_demo_request' || tool.name === 'create_support_ticket';
  const validation = useMemo(() => {
    try {
      return { input: toolInput(model, values, json), error: '' };
    } catch (err) {
      return { input: null, error: errorMessage(err) };
    }
  }, [model, values, json]);

  async function run(event: SyntheticEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (
      runningRef.current ||
      !online ||
      !tool.enabled ||
      !validation.input ||
      (writeTool && !writeConfirmed)
    )
      return;
    runningRef.current = true;
    onRunning(true);
    setError('');
    setResult(null);
    try {
      const trace = await api.runTool(tool.name, validation.input, writeTool && writeConfirmed);
      setResult(trace);
      if (writeTool && writeConfirmed && trace.status === 'completed')
        window.dispatchEvent(new Event('humanizar-requests-changed'));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      runningRef.current = false;
      onRunning(false);
      setWriteConfirmed(false);
    }
  }

  return (
    <form className="tool-playground" onSubmit={(event) => void run(event)}>
      <div className="playground-heading">
        <span className="mini-label">PRUEBA LA HERRAMIENTA</span>
        <h2>{toolLabel(tool.name)}</h2>
      </div>
      <fieldset className="tool-fields" disabled={running}>
        <legend className="sr-only">Parámetros de {toolLabel(tool.name)}</legend>
        {model.kind === 'fields' &&
          (model.fields.length ? (
            model.fields.map((field) => (
              <Field
                key={field.name}
                field={field}
                value={(Object.hasOwn(values, field.name) ? values[field.name] : undefined) ?? ''}
                prefix={prefix}
                onChange={(value) => {
                  setValues((current) => ({ ...current, [field.name]: value }));
                  setWriteConfirmed(false);
                }}
              />
            ))
          ) : (
            <p className="field-help">Esta consulta no requiere parámetros.</p>
          ))}
        {model.kind === 'json' && (
          <>
            <label htmlFor={`${prefix}-json`}>Parámetros JSON</label>
            <p className="field-help" id={`${prefix}-json-help`}>
              El servidor no publica un esquema para esta herramienta. Introduce un objeto JSON
              explícito; el servidor validará sus parámetros. Usa {'{}'} sólo si no requiere
              ninguno.
            </p>
            <textarea
              id={`${prefix}-json`}
              className="tool-json"
              value={json}
              required
              spellCheck={false}
              aria-describedby={`${prefix}-json-help`}
              aria-invalid={Boolean(json.trim() && !validation.input)}
              onChange={(event) => {
                setJson(event.target.value);
                setWriteConfirmed(false);
              }}
            />
            {json.trim() && validation.error && <p className="field-help">{validation.error}</p>}
          </>
        )}
        {model.kind === 'unsupported' && (
          <>
            <div className="notice error" role="alert">
              {model.message}
            </div>
            <details className="tool-schema">
              <summary>Consultar esquema de entrada</summary>
              <pre>{JSON.stringify(tool.input_schema, null, 2)}</pre>
            </details>
          </>
        )}
        {tool.name === 'terminal' && (
          <p className="field-help">
            Se ejecuta en el servicio aislado. Conexión:{' '}
            {health?.tools.sandbox ? 'disponible' : 'no disponible'}.
          </p>
        )}
        {writeTool && (
          <label className="tool-write-confirm">
            <input
              type="checkbox"
              checked={writeConfirmed}
              onChange={(event) => setWriteConfirmed(event.target.checked)}
            />
            <span>
              Confirmo que quiero registrar esta solicitud con los datos indicados. No se enviarán
              mensajes externos.
            </span>
          </label>
        )}
      </fieldset>
      <button
        className="primary-button tool-run"
        disabled={
          running || !online || !tool.enabled || !validation.input || (writeTool && !writeConfirmed)
        }
      >
        {running ? <LoaderCircle size={16} className="spin" /> : <ArrowRight size={16} />}
        {running
          ? 'Ejecutando…'
          : writeTool
            ? 'Confirmar y registrar solicitud'
            : 'Ejecutar herramienta'}
      </button>
      {error && (
        <div className="notice error" role="alert">
          {error}
        </div>
      )}
      {result && (
        <div className="tool-result" aria-live="polite">
          <div>
            <span className={result.status === 'error' ? 'result-error' : 'result-success'}>
              {result.status === 'error'
                ? 'La herramienta informó un error'
                : 'Ejecución completada'}
            </span>
            <span>{result.duration_ms} ms</span>
          </div>
          <pre>{result.output}</pre>
        </div>
      )}
    </form>
  );
}
