import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
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
});
