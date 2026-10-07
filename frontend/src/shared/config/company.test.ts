import { describe, expect, it } from 'vitest';
import { companyPresentation, safeCompanyWebsite } from './company';
import { isCompanyIdentity } from '../api/validation';
import type { Config } from '../api/types';

const config: Config = {
  company_name: 'Empresa Ejemplo',
  assistant_name: 'Asistente Ejemplo',
  company_description: 'Descripción sintética.',
  mode: 'demo',
  model: 'demo',
  embedding: 'hash',
  max_upload_mb: 20,
};

describe('configured company presentation', () => {
  it('uses neutral defaults that name only the configured company', () => {
    const softop = companyPresentation(
      { ...config, company_name: 'Softop', assistant_name: 'Asistente Softop' },
      null,
    );
    expect(softop.website).toBeNull();
    expect(softop.prompts.length).toBeGreaterThan(0);
    expect(softop.prompts.some((prompt) => prompt.question.includes('Softop'))).toBe(true);
    const other = companyPresentation(config, null);
    expect(JSON.stringify(other)).not.toContain('Softop');
    expect(Object.keys(other).sort()).toEqual(['assistant', 'company', 'prompts', 'website']);
  });

  it('uses published questions and website without leaking a stale company identity', () => {
    const identity = {
      company_name: config.company_name,
      company_description: config.company_description,
      assistant_name: config.assistant_name,
      website: 'https://example.invalid/contact',
      suggested_questions: ['¿Cómo consultar mi pedido?'],
    };
    const current = companyPresentation(config, identity);
    expect(current.website).toBe(identity.website);
    expect(current.prompts.map((prompt) => prompt.question)).toEqual(identity.suggested_questions);
    const changed = companyPresentation({ ...config, company_name: 'Nueva Empresa' }, identity);
    expect(changed.website).toBeNull();
    expect(changed.prompts.some((prompt) => prompt.question.includes('pedido'))).toBe(false);
  });

  it('hides suggestions for an explicit empty list and keeps defaults only when absent', () => {
    const identity = {
      company_name: config.company_name,
      company_description: config.company_description,
      assistant_name: config.assistant_name,
    };
    expect(companyPresentation(config, { ...identity, suggested_questions: [] }).prompts).toEqual(
      [],
    );
    const absent = companyPresentation(config, identity).prompts;
    expect(absent.length).toBeGreaterThan(0);
    expect(companyPresentation(config, null).prompts).toEqual(absent);
  });

  it.each([
    'javascript:alert(1)',
    'data:text/html,hello',
    '/relative',
    'https://user:password@example.invalid',
    'mailto:info@example.invalid',
  ])('rejects unsafe company links: %s', (website) => {
    expect(safeCompanyWebsite(website)).toBeNull();
    expect(isCompanyIdentity({ ...config, website })).toBe(false);
  });

  it('validates optional identity fields while preserving an old API response', () => {
    expect(isCompanyIdentity(config)).toBe(true);
    expect(
      isCompanyIdentity({
        ...config,
        website: 'https://example.invalid',
        suggested_questions: ['Pregunta'],
      }),
    ).toBe(true);
    expect(isCompanyIdentity({ ...config, suggested_questions: [''] })).toBe(false);
    expect(isCompanyIdentity({ ...config, suggested_questions: [4] })).toBe(false);
    expect(
      isCompanyIdentity({ ...config, suggested_questions: Array<string>(13).fill('Pregunta') }),
    ).toBe(false);
  });
});
