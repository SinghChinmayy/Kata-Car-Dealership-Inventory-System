# Use normalized email and password accounts

User Accounts authenticate with a trimmed, lowercased email address and password. Email is validated with `EmailStr` (maximum 254 characters) and protected by a database unique index; a duplicate registration maps its integrity failure to 409, while every failed login returns generic 401. The system deliberately does not remove provider-specific dots or plus tags, and excludes email verification, password recovery, and profile fields from the kata.

## Consequences

Returning 409 for duplicate registration reveals that an email is registered. This accepted kata trade-off is documented in the README; responses never expose password hashes and return only an account's ID, email, and role.
