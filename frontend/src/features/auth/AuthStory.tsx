import { Check, ChevronRight, Sparkles } from 'lucide-react';

export function AuthStory({
  assistant,
  company,
  humanizar,
  website,
}: {
  assistant: string;
  company: string;
  humanizar: boolean;
  website: string | null;
}) {
  const brand = (
    <>
      <Sparkles size={29} strokeWidth={1.4} />
      <span>
        {assistant}
        <i>.</i>
      </span>
    </>
  );
  return (
    <section className="auth-story">
      {website ? (
        <a href={website} target="_blank" rel="noopener noreferrer" className="auth-brand">
          {brand}
        </a>
      ) : (
        <div className="auth-brand">{brand}</div>
      )}
      <div className="auth-editorial">
        <span className="page-eyebrow">
          <span className="status-dot" />{' '}
          {humanizar ? 'SOFTWARE. AGENTES. POSIBILIDADES.' : 'INFORMACIÓN. AYUDA. CONVERSACIÓN.'}
        </span>
        <h1>
          Las buenas preguntas
          <br />
          abren <span>nuevos caminos.</span>
        </h1>
        <p>
          Conoce los productos de {company}, encuentra la solución para tu empresa y da el siguiente
          paso con un asistente que conecta la información.
        </p>
        <div className="auth-orbit" aria-hidden="true">
          <svg viewBox="0 0 300 240" fill="none">
            <g stroke="#86c4af" strokeWidth=".65">
              <ellipse cx="150" cy="120" rx="105" ry="82" />
              <ellipse cx="150" cy="120" rx="70" ry="82" />
              <ellipse cx="150" cy="120" rx="32" ry="82" />
              <ellipse cx="150" cy="120" rx="105" ry="29" />
              <ellipse cx="150" cy="120" rx="105" ry="57" />
              <ellipse cx="150" cy="120" rx="44" ry="105" transform="rotate(50 150 120)" />
              <ellipse cx="150" cy="120" rx="44" ry="105" transform="rotate(-50 150 120)" />
            </g>
            <path
              d="m150 89 8.5 22.5L181 120l-22.5 8.5L150 151l-8.5-22.5L119 120l22.5-8.5Z"
              fill="#c3ecd9"
            />
            <circle cx="66" cy="74" r="4" fill="#a8e5cd" />
            <circle cx="239" cy="162" r="3" fill="#aaa2d2" />
          </svg>
          <span className="orbit-chip chip-one">
            <Sparkles size={13} /> {humanizar ? 'Agentes a medida' : 'Información de la empresa'}
          </span>
          <span className="orbit-chip chip-two">
            <Check size={13} /> Respuestas con fuentes
          </span>
        </div>
      </div>
      <div className="auth-story-footer">
        <span>
          {company} · {humanizar ? 'Tecnología que resuelve.' : 'Información que conecta.'}
        </span>
        {website && (
          <a href={website} target="_blank" rel="noopener noreferrer">
            Conoce {company} <ChevronRight size={12} />
          </a>
        )}
      </div>
    </section>
  );
}
