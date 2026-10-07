import { isIP } from 'node:net';
import { deploymentEnv, routes } from '@vercel/config/v1';
import type { Route, VercelConfig } from '@vercel/config/v1';

type DeploymentEnvironment = Record<string, string | undefined>;
type DeploymentRoute = (Route & { continue?: boolean }) | { handle: 'filesystem' };
type DeploymentConfig = Omit<VercelConfig, 'routes'> & { routes: DeploymentRoute[] };

const PRIVATE_RESPONSE_HEADERS = {
  'Cache-Control': 'private, no-store',
  'CDN-Cache-Control': 'private, no-store',
  'Vercel-CDN-Cache-Control': 'private, no-store',
  'x-vercel-enable-rewrite-caching': '0',
};

/** Every non-API route can serve the SPA, so every one of them carries the same policy. */
export const NON_API_ROUTE = '^/(?!api(?:/|$)).*$';

export const CONTENT_SECURITY_POLICY = [
  "default-src 'self'",
  "script-src 'self'",
  "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
  "img-src 'self' data:",
  "font-src 'self' https://fonts.gstatic.com",
  "connect-src 'self'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
  "object-src 'none'",
].join('; ');

const SECURITY_HEADERS = {
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'Referrer-Policy': 'strict-origin-when-cross-origin',
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
  'Strict-Transport-Security': 'max-age=31536000',
};

/** Only an explicit, canonical public HTTPS hostname can receive application traffic. */
export function validateApiOrigin(value: string | undefined): string {
  const invalid = () =>
    new Error('API_ORIGIN debe ser un origen HTTPS público, sin ruta ni credenciales.');
  if (!value?.trim() || value !== value.trim()) throw invalid();
  let origin: URL;
  try {
    origin = new URL(value);
  } catch {
    throw invalid();
  }
  const hostname = origin.hostname;
  if (
    origin.protocol !== 'https:' ||
    origin.username ||
    origin.password ||
    origin.pathname !== '/' ||
    origin.search ||
    origin.hash ||
    hostname.length > 253 ||
    isIP(hostname) !== 0 ||
    !/^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/.test(hostname) ||
    /\.(?:localhost|local|internal|lan|home|test|invalid|example|onion|arpa)$/.test(hostname) ||
    (value !== origin.origin && value !== `${origin.origin}/`)
  )
    throw invalid();
  return origin.origin;
}

/** Server configuration only: this module is never imported by the browser application. */
export function createDeploymentConfig(environment: DeploymentEnvironment): DeploymentConfig {
  const apiOrigin = validateApiOrigin(environment.API_ORIGIN);
  if (!environment.ORIGIN_SECRET || !/^[\x21-\x7e]{32,512}$/.test(environment.ORIGIN_SECRET))
    throw new Error(
      'ORIGIN_SECRET debe configurarse como variable protegida de al menos 32 caracteres.',
    );
  if (
    environment.VITE_ORIGIN_SECRET !== undefined ||
    environment.VITE_ANTHROPIC_API_KEY !== undefined
  )
    throw new Error('Las credenciales no pueden usar variables públicas VITE_.');

  const apiRewrite = routes.rewrite('/api/:path(.*)?', `${apiOrigin}/api/:path`, {
    // The SDK emits "$ORIGIN_SECRET" plus env metadata, never the environment value.
    requestHeaders: { 'x-origin-secret': deploymentEnv('ORIGIN_SECRET') },
    responseHeaders: PRIVATE_RESPONSE_HEADERS,
    respectOriginCacheControl: false,
  });

  return {
    framework: 'vite',
    installCommand: 'npm ci',
    buildCommand: 'npm run build',
    outputDirectory: 'dist',
    routes: [
      { src: '^/(.*)$', headers: SECURITY_HEADERS, continue: true },
      {
        src: NON_API_ROUTE,
        headers: {
          'Content-Security-Policy': CONTENT_SECURITY_POLICY,
          'Cache-Control': 'no-cache',
        },
        continue: true,
      },
      // Vite emits content-hashed assets: cache them for a year, never the HTML shell.
      {
        src: '^/assets/(.*)$',
        headers: { 'Cache-Control': 'public, max-age=31536000, immutable' },
        continue: true,
      },
      { src: '^/api(?:/.*)?$', headers: PRIVATE_RESPONSE_HEADERS, continue: true },
      apiRewrite,
      { handle: 'filesystem' },
      // An API failure must remain an API response instead of falling through to HTML.
      { src: NON_API_ROUTE, dest: '/index.html' },
    ],
  } satisfies DeploymentConfig;
}
