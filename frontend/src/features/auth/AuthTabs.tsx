export type AuthMode = 'login' | 'register';

export function AuthTabs({
  mode,
  busy,
  onSelect,
}: {
  mode: AuthMode;
  busy: boolean;
  /** Switches the access mode and clears any previous error. */
  onSelect: (mode: AuthMode) => void;
}) {
  return (
    <div className="auth-tabs" role="tablist" aria-label="Acceso a la cuenta">
      <button
        id="auth-tab-login"
        role="tab"
        aria-controls="auth-panel"
        aria-selected={mode === 'login'}
        tabIndex={mode === 'login' ? 0 : -1}
        disabled={busy}
        onKeyDown={(event) => {
          if (['ArrowLeft', 'ArrowRight', 'End'].includes(event.key)) {
            event.preventDefault();
            onSelect('register');
            document.getElementById('auth-tab-register')?.focus();
          }
        }}
        onClick={() => {
          onSelect('login');
        }}
        className={mode === 'login' ? 'selected' : ''}
      >
        Entrar
      </button>
      <button
        id="auth-tab-register"
        role="tab"
        aria-controls="auth-panel"
        aria-selected={mode === 'register'}
        tabIndex={mode === 'register' ? 0 : -1}
        disabled={busy}
        onKeyDown={(event) => {
          if (['ArrowLeft', 'ArrowRight', 'Home'].includes(event.key)) {
            event.preventDefault();
            onSelect('login');
            document.getElementById('auth-tab-login')?.focus();
          }
        }}
        onClick={() => {
          onSelect('register');
        }}
        className={mode === 'register' ? 'selected' : ''}
      >
        Crear cuenta
      </button>
    </div>
  );
}
