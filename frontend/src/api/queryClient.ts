import { QueryClient } from "@tanstack/react-query";
import { ApiError } from "./client";

/**
 * Shared by the app and the tests. A 4xx means the request itself is wrong (bad input,
 * no permission, not found), so retrying only delays the error; server and network
 * hiccups get one more attempt.
 */
export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: (failureCount, error) =>
          !(error instanceof ApiError && error.status < 500) && failureCount < 1
      },
      mutations: { retry: false }
    }
  });
}
