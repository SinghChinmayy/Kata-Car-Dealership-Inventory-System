import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { splitErrors } from "../api/client";
import { patchCachedListing } from "../api/listingCache";
import type { VehicleListing } from "../api/types";
import { useApi } from "../api/useApi";
import { FormAlert } from "./FormAlert";
import { Modal } from "./Modal";
import { TextField } from "./TextField";
import { useToast } from "./Toast";
import { primaryButton, secondaryButton } from "./buttonStyles";

type Props = { listing: VehicleListing; onClose: () => void };

export function RestockDialog({ listing, onClose }: Props) {
  const api = useApi();
  const queryClient = useQueryClient();
  const toast = useToast();
  const [quantity, setQuantity] = useState("");
  const name = `${listing.make} ${listing.model}`;
  const restock = useMutation({
    mutationFn: () =>
      api<VehicleListing>(`/api/vehicles/${listing.id}/restock`, {
        method: "POST",
        body: { quantity: Number(quantity) }
      }),
    onSuccess: (updated) => {
      patchCachedListing(queryClient, updated);
      toast(`Restocked ${name}`);
      onClose();
    }
  });
  const { fields: errors, alert: formError } = splitErrors(restock.error, [
    "quantity"
  ]);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    restock.mutate();
  }

  return (
    <Modal title={`Restock ${name}`} onClose={onClose}>
      <form className="mt-5 space-y-4" onSubmit={handleSubmit}>
        <p className="text-sm text-zinc-500">
          Currently {listing.quantity} in stock.
        </p>
        <FormAlert message={formError} />
        <TextField
          label="Units to add"
          type="number"
          min={1}
          step={1}
          required
          value={quantity}
          error={errors.quantity}
          onChange={(event) => setQuantity(event.target.value)}
        />
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" className={secondaryButton} onClick={onClose}>
            Cancel
          </button>
          <button
            type="submit"
            className={primaryButton}
            disabled={restock.isPending}
          >
            {restock.isPending ? "Adding…" : "Add stock"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
