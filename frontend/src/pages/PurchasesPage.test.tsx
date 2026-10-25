import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { buyer, page, purchase } from "../test/fixtures";
import { apiError } from "../test/handlers";
import { renderSignedIn } from "../test/render";
import { server } from "../test/server";

describe("My purchases", () => {
  it("lists what the account bought, newest first, from the header link", async () => {
    server.use(
      http.get("*/api/purchases/me", () =>
        HttpResponse.json(
          page([
            purchase({
              id: "c0ffee00-0000-4000-8000-000000000002",
              make: "Honda",
              model: "City",
              category: "Sedan",
              price: "1150000.00",
              purchased_at: "2026-10-25T06:30:00Z"
            }),
            purchase()
          ])
        )
      )
    );
    const { user } = await renderSignedIn(buyer);

    await user.click(screen.getByRole("link", { name: "My purchases" }));

    expect(
      await screen.findByRole("heading", { name: "My purchases" })
    ).toBeInTheDocument();
    const list = await screen.findByRole("list", { name: "Purchases" });
    const [city, nexon] = within(list).getAllByRole("listitem");
    expect(city).toHaveTextContent("Honda City");
    expect(city).toHaveTextContent("Sedan");
    expect(city).toHaveTextContent("₹11,50,000.00");
    expect(city).toHaveTextContent("25 Oct 2026");
    expect(nexon).toHaveTextContent("Tata Nexon");
    expect(nexon).toHaveTextContent("₹12,50,000.00");
    expect(nexon).toHaveTextContent("24 Oct 2026");
  });

  it("points to the inventory when nothing has been bought yet", async () => {
    server.use(
      http.get("*/api/purchases/me", () => HttpResponse.json(page([])))
    );
    const { user } = await renderSignedIn(buyer);

    await user.click(screen.getByRole("link", { name: "My purchases" }));
    expect(
      await screen.findByText("You haven't bought any vehicles yet.")
    ).toBeInTheDocument();
    await user.click(screen.getByRole("link", { name: "Browse inventory" }));

    expect(
      await screen.findByRole("heading", { name: "Inventory" })
    ).toBeInTheDocument();
  });

  it("pages through a long history", async () => {
    const requestedPages: (string | null)[] = [];
    server.use(
      http.get("*/api/purchases/me", ({ request }) => {
        const requested = new URL(request.url).searchParams.get("page");
        requestedPages.push(requested);
        return requested === "2"
          ? HttpResponse.json(
              page([purchase({ model: "Harrier" })], { total: 21, page: 2 })
            )
          : HttpResponse.json(page([purchase()], { total: 21 }));
      })
    );
    const { user } = await renderSignedIn(buyer);

    await user.click(screen.getByRole("link", { name: "My purchases" }));
    expect(await screen.findByText("Page 1 of 2")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Next" }));

    expect(
      await screen.findByRole("heading", { name: "Tata Harrier" })
    ).toBeInTheDocument();
    expect(screen.getByText("Page 2 of 2")).toBeInTheDocument();
    expect(requestedPages).toEqual([null, "2"]);
  });

  it("says so when the history cannot be loaded", async () => {
    server.use(
      http.get("*/api/purchases/me", () =>
        apiError(503, "service_unavailable", "Database is unavailable.")
      )
    );
    const { user } = await renderSignedIn(buyer);

    await user.click(screen.getByRole("link", { name: "My purchases" }));

    // One retry for a server error comes first, as everywhere else in the app.
    expect(
      await screen.findByRole("alert", {}, { timeout: 3000 })
    ).toHaveTextContent("Database is unavailable.");
    expect(screen.queryByText("Loading purchases…")).not.toBeInTheDocument();
  });
});
