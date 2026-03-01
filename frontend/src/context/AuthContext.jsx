import { useState, useEffect } from "react";
import api from "../lib/api";
import AuthContext from "./authContextValue";

export { AuthContext };

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem("evua_token"));
  const [loading, setLoading] = useState(!!localStorage.getItem("evua_token"));

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    api
      .get("/auth/me")
      .then((res) => {
        if (!cancelled) {
          setUser(res.data);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          localStorage.removeItem("evua_token");
          localStorage.removeItem("evua_user");
          setToken(null);
          setUser(null);
          setLoading(false);
        }
      });
    return () => { cancelled = true; };
  }, [token]);

  const login = async (email, password) => {
    const res = await api.post("/auth/login", { email, password });
    const { access_token, user: userData } = res.data;
    localStorage.setItem("evua_token", access_token);
    localStorage.setItem("evua_user", JSON.stringify(userData));
    setToken(access_token);
    setUser(userData);
    return userData;
  };

  const register = async (name, email, password) => {
    const res = await api.post("/auth/register", { name, email, password });
    const { access_token, user: userData } = res.data;
    localStorage.setItem("evua_token", access_token);
    localStorage.setItem("evua_user", JSON.stringify(userData));
    setToken(access_token);
    setUser(userData);
    return userData;
  };

  const logout = () => {
    localStorage.removeItem("evua_token");
    localStorage.removeItem("evua_user");
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
