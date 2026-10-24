import { useId, type SelectHTMLAttributes } from "react";
import { fieldControl, fieldError, fieldLabel } from "./fieldStyles";

type Props = SelectHTMLAttributes<HTMLSelectElement> & {
  label: string;
  options: string[];
  placeholder: string;
  error?: string;
  /** Keep the label for assistive technology but hide it visually (compact rows). */
  hideLabel?: boolean;
};

/** Labelled dropdown that shows a field-level error from the API beneath it. */
export function SelectField({
  label,
  options,
  placeholder,
  error,
  hideLabel = false,
  className = "",
  ...select
}: Props) {
  const id = useId();
  const errorId = `${id}-error`;
  return (
    <div className={className}>
      <label htmlFor={id} className={hideLabel ? "sr-only" : fieldLabel}>
        {label}
      </label>
      <select
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        className={`${fieldControl} pr-8 ${hideLabel ? "" : "mt-1.5"}`}
        {...select}
      >
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
      {error && (
        <p id={errorId} className={fieldError}>
          {error}
        </p>
      )}
    </div>
  );
}
