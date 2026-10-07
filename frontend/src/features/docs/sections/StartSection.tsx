import { Terminal } from 'lucide-react';
import { DocsSection } from '../DocsSection';
import { ExternalLink } from '../ExternalLink';
import { REPOSITORY_URL, repositoryFile } from '../docsLinks';

const LOCAL_COMMANDS = [
  `git clone ${REPOSITORY_URL}.git softop-ai-agent`,
  'cd softop-ai-agent',
  'make setup',
  'make check',
  'make dev',
].join('\n');

export function StartSection() {
  return (
    <DocsSection
      id="empezar"
      label="EJECUTAR EN LOCAL"
      title="Del clon a la primera respuesta, con comandos reproducibles."
    >
      <p>
        El <ExternalLink href={repositoryFile('README.md')}>README</ExternalLink> reúne requisitos,
        variables sin valores sensibles, arranque y comprobaciones. Sin clave del proveedor, el modo
        demo responde de forma extractiva y lo indica. Todos los enlaces del proyecto están en{' '}
        <a href="#recursos">Recursos y enlaces</a>.
      </p>
      <div className="docs-start-code">
        <div>
          <Terminal size={14} />
          <span>Flujo de trabajo documentado</span>
          <span>Desde una copia nueva</span>
        </div>
        <pre>
          <code>{LOCAL_COMMANDS}</code>
        </pre>
        <p>
          La configuración privada se crea localmente a partir de la plantilla pública; el
          repositorio no incluye claves ni credenciales predeterminadas. Para preparar un equipo de
          presentación, consulta la{' '}
          <ExternalLink href={repositoryFile('docs/FEDORA.md')}>guía de Fedora</ExternalLink>.
        </p>
      </div>
    </DocsSection>
  );
}
