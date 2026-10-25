import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { buyer, listing, page } from "../test/fixtures";
import { renderSignedIn } from "../test/render";
import { server } from "../test/server";

describe("Vehicle details", () => {
  it("opens from the card's title with the category, price and stock", async () => {
    server.use(
      http.get("*/api/vehicles/search", () =>
        HttpResponse.json(page([listing()]))
      )
    );
    const { user } = await renderSignedIn(buyer);
    const card = await screen.findByRole("article", { name: "Tata Nexon" });

    await user.click(within(card).getByRole("button", { name: "Tata Nexon" }));

    const dialog = screen.getByRole("dialog", { name: "Tata Nexon" });
    expect(dialog).toHaveTextContent("SUV");
    expect(dialog).toHaveTextContent("₹12,50,000.00");
    expect(dialog).toHaveTextContent("3 in stock");
  });
});
