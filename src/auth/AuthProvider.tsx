import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { AuthContext } from './AuthContext';
import { authService } from './authService';
import { getPermissions } from '../constants/permissions';
import type { User, LoginCredentials, PermissionMap } from './types';

const EMPTY_PERMISSIONS: PermissionMap = {
  viewDashboard: false,
  viewAllSkills: false,
  createSkill: false,
  assignSkill: false,
  revokeSkill: false,
  viewAllModels: false,
  manageModels: false,
  viewAllMonitoring: false,
  viewOwnMonitoring: false,
  manageUsers: false,
  viewWorkspace: false,
};

const DEMO_USER: User = {
  id: 'demo-user-1',
  email: 'admin@example.com',
  name: 'Admin User',
  role: 'ORG_ADMIN',
  createdAt: new Date().toISOString(),
};

const DEMO_PERMISSIONS: PermissionMap = getPermissions('ORG_ADMIN');
const DEMO_MODE_ENABLED =
  (import.meta as any).env?.DEV
  && String((import.meta as any).env?.VITE_ENABLE_DEMO_LOGIN || 'false').toLowerCase() === 'true';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const restoreSession = async () => {
      const storedToken = localStorage.getItem('auth_token');
      const isDemo = localStorage.getItem('demo_mode') === 'true';

      if (isDemo && DEMO_MODE_ENABLED) {
        setUser(DEMO_USER);
        setToken('demo-token');
        setIsLoading(false);
        return;
      }

      if (isDemo && !DEMO_MODE_ENABLED) {
        localStorage.removeItem('demo_mode');
      }

      if (!storedToken) {
        setIsLoading(false);
        return;
      }

      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 3000);
        const restoredUser = await Promise.race([
          authService.me(),
          new Promise<never>((_, reject) => {
            controller.signal.addEventListener('abort', () => reject(new Error('timeout')));
          }),
        ]);
        clearTimeout(timeout);
        setUser(restoredUser);
        setToken(storedToken);
      } catch {
        authService.logout();
      } finally {
        setIsLoading(false);
      }
    };

    restoreSession();
  }, []);

  const login = useCallback(async (credentials: LoginCredentials) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await authService.login(credentials);
      localStorage.setItem('auth_token', response.token);
      if (response.refreshToken) {
        localStorage.setItem('refresh_token', response.refreshToken);
      }
      localStorage.setItem('sf_account', credentials.account);
      localStorage.setItem('sf_username', credentials.username);
      localStorage.setItem('sf_role', response.user.role);
      setUser(response.user);
      setToken(response.token);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Login failed';
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loginDemo = useCallback(() => {
    if (!DEMO_MODE_ENABLED) {
      setError('Demo mode is disabled in this environment');
      setIsLoading(false);
      return;
    }

    localStorage.setItem('demo_mode', 'true');
    setUser(DEMO_USER);
    setToken('demo-token');
    setError(null);
    setIsLoading(false);
  }, []);

  const logout = useCallback(() => {
    authService.logout();
    localStorage.removeItem('demo_mode');
    setUser(null);
    setToken(null);
    setError(null);
  }, []);

  const clearError = useCallback(() => setError(null), []);

  const permissions = useMemo<PermissionMap>(
    () => (user ? getPermissions(user.role) : EMPTY_PERMISSIONS),
    [user],
  );

  const value = useMemo(
    () => ({
      user,
      token,
      isAuthenticated: !!user && !!token,
      isLoading,
      error,
      role: user?.role ?? null,
      permissions,
      login,
      loginDemo,
      logout,
      clearError,
    }),
    [user, token, isLoading, error, permissions, login, loginDemo, logout, clearError],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
