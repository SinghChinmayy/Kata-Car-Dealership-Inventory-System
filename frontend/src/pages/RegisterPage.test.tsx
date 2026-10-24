import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { buyer } from "../test/fixtures";
import { apiError, signedInAs } from "../test/handlers";
import { renderApp } from "../test/render";
import { server } from "../test/server";

describe("Registration", () => {
  it("creates the account and signs straight in", async () => {
    let registerBody: unknown;
    server.use(
      http.post("*/api/auth/register", async ({ request }) => {
        registerBody = await request.json();
        return HttpResponse.json(buyer, { status: 201 });
      }),
      ...signedInAs(buyer)
    );
    const { user } = renderApp("/register");

    await user.type(screen.getByLabelText(/email/i), "buyer@example.com");
    await user.type(screen.getByLabelText(/password/i), "valid-password");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    expect(await screen.findByText("buyer@example.com")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /log out/i })
    ).toBeInTheDocument();
    expect(registerBody).toEqual({
      email: "buyer@example.com",
      password: "valid-password"
    });
  });

  it("shows field errors from the API next to the matching inputs", async () => {
    server.use(
      http.post("*/api/auth/register", () =>
        apiError(
          409,
          "duplicate_email",
          "An account with this email already exists."
        )
      )
    );
    const { user } = renderApp("/register");

    await user.type(screen.getByLabelText(/email/i), "buyer@example.com");
    await user.type(screen.getByLabelText(/password/i), "valid-password");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    const email = screen.getByLabelText(/email/i);
    expect(
      await screen.findByText("An account with this email already exists.")
    ).toBeVisible();
    expect(email).toHaveAttribute("aria-invalid", "true");
    expect(email).toHaveAccessibleDescription(
      "An account with this email already exists."
    );
  });

  it("puts a validation error on the password input", async () => {
    server.use(
      http.post("*/api/auth/register", () =>
        apiError(422, "validation_error", "Request validation failed.", {
          password: "String should have at least 12 characters"
        })
      )
    );
    const { user } = renderApp("/register");

    await user.type(screen.getByLabelText(/email/i), "buyer@example.com");
    await user.type(screen.getByLabelText(/password/i), "short");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    expect(
      await screen.findByLabelText(/password/i)
    ).toHaveAccessibleDescription("String should have at least 12 characters");
  });
});
