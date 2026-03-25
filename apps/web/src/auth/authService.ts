import type { LoginCredentials, AuthResponse, Role, User } from './types';

const API_BASE = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000';

const ROLE_ALIASES: Record<string, Role> = {
  ADMIN: 'ORG_ADMIN',
  ACCOUNTADMIN: 'ORG_ADMIN',
  SYSADMIN: 'ORG_ADMIN',
  ORG_ADMIN: 'ORG_ADMIN',
  SECURITYADMIN: 'SECURITY_ADMIN',
  SECURITY_ADMIN: 'SECURITY_ADMIN',
  DATA_ENGINEER: 'DATA_ENGINEER',
  ANALYTICS_ENGINEER: 'ANALYTICS_ENGINEER',
  DATA_SCIENTIST: 'DATA_SCIENTIST',
  BUSINESS_USER: 'BUSINESS_USER',
  SYSTEM_AGENT: 'SYSTEM_AGENT',
  VIEWER: 'VIEWER',
  USER: 'BUSINESS_USER',
};

function normalizeRole(role: string): Role {
  return ROLE_ALIASES[(role || '').toUpperCase()] || 'VIEWER';
}

function readAuthToken(payload: { access_token?: string; token?: string }): string {
  const token = payload.access_token || payload.token;
  if (!token) {
    throw new Error('Authentication response missing access token');
  }
  return token;
}

export const authService = {
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const email = credentials.email || credentials.username || '';
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email,
        password: credentials.password,
      }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body?.detail || body?.message || 'Invalid credentials');
    }
    const data = await res.json() as any;
    const token = readAuthToken(data);
    return {
      token,
      refreshToken: data.refresh_token || data.refreshToken || '',
      user: {
        id: data.user_id,
        email: data.email,
        name: data.display_name,
        role: normalizeRole(data.role),
        createdAt: '',
      },
    };
  },

  async me(): Promise<User> {
    const token = localStorage.getItem('auth_token');
    if (!token) throw new Error('No token');
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('Session expired');
    const data = await res.json() as any;
    return {
      id: data.user_id,
      email: data.email,
      name: data.display_name,
      role: normalizeRole(data.role),
      createdAt: '',
    };
  },

  async refresh(): Promise<AuthResponse> {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) {
      throw new Error('Cannot refresh - no refresh token stored');
    }

    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refreshToken }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body?.detail || body?.message || 'Refresh failed');
    }

    const data = await res.json() as any;
    const token = readAuthToken(data);
    const nextRefreshToken = data.refresh_token || data.refreshToken || refreshToken;

    return {
      token,
      refreshToken: nextRefreshToken,
      user: {
        id: data.user_id,
        email: data.email,
        name: data.display_name,
        role: normalizeRole(data.role),
        createdAt: '',
      },
    };
  },

  logout(): void {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('refresh_token');
  },
};
