import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { buyer, listing, page } from "../test/fixtures";
import { renderSignedIn } from "../test/render";
import { server } from "../test/server";

describe("Purchase vehicle", () => {
  it("asks for confirmation with the price before buying", async () => {
    let purchases = 0;
    server.use(
      http.get("*/api/vehicles/search", () =>
        HttpResponse.json(page([listing()]))
      ),
      http.post("*/api/vehicles/:id/purchase", () => {
        purchases += 1;
        return HttpResponse.json(listing({ quantity: 2 }));
      })
    );
    const { user } = await renderSignedIn(buyer);
    const card = await screen.findByRole("article", { name: "Tata Nexon" });

    await user.click(within(card).getByRole("button", { name: "Purchase" }));
    const dialog = screen.getByRole("dialog", { name: "Buy Tata Nexon?" });
    expect(dialog).toHaveTextContent("₹12,50,000.00");
    expect(purchases).toBe(0);
    await user.click(
      within(dialog).getByRole("button", { name: "Confirm purchase" })
    );

    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    );
    expect(screen.getByRole("status")).toHaveTextContent(
      "Purchased Tata Nexon"
    );
    expect(purchases).toBe(1);
  });

  it("focuses Cancel first and buys nothing when cancelled", async () => {
    let purchases = 0;
    server.use(
      http.get("*/api/vehicles/search", () =>
        HttpResponse.json(page([listing()]))
      ),
      http.post("*/api/vehicles/:id/purchase", () => {
        purchases += 1;
        return HttpResponse.json(listing({ quantity: 2 }));
      })
    );
    const { user } = await renderSignedIn(buyer);
    const card = await screen.findByRole("article", { name: "Tata Nexon" });

    await user.click(within(card).getByRole("button", { name: "Purchase" }));
    const cancel = within(screen.getByRole("dialog")).getByRole("button", {
      name: "Cancel"
    });
    expect(cancel).toHaveFocus();
    await user.click(cancel);

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(within(card).getByText("3 in stock")).toBeInTheDocument();
    expect(purchases).toBe(0);
  });
});
