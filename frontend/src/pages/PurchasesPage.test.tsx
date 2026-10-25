import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { buyer, page, purchase } from "../test/fixtures";
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
});
