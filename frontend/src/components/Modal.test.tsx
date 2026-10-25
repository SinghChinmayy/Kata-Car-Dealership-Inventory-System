import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { Modal } from "./Modal";

describe("Modal", () => {
  it("keeps Tab focus inside the dialog", async () => {
    const user = userEvent.setup();
    render(
      <>
        <button type="button">Behind the dialog</button>
        <Modal title="Example" onClose={() => {}}>
          <button type="button">First</button>
          <button type="button">Last</button>
        </Modal>
      </>
    );
    const first = screen.getByRole("button", { name: "First" });
    const last = screen.getByRole("button", { name: "Last" });
    expect(first).toHaveFocus();

    await user.tab();
    expect(last).toHaveFocus();
    await user.tab();
    expect(first).toHaveFocus();
    await user.tab({ shift: true });
    expect(last).toHaveFocus();
  });
});
