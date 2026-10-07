import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import {
  CONTENT_SECURITY_POLICY,
  createDeploymentConfig,
  validateApiOrigin,
} from '../deployment/config';

const environment = {
  API_ORIGIN: 'https://api.example.com',
  ORIGIN_SECRET: 'test-only-origin-credential-at-least-32-characters',
};

describe('deployment origin boundaries', () => {
  it('accepts an explicit HTTPS hostname and normalizes its root slash', () => {
    expect(validateApiOrigin(environment.API_ORIGIN)).toBe(environment.API_ORIGIN);
    expect(validateApiOrigin(`${environment.API_ORIGIN}/`)).toBe(environment.API_ORIGIN);
  });

  it.each([
    undefined,
    '',
    'http://api.example.com',
    'https://api.example.com/api',
    'https://api.example.com//',
    'https://api.example.com/?mode=demo',
    'https://api.example.com/#fragment',
    'https://user:password@api.example.com',
    'https://localhost',
    'https://api.localhost',
    'https://api.local',
    'https://api.internal',
    'https://api.test',
    'https://127.0.0.1',
    'https://10.0.0.1',
    'https://[::1]',
    'https://2130706433',
    'https://API.example.com',
    'https://api.example.com.',
    ' https://api.example.com',
  ])('rejects an unsafe or noncanonical API origin: %s', (origin) => {
    expect(() => validateApiOrigin(origin)).toThrow('API_ORIGIN');
  });

  it.each([undefined, '', 'short', 'x'.repeat(32) + '\r\n', ' '.repeat(40)])(
    'requires a header-safe protected origin credential',
    (secret) => {
      expect(() => createDeploymentConfig({ ...environment, ORIGIN_SECRET: secret })).toThrow(
        'ORIGIN_SECRET',
      );
    },
  );

  it('refuses a browser-exposed origin credential', () => {
    expect(() =>
      createDeploymentConfig({ ...environment, VITE_ORIGIN_SECRET: environment.ORIGIN_SECRET }),
    ).toThrow('VITE_');
  });
});

describe('Vercel reverse proxy configuration', () => {
  it('serializes only a runtime reference to the origin credential', () => {
    const config = createDeploymentConfig(environment);
    const serialized = JSON.stringify(config);
    expect(serialized).not.toContain(environment.ORIGIN_SECRET);
    expect(serialized).toContain('"args":"$ORIGIN_SECRET"');
    expect(serialized).toContain('"env":["ORIGIN_SECRET"]');
    expect(serialized).toContain('"op":"set","target":{"key":"x-origin-secret"}');
    expect(serialized).not.toMatch(/"(?:authorization|cookie)"/i);
  });

  it.each(['/api', '/api/', '/api/health', '/api/docs', '/api/auth/refresh', '/api/chat/stream'])(
    'routes %s to the backend before the static filesystem and SPA fallback',
    (path) => {
      const config = createDeploymentConfig(environment);
      const routeIndex = config.routes.findIndex(
        (route) =>
          'src' in route && route.src && 'dest' in route && new RegExp(route.src).test(path),
      );
      const filesystemIndex = config.routes.findIndex((route) => 'handle' in route);
      expect(routeIndex).toBeGreaterThanOrEqual(0);
      expect(routeIndex).toBeLessThan(filesystemIndex);
      const route = config.routes[routeIndex];
      if (!route || !('dest' in route)) throw new Error('Missing API rewrite');
      expect(route.dest).toBe('https://api.example.com/api/$1');
      expect(route.respectOriginCacheControl).toBe(false);
      expect(route.transforms).toEqual(
        expect.arrayContaining([
          expect.objectContaining({
            type: 'response.headers',
            target: { key: 'Cache-Control' },
            args: 'private, no-store',
          }),
        ]),
      );
    },
  );

  it('preserves static files and direct docs reloads without ever rewriting API failures to HTML', () => {
    const config = createDeploymentConfig(environment);
    const fallback = config.routes.at(-1);
    if (!fallback || !('src' in fallback) || !fallback.src) throw new Error('Missing SPA fallback');
    const pattern = new RegExp(fallback.src);
    expect(pattern.test('/')).toBe(true);
    expect(pattern.test('/docs')).toBe(true);
    expect(pattern.test('/docs/')).toBe(true);
    expect(pattern.test('/api/unknown')).toBe(false);
    expect(pattern.test('/api')).toBe(false);
    expect('dest' in fallback && fallback.dest).toBe('/index.html');
    expect(config.routes.at(-2)).toEqual({ handle: 'filesystem' });
  });

  /** Headers that Vercel applies to a path, in route order. */
  function headersFor(path: string): Record<string, string>[] {
    return createDeploymentConfig(environment).routes.flatMap((route) =>
      'headers' in route && route.src && new RegExp(route.src).test(path) ? [route.headers] : [],
    );
  }

  it.each(['/', '/docs', '/docs/', '/conversation/deep-link', '/assets/index.js', '/favicon.svg'])(
    'applies the CSP and security headers to every SPA-served path: %s',
    (path) => {
      const merged = Object.assign({}, ...headersFor(path)) as Record<string, string>;
      expect(merged['Content-Security-Policy']).toBe(CONTENT_SECURITY_POLICY);
      expect(merged['X-Content-Type-Options']).toBe('nosniff');
      expect(merged['X-Frame-Options']).toBe('DENY');
    },
  );

  it.each(['/api', '/api/', '/api/docs', '/api/health'])(
    'leaves the API responses (including Swagger) outside the SPA CSP: %s',
    (path) => {
      expect(headersFor(path).filter((headers) => 'Content-Security-Policy' in headers)).toEqual(
        [],
      );
      expect(headersFor(path).some((headers) => headers['X-Frame-Options'] === 'DENY')).toBe(true);
    },
  );

  it('allows exactly the Google Fonts origins and no remote images', () => {
    const directives = Object.fromEntries(
      CONTENT_SECURITY_POLICY.split('; ').map((directive) => {
        const [name = '', ...values] = directive.split(' ');
        return [name, values];
      }),
    );
    expect(directives['style-src']).toEqual([
      "'self'",
      "'unsafe-inline'",
      'https://fonts.googleapis.com',
    ]);
    expect(directives['font-src']).toEqual(["'self'", 'https://fonts.gstatic.com']);
    expect(directives['img-src']).toEqual(["'self'", 'data:']);
    expect(directives['script-src']).toEqual(["'self'"]);
    expect(directives['connect-src']).toEqual(["'self'"]);
  });

  it('mirrors the same CSP and security headers in the Docker nginx configuration', () => {
    const nginx = readFileSync(new URL('../nginx.conf', import.meta.url), 'utf8');
    const spaLocation = nginx.slice(nginx.indexOf('location / {'));
    expect(spaLocation).toContain(
      `add_header Content-Security-Policy "${CONTENT_SECURITY_POLICY}" always;`,
    );
    for (const header of [
      'X-Content-Type-Options "nosniff"',
      'X-Frame-Options "DENY"',
      'Referrer-Policy "strict-origin-when-cross-origin"',
      'Permissions-Policy "camera=(), microphone=(), geolocation=()"',
      'Strict-Transport-Security "max-age=31536000"',
    ])
      expect(spaLocation).toContain(`add_header ${header} always;`);
    const apiLocation = nginx.slice(
      nginx.indexOf('location /api/ {'),
      nginx.indexOf('location / {'),
    );
    expect(apiLocation).not.toContain('Content-Security-Policy');
  });
});
