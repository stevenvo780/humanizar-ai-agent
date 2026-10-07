import type { RefObject } from 'react';
import { ArrowRight, X } from 'lucide-react';
import { BrandMark } from '../../shared/ui/BrandMark';

export function HelpModal({
  dialogRef,
  onClose,
  company,
  assistant,
  isAdmin,
  demoMode,
}: {
  dialogRef: RefObject<HTMLElement | null>;
  onClose: () => void;
  company: string;
  assistant: string;
  isAdmin: boolean;
  demoMode: boolean;
}) {
  return (
    <div className="modal-backdrop">
      <section
        className="help-modal"
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="help-title"
      >
        <button className="icon-button modal-close" aria-label="Cerrar ayuda" onClick={onClose}>
          <X size={20} />
        </button>
        <BrandMark />
        <h2 id="help-title">
          Conoce {company}.
          <br />
          Resuelve tus dudas con {assistant}.
        </h2>
        <p>
          Pregunta cómo usar {company}, resolver un problema o pedir ayuda. El asistente consulta la
          documentación de la empresa y puede usar herramientas para ayudarte. Abre las fuentes para
          revisar la información de cada respuesta.
        </p>
        <p>
          En <strong>Mis solicitudes</strong> puedes revisar las demostraciones y los tickets de
          soporte que confirmaste.{' '}
          {isAdmin &&
            'Desde tu cuenta de administrador también puedes gestionar la documentación y las herramientas.'}
        </p>
        <p className="help-detail">
          {demoMode
            ? 'Este asistente está en modo demo: las respuestas son de demostración y no llaman a Claude. Los documentos y las herramientas usan la API real.'
            : 'La información del modelo y el estado de las conexiones aparecen en la barra lateral.'}{' '}
          El historial se guarda en tu cuenta.
        </p>
        <button className="primary-button" onClick={onClose}>
          Empezar a explorar
          <ArrowRight size={16} />
        </button>
      </section>
    </div>
  );
}
