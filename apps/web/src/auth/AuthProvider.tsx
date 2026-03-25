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

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const restoreSession = async () => {
      const storedToken = localStorage.getItem('auth_token');
      if (!storedToken) {
        setIsLoading(false);
        return;
      }

      try {
        const restoredUser = await authService.me();
        setUser(restoredUser);
        setToken(storedToken);
      } catch {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('refresh_token');
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

  const logout = useCallback(() => {
    authService.logout();
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
      logout,
      clearError,
    }),
    [user, token, isLoading, error, permissions, login, logout, clearError],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
