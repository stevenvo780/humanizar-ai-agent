import { useEffect, useState } from 'react';
import { api } from '../../shared/api/api';
import { companyPresentation } from '../../shared/config/company';
import type { CompanyIdentity } from '../../shared/api/types';
import { DocsFooter } from './DocsFooter';
import { DocsHeader } from './DocsHeader';
import { DocsIndex } from './DocsIndex';
import { AgentSection } from './sections/AgentSection';
import { ArchitectureSection } from './sections/ArchitectureSection';
import { DataSection } from './sections/DataSection';
import { HeroSection } from './sections/HeroSection';
import { QualitySection } from './sections/QualitySection';
import { SecuritySection } from './sections/SecuritySection';
import { StartSection } from './sections/StartSection';
import { StatusSection } from './sections/StatusSection';
import { ToolsSection } from './sections/ToolsSection';
import { useActiveDocsSection } from './useActiveDocsSection';
import './docs.css';

export default function DocsPage() {
  const [identity, setIdentity] = useState<CompanyIdentity | null>(null);
  const { company, assistant } = companyPresentation(null, identity);
  useEffect(() => {
    let current = true;
    api
      .company()
      .then((result) => {
        if (current) setIdentity(result);
      })
      .catch(() => {
        /* The public page keeps a neutral name when the API is unavailable. */
      });
    return () => {
      current = false;
    };
  }, []);
  useEffect(() => {
    document.title = `${identity ? assistant : 'Asistente'} — Documentación técnica`;
  }, [assistant, identity]);
  const [active, setActive] = useActiveDocsSection();

  return (
    <div className="docs-page">
      <a href="#docs-content" className="skip-link">
        Saltar a la documentación
      </a>
      <DocsHeader assistant={assistant} />
      <div className="docs-layout">
        <DocsIndex active={active} onSelect={setActive} />
        <main id="docs-content" className="docs-content">
          <HeroSection company={company} assistant={assistant} configured={identity !== null} />
          <ArchitectureSection assistant={assistant} />
          <AgentSection />
          <DataSection />
          <SecuritySection />
          <ToolsSection />
          <QualitySection />
          <StatusSection />
          <StartSection />
          <DocsFooter assistant={assistant} />
        </main>
      </div>
    </div>
  );
}
