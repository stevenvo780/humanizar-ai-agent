import { WifiOff } from 'lucide-react';

export function WorkspaceNotices({
  online,
  loading,
  connectionError,
  storageError,
  onRetry,
}: {
  online: boolean;
  loading: boolean;
  connectionError: string;
  storageError: string;
  onRetry: () => Promise<void>;
}) {
  return (
    <>
      {((!online && !loading) || connectionError) && (
        <div className="offline-banner" role="status">
          <WifiOff size={16} />
          <span>
            {!online
              ? 'No podemos conectar con el servidor. Tu historial sigue aquí.'
              : connectionError}
          </span>
          <button onClick={() => void onRetry()} disabled={loading}>
            {loading ? 'Conectando…' : 'Reintentar'}
          </button>
        </div>
      )}
      {storageError && (
        <div className="notice error" role="status">
          {storageError}
        </div>
      )}
    </>
  );
}
