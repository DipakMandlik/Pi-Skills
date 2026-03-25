import type { LoginCredentials, AuthResponse, Role, User } from './types';

const MCP_BASE =
  (import.meta as any).env?.VITE_MCP_BASE_URL
  || 'http://localhost:5000';

const BACKEND_BASE =
  (import.meta as any).env?.VITE_BACKEND_BASE_URL
  || (import.meta as any).env?.VITE_API_BASE_URL
  || 'http://localhost:8000';

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

interface MCPLoginResponse {
  access_token?: string;
  refresh_token?: string;
  token: string;
  refreshToken?: string;
  user: User;
}

function readAuthTokens(payload: {
  token?: string;
  access_token?: string;
  refreshToken?: string;
  refresh_token?: string;
}): { token: string; refreshToken?: string } {
  const token = payload.access_token || payload.token;
  if (!token) {
    throw new Error('Authentication response missing access token');
  }
  return {
    token,
    refreshToken: payload.refresh_token || payload.refreshToken,
  };
}

let refreshInFlight: Promise<string | null> | null = null;

export const authService = {
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const res = await fetch(`${MCP_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        account: credentials.account,
        username: credentials.username,
        password: credentials.password,
        role: credentials.role,
      }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body?.detail?.detail || body?.detail || body?.message || 'Snowflake authentication failed');
    }

    const loginData = await res.json() as MCPLoginResponse;
    const tokens = readAuthTokens(loginData);
    const user: User = {
      ...loginData.user,
      role: normalizeRole(loginData.user.role),
    };

    return {
      token: tokens.token,
      refreshToken: tokens.refreshToken,
      user,
    };
  },

  async refreshSession(): Promise<string | null> {
    if (refreshInFlight) {
      return refreshInFlight;
    }

    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) {
      return null;
    }

    refreshInFlight = (async () => {
      try {
        const res = await fetch(`${MCP_BASE}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refreshToken }),
        });

        if (!res.ok) {
          return null;
        }

        const data = await res.json() as MCPLoginResponse;
        const tokens = readAuthTokens(data);
        localStorage.setItem('auth_token', tokens.token);
        if (tokens.refreshToken) {
          localStorage.setItem('refresh_token', tokens.refreshToken);
        }
        if (data.user?.role) {
          localStorage.setItem('sf_role', normalizeRole(data.user.role));
        }
        return tokens.token;
      } catch {
        return null;
      } finally {
        refreshInFlight = null;
      }
    })();

    return refreshInFlight;
  },

  async me(): Promise<User> {
    const token = localStorage.getItem('auth_token');
    if (!token) throw new Error('No token');

    // Primary auth source: MCP session endpoint.
    const mcpRes = await fetch(`${MCP_BASE}/users/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (mcpRes.ok) {
      const data = await mcpRes.json() as User;
      return {
        id: data.id,
        email: data.email,
        name: data.name || data.email,
        role: normalizeRole(data.role),
        createdAt: data.createdAt || new Date().toISOString(),
      };
    }

    // Fallback: backend auth contract for environments/tests that bootstrap
    // a backend JWT directly in localStorage.
    const backendRes = await fetch(`${BACKEND_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (backendRes.ok) {
      const data = await backendRes.json() as {
        user_id: string;
        email: string;
        role: string;
        display_name?: string;
      };
      return {
        id: data.user_id,
        email: data.email,
        name: data.display_name || data.email,
        role: normalizeRole(data.role),
        createdAt: new Date().toISOString(),
      };
    }

    throw new Error('Session expired');
  },

  logout(): void {
    const explorerCachePrefix = 'mcp-explorer-cache-v1:';
    for (let i = localStorage.length - 1; i >= 0; i -= 1) {
      const key = localStorage.key(i);
      if (key && key.startsWith(explorerCachePrefix)) {
        localStorage.removeItem(key);
      }
    }
    localStorage.removeItem('auth_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('sf_account');
    localStorage.removeItem('sf_username');
    localStorage.removeItem('sf_role');
  },
};
