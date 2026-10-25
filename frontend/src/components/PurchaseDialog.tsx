import type { VehicleListing } from "../api/types";
import { formatPrice } from "../format";
import { Modal } from "./Modal";
import { primaryButton, secondaryButton } from "./buttonStyles";

type Props = {
  listing: VehicleListing;
  purchasing: boolean;
  onConfirm: () => void;
  onClose: () => void;
};

/**
 * A purchase is final, so the buyer confirms the price before the request is sent.
 * Cancel comes first so it receives focus: buying is never the default action.
 */
export function PurchaseDialog({
  listing,
  purchasing,
  onConfirm,
  onClose
}: Props) {
  return (
    <Modal title={`Buy ${listing.make} ${listing.model}?`} onClose={onClose}>
      <p className="mt-2 text-sm leading-6 text-zinc-600">
        You are buying one unit for{" "}
        <span className="font-medium text-zinc-900">
          {formatPrice(listing.price)}
        </span>
        .
      </p>
      <div className="mt-6 flex justify-end gap-2">
        <button type="button" className={secondaryButton} onClick={onClose}>
          Cancel
        </button>
        <button
          type="button"
          className={primaryButton}
          disabled={purchasing}
          onClick={onConfirm}
        >
          {purchasing ? "Buying…" : "Confirm purchase"}
        </button>
      </div>
    </Modal>
  );
}
