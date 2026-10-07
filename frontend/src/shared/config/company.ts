import type { CompanyIdentity, Config } from '../api/types';

export interface QuickPrompt {
  title: string;
  subtitle: string;
  question: string;
}

export function safeCompanyWebsite(value: unknown): string | null {
  if (typeof value !== 'string') return null;
  try {
    const url = new URL(value);
    return (url.protocol === 'https:' || url.protocol === 'http:') &&
      !url.username &&
      !url.password &&
      url.hostname
      ? url.href
      : null;
  } catch {
    return null;
  }
}

export function companyPresentation(config: Config | null, identity: CompanyIdentity | null) {
  const company = config?.company_name ?? identity?.company_name ?? 'la empresa';
  const assistant = config?.assistant_name ?? identity?.assistant_name ?? 'Asistente';
  const currentIdentity = identity?.company_name === company ? identity : null;
  const website = safeCompanyWebsite(currentIdentity?.website);
  // Neutral defaults: the backend publishes the company's own suggested questions.
  const defaults: QuickPrompt[] = [
    {
      title: 'Qué ofrece',
      subtitle: 'Conoce las funciones documentadas.',
      question: `¿Qué funciones ofrece ${company}?`,
    },
    {
      title: 'Primeros pasos',
      subtitle: 'Aprende a realizar una tarea paso a paso.',
      question: `¿Cómo empiezo a usar ${company}?`,
    },
    {
      title: 'Resolver un problema',
      subtitle: 'Encuentra la solución documentada.',
      question: `¿Qué hago si algo no funciona como espero en ${company}?`,
    },
    {
      title: 'Ayuda y soporte',
      subtitle: 'Resuelve tus dudas con fuentes.',
      question: `¿Qué opciones de soporte ofrece ${company}?`,
    },
  ];
  // Only an absent list falls back to defaults; an explicit empty list hides the suggestions.
  const questions = currentIdentity?.suggested_questions;
  const prompts = questions
    ? questions.map(
        (question): QuickPrompt =>
          defaults.find((prompt) => prompt.question === question) ?? {
            title: question.length > 100 ? `${question.slice(0, 97)}…` : question,
            subtitle: 'Consulta la información documentada.',
            question,
          },
      )
    : defaults;
  return { company, assistant, website, prompts };
}
