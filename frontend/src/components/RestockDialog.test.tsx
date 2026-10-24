import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { administrator, listing, page } from "../test/fixtures";
import { apiError } from "../test/handlers";
import { renderSignedIn } from "../test/render";
import { server } from "../test/server";

describe("Restock", () => {
  it("adds units and updates the card's stock", async () => {
    let restockBody: unknown;
    server.use(
      http.get("*/api/vehicles/search", () =>
        HttpResponse.json(page([listing({ quantity: 0 })]))
      ),
      http.post("*/api/vehicles/:id/restock", async ({ request }) => {
        restockBody = await request.json();
        return HttpResponse.json(listing({ quantity: 5 }));
      })
    );
    const { user } = await renderSignedIn(administrator);
    const card = await screen.findByRole("article", { name: "Tata Nexon" });

    await user.click(within(card).getByRole("button", { name: "Restock" }));
    const dialog = screen.getByRole("dialog", { name: "Restock Tata Nexon" });
    await user.type(within(dialog).getByLabelText("Units to add"), "5");
    await user.click(within(dialog).getByRole("button", { name: "Add stock" }));

    expect(await within(card).findByText("5 in stock")).toBeInTheDocument();
    expect(
      within(card).getByRole("button", { name: "Purchase" })
    ).toBeEnabled();
    expect(restockBody).toEqual({ quantity: 5 });
    expect(screen.getByRole("status")).toHaveTextContent(
      "Restocked Tata Nexon"
    );
  });

  it("shows the API's quantity error in the dialog", async () => {
    server.use(
      http.get("*/api/vehicles/search", () =>
        HttpResponse.json(page([listing()]))
      ),
      http.post("*/api/vehicles/:id/restock", () =>
        apiError(422, "validation_error", "Request validation failed.", {
          quantity: "Would exceed the maximum stock quantity."
        })
      )
    );
    const { user } = await renderSignedIn(administrator);
    const card = await screen.findByRole("article", { name: "Tata Nexon" });

    await user.click(within(card).getByRole("button", { name: "Restock" }));
    const dialog = screen.getByRole("dialog", { name: "Restock Tata Nexon" });
    await user.type(
      within(dialog).getByLabelText("Units to add"),
      "2147483647"
    );
    await user.click(within(dialog).getByRole("button", { name: "Add stock" }));

    expect(
      await within(dialog).findByLabelText("Units to add")
    ).toHaveAccessibleDescription("Would exceed the maximum stock quantity.");
  });
});
