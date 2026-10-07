import { useEffect, useState } from 'react';
import { api } from '../../shared/api/api';
import { companyPresentation } from '../../shared/config/company';
import type { CompanyIdentity } from '../../shared/api/types';
import { DocsFooter } from './DocsFooter';
import { DocsHeader } from './DocsHeader';
import { DocsIndex } from './DocsIndex';
import { PresentationBar } from './PresentationBar';
import { sectionIds, sections } from './docsContent';
import { presentationStatus } from './presentation';
import { AgentSection } from './sections/AgentSection';
import { ArchitectureSection } from './sections/ArchitectureSection';
import { CapabilitiesSection } from './sections/CapabilitiesSection';
import { DataSection } from './sections/DataSection';
import { HeroSection } from './sections/HeroSection';
import { ProcessSection } from './sections/ProcessSection';
import { QualitySection } from './sections/QualitySection';
import { ResourcesSection } from './sections/ResourcesSection';
import { SecuritySection } from './sections/SecuritySection';
import { StartSection } from './sections/StartSection';
import { StatusSection } from './sections/StatusSection';
import { ToolsSection } from './sections/ToolsSection';
import { useActiveDocsSection } from './useActiveDocsSection';
import { usePresentationMode } from './usePresentationMode';
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
  const presentation = usePresentationMode(sectionIds, active, setActive);
  const slide = presentation.index === null ? undefined : sections[presentation.index];

  return (
    <div className={`docs-page${slide ? ' is-presenting' : ''}`}>
      <a href="#docs-content" className="skip-link">
        Saltar a la documentación
      </a>
      <DocsHeader
        assistant={assistant}
        presenting={slide !== undefined}
        onTogglePresentation={slide ? presentation.stop : presentation.start}
        presentRef={presentation.triggerRef}
      />
      <div className="docs-layout">
        <DocsIndex active={active} onSelect={setActive} />
        <main id="docs-content" className="docs-content">
          <HeroSection company={company} assistant={assistant} configured={identity !== null} />
          <ResourcesSection />
          <CapabilitiesSection />
          <ProcessSection />
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
      {slide && presentation.index !== null && (
        <PresentationBar
          index={presentation.index}
          total={sections.length}
          label={slide.label}
          onStep={presentation.step}
          onExit={presentation.stop}
        />
      )}
      <p className="sr-only" role="status" aria-live="polite" aria-atomic="true">
        {slide && presentation.index !== null
          ? presentationStatus(presentation.index, sections.length, slide.label)
          : ''}
      </p>
    </div>
  );
}
