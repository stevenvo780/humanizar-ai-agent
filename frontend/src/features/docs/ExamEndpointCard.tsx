import { ArrowUpRight, FlaskConical, Terminal } from 'lucide-react';
import { CopyButton } from './CopyButton';
import { ExternalLink } from './ExternalLink';
import { EXAM_CURL, repositoryFile } from './docsLinks';

/** The Softop technical exam deliverable, presented where reviewers look first. */
export function ExamEndpointCard() {
  return (
    <article
      id="prueba-tecnica"
      className="docs-exam-card"
      tabIndex={-1}
      aria-labelledby="prueba-tecnica-title"
    >
      <span className="docs-exam-eyebrow">
        <FlaskConical size={14} /> PRUEBA TÉCNICA · SOFTOP
      </span>
      <h3 id="prueba-tecnica-title">
        Prueba técnica: <code>POST /preguntar</code>
      </h3>
      <p>
        Responde preguntas sobre el software de gestión para ópticas usando solo sus diez preguntas
        frecuentes: recupera los fragmentos relevantes, los inyecta en un prompt que restringe al
        modelo y devuelve su respuesta. Si la información no está en las FAQ, lo indica sin llamar
        al modelo.
      </p>
      <dl className="docs-exam-contract">
        <div>
          <dt>Entrada</dt>
          <dd>
            <code>{'{"pregunta": "..."}'}</code>
          </dd>
        </div>
        <div>
          <dt>Salida</dt>
          <dd>
            <code>{'{"respuesta": "..."}'}</code>
          </dd>
        </div>
        <div>
          <dt>Acceso</dt>
          <dd>Público, sin cuenta, con límite por IP</dd>
        </div>
      </dl>
      <div className="docs-start-code">
        <div>
          <Terminal size={14} />
          <span>Pruébalo desde una terminal</span>
          <CopyButton text={EXAM_CURL} label="el comando curl" />
        </div>
        <pre>
          <code>{EXAM_CURL}</code>
        </pre>
      </div>
      <div className="docs-exam-links">
        <ExternalLink href={repositoryFile('softop-rag/README.md')}>
          Entrega independiente · softop-rag/README.md <ArrowUpRight size={14} />
        </ExternalLink>
        <ExternalLink href={repositoryFile('specs/002-exam-adaptation/spec.md')}>
          Especificación 002 · spec.md <ArrowUpRight size={14} />
        </ExternalLink>
      </div>
    </article>
  );
}
