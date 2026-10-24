import { secondaryButton } from "./buttonStyles";

type Props = {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
};

export function Pagination({ page, pageSize, total, onPageChange }: Props) {
  const pages = Math.ceil(total / pageSize);
  if (pages <= 1) return null;
  return (
    <nav
      aria-label="Result pages"
      className="mt-8 flex items-center justify-center gap-3 text-sm text-zinc-500"
    >
      <button
        type="button"
        className={secondaryButton}
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
      >
        Previous
      </button>
      <span className="tabular-nums">
        Page {page} of {pages}
      </span>
      <button
        type="button"
        className={secondaryButton}
        disabled={page >= pages}
        onClick={() => onPageChange(page + 1)}
      >
        Next
      </button>
    </nav>
  );
}
