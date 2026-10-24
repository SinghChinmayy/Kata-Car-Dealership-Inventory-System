import { useCallback } from "react";
import { useAuth } from "../auth/AuthContext";
import { apiRequest } from "./client";

type Options = Omit<Parameters<typeof apiRequest>[1], "token">;

/** apiRequest bound to the signed-in account's bearer token. */
export function useApi() {
  const { session } = useAuth();
  const token = session?.token;
  return useCallback(
    <T>(path: string, options: Options = {}) =>
      apiRequest<T>(path, { ...options, token }),
    [token]
  );
}
