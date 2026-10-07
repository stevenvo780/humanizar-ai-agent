import type { VercelConfig } from '@vercel/config/v1';
import { createDeploymentConfig } from './deployment/config';

// Evaluated by Vercel's configuration compiler, independently of the Vite build.
export const config: VercelConfig = createDeploymentConfig(process.env);
