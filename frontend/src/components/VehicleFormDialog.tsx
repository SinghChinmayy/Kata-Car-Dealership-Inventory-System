import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { splitErrors } from "../api/client";
import type { VehicleListing } from "../api/types";
import { useApi } from "../api/useApi";
import { FormAlert } from "./FormAlert";
import { Modal } from "./Modal";
import { SelectField } from "./SelectField";
import { TextField } from "./TextField";
import { useToast } from "./Toast";
import { primaryButton, secondaryButton } from "./buttonStyles";

type Props = {
  /** The listing being edited; absent when adding a new one. */
  listing?: VehicleListing;
  categories: string[];
  onClose: () => void;
};

/** Shared add/edit form. Editing never sends quantity: stock changes via purchase/restock. */
export function VehicleFormDialog({ listing, categories, onClose }: Props) {
  const api = useApi();
  const queryClient = useQueryClient();
  const toast = useToast();
  const [form, setForm] = useState({
    make: listing?.make ?? "",
    model: listing?.model ?? "",
    category: listing?.category ?? "",
    price: listing?.price ?? "",
    quantity: "",
    image_url: listing?.image_url ?? ""
  });
  const set = (key: keyof typeof form) => (value: string) =>
    setForm((current) => ({ ...current, [key]: value }));

  const save = useMutation({
    mutationFn: () => {
      const catalogue = {
        make: form.make,
        model: form.model,
        category: form.category,
        price: form.price,
        // A blank field means no photo; edits send it too, as PUT replaces every field.
        image_url: form.image_url.trim() || null
      };
      return listing
        ? api<VehicleListing>(`/api/vehicles/${listing.id}`, {
            method: "PUT",
            body: catalogue
          })
        : api<VehicleListing>("/api/vehicles", {
            method: "POST",
            body: { ...catalogue, quantity: Number(form.quantity) }
          });
    },
    onSuccess: (saved) => {
      void queryClient.invalidateQueries({ queryKey: ["vehicles", "search"] });
      toast(`${listing ? "Updated" : "Added"} ${saved.make} ${saved.model}`);
      onClose();
    }
  });
  const { fields: errors, alert: formError } = splitErrors(save.error, [
    "make",
    "model",
    "category",
    "price",
    "quantity",
    "image_url"
  ]);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    save.mutate();
  }

  return (
    <Modal title={listing ? "Edit vehicle" : "Add vehicle"} onClose={onClose}>
      <form className="mt-5 grid gap-4 sm:grid-cols-2" onSubmit={handleSubmit}>
        {/* empty:hidden drops the grid gap when there is no alert. */}
        <div className="empty:hidden sm:col-span-2">
          <FormAlert message={formError} />
        </div>
        <TextField
          label="Make"
          required
          value={form.make}
          error={errors.make}
          onChange={(event) => set("make")(event.target.value)}
        />
        <TextField
          label="Model"
          required
          value={form.model}
          error={errors.model}
          onChange={(event) => set("model")(event.target.value)}
        />
        <SelectField
          label="Category"
          placeholder="Choose a category"
          required
          options={categories}
          value={form.category}
          error={errors.category}
          onChange={(event) => set("category")(event.target.value)}
        />
        <TextField
          label="Price (₹)"
          inputMode="decimal"
          required
          value={form.price}
          error={errors.price}
          onChange={(event) => set("price")(event.target.value)}
        />
        {!listing && (
          <TextField
            label="Quantity"
            type="number"
            min={0}
            step={1}
            required
            value={form.quantity}
            error={errors.quantity}
            onChange={(event) => set("quantity")(event.target.value)}
          />
        )}
        <TextField
          label="Photo URL (optional)"
          className="sm:col-span-2"
          inputMode="url"
          placeholder="https://…"
          value={form.image_url}
          error={errors.image_url}
          onChange={(event) => set("image_url")(event.target.value)}
        />
        <div className="flex justify-end gap-2 pt-2 sm:col-span-2">
          <button type="button" className={secondaryButton} onClick={onClose}>
            Cancel
          </button>
          <button
            type="submit"
            className={primaryButton}
            disabled={save.isPending}
          >
            {save.isPending ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
