import { useId } from "react";
import type { VehicleListing } from "../api/types";
import { formatPrice, formatStock } from "../format";
import { primaryButton, secondaryButton } from "./buttonStyles";

export type AdminActions = {
  onEdit: (listing: VehicleListing) => void;
  onRestock: (listing: VehicleListing) => void;
  onDelete: (listing: VehicleListing) => void;
};

type Props = {
  listing: VehicleListing;
  purchasing: boolean;
  onPurchase: (listing: VehicleListing) => void;
  /** Present only for administrators. */
  admin?: AdminActions;
};

export function VehicleCard({ listing, purchasing, onPurchase, admin }: Props) {
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
      <button
        type="button"
        className={`${primaryButton} mt-5`}
        disabled={!inStock || purchasing}
        onClick={() => onPurchase(listing)}
      >
        Purchase
      </button>
      {admin && (
        <div className="mt-3 grid grid-cols-3 gap-2 text-sm">
          <button
            type="button"
            className={`${secondaryButton} px-2 py-1.5`}
            onClick={() => admin.onEdit(listing)}
          >
            Edit
          </button>
          <button
            type="button"
            className={`${secondaryButton} px-2 py-1.5`}
            onClick={() => admin.onRestock(listing)}
          >
            Restock
          </button>
          <button
            type="button"
            className={`${secondaryButton} px-2 py-1.5 text-rose-300 hover:border-rose-500`}
            onClick={() => admin.onDelete(listing)}
          >
            Delete
          </button>
        </div>
      )}
    </article>
  );
}
