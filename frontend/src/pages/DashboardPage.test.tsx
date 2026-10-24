import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { buyer, listing, page } from "../test/fixtures";
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
});
