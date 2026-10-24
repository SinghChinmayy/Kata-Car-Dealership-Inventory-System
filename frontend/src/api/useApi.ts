import { useCallback } from "react";
import { useAuth } from "../auth/AuthContext";
import { useToast } from "../components/Toast";
import { ApiError, apiRequest } from "./client";

type Options = Omit<Parameters<typeof apiRequest>[1], "token">;

/**
 * apiRequest bound to the signed-in account's bearer token. A 401 means the in-memory token
 * expired or the account changed, so the session ends and the guards return to sign in.
 */
export function useApi() {
  const { session, logout } = useAuth();
  const toast = useToast();
  const token = session?.token;
  return useCallback(
    async <T>(path: string, options: Options = {}) => {
      try {
        return await apiRequest<T>(path, { ...options, token });
      } catch (error) {
        if (error instanceof ApiError && error.status === 401 && token) {
          logout();
          toast("Your session has ended. Please sign in again.");
        }
        throw error;
      }
    },
    [token, logout, toast]
  );
}
