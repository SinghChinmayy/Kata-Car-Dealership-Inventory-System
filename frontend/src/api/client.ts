/** Error details from the API's standard error envelope (docs/api-error-contract.md). */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly fields: Record<string, string> = {}
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
  token?: string | null;
  query?: Record<string, string | number | undefined>;
};

// Relative /api paths go through the Vite proxy in development; a base URL can be set for
// split hosting. Resolving against the page origin keeps fetch happy in tests too.
const baseUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin;

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const url = new URL(path, baseUrl);
  for (const [key, value] of Object.entries(options.query ?? {})) {
    if (value !== undefined && value !== "")
      url.searchParams.set(key, String(value));
  }
  const headers: Record<string, string> = {};
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (options.token) headers.Authorization = `Bearer ${options.token}`;

  const response = await fetch(url, {
    method: options.method ?? "GET",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body)
  });
  if (response.status === 204) return undefined as T;
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const error = payload?.error;
    throw new ApiError(
      response.status,
      error?.code ?? "http_error",
      error?.message ?? "The request failed.",
      error?.fields ?? {}
    );
  }
  return payload as T;
}

/** A message safe to show the user for any failure, preferring the API's own wording. */
export function errorMessage(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : "Something went wrong. Please try again.";
}

/** Field-level messages to show beside inputs; a duplicate email belongs on the email field. */
export function fieldErrors(error: unknown): Record<string, string> {
  if (!(error instanceof ApiError)) return {};
  if (error.code === "duplicate_email") return { email: error.message };
  return error.fields;
}

/**
 * Split an API error between the inputs that can display it and a banner message, so no
 * error is ever silently dropped: field errors without a visible input join the banner.
 */
export function splitErrors(
  error: unknown,
  shownFields: readonly string[]
): { fields: Record<string, string>; alert: string | null } {
  if (!error) return { fields: {}, alert: null };
  const all = fieldErrors(error);
  const fields: Record<string, string> = {};
  const leftovers: string[] = [];
  for (const [field, message] of Object.entries(all)) {
    if (shownFields.includes(field)) fields[field] = message;
    else leftovers.push(`${field}: ${message}`);
  }
  if (leftovers.length > 0) return { fields, alert: leftovers.join(" ") };
  return {
    fields,
    alert: Object.keys(all).length > 0 ? null : errorMessage(error)
  };
}
