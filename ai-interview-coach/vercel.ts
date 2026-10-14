import { createVercelConfig } from './deployment/vercel-config.mjs';

// Vercel evaluates this with the selected deployment environment's variables.
export const config = createVercelConfig(process.env.VITE_API_URL);
