import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { buyer, listing, page } from "../test/fixtures";
import { apiError } from "../test/handlers";
import { renderSignedIn } from "../test/render";
import { server } from "../test/server";

describe("Dashboard", () => {
  it("shows each vehicle with its category, INR price and stock", async () => {
    server.use(
      http.get("*/api/vehicles/search", () =>
        HttpResponse.json(
          page([
            listing(),
            listing({
              id: "a1b2c3d4-0000-4000-8000-000000000002",
              make: "Maruti",
              model: "Swift",
              category: "Hatchback",
              price: "650000.00",
              quantity: 0
            })
          ])
        )
      )
    );
    await renderSignedIn(buyer);

    const nexon = await screen.findByRole("article", { name: "Tata Nexon" });
    expect(within(nexon).getByText("SUV")).toBeInTheDocument();
    expect(within(nexon).getByText("₹12,50,000.00")).toBeInTheDocument();
    expect(within(nexon).getByText("3 in stock")).toBeInTheDocument();
    const swift = screen.getByRole("article", { name: "Maruti Swift" });
    expect(within(swift).getByText("₹6,50,000.00")).toBeInTheDocument();
    expect(within(swift).getByText("Out of stock")).toBeInTheDocument();
  });

  it("explains when no vehicles match", async () => {
    await renderSignedIn(buyer);

    expect(await screen.findByText(/no vehicles match/i)).toBeInTheDocument();
  });

  it("buys one unit and updates the card, with Purchase disabled at zero", async () => {
    let purchasedId: string | undefined;
    server.use(
      http.get("*/api/vehicles/search", () =>
        HttpResponse.json(page([listing({ quantity: 1 })]))
      ),
      http.post("*/api/vehicles/:id/purchase", ({ params }) => {
        purchasedId = params.id as string;
        return HttpResponse.json(listing({ quantity: 0 }));
      })
    );
    const { user } = await renderSignedIn(buyer);
    const card = await screen.findByRole("article", { name: "Tata Nexon" });

    await user.click(within(card).getByRole("button", { name: "Purchase" }));

    expect(await within(card).findByText("Out of stock")).toBeInTheDocument();
    expect(
      within(card).getByRole("button", { name: "Purchase" })
    ).toBeDisabled();
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Purchased Tata Nexon"
    );
    expect(purchasedId).toBe(listing().id);
  });

  it("marks a listing sold out when someone else bought the last unit", async () => {
    server.use(
      http.get("*/api/vehicles/search", () =>
        HttpResponse.json(page([listing({ quantity: 1 })]))
      ),
      http.post("*/api/vehicles/:id/purchase", () =>
        apiError(409, "out_of_stock", "This vehicle is out of stock.")
      )
    );
    const { user } = await renderSignedIn(buyer);
    const card = await screen.findByRole("article", { name: "Tata Nexon" });
    server.use(
      http.get("*/api/vehicles/search", () =>
        HttpResponse.json(page([listing({ quantity: 0 })]))
      )
    );

    await user.click(within(card).getByRole("button", { name: "Purchase" }));

    expect(await screen.findByRole("status")).toHaveTextContent(
      "This vehicle is out of stock."
    );
    expect(await within(card).findByText("Out of stock")).toBeInTheDocument();
    expect(
      within(card).getByRole("button", { name: "Purchase" })
    ).toBeDisabled();
  });

  it("retries a server hiccup once before giving up", async () => {
    let calls = 0;
    server.use(
      http.get("*/api/vehicles/search", () => {
        calls += 1;
        return calls === 1
          ? apiError(503, "service_unavailable", "Database unavailable.")
          : HttpResponse.json(page([listing()]));
      })
    );
    await renderSignedIn(buyer);

    expect(
      await screen.findByRole(
        "article",
        { name: "Tata Nexon" },
        { timeout: 3000 }
      )
    ).toBeInTheDocument();
    expect(calls).toBe(2);
  });
});
