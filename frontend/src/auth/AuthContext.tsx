import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "../api/client";
import type { TokenResponse, User } from "../api/types";

type Session = { token: string; user: User };

type AuthValue = {
  session: Session | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthValue | null>(null);

/** Holds the access token in memory only (ADR 0003): a browser refresh requires a new login. */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);

  const login = useCallback(async (email: string, password: string) => {
    const { access_token: token } = await apiRequest<TokenResponse>(
      "/api/auth/login",
      {
        method: "POST",
        body: { email, password }
      }
    );
    const user = await apiRequest<User>("/api/auth/me", { token });
    setSession({ token, user });
  }, []);

  const register = useCallback(
    async (email: string, password: string) => {
      await apiRequest<User>("/api/auth/register", {
        method: "POST",
        body: { email, password }
      });
      await login(email, password);
    },
    [login]
  );

  const queryClient = useQueryClient();
  // Dropping cached data on sign-out keeps one account's results from showing to the next.
  const logout = useCallback(() => {
    setSession(null);
    queryClient.clear();
  }, [queryClient]);

  const value = useMemo(
    () => ({ session, login, register, logout }),
    [session, login, register, logout]
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
