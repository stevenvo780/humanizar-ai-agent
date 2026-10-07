import type { CompanyIdentity, Config } from './types';

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
  const humanizar = company.trim().toLowerCase() === 'humanizar';
  const currentIdentity = identity?.company_name === company ? identity : null;
  const website =
    safeCompanyWebsite(currentIdentity?.website) ??
    (humanizar && currentIdentity?.website === undefined ? 'https://humanizar.tech/' : null);
  const defaults: QuickPrompt[] = humanizar
    ? [
        {
          title: 'Productos y servicios',
          subtitle: 'Productos y servicios para ti.',
          question: `¿Qué productos y servicios ofrece ${company}?`,
        },
        {
          title: 'Agentes de IA a medida',
          subtitle: 'Explora cómo pueden ayudarte.',
          question: `¿Cómo funcionan los agentes de IA a medida de ${company}?`,
        },
        {
          title: 'Hablemos de tu proyecto',
          subtitle: 'Contacto y solicitud de demostración.',
          question: `¿Cómo puedo contactar a ${company} para solicitar una demostración?`,
        },
        {
          title: 'Conoce Cauce V3',
          subtitle: 'Pregunta por la plataforma.',
          question: '¿Qué es Cauce V3?',
        },
      ]
    : [
        {
          title: 'Productos y servicios',
          subtitle: 'Conoce lo que ofrece la empresa.',
          question: `¿Qué productos y servicios ofrece ${company}?`,
        },
        {
          title: 'Encuentra una solución',
          subtitle: 'Consulta la documentación disponible.',
          question: `¿Cómo puede ayudarme ${company}?`,
        },
        {
          title: 'Contacto',
          subtitle: 'Encuentra los canales documentados.',
          question: `¿Cómo puedo contactar a ${company}?`,
        },
        {
          title: 'Ayuda y soporte',
          subtitle: 'Resuelve tus dudas con fuentes.',
          question: `¿Qué opciones de soporte ofrece ${company}?`,
        },
      ];
  const questions = currentIdentity?.suggested_questions;
  const prompts = questions?.length
    ? questions.map(
        (question): QuickPrompt =>
          defaults.find((prompt) => prompt.question === question) ?? {
            title: question.length > 100 ? `${question.slice(0, 97)}…` : question,
            subtitle: 'Consulta la información documentada.',
            question,
          },
      )
    : defaults;
  return { company, assistant, humanizar, website, prompts };
}
