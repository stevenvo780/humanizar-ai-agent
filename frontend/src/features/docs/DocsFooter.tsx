import { ArrowRight, Sparkles } from 'lucide-react';
import { SiteLink } from '../../shared/routing/navigation';

export function DocsFooter({ assistant }: { assistant: string }) {
  return (
    <footer className="docs-footer">
      <div>
        <Sparkles size={20} />
        <span>
          {assistant}
          <strong>Información clara. Código que explica sus decisiones.</strong>
        </span>
      </div>
      <SiteLink href="/">
        Volver al asistente
        <ArrowRight size={15} />
      </SiteLink>
    </footer>
  );
}
