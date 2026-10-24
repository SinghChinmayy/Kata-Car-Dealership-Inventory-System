import { http, HttpResponse } from "msw";
import type { User } from "../api/types";

/** Handlers for a successful login as the given account, issuing the given token. */
export function signedInAs(account: User, token = "token-1") {
  return [
    http.post("*/api/auth/login", () =>
      HttpResponse.json({ access_token: token, token_type: "bearer" })
    ),
    http.get("*/api/auth/me", ({ request }) =>
      request.headers.get("Authorization") === `Bearer ${token}`
        ? HttpResponse.json(account)
        : new HttpResponse(null, { status: 401 })
    )
  ];
}

/** Build the API error envelope for a status and code. */
export function apiError(
  status: number,
  code: string,
  message: string,
  fields?: object
) {
  return HttpResponse.json(
    {
      error: {
        code,
        message,
        request_id: "3f1e9a52-6c1b-4f1e-9a0a-5c7f3e2d1b00",
        ...(fields ? { fields } : {})
      }
    },
    { status }
  );
}
