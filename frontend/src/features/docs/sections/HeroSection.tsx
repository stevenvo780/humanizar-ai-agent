import {
  Braces,
  CheckCheck,
  Code2,
  Database,
  FileCheck2,
  Fingerprint,
  GitBranch,
  Sparkles,
} from 'lucide-react';

export function HeroSection({
  company,
  assistant,
  configured,
}: {
  company: string;
  assistant: string;
  configured: boolean;
}) {
  return (
    <section className="docs-hero" id="vision" tabIndex={-1} aria-labelledby="docs-hero-title">
      {/* prettier-ignore */}
      <div className="docs-eyebrow">
        <GitBranch size={13} /> DOCUMENTACIÓN TÉCNICA{' '}
        <span>01 / {company.toUpperCase()}</span>
      </div>
      <h1 id="docs-hero-title">
        La claridad también
        <br />
        está <span>en el código.</span>
      </h1>
      <p className="docs-hero-intro">
        Una conversación sencilla por fuera. Una arquitectura con contratos, fuentes y límites
        claros por dentro. Así está construido {assistant}.
      </p>
      <p className="docs-snapshot-note">
        Base preparada para la prueba técnica de Softop.{' '}
        {configured
          ? `${company} es la empresa configurada actualmente;`
          : 'La empresa se configura en el backend;'}{' '}
        el perfil, los documentos y las herramientas se adaptan a los requisitos.
      </p>
      <div className="docs-hero-tags">
        <span>
          <Code2 size={12} /> React + TypeScript
        </span>
        <span>
          <Braces size={12} /> FastAPI
        </span>
        <span>
          <Sparkles size={12} /> Claude Haiku
        </span>
        <span>
          <Database size={12} /> PostgreSQL + Qdrant
        </span>
      </div>
      <div className="docs-evidence-heading">
        <span>
          <FileCheck2 size={13} /> EVIDENCIA REGISTRADA
        </span>
        <time dateTime="2026-10-07">7 de octubre de 2026</time>
      </div>
      <div className="docs-metrics">
        <div>
          <span className="docs-metric-title">
            <FileCheck2 size={18} /> Pruebas por capa
          </span>
          <p>API, sandbox, despliegue y web</p>
          <small>Se ejecutan en cada comprobación</small>
        </div>
        <div>
          <span className="docs-metric-title">
            <Fingerprint size={18} /> Tipos, sin atajos
          </span>
          <p>TypeScript strict · mypy estricto</p>
          <small>Lint, formato, contratos y builds</small>
        </div>
        <div>
          <span className="docs-metric-title">
            <CheckCheck size={18} /> Evidencia visible
          </span>
          <p>Fuentes y herramientas reales</p>
          <small>Referencias y trazas de ejecución</small>
        </div>
      </div>
      <p className="docs-snapshot-note">
        El inventario y la evidencia están fechados; esta página no ejecuta comprobaciones en vivo.
        La actualización del backend auditado está pendiente del acceso SSH al VPS.
      </p>
    </section>
  );
}
