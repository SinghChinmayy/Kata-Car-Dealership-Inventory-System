// Test-only values for the throwaway E2E database; never used outside `npm run e2e`.
export const E2E_DATABASE_URL =
  "postgresql+psycopg://dealership:dealership@localhost:5432/dealership_e2e";
export const E2E_ADMIN = {
  email: "e2e-admin@example.com",
  password: "e2e-admin-password"
};
