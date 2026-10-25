import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { VehicleListing } from "../api/types";
import { listing } from "../test/fixtures";
import { VehicleCard } from "./VehicleCard";

const PHOTO = "https://upload.wikimedia.org/wikipedia/commons/nexon.jpg";

function renderCard(overrides: Partial<VehicleListing> = {}) {
  render(
    <VehicleCard
      listing={listing(overrides) as VehicleListing}
      purchasing={false}
      onPurchase={vi.fn()}
    />
  );
}

describe("Vehicle card", () => {
  it("shows the listing's photo", () => {
    renderCard({ image_url: PHOTO });

    expect(screen.getByRole("img", { name: "Tata Nexon" })).toHaveAttribute(
      "src",
      PHOTO
    );
  });
});
