import { describe, expect, it } from 'vitest';
import { createDeploymentConfig, validateApiOrigin } from '../deployment/config';

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
});
