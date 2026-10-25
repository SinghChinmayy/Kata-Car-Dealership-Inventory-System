import { useId } from "react";
import type { VehicleListing } from "../api/types";
import { formatPrice, formatStock } from "../format";
import { dangerTextButton, primaryButton, textButton } from "./buttonStyles";
import { VehiclePhoto } from "./VehiclePhoto";

export type AdminActions = {
  onEdit: (listing: VehicleListing) => void;
  onRestock: (listing: VehicleListing) => void;
  onDelete: (listing: VehicleListing) => void;
};

type Props = {
  listing: VehicleListing;
  purchasing: boolean;
  onPurchase: (listing: VehicleListing) => void;
  /** Opens the listing's details; without it the name is plain text. */
  onOpenDetails?: (listing: VehicleListing) => void;
  /** Present only for administrators. */
  admin?: AdminActions;
};

export function VehicleCard({
  listing,
  purchasing,
  onPurchase,
  onOpenDetails,
  admin
}: Props) {
  const titleId = useId();
  const inStock = listing.quantity > 0;
  return (
    <article
      aria-labelledby={titleId}
      className="flex flex-col overflow-hidden rounded-xl border border-zinc-200 bg-white"
    >
      {/* Clicking the photo is a mouse shortcut for the title button, which keyboard
          users reach instead, so the photo adds no second tab stop. */}
      <div
        className={onOpenDetails ? "cursor-pointer" : undefined}
        onClick={onOpenDetails ? () => onOpenDetails(listing) : undefined}
      >
        {/* Keyed by URL so a new photo gets a fresh try after an earlier one failed. */}
        <VehiclePhoto key={listing.image_url} listing={listing} />
      </div>
      <div className="flex flex-1 flex-col p-5">
        <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">
          {listing.category}
        </p>
        <h3 id={titleId} className="mt-1 text-base font-semibold text-zinc-900">
          {onOpenDetails ? (
            <button
              type="button"
              aria-haspopup="dialog"
              className={titleButton}
              onClick={() => onOpenDetails(listing)}
            >
              {listing.make} {listing.model}
            </button>
          ) : (
            `${listing.make} ${listing.model}`
          )}
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
      </div>
    </article>
  );
}

/** The card title as a quiet link-like button: same type, underline on hover and focus. */
const titleButton =
  "rounded-sm text-left underline-offset-4 hover:underline focus-visible:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-2";
