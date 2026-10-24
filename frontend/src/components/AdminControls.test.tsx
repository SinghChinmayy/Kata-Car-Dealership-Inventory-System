import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { administrator, buyer, listing, page } from "../test/fixtures";
import { renderSignedIn } from "../test/render";
import { server } from "../test/server";

const oneListing = () =>
  server.use(
    http.get("*/api/vehicles/search", () =>
      HttpResponse.json(page([listing()]))
    )
  );

describe("Admin controls", () => {
  it("are shown to administrators with a role badge", async () => {
    oneListing();
    await renderSignedIn(administrator);

    const card = await screen.findByRole("article", { name: "Tata Nexon" });
    expect(
      screen.getByRole("button", { name: "Add vehicle" })
    ).toBeInTheDocument();
    expect(
      within(card).getByRole("button", { name: "Edit" })
    ).toBeInTheDocument();
    expect(
      within(card).getByRole("button", { name: "Restock" })
    ).toBeInTheDocument();
    expect(
      within(card).getByRole("button", { name: "Delete" })
    ).toBeInTheDocument();
    expect(screen.getByText("Administrator")).toBeInTheDocument();
  });

  it("are hidden from standard users", async () => {
    oneListing();
    await renderSignedIn(buyer);

    const card = await screen.findByRole("article", { name: "Tata Nexon" });
    expect(
      screen.queryByRole("button", { name: "Add vehicle" })
    ).not.toBeInTheDocument();
    expect(
      within(card).queryByRole("button", { name: "Edit" })
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Administrator")).not.toBeInTheDocument();
  });
});
