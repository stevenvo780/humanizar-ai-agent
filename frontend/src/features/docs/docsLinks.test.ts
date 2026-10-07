import { existsSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import {
  API_DOCS_PATH,
  EXTERNAL_LINK,
  OPENAPI_PATH,
  PUBLIC_APP_URL,
  REPOSITORY_FILES,
  REPOSITORY_URL,
  repositoryFile,
  resourceGroups,
} from './docsLinks';

const REPOSITORY_ROOT = fileURLToPath(new URL('../../../../', import.meta.url));
const PUBLIC_HOSTS = new Set(['github.com', new URL(PUBLIC_APP_URL).hostname]);
const links = resourceGroups.flatMap((group) => group.links);

describe('documentation links', () => {
  it('links only files that exist in the repository', () => {
    for (const path of REPOSITORY_FILES) {
      const absolute = join(REPOSITORY_ROOT, path);
      expect(existsSync(absolute), path).toBe(true);
      expect(statSync(absolute).isFile(), path).toBe(true);
    }
  });

  it('builds file links on the public dev branch', () => {
    expect(REPOSITORY_URL).toBe('https://github.com/stevenvo780/humanizar-ai-agent');
    expect(repositoryFile('docs/VALIDATION.md')).toBe(
      'https://github.com/stevenvo780/humanizar-ai-agent/blob/dev/docs/VALIDATION.md',
    );
    for (const link of links) {
      if (link.path !== undefined) expect(link.href).toBe(repositoryFile(link.path));
    }
  });

  it('includes every requested resource exactly once', () => {
    const hrefs = links.map((link) => link.href);
    expect(new Set(hrefs).size).toBe(hrefs.length);
    expect(hrefs).toEqual(
      expect.arrayContaining([
        PUBLIC_APP_URL,
        API_DOCS_PATH,
        OPENAPI_PATH,
        `${REPOSITORY_URL}/tree/dev`,
        `${REPOSITORY_URL}/commits/dev`,
        `${REPOSITORY_URL}/issues`,
      ]),
    );
    const linkedFiles = new Set(links.flatMap((link) => (link.path ? [link.path] : [])));
    const pageOnlyFiles = REPOSITORY_FILES.filter((path) => !linkedFiles.has(path));
    expect(pageOnlyFiles).toEqual(['docs/FEDORA.md']);
  });

  it('points only to public HTTPS hosts or the same-origin API', () => {
    for (const link of links) {
      expect(link.label.trim(), link.href).not.toBe('');
      expect(link.detail.trim(), link.href).not.toBe('');
      if (link.href.startsWith('/')) {
        expect(link.href.startsWith('/api/'), link.href).toBe(true);
        continue;
      }
      const url = new URL(link.href);
      expect(url.protocol, link.href).toBe('https:');
      expect(PUBLIC_HOSTS.has(url.hostname), link.href).toBe(true);
      expect(url.username + url.password, link.href).toBe('');
    }
  });

  it('opens external links in an isolated new tab', () => {
    expect(EXTERNAL_LINK).toEqual({ target: '_blank', rel: 'noopener noreferrer' });
  });
});
