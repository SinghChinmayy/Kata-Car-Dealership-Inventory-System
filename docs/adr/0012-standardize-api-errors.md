# Standardize API errors

Every API failure will use `{ "error": { "code", "message", "fields", "request_id" } }`; `fields` appears only on validation failures as a field-to-message map and never echoes submitted values. `request_id` is the safe correlation identifier produced or read by request middleware. Domain exceptions own their status and code, while handlers normalize domain errors, request validation, FastAPI `HTTPException`s (including authentication dependencies and 404/405), and unhandled failures. The frontend accesses errors solely through `parseApiError`.

## Consequences

`invalid_credentials` distinguishes a failed login from `unauthorized`, which represents an absent, invalid, or expired access token. The codes are deliberately few and documented as a stable frontend contract.
