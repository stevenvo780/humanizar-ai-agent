import { Network } from 'lucide-react';

export function ArchitectureDiagram({ assistant }: { assistant: string }) {
  return (
    <figure className="docs-architecture">
      <figcaption>
        <span>
          <Network size={16} /> Un contrato claro entre cada pieza
        </span>
        <span>Vercel → VPS · REST + SSE</span>
      </figcaption>
      <div className="docs-diagram-scroll">
        <svg
          viewBox="0 0 760 390"
          role="img"
          aria-labelledby="architecture-title architecture-description"
        >
          <title id="architecture-title">{`Arquitectura de ${assistant}`}</title>
          <desc id="architecture-description">
            React se sirve desde Vercel. Las llamadas REST y SSE del mismo origen pasan por un
            rewrite que añade una cabecera privada hacia FastAPI en Docker en el VPS. La API valida
            JWT, consulta PostgreSQL con TLS en el schema lumen, recupera evidencia de Qdrant local
            y coordina Claude Haiku y el sandbox aislado. SQLite es la alternativa local opcional.
            MCP consulta la misma API por HTTP. Este diagrama describe la configuración desplegada;
            la evidencia de cada comprobación se registra por separado.
          </desc>
          <defs>
            <marker
              id="docs-arrow"
              markerWidth="6"
              markerHeight="6"
              refX="5"
              refY="3"
              orient="auto"
            >
              <path d="M0 0 6 3 0 6" fill="none" stroke="#6f9484" />
            </marker>
          </defs>
          <g fill="none" stroke="#587e70" strokeWidth="1.2" markerEnd="url(#docs-arrow)">
            <path d="M164 90h48" />
            <path d="M362 90h54" />
            <path d="M502 120v42" />
            <path d="M502 120v20H285v22" />
            <path d="M285 218v49" />
            <path d="M362 298h32V190h22" />
            <path d="M285 298h131" />
            <path d="M164 298h23V38h315v22" strokeDasharray="4 5" />
          </g>
          <g className="diagram-labels" fill="#7b9a8b" fontSize="9">
            <text x="177" y="78">
              REST/SSE
            </text>
            <text x="376" y="78">
              HTTPS
            </text>
            <text x="300" y="132">
              agente
            </text>
            <text x="529" y="144">
              datos
            </text>
            <text x="375" y="178">
              persiste
            </text>
            <text x="299" y="247">
              tool_use
            </text>
            <text x="18" y="250">
              stdio · identidad por HTTP
            </text>
          </g>
          <g className="diagram-boxes">
            <rect x="14" y="60" width="150" height="60" rx="9" />
            <rect x="14" y="267" width="150" height="60" rx="9" />
            <rect x="212" y="60" width="150" height="60" rx="9" className="diagram-box-primary" />
            <rect x="416" y="60" width="173" height="60" rx="9" />
            <rect x="212" y="162" width="150" height="56" rx="9" className="diagram-box-lavender" />
            <rect x="416" y="162" width="173" height="56" rx="9" />
            <rect x="212" y="267" width="150" height="60" rx="9" />
            <rect x="416" y="267" width="173" height="60" rx="9" />
          </g>
          <g className="diagram-node-titles" fill="#d0e4d8" fontSize="12">
            <text x="32" y="85">
              React · Vercel
            </text>
            <text x="32" y="292">
              MCP read-only
            </text>
            <text x="230" y="85">
              Rewrite protegido
            </text>
            <text x="434" y="85">
              FastAPI · VPS Docker
            </text>
            <text x="230" y="185">
              Claude Haiku 4.5
            </text>
            <text x="434" y="185">
              PostgreSQL + Qdrant
            </text>
            <text x="230" y="292">
              Herramientas
            </text>
            <text x="434" y="292">
              Sandbox Docker
            </text>
          </g>
          <g fill="#819c8f" fontSize="9">
            <text x="32" y="104">
              TypeScript · Cliente web
            </text>
            <text x="32" y="311">
              Misma API · sin secretos
            </text>
            <text x="230" y="104">
              Mismo origen · header privado
            </text>
            <text x="434" y="104">
              JWT · roles · orquestación
            </text>
            <text x="230" y="203">
              Ciclo nativo y limitado
            </text>
            <text x="434" y="203">
              SQL con TLS · Qdrant local
            </text>
            <text x="230" y="311">
              Registro compartido
            </text>
            <text x="434" y="311">
              Presets · aislamiento
            </text>
          </g>
          <g fill="#658878" fontSize="8">
            <text x="14" y="376">
              SQLite opcional para desarrollo local. Secretos fuera del navegador.
            </text>
            <text x="416" y="376">
              La terminal solo ejecuta presets en su servicio aislado.
            </text>
          </g>
        </svg>
      </div>
      <p>
        El navegador conserva llamadas a <code>/api</code> en el mismo origen. El proxy añade la
        cabecera privada en el servidor; la API concentra permisos, recuperación, persistencia y
        ejecución. El modelo recibe resultados de herramientas, no acceso directo a las bases.
      </p>
    </figure>
  );
}
