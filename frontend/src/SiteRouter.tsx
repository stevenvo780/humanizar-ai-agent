import { lazy, Suspense, useEffect, useState } from 'react';
import { LoaderCircle } from 'lucide-react';
import SessionApp from './SessionApp';
import { isDocumentationPath } from './navigation';

const Documentation = lazy(() => import('./DocsPage'));

export default function SiteRouter() {
  const [path, setPath] = useState(window.location.pathname);
  useEffect(() => {
    const changed = () => setPath(window.location.pathname);
    window.addEventListener('popstate', changed);
    return () => window.removeEventListener('popstate', changed);
  }, []);
  if (!isDocumentationPath(path)) return <SessionApp />;
  return (
    <Suspense
      fallback={
        <main className="session-loading">
          <LoaderCircle className="spin" size={25} />
          <strong>Documentación técnica</strong>
          <span>Preparando la lectura…</span>
        </main>
      }
    >
      <Documentation />
    </Suspense>
  );
}
