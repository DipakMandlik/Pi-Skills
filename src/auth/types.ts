export type Role =
  | 'ORG_ADMIN'
  | 'SECURITY_ADMIN'
  | 'DATA_ENGINEER'
  | 'ANALYTICS_ENGINEER'
  | 'DATA_SCIENTIST'
  | 'BUSINESS_USER'
  | 'VIEWER'
  | 'SYSTEM_AGENT';

export interface User {
  id: string;
  email: string;
  name: string;
  role: Role;
  avatar?: string;
  createdAt: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface LoginCredentials {
  account: string;
  username: string;
  password: string;
  role: string;
}

export interface AuthResponse {
  token: string;
  refreshToken?: string;
  user: User;
}

export type Permission =
  | 'viewDashboard'
  | 'viewAllSkills'
  | 'createSkill'
  | 'assignSkill'
  | 'revokeSkill'
  | 'viewAllModels'
  | 'manageModels'
  | 'viewAllMonitoring'
  | 'viewOwnMonitoring'
  | 'manageUsers'
  | 'viewWorkspace';

export type PermissionMap = Record<Permission, boolean>;
