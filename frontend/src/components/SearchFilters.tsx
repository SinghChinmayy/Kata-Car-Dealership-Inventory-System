import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent
} from "react";
import { SelectField } from "./SelectField";
import { TextField } from "./TextField";
import { secondaryButton } from "./buttonStyles";

export const FILTER_KEYS = ["q", "category", "min_price", "max_price"] as const;

export type Filters = Partial<Record<(typeof FILTER_KEYS)[number], string>>;

type Props = {
  initial: Filters;
  categories: string[];
  errors: Record<string, string>;
  onSearch: (filters: Filters) => void;
};

/** Wait this long after the last keystroke before searching. */
export const SEARCH_DELAY_MS = 300;

const filled = (filters: Filters): Filters =>
  // Only filled filters are sent; blank ones mean "any".
  Object.fromEntries(
    Object.entries(filters).filter(([, value]) => value && value.trim() !== "")
  );

/**
 * Filter bar that searches as you type. Text and price changes are sent after a short
 * pause, a category choice or Enter applies immediately, and the dashboard mirrors the
 * applied filters in the URL.
 */
export function SearchFilters({
  initial,
  categories,
  errors,
  onSearch
}: Props) {
  const [filters, setFilters] = useState<Filters>(initial);
  // What the URL already reflects; avoids re-sending it and detects back/forward.
  const applied = useRef(JSON.stringify(filled(initial)));

  const apply = useCallback(
    (next: Filters) => {
      const key = JSON.stringify(filled(next));
      if (key === applied.current) return;
      applied.current = key;
      onSearch(filled(next));
    },
    [onSearch]
  );

  useEffect(() => {
    const timer = window.setTimeout(() => apply(filters), SEARCH_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [filters, apply]);

  // Back/forward changed the URL: show those filters instead of the typed ones.
  const initialKey = JSON.stringify(filled(initial));
  useEffect(() => {
    if (initialKey !== applied.current) {
      applied.current = initialKey;
      setFilters(JSON.parse(initialKey) as Filters);
    }
  }, [initialKey]);

  const set = (key: keyof Filters) => (value: string) =>
    setFilters((current) => ({ ...current, [key]: value }));

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    apply(filters);
  }

  function handleCategory(value: string) {
    const next = { ...filters, category: value };
    setFilters(next);
    apply(next);
  }

  function handleClear() {
    setFilters({});
    apply({});
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
        onChange={(event) => handleCategory(event.target.value)}
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
        <button type="button" className={secondaryButton} onClick={handleClear}>
          Clear
        </button>
      </div>
    </form>
  );
}
