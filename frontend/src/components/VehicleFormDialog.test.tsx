import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { administrator, listing, page } from "../test/fixtures";
import { apiError } from "../test/handlers";
import { renderSignedIn } from "../test/render";
import { server } from "../test/server";

describe("Add vehicle", () => {
  it("creates a listing from the form and refreshes the inventory", async () => {
    let created: unknown;
    server.use(
      http.post("*/api/vehicles", async ({ request }) => {
        created = await request.json();
        return HttpResponse.json(listing(), { status: 201 });
      })
    );
    const { user } = await renderSignedIn(administrator);
    await user.click(screen.getByRole("button", { name: "Add vehicle" }));
    const dialog = screen.getByRole("dialog", { name: "Add vehicle" });
    server.use(
      http.get("*/api/vehicles/search", () =>
        HttpResponse.json(page([listing()]))
      )
    );

    await user.type(within(dialog).getByLabelText("Make"), "Tata");
    await user.type(within(dialog).getByLabelText("Model"), "Nexon");
    await user.selectOptions(within(dialog).getByLabelText("Category"), "SUV");
    await user.type(within(dialog).getByLabelText("Price (₹)"), "1250000");
    await user.type(within(dialog).getByLabelText("Quantity"), "3");
    await user.click(within(dialog).getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    );
    expect(created).toEqual({
      make: "Tata",
      model: "Nexon",
      category: "SUV",
      price: "1250000",
      quantity: 3
    });
    expect(screen.getByRole("status")).toHaveTextContent("Added Tata Nexon");
    expect(
      await screen.findByRole("article", { name: "Tata Nexon" })
    ).toBeInTheDocument();
  });

  it("keeps the dialog open with field errors, and Cancel closes it", async () => {
    server.use(
      http.post("*/api/vehicles", () =>
        apiError(422, "validation_error", "Request validation failed.", {
          price: "Input should be greater than 0"
        })
      )
    );
    const { user } = await renderSignedIn(administrator);
    await user.click(screen.getByRole("button", { name: "Add vehicle" }));
    const dialog = screen.getByRole("dialog", { name: "Add vehicle" });

    await user.type(within(dialog).getByLabelText("Make"), "Tata");
    await user.type(within(dialog).getByLabelText("Model"), "Nexon");
    await user.selectOptions(within(dialog).getByLabelText("Category"), "SUV");
    await user.type(within(dialog).getByLabelText("Price (₹)"), "0");
    await user.type(within(dialog).getByLabelText("Quantity"), "1");
    await user.click(within(dialog).getByRole("button", { name: "Save" }));

    expect(
      await within(dialog).findByLabelText("Price (₹)")
    ).toHaveAccessibleDescription("Input should be greater than 0");

    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});

describe("Vehicle form errors", () => {
  it("shows a category error under the dropdown", async () => {
    server.use(
      http.post("*/api/vehicles", () =>
        apiError(422, "validation_error", "Request validation failed.", {
          category: "Input should be a listed category"
        })
      )
    );
    const { user } = await renderSignedIn(administrator);
    await user.click(screen.getByRole("button", { name: "Add vehicle" }));
    const dialog = screen.getByRole("dialog", { name: "Add vehicle" });

    await user.type(within(dialog).getByLabelText("Make"), "Tata");
    await user.type(within(dialog).getByLabelText("Model"), "Nexon");
    await user.selectOptions(within(dialog).getByLabelText("Category"), "SUV");
    await user.type(within(dialog).getByLabelText("Price (₹)"), "100");
    await user.type(within(dialog).getByLabelText("Quantity"), "1");
    await user.click(within(dialog).getByRole("button", { name: "Save" }));

    expect(
      await within(dialog).findByLabelText("Category")
    ).toHaveAccessibleDescription("Input should be a listed category");
  });
});

describe("Edit vehicle", () => {
  it("prefills the listing, sends only catalogue fields and updates the card", async () => {
    let updated: unknown;
    server.use(
      http.get("*/api/vehicles/search", () =>
        HttpResponse.json(page([listing()]))
      ),
      http.put("*/api/vehicles/:id", async ({ request }) => {
        updated = await request.json();
        return HttpResponse.json(
          listing({ model: "Nexon EV", price: "1499999.50" })
        );
      })
    );
    const { user } = await renderSignedIn(administrator);
    const card = await screen.findByRole("article", { name: "Tata Nexon" });
    await user.click(within(card).getByRole("button", { name: "Edit" }));
    const dialog = screen.getByRole("dialog", { name: "Edit vehicle" });
    expect(within(dialog).getByLabelText("Make")).toHaveValue("Tata");
    expect(within(dialog).queryByLabelText("Quantity")).not.toBeInTheDocument();
    server.use(
      http.get("*/api/vehicles/search", () =>
        HttpResponse.json(
          page([listing({ model: "Nexon EV", price: "1499999.50" })])
        )
      )
    );

    const model = within(dialog).getByLabelText("Model");
    await user.clear(model);
    await user.type(model, "Nexon EV");
    const price = within(dialog).getByLabelText("Price (₹)");
    await user.clear(price);
    await user.type(price, "1499999.50");
    await user.click(within(dialog).getByRole("button", { name: "Save" }));

    expect(
      await screen.findByRole("article", { name: "Tata Nexon EV" })
    ).toBeInTheDocument();
    expect(updated).toEqual({
      make: "Tata",
      model: "Nexon EV",
      category: "SUV",
      price: "1499999.50"
    });
    expect(screen.getByRole("status")).toHaveTextContent(
      "Updated Tata Nexon EV"
    );
  });
});
