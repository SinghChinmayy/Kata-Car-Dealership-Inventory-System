import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { buyer, listing, page } from "../test/fixtures";
import { renderSignedIn } from "../test/render";
import { server } from "../test/server";

const PETROL_SPECS = {
  year: 2024,
  colour: "Pure Grey",
  description: "Compact SUV with a five-star safety rating.",
  fuel_type: "Petrol",
  engine_cc: 1199,
  power_bhp: 118,
  transmission: "Manual",
  seats: 5,
  mileage_kmpl: "17.4"
};

/** The term/value pairs of a spec section's description list. */
function specs(section: HTMLElement): Record<string, string | null> {
  return Object.fromEntries(
    within(section)
      .getAllByRole("term")
      .map((term) => [
        term.textContent,
        term.nextElementSibling?.textContent ?? null
      ])
  );
}

async function openDetails(overrides: Record<string, unknown> = {}) {
  server.use(
    http.get("*/api/vehicles/search", () =>
      HttpResponse.json(page([listing(overrides)]))
    )
  );
  const view = await renderSignedIn(buyer);
  const card = await screen.findByRole("article", { name: "Tata Nexon" });
  await view.user.click(
    within(card).getByRole("button", { name: "Tata Nexon" })
  );
  return {
    ...view,
    dialog: screen.getByRole("dialog", { name: "Tata Nexon" })
  };
}

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

  it("shows the spec sheet in sections", async () => {
    const { dialog } = await openDetails(PETROL_SPECS);

    expect(dialog).toHaveTextContent("SUV · 2024 · Pure Grey");
    expect(
      within(dialog).getByRole("region", { name: "Overview" })
    ).toHaveTextContent("Compact SUV with a five-star safety rating.");
    expect(
      specs(
        within(dialog).getByRole("region", { name: "Engine & performance" })
      )
    ).toEqual({
      Fuel: "Petrol",
      Engine: "1199 cc",
      Power: "118 bhp",
      Transmission: "Manual"
    });
    expect(
      specs(within(dialog).getByRole("region", { name: "Practicality" }))
    ).toEqual({ Seats: "5", Mileage: "17.4 km/l" });
  });

  it("shows an electric car's battery and range", async () => {
    const { dialog } = await openDetails({
      ...PETROL_SPECS,
      fuel_type: "Electric",
      engine_cc: null,
      battery_kwh: "45.0",
      transmission: "Automatic",
      mileage_kmpl: null,
      range_km: 489
    });

    expect(
      specs(
        within(dialog).getByRole("region", { name: "Engine & performance" })
      )
    ).toEqual({
      Fuel: "Electric",
      Battery: "45.0 kWh",
      Power: "118 bhp",
      Transmission: "Automatic"
    });
    expect(
      specs(within(dialog).getByRole("region", { name: "Practicality" }))
    ).toEqual({ Seats: "5", Range: "489 km" });
  });
});
