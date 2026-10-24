import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { administrator, listing, page } from "../test/fixtures";
import { renderSignedIn } from "../test/render";
import { emptyPage, server } from "../test/server";

describe("Delete vehicle", () => {
  it("asks for confirmation, then removes the listing", async () => {
    let deletedId: string | undefined;
    server.use(
      http.get("*/api/vehicles/search", () =>
        HttpResponse.json(page([listing()]))
      ),
      http.delete("*/api/vehicles/:id", ({ params }) => {
        deletedId = params.id as string;
        return new HttpResponse(null, { status: 204 });
      })
    );
    const { user } = await renderSignedIn(administrator);
    const card = await screen.findByRole("article", { name: "Tata Nexon" });

    await user.click(within(card).getByRole("button", { name: "Delete" }));
    const dialog = screen.getByRole("dialog", { name: "Delete Tata Nexon?" });
    expect(dialog).toHaveTextContent(/disappear from the inventory/i);
    server.use(
      http.get("*/api/vehicles/search", () => HttpResponse.json(emptyPage))
    );
    await user.click(within(dialog).getByRole("button", { name: "Delete" }));

    expect(await screen.findByText(/no vehicles match/i)).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Deleted Tata Nexon");
    expect(deletedId).toBe(listing().id);
  });

  it("does nothing when cancelled", async () => {
    server.use(
      http.get("*/api/vehicles/search", () =>
        HttpResponse.json(page([listing()]))
      )
    );
    const { user } = await renderSignedIn(administrator);
    const card = await screen.findByRole("article", { name: "Tata Nexon" });

    await user.click(within(card).getByRole("button", { name: "Delete" }));
    await user.click(
      within(screen.getByRole("dialog")).getByRole("button", { name: "Cancel" })
    );

    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    );
    expect(
      screen.getByRole("article", { name: "Tata Nexon" })
    ).toBeInTheDocument();
  });
});
