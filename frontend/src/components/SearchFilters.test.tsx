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
          params.has("q") ? page([listing()]) : emptyPage
        );
      })
    );
    const { user } = await renderSignedIn(buyer);

    await user.type(screen.getByLabelText("Search make or model"), "ta");
    await user.selectOptions(await screen.findByLabelText("Category"), "SUV");
    await user.type(screen.getByLabelText("Min price (₹)"), "1000000");
    await user.click(screen.getByRole("button", { name: "Search" }));

    expect(
      await screen.findByRole("article", { name: "Tata Nexon" })
    ).toBeInTheDocument();
    expect(Object.fromEntries(searches.at(-1)!)).toEqual({
      q: "ta",
      category: "SUV",
      min_price: "1000000"
    });

    await user.click(screen.getByRole("button", { name: "Clear" }));

    expect(await screen.findByText(/no vehicles match/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Search make or model")).toHaveValue("");
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

  it("never hides an error that has no matching filter box", async () => {
    server.use(
      http.get("*/api/vehicles/search", () =>
        apiError(422, "validation_error", "Request validation failed.", {
          page: "Input should be a valid integer"
        })
      )
    );
    await renderSignedIn(buyer);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "page: Input should be a valid integer"
    );
  });

  it("shows a category error under the category dropdown", async () => {
    server.use(
      http.get("*/api/vehicles/search", ({ request }) =>
        new URL(request.url).searchParams.has("category")
          ? apiError(422, "validation_error", "Request validation failed.", {
              category: "Input should be a listed category"
            })
          : HttpResponse.json(emptyPage)
      )
    );
    const { user } = await renderSignedIn(buyer);

    await user.selectOptions(await screen.findByLabelText("Category"), "SUV");
    await user.click(screen.getByRole("button", { name: "Search" }));

    expect(
      await screen.findByLabelText("Category")
    ).toHaveAccessibleDescription("Input should be a listed category");
  });

  it("searches make and model together from one box", async () => {
    const searches: URLSearchParams[] = [];
    server.use(
      http.get("*/api/vehicles/search", ({ request }) => {
        const params = new URL(request.url).searchParams;
        searches.push(params);
        return HttpResponse.json(
          params.has("q")
            ? page([listing({ make: "Toyota", model: "Hilux" })])
            : emptyPage
        );
      })
    );
    const { user } = await renderSignedIn(buyer);

    await user.type(screen.getByLabelText("Search make or model"), "hil");
    await user.click(screen.getByRole("button", { name: "Search" }));

    expect(
      await screen.findByRole("article", { name: "Toyota Hilux" })
    ).toBeInTheDocument();
    expect(Object.fromEntries(searches.at(-1)!)).toEqual({ q: "hil" });
  });

  it("searches as you type, without a Search button", async () => {
    const searches: URLSearchParams[] = [];
    server.use(
      http.get("*/api/vehicles/search", ({ request }) => {
        const params = new URL(request.url).searchParams;
        searches.push(params);
        return HttpResponse.json(
          params.get("q") === "hilx"
            ? page([listing({ make: "Toyota", model: "Hilux" })])
            : emptyPage
        );
      })
    );
    const { user } = await renderSignedIn(buyer);

    await user.type(screen.getByLabelText("Search make or model"), "hilx");

    expect(
      await screen.findByRole("article", { name: "Toyota Hilux" })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Search" })
    ).not.toBeInTheDocument();
    // A short pause after typing sends one search, not one per keystroke.
    expect(searches.filter((params) => params.has("q"))).toHaveLength(1);
  });

  it("applies a category choice immediately", async () => {
    server.use(
      http.get("*/api/vehicles/search", ({ request }) =>
        HttpResponse.json(
          new URL(request.url).searchParams.get("category") === "Truck"
            ? page([
                listing({ make: "Toyota", model: "Hilux", category: "Truck" })
              ])
            : emptyPage
        )
      )
    );
    const { user } = await renderSignedIn(buyer);

    await user.selectOptions(await screen.findByLabelText("Category"), "Truck");

    expect(
      await screen.findByRole("article", { name: "Toyota Hilux" })
    ).toBeInTheDocument();
  });
});
