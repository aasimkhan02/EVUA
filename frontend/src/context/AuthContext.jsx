import React, { createContext, useState, useEffect, useContext, useCallback } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
const TOKEN_KEY = 'evua_token';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user,    setUser]    = useState(null);
  const [token,   setToken]   = useState(() => localStorage.getItem(TOKEN_KEY));
  const [loading, setLoading] = useState(true);

  // ── Hard logout — wipes everything ────────────────────────────────────────
  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    localStorage.removeItem(TOKEN_KEY);
    // Clear migration run data so the next user starts fresh
    localStorage.removeItem('evua:last-run');
    localStorage.removeItem('evua:migration-prefs');
  }, []);

  // ── Verify token on mount by calling /auth/me ──────────────────────────────
  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (!stored) {
      setLoading(false);
      return;
    }

    // Validate the token is still accepted by the server
    fetch(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${stored}` },
    })
      .then(res => {
        if (res.ok) return res.json();
        // Token rejected (expired / invalid / user deleted) — force logout
        throw new Error('invalid');
      })
      .then(userData => {
        setToken(stored);
        setUser(userData);
      })
      .catch(() => {
        // Bad token — clear it silently so user lands on login
        localStorage.removeItem(TOKEN_KEY);
        setToken(null);
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []); // only on mount

  // ── login — called after successful /auth/login ────────────────────────────
  const login = useCallback((newToken, userData) => {
    localStorage.setItem(TOKEN_KEY, newToken);
    setToken(newToken);
    setUser(userData);
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout, isAuthenticated: !!token }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
