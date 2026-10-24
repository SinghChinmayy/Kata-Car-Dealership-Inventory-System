import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { renderApp } from "../test/render";

describe("Toast", () => {
  it("keeps an empty live region mounted so screen readers announce later messages", () => {
    renderApp("/login");

    const region = screen.getByRole("status");
    expect(region).toBeEmptyDOMElement();
    expect(region).toHaveAttribute("aria-live", "polite");
  });
});
