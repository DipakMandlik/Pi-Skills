import { afterEach, describe, expect, it, vi } from 'vitest';

import { authService } from './authService';

describe('apps/web authService token contract parsing', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('maps canonical access_token response field', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          access_token: 'canonical-access',
          user_id: 'u-1',
          email: 'admin@example.com',
          display_name: 'Admin',
          role: 'ORG_ADMIN',
        }),
      } as Response),
    );

    const result = await authService.login({
      email: 'admin@example.com',
      password: 'secret',
    });

    expect(result.token).toBe('canonical-access');
    expect(result.user.id).toBe('u-1');
    expect(result.user.role).toBe('ORG_ADMIN');
  });

  it('maps legacy token response field', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          token: 'legacy-access',
          user_id: 'u-2',
          email: 'viewer@example.com',
          display_name: 'Viewer',
          role: 'VIEWER',
        }),
      } as Response),
    );

    const result = await authService.login({
      username: 'viewer@example.com',
      password: 'secret',
    });

    expect(result.token).toBe('legacy-access');
    expect(result.user.id).toBe('u-2');
    expect(result.user.role).toBe('VIEWER');
  });

  it('maps refresh token fields when present', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          access_token: 'canonical-access',
          refresh_token: 'refresh-123',
          user_id: 'u-3',
          email: 'engineer@example.com',
          display_name: 'Engineer',
          role: 'DATA_ENGINEER',
        }),
      } as Response),
    );

    const result = await authService.login({
      email: 'engineer@example.com',
      password: 'secret',
    });

    expect(result.token).toBe('canonical-access');
    expect(result.refreshToken).toBe('refresh-123');
    expect(result.user.role).toBe('DATA_ENGINEER');
  });
});
