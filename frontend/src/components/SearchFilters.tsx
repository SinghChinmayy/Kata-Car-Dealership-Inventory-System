import { useState, type FormEvent } from "react";
import { SelectField } from "./SelectField";
import { TextField } from "./TextField";
import { primaryButton, secondaryButton } from "./buttonStyles";

export const FILTER_KEYS = [
  "make",
  "model",
  "category",
  "min_price",
  "max_price"
] as const;

export type Filters = Partial<Record<(typeof FILTER_KEYS)[number], string>>;

type Props = {
  initial: Filters;
  categories: string[];
  errors: Record<string, string>;
  onSearch: (filters: Filters) => void;
};

/** Filter bar; the dashboard keeps the submitted filters in the URL. */
export function SearchFilters({
  initial,
  categories,
  errors,
  onSearch
}: Props) {
  const [filters, setFilters] = useState<Filters>(initial);
  const set = (key: keyof Filters) => (value: string) =>
    setFilters((current) => ({ ...current, [key]: value }));

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    // Only filled filters are sent; blank ones mean "any".
    const filled = Object.fromEntries(
      Object.entries(filters).filter(
        ([, value]) => value && value.trim() !== ""
      )
    );
    onSearch(filled);
  }

  function handleClear() {
    setFilters({});
    onSearch({});
  }

  return (
    <form
      role="search"
      onSubmit={handleSubmit}
      className="mt-6 grid gap-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-5 sm:grid-cols-2 lg:grid-cols-[repeat(5,minmax(0,1fr))_auto]"
    >
      <TextField
        label="Make"
        value={filters.make ?? ""}
        error={errors.make}
        onChange={(event) => set("make")(event.target.value)}
      />
      <TextField
        label="Model"
        value={filters.model ?? ""}
        error={errors.model}
        onChange={(event) => set("model")(event.target.value)}
      />
      <SelectField
        label="Category"
        placeholder="Any category"
        options={categories}
        value={filters.category ?? ""}
        onChange={(event) => set("category")(event.target.value)}
      />
      <TextField
        label="Min price (₹)"
        inputMode="decimal"
        value={filters.min_price ?? ""}
        error={errors.min_price}
        onChange={(event) => set("min_price")(event.target.value)}
      />
      <TextField
        label="Max price (₹)"
        inputMode="decimal"
        value={filters.max_price ?? ""}
        error={errors.max_price}
        onChange={(event) => set("max_price")(event.target.value)}
      />
      <div className="flex items-end gap-2 sm:col-span-2 lg:col-span-1">
        <button type="submit" className={`${primaryButton} flex-1`}>
          Search
        </button>
        <button type="button" className={secondaryButton} onClick={handleClear}>
          Clear
        </button>
      </div>
    </form>
  );
}
