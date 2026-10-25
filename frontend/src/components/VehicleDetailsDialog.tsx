import type { VehicleListing } from "../api/types";
import { formatPrice, formatStock } from "../format";
import { Modal } from "./Modal";
import { secondaryButton } from "./buttonStyles";

type Props = { listing: VehicleListing; onClose: () => void };

/** Everything known about one listing, opened from its card. */
export function VehicleDetailsDialog({ listing, onClose }: Props) {
  const inStock = listing.quantity > 0;
  return (
    <Modal title={`${listing.make} ${listing.model}`} onClose={onClose}>
      <p className="mt-1 text-xs font-medium uppercase tracking-wide text-zinc-500">
        {listing.category}
      </p>
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
      <div className="mt-6 flex justify-end">
        <button type="button" className={secondaryButton} onClick={onClose}>
          Close
        </button>
      </div>
    </Modal>
  );
}
