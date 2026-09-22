"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { User } from "@/lib/types";

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<User>;
  signUp: (payload: { email: string; password: string; password_confirmation: string; full_name: string; timezone: string }) => Promise<User>;
  updateProfile: (payload: { full_name?: string; timezone?: string }) => Promise<User>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.me().then(setUser).catch(() => setUser(null)).finally(() => setLoading(false));
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      signIn: async (email, password) => {
        const response = await api.login({ email, password });
        setUser(response.user);
        return response.user;
      },
      signUp: async (payload) => {
        const response = await api.register(payload);
        setUser(response.user);
        return response.user;
      },
      updateProfile: async (payload) => {
        const updated = await api.updateProfile(payload);
        setUser(updated);
        return updated;
      },
      signOut: async () => {
        await api.logout();
        setUser(null);
      },
    }),
    [loading, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth deve ser usado dentro de AuthProvider");
  return context;
}
