import { screen } from "@testing-library/react";
import { http } from "msw";
import { describe, expect, it } from "vitest";
import { buyer } from "./test/fixtures";
import { apiError } from "./test/handlers";
import { renderApp, renderSignedIn } from "./test/render";
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
    const { user } = await renderSignedIn(buyer);

    await user.click(screen.getByRole("button", { name: /log out/i }));

    expect(
      await screen.findByRole("heading", { name: "Sign in" })
    ).toBeInTheDocument();
    expect(screen.queryByText(buyer.email)).not.toBeInTheDocument();
  });

  it("ends the session and asks to sign in again when the token stops working", async () => {
    const { user } = await renderSignedIn(buyer);
    server.use(
      http.get("*/api/vehicles/search", () =>
        apiError(401, "unauthorized", "Authentication is required.")
      )
    );

    await user.type(screen.getByLabelText("Search make or model"), "tata");
    await user.click(screen.getByRole("button", { name: "Search" }));

    expect(
      await screen.findByRole("heading", { name: "Sign in" })
    ).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(
      "Your session has ended. Please sign in again."
    );
    expect(screen.queryByText(buyer.email)).not.toBeInTheDocument();
  });
});
