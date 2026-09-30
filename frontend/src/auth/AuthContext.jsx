import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { AUTH_EXPIRED_EVENT, fetchCurrentUser, loginRequest, logoutRequest, registerRequest } from '../api';
import { clearToken, getToken, setToken } from './tokenStorage';

// Mirrors backend app/auth/permissions.py. The UI only uses these to hide controls;
// the API enforces every permission independently.
export const PERMISSIONS = {
  VIEW_CASES: 'cases:view',
  INVESTIGATE: 'cases:investigate',
  REVIEW_CASES: 'cases:review',
  MANAGE_USERS: 'users:manage',
  MANAGE_ORGANIZATION: 'organization:manage',
  VIEW_ORGANIZATION_AUDIT: 'organization:audit',
};

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  // status: 'loading' (validating a stored token) | 'authenticated' | 'anonymous'
  const [status, setStatus] = useState(() => (getToken() ? 'loading' : 'anonymous'));
  const [user, setUser] = useState(null);

  const signOutLocally = useCallback(() => {
    clearToken();
    setUser(null);
    setStatus('anonymous');
  }, []);

  // Validate a stored token on load: the server, not the client, decides if it's still good.
  useEffect(() => {
    if (!getToken()) return;
    fetchCurrentUser()
      .then((res) => {
        setUser(res.data);
        setStatus('authenticated');
      })
      .catch(signOutLocally);
  }, [signOutLocally]);

  useEffect(() => {
    window.addEventListener(AUTH_EXPIRED_EVENT, signOutLocally);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, signOutLocally);
  }, [signOutLocally]);

  const acceptSession = useCallback((data) => {
    setToken(data.access_token);
    setUser(data.user);
    setStatus('authenticated');
    return data.user;
  }, []);

  const login = useCallback(
    async (email, password) => acceptSession((await loginRequest(email, password)).data),
    [acceptSession]
  );

  const register = useCallback(
    async (payload) => acceptSession((await registerRequest(payload)).data),
    [acceptSession]
  );

  const logout = useCallback(async () => {
    try {
      await logoutRequest(); // records the sign-out in the audit trail
    } catch {
      /* token may already be invalid; signing out locally is what matters */
    }
    signOutLocally();
  }, [signOutLocally]);

  const refreshUser = useCallback(async () => {
    const res = await fetchCurrentUser();
    setUser(res.data);
    return res.data;
  }, []);

  const can = useCallback((permission) => Boolean(user?.permissions?.includes(permission)), [user]);

  const value = useMemo(
    () => ({ status, user, organization: user?.organization ?? null, login, register, logout, refreshUser, can }),
    [status, user, login, register, logout, refreshUser, can]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
