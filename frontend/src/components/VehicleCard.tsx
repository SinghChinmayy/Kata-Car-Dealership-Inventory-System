import { useId } from "react";
import type { VehicleListing } from "../api/types";
import { formatPrice, formatStock } from "../format";

export function VehicleCard({ listing }: { listing: VehicleListing }) {
  const titleId = useId();
  const inStock = listing.quantity > 0;
  return (
    <article
      aria-labelledby={titleId}
      className="flex flex-col rounded-2xl border border-slate-800 bg-slate-900/70 p-5 shadow-lg transition hover:border-slate-700"
    >
      <div className="flex items-start justify-between gap-3">
        <h3 id={titleId} className="text-lg font-semibold text-white">
          {listing.make} {listing.model}
        </h3>
        <span className="rounded-full bg-slate-800 px-2.5 py-0.5 text-xs font-medium text-slate-300">
          {listing.category}
        </span>
      </div>
      <p className="mt-4 text-2xl font-semibold text-amber-400">
        {formatPrice(listing.price)}
      </p>
      <p
        className={`mt-1 text-sm ${inStock ? "text-emerald-400" : "text-rose-400"}`}
      >
        {formatStock(listing.quantity)}
      </p>
    </article>
  );
}
