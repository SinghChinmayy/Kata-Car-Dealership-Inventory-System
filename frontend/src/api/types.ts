export type Role = "standard_user" | "administrator";

export type User = { id: string; email: string; role: Role };

export type TokenResponse = { access_token: string; token_type: "bearer" };
