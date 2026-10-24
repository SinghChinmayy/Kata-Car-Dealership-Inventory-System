import { useId, type SelectHTMLAttributes } from "react";

type Props = SelectHTMLAttributes<HTMLSelectElement> & {
  label: string;
  options: string[];
  placeholder: string;
  error?: string;
};

/** Labelled dropdown that shows a field-level error from the API beneath it. */
export function SelectField({
  label,
  options,
  placeholder,
  error,
  className = "",
  ...select
}: Props) {
  const id = useId();
  const errorId = `${id}-error`;
  return (
    <div className={className}>
      <label htmlFor={id} className="block text-sm font-medium text-slate-300">
        {label}
      </label>
      <select
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 focus:border-amber-400 focus:outline-none focus:ring-1 focus:ring-amber-400 aria-[invalid=true]:border-rose-500"
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
        <p id={errorId} className="mt-1 text-sm text-rose-400">
          {error}
        </p>
      )}
    </div>
  );
}
