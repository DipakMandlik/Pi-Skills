export const ROUTES = {
  LOGIN: '/login',
  DASHBOARD: '/dashboard',
  WORKSPACE: '/workspace',
  SKILLS: '/skills',
  MODELS: '/models',
  MONITORING: '/monitoring',
  UNAUTHORIZED: '/unauthorized',
} as const;

export type RoutePath = (typeof ROUTES)[keyof typeof ROUTES];
