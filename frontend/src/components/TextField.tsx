import { useId, type InputHTMLAttributes } from "react";
import { fieldControl, fieldError, fieldLabel } from "./fieldStyles";

type Props = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  error?: string;
  /** Keep the label for assistive technology but hide it visually (compact rows). */
  hideLabel?: boolean;
};

/** Labelled input that shows a field-level error from the API beneath it. */
export function TextField({
  label,
  error,
  hideLabel = false,
  className = "",
  ...input
}: Props) {
  const id = useId();
  const errorId = `${id}-error`;
  return (
    <div className={className}>
      <label htmlFor={id} className={hideLabel ? "sr-only" : fieldLabel}>
        {label}
      </label>
      <input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        className={`${fieldControl} ${hideLabel ? "" : "mt-1.5"}`}
        {...input}
      />
      {error && (
        <p id={errorId} className={fieldError}>
          {error}
        </p>
      )}
    </div>
  );
}
