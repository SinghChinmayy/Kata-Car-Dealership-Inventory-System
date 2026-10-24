import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { buyer, listing, page } from "../test/fixtures";
import { apiError } from "../test/handlers";
import { renderSignedIn } from "../test/render";
import { emptyPage, server } from "../test/server";

describe("Search filters", () => {
  it("searches with every filled filter, and Clear goes back to everything", async () => {
    const searches: URLSearchParams[] = [];
    server.use(
      http.get("*/api/vehicles/search", ({ request }) => {
        const params = new URL(request.url).searchParams;
        searches.push(params);
        return HttpResponse.json(
          params.has("make") ? page([listing()]) : emptyPage
        );
      })
    );
    const { user } = await renderSignedIn(buyer);

    await user.type(screen.getByLabelText("Make"), "ta");
    await user.selectOptions(await screen.findByLabelText("Category"), "SUV");
    await user.type(screen.getByLabelText("Min price (₹)"), "1000000");
    await user.click(screen.getByRole("button", { name: "Search" }));

    expect(
      await screen.findByRole("article", { name: "Tata Nexon" })
    ).toBeInTheDocument();
    expect(Object.fromEntries(searches.at(-1)!)).toEqual({
      make: "ta",
      category: "SUV",
      min_price: "1000000"
    });

    await user.click(screen.getByRole("button", { name: "Clear" }));

    expect(await screen.findByText(/no vehicles match/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Make")).toHaveValue("");
    await waitFor(() =>
      expect(Object.fromEntries(searches.at(-1)!)).toEqual({})
    );
  });

  it("shows a rejected price range on the field the API names", async () => {
    server.use(
      http.get("*/api/vehicles/search", ({ request }) =>
        new URL(request.url).searchParams.has("max_price")
          ? apiError(422, "validation_error", "Request validation failed.", {
              min_price: "Must be less than or equal to max_price."
            })
          : HttpResponse.json(emptyPage)
      )
    );
    const { user } = await renderSignedIn(buyer);

    await user.type(screen.getByLabelText("Min price (₹)"), "900000");
    await user.type(screen.getByLabelText("Max price (₹)"), "100000");
    await user.click(screen.getByRole("button", { name: "Search" }));

    expect(
      await screen.findByLabelText("Min price (₹)")
    ).toHaveAccessibleDescription("Must be less than or equal to max_price.");
  });
});
