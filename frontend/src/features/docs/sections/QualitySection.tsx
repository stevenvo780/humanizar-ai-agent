import { Check } from 'lucide-react';
import { DocsSection } from '../DocsSection';
import { ExternalLink } from '../ExternalLink';
import { repositoryFile } from '../docsLinks';

export function QualitySection() {
  return (
    <DocsSection
      id="calidad"
      label="CALIDAD Y EVIDENCIA"
      title="El estándar se demuestra con comprobaciones."
    >
      <p>
        La base cuenta con <strong>pruebas automatizadas en cada capa</strong>, incluidas pruebas
        reales de persistencia PostgreSQL, y comprobaciones de formato, tipos y build. La evidencia
        describe la base registrada; cada cambio posterior debe volver a pasar sus comprobaciones.
        Los totales de cada ejecución están en{' '}
        <ExternalLink href={repositoryFile('docs/VALIDATION.md')}>VALIDATION.md</ExternalLink>.
      </p>
      <div className="docs-quality-table-wrap">
        <table className="docs-quality-table">
          <caption>Inventario y evidencia registrados el 7 de octubre de 2026</caption>
          <thead>
            <tr>
              <th scope="col">Capa</th>
              <th scope="col">Comprobaciones</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row">API y agente</th>
              <td>Ruff, formato, mypy estricto, agente, autenticación y persistencia PostgreSQL</td>
            </tr>
            <tr>
              <th scope="row">Sandbox y utilidades</th>
              <td>Ruff, formato, tipos, límites de ejecución, importación y empaquetado</td>
            </tr>
            <tr>
              <th scope="row">Helpers de despliegue</th>
              <td>Orígenes, TLS, secretos, bootstrap y configuración reproducible</td>
            </tr>
            <tr>
              <th scope="row">Frontend</th>
              <td>ESLint con tipos, hooks y accesibilidad; Prettier; TypeScript; Vitest; build</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div className="docs-quality-checks">
        <span>
          <Check size={13} /> 0 vulnerabilidades web en el audit registrado
        </span>
        <span>
          <Check size={13} /> Locks de dependencias
        </span>
        <span>
          <Check size={13} /> Revisión independiente
        </span>
        <span>
          <Check size={13} /> Smoke desktop y móvil
        </span>
      </div>
      <p>
        Las pruebas relevantes cubren UTF-8 fragmentado y errores SSE; refresh y logout;
        confirmaciones permitidas; aislamiento de cuentas, ingesta, citas y presupuestos del agente.
        PostgreSQL tiene pruebas en una base temporal y una conexión productiva con TLS verificado.
        Las rutas de Vercel se compilan sin serializar secretos. El smoke del despliegue público
        comprobó acceso, sesión renovable, historial, fuentes, Swagger y documentación, sin errores
        JavaScript ni overflow móvil. Un reinicio de la API conservó el historial y las sesiones.
      </p>
      <p>
        La{' '}
        <ExternalLink href={repositoryFile('docs/QUALITY.md')}>
          auditoría de calidad y adaptación
        </ExternalLink>{' '}
        relaciona cada hallazgo con su corrección y sus regresiones. Incluye importación local
        segura, formularios derivados del esquema, sesiones ante fallos temporales, anuncio
        accesible y verificaciones de Spec Kit que conservan la selección activa.
      </p>
    </DocsSection>
  );
}
