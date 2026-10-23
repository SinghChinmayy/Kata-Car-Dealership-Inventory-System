# Start with access-token-only authentication

The API will authenticate requests with 60-minute HS256 JWT access tokens supplied through the `Authorization: Bearer <token>` header. Tokens contain the User Account UUID as `sub` plus standard issuance and expiry claims; every protected request loads the current User Account and role from PostgreSQL. The React frontend holds the access token only in memory. Passwords will be hashed with `pwdlib[argon2]`, PyJWT will create and verify tokens, and FastAPI's `HTTPBearer` will read credentials; refresh tokens are deliberately deferred so token expiry or a browser refresh requires a new login.

## Consequences

Users will need to sign in after an access token expires and after a browser refresh. A future refresh-token implementation must add its own issuance, rotation, storage, and revocation design. Loading the account and role on each protected request adds one database lookup, but means role changes take effect immediately instead of waiting for issued tokens to expire.
