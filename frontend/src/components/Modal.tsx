import { useEffect, useId, useRef, type ReactNode } from "react";

type Props = { title: string; onClose: () => void; children: ReactNode };

const FOCUSABLE =
  "a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]), [tabindex]:not([tabindex='-1'])";

/**
 * Accessible modal: labelled by its title, focuses its first control, keeps Tab inside
 * itself, and closes on Escape.
 */
export function Modal({ title, onClose, children }: Props) {
  const titleId = useId();
  const panel = useRef<HTMLDivElement>(null);

  useEffect(() => {
    panel.current
      ?.querySelector<HTMLElement>("input, select, textarea, button")
      ?.focus();
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
      if (event.key === "Tab" && panel.current) wrapTab(event, panel.current);
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-zinc-950/40 p-4">
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="max-h-full w-full max-w-lg overflow-y-auto rounded-xl border border-zinc-200 bg-white p-6 shadow-xl"
      >
        <h2
          id={titleId}
          className="text-lg font-semibold tracking-tight text-zinc-900"
        >
          {title}
        </h2>
        {children}
      </div>
    </div>
  );
}

/** Move Tab past either end of the dialog round to the other end, never to the page behind. */
function wrapTab(event: KeyboardEvent, panel: HTMLElement) {
  const focusable = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE));
  if (focusable.length === 0) return;
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  const inside = panel.contains(document.activeElement);
  if (event.shiftKey && (!inside || document.activeElement === first)) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && (!inside || document.activeElement === last)) {
    event.preventDefault();
    first.focus();
  }
}
