import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useCallback, useState } from "react";
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

  it("returns focus to the control that opened it", async () => {
    const user = userEvent.setup();
    function Opener() {
      const [open, setOpen] = useState(false);
      const close = useCallback(() => setOpen(false), []);
      return (
        <>
          <button type="button" onClick={() => setOpen(true)}>
            Open
          </button>
          {open && (
            <Modal title="Example" onClose={close}>
              <button type="button" onClick={close}>
                Close
              </button>
            </Modal>
          )}
        </>
      );
    }
    render(<Opener />);

    await user.click(screen.getByRole("button", { name: "Open" }));
    await user.click(screen.getByRole("button", { name: "Close" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open" })).toHaveFocus();
  });
});
