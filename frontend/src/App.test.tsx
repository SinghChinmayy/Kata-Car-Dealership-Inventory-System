import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { buyer } from "./test/fixtures";
import { signedInAs } from "./test/handlers";
import { renderApp } from "./test/render";
import { server } from "./test/server";

describe("App", () => {
  it("renders the application name", () => {
    renderApp("/login");

    expect(
      screen.getByRole("heading", { name: /car dealership inventory/i })
    ).toBeInTheDocument();
  });

  it.each(["/", "/somewhere-else"])(
    "sends anonymous visitors to sign in from %s",
    async (path) => {
      renderApp(path);

      expect(
        await screen.findByRole("heading", { name: "Sign in" })
      ).toBeInTheDocument();
    }
  );

  it("returns to sign in after logging out", async () => {
    server.use(...signedInAs(buyer));
    const { user } = renderApp("/login");
    await user.type(screen.getByLabelText(/email/i), buyer.email);
    await user.type(screen.getByLabelText(/password/i), "valid-password");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await user.click(await screen.findByRole("button", { name: /log out/i }));

    expect(
      await screen.findByRole("heading", { name: "Sign in" })
    ).toBeInTheDocument();
    expect(screen.queryByText(buyer.email)).not.toBeInTheDocument();
  });
});
