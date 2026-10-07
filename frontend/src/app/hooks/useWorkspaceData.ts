import { useCallback, useEffect, useState } from 'react';
import { api } from '../../shared/api/api';
import type {
  CompanyIdentity,
  Config,
  DocumentList,
  Health,
  ToolDefinition,
} from '../../shared/api/types';
import { companyPresentation } from '../../shared/config/company';

/** Configuration, company identity, health polling and admin data for the workspace. */
export function useWorkspaceData(isAdmin: boolean) {
  const [config, setConfig] = useState<Config | null>(null);
  const [identity, setIdentity] = useState<CompanyIdentity | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [documents, setDocuments] = useState<DocumentList>({ documents: [], total_chunks: 0 });
  const [tools, setTools] = useState<ToolDefinition[]>([]);
  const [online, setOnline] = useState(false);
  const [loading, setLoading] = useState(true);
  const [connectionError, setConnectionError] = useState('');
  const presentation = companyPresentation(config, identity);
  const { company, assistant } = presentation;

  const refreshDocuments = useCallback(async () => {
    setDocuments(await api.documents());
  }, []);
  const refresh = useCallback(async () => {
    setLoading(true);
    const results = await Promise.allSettled([
      api.config(),
      api.health(),
      isAdmin ? api.documents() : Promise.resolve({ documents: [], total_chunks: 0 }),
      isAdmin ? api.tools() : Promise.resolve({ tools: [] }),
      api.company(),
    ]);
    const [configuration, healthResult, documentResult, toolResult, companyResult] = results;
    if (configuration.status === 'fulfilled') setConfig(configuration.value);
    if (companyResult.status === 'fulfilled') setIdentity(companyResult.value);
    if (healthResult.status === 'fulfilled') {
      setHealth(healthResult.value);
      setOnline(true);
      setConnectionError('');
    } else {
      setOnline(false);
      setConnectionError('El servidor no está disponible.');
    }
    if (documentResult.status === 'fulfilled') setDocuments(documentResult.value);
    if (toolResult.status === 'fulfilled') setTools(toolResult.value.tools);
    if (
      configuration.status === 'rejected' ||
      documentResult.status === 'rejected' ||
      toolResult.status === 'rejected'
    )
      setConnectionError('No se pudo cargar toda la información. Vuelve a intentar.');
    setLoading(false);
  }, [isAdmin]);
  const markOffline = useCallback(() => setOnline(false), []);

  useEffect(() => {
    void refresh();
  }, [refresh]);
  useEffect(() => {
    document.title = `${assistant} — ${company}`;
  }, [assistant, company]);
  useEffect(() => {
    const check = async () => {
      try {
        const result = await api.health();
        setHealth(result);
        setOnline(true);
      } catch {
        setOnline(false);
      }
    };
    const reconnect = () => {
      void refresh();
    };
    const disconnect = () => setOnline(false);
    window.addEventListener('online', reconnect);
    window.addEventListener('offline', disconnect);
    const interval = window.setInterval(() => {
      void check();
    }, 20000);
    return () => {
      window.removeEventListener('online', reconnect);
      window.removeEventListener('offline', disconnect);
      window.clearInterval(interval);
    };
  }, [refresh]);

  return {
    config,
    health,
    documents,
    tools,
    online,
    loading,
    connectionError,
    presentation,
    refresh,
    refreshDocuments,
    markOffline,
  };
}
