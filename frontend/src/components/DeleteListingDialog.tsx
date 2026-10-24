import { useMutation, useQueryClient } from "@tanstack/react-query";
import { errorMessage } from "../api/client";
import type { VehicleListing } from "../api/types";
import { useApi } from "../api/useApi";
import { FormAlert } from "./FormAlert";
import { Modal } from "./Modal";
import { useToast } from "./Toast";
import { dangerButton, secondaryButton } from "./buttonStyles";

type Props = { listing: VehicleListing; onClose: () => void };

/** Cancel comes first so it receives focus: deletion is never the default action. */
export function DeleteListingDialog({ listing, onClose }: Props) {
  const api = useApi();
  const queryClient = useQueryClient();
  const toast = useToast();
  const name = `${listing.make} ${listing.model}`;
  const remove = useMutation({
    mutationFn: () =>
      api<void>(`/api/vehicles/${listing.id}`, { method: "DELETE" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["vehicles", "search"] });
      toast(`Deleted ${name}`);
      onClose();
    }
  });

  return (
    <Modal title={`Delete ${name}?`} onClose={onClose}>
      <p className="mt-3 text-slate-300">
        It will disappear from the inventory and can no longer be bought or
        restocked. Its sales history is kept.
      </p>
      <div className="mt-4">
        <FormAlert
          message={remove.isError ? errorMessage(remove.error) : null}
        />
      </div>
      <div className="mt-6 flex justify-end gap-2">
        <button type="button" className={secondaryButton} onClick={onClose}>
          Cancel
        </button>
        <button
          type="button"
          className={dangerButton}
          disabled={remove.isPending}
          onClick={() => remove.mutate()}
        >
          {remove.isPending ? "Deleting…" : "Delete"}
        </button>
      </div>
    </Modal>
  );
}
