import { MessageSquare } from 'lucide-react';
import { DocsSection } from '../DocsSection';

export function AgentSection() {
  return (
    <DocsSection
      id="agente"
      number="03"
      label="PROCESO DEL AGENTE"
      title="De una pregunta a una respuesta verificable."
    >
      <p>
        El modo Anthropic utiliza el ciclo nativo de <code>tool_use</code> y{' '}
        <code>tool_result</code> de Claude Haiku 4.5. Cada conversación tiene límites de turnos,
        tokens, tiempo y llamadas a herramientas.
      </p>
      <ol className="docs-process">
        <li>
          <span>01</span>
          <div>
            <h3>Recuperar el contexto</h3>
            <p>
              La API obtiene el historial de la cuenta desde la base de datos y busca fragmentos
              relevantes en la documentación empresarial.
            </p>
          </div>
        </li>
        <li>
          <span>02</span>
          <div>
            <h3>Elegir y ejecutar herramientas</h3>
            <p>
              El modelo puede consultar conocimiento, calcular o proponer una solicitud. La API
              valida los argumentos, comprueba permisos y registra el resultado real.
            </p>
          </div>
        </li>
        <li>
          <span>03</span>
          <div>
            <h3>Pedir confirmación cuando hay una acción</h3>
            <p>
              Una propuesta de demo o soporte todavía no crea un registro. El usuario revisa los
              datos y confirma con una acción explícita.
            </p>
          </div>
        </li>
        <li>
          <span>04</span>
          <div>
            <h3>Responder con fuentes</h3>
            <p>
              Antes de emitir la respuesta, se sanean y ordenan las referencias. Los fragmentos
              consultados se pueden desplegar; si falta evidencia, el asistente lo indica. Una
              herramienta exitosa no habilita afirmaciones ajenas a su resultado: sin citas válidas,
              sólo se muestran resultados deterministas pertinentes.
            </p>
          </div>
        </li>
      </ol>
      <div className="docs-callout">
        <MessageSquare size={19} />
        <div>
          <h3>Avances reales, sin razonamiento interno</h3>
          <p>
            SSE emite eventos de estado, herramientas y respuesta. El frontend muestra actividad
            comprobable; no expone ni inventa una cadena de pensamiento. Los errores y las
            interrupciones se comunican como tales.
          </p>
        </div>
      </div>
    </DocsSection>
  );
}
