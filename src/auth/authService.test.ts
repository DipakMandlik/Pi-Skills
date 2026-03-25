import { afterEach, describe, expect, it, vi } from 'vitest';

import { authService } from './authService';

function makeLocalStorage() {
  const store = new Map<string, string>();
  return {
    get length() {
      return store.size;
    },
    key: (index: number) => Array.from(store.keys())[index] ?? null,
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => {
      store.set(key, value);
    },
    removeItem: (key: string) => {
      store.delete(key);
    },
    clear: () => {
      store.clear();
    },
  };
}

describe('authService.me fallback behavior', () => {
  const storage = makeLocalStorage();
  vi.stubGlobal('localStorage', storage);

  afterEach(() => {
    vi.restoreAllMocks();
    storage.clear();
  });

  it('uses MCP /users/me when available', async () => {
    localStorage.setItem('auth_token', 'mcp-token');

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          id: 'abc',
          email: 'admin@example.com',
          name: 'Admin User',
          role: 'ORG_ADMIN',
          createdAt: '2026-01-01T00:00:00.000Z',
        }),
      } as Response),
    );

    const me = await authService.me();
    expect(me.id).toBe('abc');
    expect(me.role).toBe('ORG_ADMIN');
  });

  it('falls back to backend /auth/me when MCP rejects token', async () => {
    localStorage.setItem('auth_token', 'backend-token');

    vi.stubGlobal(
      'fetch',
      vi.fn()
        .mockResolvedValueOnce({ ok: false, json: async () => ({}) } as Response)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            user_id: 'u-1',
            email: 'user@platform.local',
            role: 'BUSINESS_USER',
            display_name: 'Test User',
          }),
        } as Response),
    );

    const me = await authService.me();
    expect(me.id).toBe('u-1');
    expect(me.name).toBe('Test User');
    expect(me.role).toBe('BUSINESS_USER');
  });

  it('clears user auth and explorer cache keys on logout', () => {
    localStorage.setItem('auth_token', 'tkn');
    localStorage.setItem('sf_account', 'acct');
    localStorage.setItem('sf_username', 'user');
    localStorage.setItem('sf_role', 'ORG_ADMIN');
    localStorage.setItem('mcp-explorer-cache-v1:acct:user:ORG_ADMIN', 'cached');
    localStorage.setItem('unrelated_key', 'keep');

    authService.logout();

    expect(localStorage.getItem('auth_token')).toBeNull();
    expect(localStorage.getItem('sf_account')).toBeNull();
    expect(localStorage.getItem('sf_username')).toBeNull();
    expect(localStorage.getItem('sf_role')).toBeNull();
    expect(localStorage.getItem('mcp-explorer-cache-v1:acct:user:ORG_ADMIN')).toBeNull();
    expect(localStorage.getItem('unrelated_key')).toBe('keep');
  });
});

describe('authService token contract parsing', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('accepts canonical access_token and refresh_token response fields', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          access_token: 'canonical-access',
          refresh_token: 'canonical-refresh',
          user: {
            id: 'u-1',
            email: 'admin@example.com',
            name: 'Admin',
            role: 'ORG_ADMIN',
            createdAt: '2026-01-01T00:00:00.000Z',
          },
        }),
      } as Response),
    );

    const result = await authService.login({
      account: 'acct',
      username: 'admin',
      password: 'secret',
      role: 'ORG_ADMIN',
    });

    expect(result.token).toBe('canonical-access');
    expect(result.refreshToken).toBe('canonical-refresh');
  });

  it('accepts legacy token and refreshToken response fields', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          token: 'legacy-access',
          refreshToken: 'legacy-refresh',
          user: {
            id: 'u-2',
            email: 'viewer@example.com',
            name: 'Viewer',
            role: 'VIEWER',
            createdAt: '2026-01-01T00:00:00.000Z',
          },
        }),
      } as Response),
    );

    const result = await authService.login({
      account: 'acct',
      username: 'viewer',
      password: 'secret',
      role: 'VIEWER',
    });

    expect(result.token).toBe('legacy-access');
    expect(result.refreshToken).toBe('legacy-refresh');
  });
});
