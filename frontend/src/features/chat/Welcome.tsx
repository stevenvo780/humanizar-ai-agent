import { ArrowDown, ArrowUpRight, BookOpen, Code2, FileText, WandSparkles } from 'lucide-react';
import type { QuickPrompt } from '../../shared/config/company';
import { Orb } from './Orb';

const promptStyles = [
  { icon: BookOpen, color: 'mint' },
  { icon: WandSparkles, color: 'lavender' },
  { icon: FileText, color: 'peach' },
  { icon: Code2, color: 'blue' },
];

export function Welcome({
  assistant,
  company,
  humanizar,
  prompts,
  disabled,
  onPrompt,
}: {
  assistant: string;
  company: string;
  humanizar: boolean;
  prompts: QuickPrompt[];
  disabled: boolean;
  onPrompt: (question: string) => Promise<void>;
}) {
  return (
    <section className="welcome">
      <div className="welcome-eyebrow">
        <span /> RESPUESTAS CLARAS. DECISIONES MÁS FÁCILES.
      </div>
      <Orb />
      <div className="welcome-heading">
        <span className="greeting">Hola, soy {assistant}.</span>
        <h1>
          Todo sobre {company},
          <br />
          <span>en una conversación.</span>
        </h1>
        <p>
          {humanizar
            ? 'Descubre servicios, explora agentes de IA y resuelve tus dudas.'
            : 'Descubre productos y servicios y resuelve tus dudas con fuentes.'}
          <br className="desktop-break" /> Te ayudamos a dar el siguiente paso.
        </p>
      </div>
      {prompts.length > 0 && (
        <>
          <div className="prompt-section-heading">
            <span>¿Cómo podemos ayudarte?</span>
            <ArrowDown size={13} />
          </div>
          <div className="prompt-grid">
            {prompts.map((prompt, index) => {
              const style = promptStyles[index % promptStyles.length] ?? {
                icon: BookOpen,
                color: 'mint',
              };
              return (
                <button
                  className="prompt-card"
                  key={`${index}-${prompt.question}`}
                  disabled={disabled}
                  onClick={() => void onPrompt(prompt.question)}
                >
                  <span className={`prompt-icon ${style.color}`}>
                    <style.icon size={19} strokeWidth={1.7} />
                  </span>
                  <strong>{prompt.title}</strong>
                  <p>{prompt.subtitle}</p>
                  <ArrowUpRight className="prompt-arrow" size={17} />
                </button>
              );
            })}
          </div>
        </>
      )}
    </section>
  );
}
