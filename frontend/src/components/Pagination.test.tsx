import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { buyer, listing, page } from "../test/fixtures";
import { renderSignedIn } from "../test/render";
import { server } from "../test/server";

describe("Pagination", () => {
  it("moves between result pages while keeping the filters", async () => {
    const searches: URLSearchParams[] = [];
    server.use(
      http.get("*/api/vehicles/search", ({ request }) => {
        const params = new URL(request.url).searchParams;
        searches.push(params);
        const current = Number(params.get("page") ?? "1");
        return HttpResponse.json(
          page([listing({ model: `Model ${current}` })], {
            total: 45,
            page: current
          })
        );
      })
    );
    const { user } = await renderSignedIn(buyer);
    await user.type(screen.getByLabelText("Search make or model"), "tata");
    await user.click(screen.getByRole("button", { name: "Search" }));

    expect(await screen.findByText("Page 1 of 3")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Next" }));

    expect(await screen.findByText("Page 2 of 3")).toBeInTheDocument();
    expect(
      screen.getByRole("article", { name: "Tata Model 2" })
    ).toBeInTheDocument();
    expect(Object.fromEntries(searches.at(-1)!)).toEqual({
      q: "tata",
      page: "2"
    });
  });

  it("hides the controls when everything fits on one page", async () => {
    server.use(
      http.get("*/api/vehicles/search", () =>
        HttpResponse.json(page([listing()]))
      )
    );
    await renderSignedIn(buyer);

    await screen.findByRole("article", { name: "Tata Nexon" });
    expect(
      screen.queryByRole("navigation", { name: /pages/i })
    ).not.toBeInTheDocument();
  });
});
