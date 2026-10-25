import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, it, vi } from "vitest";
import { buyer } from "../test/fixtures";
import { renderApp } from "../test/render";
import { server } from "../test/server";

describe("Login", () => {
  it("signs in with valid credentials and lands on the dashboard", async () => {
    let loginBody: unknown;
    server.use(
      http.post("*/api/auth/login", async ({ request }) => {
        loginBody = await request.json();
        return HttpResponse.json({
          access_token: "token-1",
          token_type: "bearer"
        });
      }),
      http.get("*/api/auth/me", ({ request }) =>
        request.headers.get("Authorization") === "Bearer token-1"
          ? HttpResponse.json(buyer)
          : new HttpResponse(null, { status: 401 })
      )
    );
    const { user } = renderApp("/login");

    await user.type(screen.getByLabelText(/email/i), "buyer@example.com");
    await user.type(screen.getByLabelText(/password/i), "valid-password");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByText("buyer@example.com")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /log out/i })
    ).toBeInTheDocument();
    expect(loginBody).toEqual({
      email: "buyer@example.com",
      password: "valid-password"
    });
  });

  it("shows the generic credentials error and stays on the sign-in page", async () => {
    server.use(
      http.post("*/api/auth/login", () =>
        HttpResponse.json(
          {
            error: {
              code: "invalid_credentials",
              message: "Email or password is incorrect.",
              request_id: "3f1e9a52-6c1b-4f1e-9a0a-5c7f3e2d1b00"
            }
          },
          { status: 401 }
        )
      )
    );
    const { user } = renderApp("/login");

    await user.type(screen.getByLabelText(/email/i), "buyer@example.com");
    await user.type(screen.getByLabelText(/password/i), "wrong-password");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Email or password is incorrect."
    );
    expect(screen.getByRole("button", { name: /sign in/i })).toBeEnabled();
  });

  describe("demo accounts", () => {
    afterEach(() => {
      vi.unstubAllEnvs();
    });

    it("shows the published demo logins and signs in with one of them", async () => {
      vi.stubEnv("VITE_DEMO_ADMIN_EMAIL", "demo.admin@example.com");
      vi.stubEnv("VITE_DEMO_ADMIN_PASSWORD", "demo-admin-password");
      vi.stubEnv("VITE_DEMO_BUYER_EMAIL", "demo.buyer@example.com");
      vi.stubEnv("VITE_DEMO_BUYER_PASSWORD", "demo-buyer-password");
      let loginBody: unknown;
      server.use(
        http.post("*/api/auth/login", async ({ request }) => {
          loginBody = await request.json();
          return HttpResponse.json({
            access_token: "token-1",
            token_type: "bearer"
          });
        }),
        http.get("*/api/auth/me", () => HttpResponse.json(buyer))
      );
      const { user } = renderApp("/login");

      const demo = screen.getByRole("region", { name: /demo accounts/i });
      expect(demo).toHaveTextContent("demo.admin@example.com");
      expect(demo).toHaveTextContent("demo-admin-password");
      expect(demo).toHaveTextContent("demo.buyer@example.com");
      expect(demo).toHaveTextContent("demo-buyer-password");

      await user.click(screen.getByRole("button", { name: /use demo buyer/i }));
      expect(screen.getByLabelText(/email/i)).toHaveValue(
        "demo.buyer@example.com"
      );
      await user.click(screen.getByRole("button", { name: /^sign in$/i }));

      expect(
        await screen.findByRole("button", { name: /log out/i })
      ).toBeInTheDocument();
      expect(loginBody).toEqual({
        email: "demo.buyer@example.com",
        password: "demo-buyer-password"
      });
    });
  });
});
