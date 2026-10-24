import { useState, type FormEvent } from "react";
import { SelectField } from "./SelectField";
import { TextField } from "./TextField";
import { primaryButton, secondaryButton } from "./buttonStyles";

export const FILTER_KEYS = ["q", "category", "min_price", "max_price"] as const;

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
      className="mt-6 flex flex-wrap items-start gap-2"
    >
      <TextField
        label="Search make or model"
        hideLabel
        type="search"
        placeholder="Search make or model"
        className="min-w-0 flex-[4_1_16rem]"
        value={filters.q ?? ""}
        error={errors.q}
        onChange={(event) => set("q")(event.target.value)}
      />
      <SelectField
        label="Category"
        hideLabel
        placeholder="Any category"
        className="min-w-0 basis-full sm:w-44 sm:flex-none"
        options={categories}
        value={filters.category ?? ""}
        error={errors.category}
        onChange={(event) => set("category")(event.target.value)}
      />
      <TextField
        label="Min price (₹)"
        hideLabel
        placeholder="Min ₹"
        className="min-w-0 flex-[1_1_6rem] sm:w-28 sm:flex-none"
        inputMode="decimal"
        value={filters.min_price ?? ""}
        error={errors.min_price}
        onChange={(event) => set("min_price")(event.target.value)}
      />
      <TextField
        label="Max price (₹)"
        hideLabel
        placeholder="Max ₹"
        className="min-w-0 flex-[1_1_6rem] sm:w-28 sm:flex-none"
        inputMode="decimal"
        value={filters.max_price ?? ""}
        error={errors.max_price}
        onChange={(event) => set("max_price")(event.target.value)}
      />
      <div className="flex gap-2">
        <button type="submit" className={primaryButton}>
          Search
        </button>
        <button type="button" className={secondaryButton} onClick={handleClear}>
          Clear
        </button>
      </div>
    </form>
  );
}
