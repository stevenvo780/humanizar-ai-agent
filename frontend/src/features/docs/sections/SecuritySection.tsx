import { CheckCheck, Fingerprint, LockKeyhole, ShieldCheck } from 'lucide-react';
import { DocsSection } from '../DocsSection';

export function SecuritySection() {
  return (
    <DocsSection
      id="seguridad"
      label="ACCESO Y SEGURIDAD"
      title="La sesión tiene dueño. La acción tiene permiso."
    >
      <div className="docs-security-list">
        <article>
          <LockKeyhole size={20} />
          <div>
            <h3>JWT en memoria, contraseñas con Argon2</h3>
            <p>
              El token de acceso permanece solo en memoria del navegador. Las contraseñas se
              almacenan como hashes Argon2; no hay credenciales predeterminadas. En producción, el
              primer administrador se provisiona por CLI privado antes de publicar; el bootstrap
              HTTP exige un token privado del operador.
            </p>
          </div>
        </article>
        <article>
          <Fingerprint size={20} />
          <div>
            <h3>Refresh rotativo y revocación de familia</h3>
            <p>
              La configuración HTTPS utiliza una cookie Secure y HttpOnly. El refresh rota sus
              credenciales y el logout revoca la familia completa. Refresh y logout requieren un
              encabezado de verificación; el cliente reintenta una sola vez al recibir un 401. Estos
              atributos se comprobaron desde el navegador en el despliegue público.
            </p>
          </div>
        </article>
        <article>
          <ShieldCheck size={20} />
          <div>
            <h3>Roles y propiedad comprobados en el backend</h3>
            <p>
              Los clientes acceden a su chat y solicitudes. Administradores gestionan documentación,
              herramientas y bandeja de clientes. La API exige permisos y propiedad de cada
              conversación; ocultar un botón no sustituye esas comprobaciones. La gestión de cuentas
              de clientes se activa cuando la API declara esa capacidad; permite crear clientes sin
              cambiar la sesión del administrador.
            </p>
          </div>
        </article>
        <article>
          <CheckCheck size={20} />
          <div>
            <h3>Confirmación explícita e idempotencia</h3>
            <p>
              Las acciones de demo y soporte requieren un clic de confirmación. Una clave por
              usuario y propuesta evita crear dos solicitudes al repetir la misma confirmación.
            </p>
          </div>
        </article>
      </div>
      <div className="docs-callout docs-callout-lavender">
        <ShieldCheck size={20} />
        <div>
          <h3>La clave del proveedor permanece en el backend</h3>
          <p>
            La clave de Anthropic se configura exclusivamente en el entorno del backend. No se
            introduce en la web, no se guarda desde la API y nunca se devuelve al navegador. Cada
            instalación necesita su propia configuración privada.
          </p>
        </div>
      </div>
    </DocsSection>
  );
}
