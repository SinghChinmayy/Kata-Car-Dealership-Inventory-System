import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { renderApp } from "./test/render";

describe("App", () => {
  it("renders the application name", () => {
    renderApp("/login");

    expect(
      screen.getByRole("heading", { name: /car dealership inventory/i })
    ).toBeInTheDocument();
  });
});
