import { useEffect, useId, useRef, type ReactNode } from "react";

type Props = { title: string; onClose: () => void; children: ReactNode };

/** Accessible modal: labelled by its title, focuses its first control, closes on Escape. */
export function Modal({ title, onClose, children }: Props) {
  const titleId = useId();
  const panel = useRef<HTMLDivElement>(null);

  useEffect(() => {
    panel.current
      ?.querySelector<HTMLElement>("input, select, textarea, button")
      ?.focus();
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/80 px-4 backdrop-blur-sm">
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl"
      >
        <h2 id={titleId} className="text-xl font-semibold text-white">
          {title}
        </h2>
        {children}
      </div>
    </div>
  );
}
