import { useId, type TextareaHTMLAttributes } from "react";
import { fieldControl, fieldError, fieldLabel } from "./fieldStyles";

type Props = TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label: string;
  error?: string;
};

/** Labelled multi-line input, styled and wired for API errors like TextField. */
export function TextAreaField({
  label,
  error,
  className = "",
  ...textarea
}: Props) {
  const id = useId();
  const errorId = `${id}-error`;
  return (
    <div className={className}>
      <label htmlFor={id} className={fieldLabel}>
        {label}
      </label>
      <textarea
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        // fieldControl is sized for one line; let the text area grow with its rows.
        className={`${fieldControl} mt-1.5 h-auto py-2 leading-6`}
        {...textarea}
      />
      {error && (
        <p id={errorId} className={fieldError}>
          {error}
        </p>
      )}
    </div>
  );
}
