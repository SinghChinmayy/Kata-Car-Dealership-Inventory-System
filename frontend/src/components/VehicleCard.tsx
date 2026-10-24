import { useId } from "react";
import type { VehicleListing } from "../api/types";
import { formatPrice, formatStock } from "../format";
import { dangerTextButton, primaryButton, textButton } from "./buttonStyles";

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
      className="flex flex-col rounded-xl border border-zinc-200 bg-white p-5"
    >
      <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">
        {listing.category}
      </p>
      <h3 id={titleId} className="mt-1 text-base font-semibold text-zinc-900">
        {listing.make} {listing.model}
      </h3>
      <p className="mt-4 text-2xl font-semibold tabular-nums tracking-tight text-zinc-900">
        {formatPrice(listing.price)}
      </p>
      <p
        className={`mt-1 inline-flex items-center gap-1.5 text-sm ${inStock ? "text-zinc-600" : "text-zinc-500"}`}
      >
        <span
          aria-hidden="true"
          className={`h-1.5 w-1.5 shrink-0 rounded-full ${inStock ? "bg-emerald-500" : "bg-zinc-300"}`}
        />
        {formatStock(listing.quantity)}
      </p>
      {/* mt-auto keeps Purchase aligned along the bottom of a row of cards. */}
      <div className="mt-auto pt-5">
        <button
          type="button"
          className={`${primaryButton} w-full`}
          disabled={!inStock || purchasing}
          onClick={() => onPurchase(listing)}
        >
          Purchase
        </button>
      </div>
      {admin && (
        <div className="mt-3 flex items-center gap-4 border-t border-zinc-100 pt-3">
          <button
            type="button"
            className={textButton}
            onClick={() => admin.onEdit(listing)}
          >
            Edit
          </button>
          <button
            type="button"
            className={textButton}
            onClick={() => admin.onRestock(listing)}
          >
            Restock
          </button>
          <button
            type="button"
            className={`${dangerTextButton} ml-auto`}
            onClick={() => admin.onDelete(listing)}
          >
            Delete
          </button>
        </div>
      )}
    </article>
  );
}
