import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent, type ReactNode } from "react";
import { splitErrors } from "../api/client";
import type { VehicleListing } from "../api/types";
import { useApi } from "../api/useApi";
import { FormAlert } from "./FormAlert";
import { Modal } from "./Modal";
import { SelectField } from "./SelectField";
import { TextAreaField } from "./TextAreaField";
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
    image_url: listing?.image_url ?? "",
    ...initialSpecs(listing)
  });
  const set = (key: keyof typeof form) => (value: string) =>
    setForm((current) => ({ ...current, [key]: value }));
  const specOptions = useQuery({
    queryKey: ["vehicles", "spec-options"],
    queryFn: () => api<SpecOptions>("/api/vehicles/spec-options"),
    staleTime: Infinity
  });

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
            body: {
              ...catalogue,
              quantity: Number(form.quantity),
              ...specPayload(form)
            }
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
    <Modal
      title={listing ? "Edit vehicle" : "Add vehicle"}
      onClose={onClose}
      wide
    >
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
        <FormSection title="Overview">
          <TextField
            label="Year"
            type="number"
            min={1900}
            step={1}
            value={form.year}
            onChange={(event) => set("year")(event.target.value)}
          />
          <TextField
            label="Colour"
            value={form.colour}
            onChange={(event) => set("colour")(event.target.value)}
          />
          <TextAreaField
            label="Description"
            className="sm:col-span-2"
            rows={3}
            maxLength={1000}
            value={form.description}
            onChange={(event) => set("description")(event.target.value)}
          />
        </FormSection>
        <FormSection title="Engine & performance">
          <SelectField
            label="Fuel type"
            placeholder="Not specified"
            options={specOptions.data?.fuel_types ?? []}
            value={form.fuel_type}
            onChange={(event) => set("fuel_type")(event.target.value)}
          />
          <SelectField
            label="Transmission"
            placeholder="Not specified"
            options={specOptions.data?.transmissions ?? []}
            value={form.transmission}
            onChange={(event) => set("transmission")(event.target.value)}
          />
          <TextField
            label="Engine (cc)"
            type="number"
            min={1}
            step={1}
            value={form.engine_cc}
            onChange={(event) => set("engine_cc")(event.target.value)}
          />
          <TextField
            label="Battery (kWh)"
            inputMode="decimal"
            value={form.battery_kwh}
            onChange={(event) => set("battery_kwh")(event.target.value)}
          />
          <TextField
            label="Power (bhp)"
            type="number"
            min={1}
            step={1}
            value={form.power_bhp}
            onChange={(event) => set("power_bhp")(event.target.value)}
          />
        </FormSection>
        <FormSection title="Practicality">
          <TextField
            label="Seats"
            type="number"
            min={1}
            step={1}
            value={form.seats}
            onChange={(event) => set("seats")(event.target.value)}
          />
          <TextField
            label="Mileage (km/l)"
            inputMode="decimal"
            value={form.mileage_kmpl}
            onChange={(event) => set("mileage_kmpl")(event.target.value)}
          />
          <TextField
            label="Range (km)"
            type="number"
            min={1}
            step={1}
            value={form.range_km}
            onChange={(event) => set("range_km")(event.target.value)}
          />
        </FormSection>
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

type SpecOptions = { fuel_types: string[]; transmissions: string[] };

type SpecForm = Record<
  | "year"
  | "colour"
  | "description"
  | "fuel_type"
  | "engine_cc"
  | "battery_kwh"
  | "power_bhp"
  | "transmission"
  | "seats"
  | "mileage_kmpl"
  | "range_km",
  string
>;

/** The listing's spec sheet as form text; a spec it lacks starts blank. */
function initialSpecs(listing?: VehicleListing): SpecForm {
  const text = (value: string | number | null | undefined) =>
    value === null || value === undefined ? "" : String(value);
  return {
    year: text(listing?.year),
    colour: text(listing?.colour),
    description: text(listing?.description),
    fuel_type: text(listing?.fuel_type),
    engine_cc: text(listing?.engine_cc),
    battery_kwh: text(listing?.battery_kwh),
    power_bhp: text(listing?.power_bhp),
    transmission: text(listing?.transmission),
    seats: text(listing?.seats),
    mileage_kmpl: text(listing?.mileage_kmpl),
    range_km: text(listing?.range_km)
  };
}

/**
 * The spec sheet as the API expects it: whole numbers as numbers, decimals as exact
 * strings (like price), trimmed text, and null for anything left blank.
 */
function specPayload(form: SpecForm) {
  const text = (value: string) => value.trim() || null;
  const whole = (value: string) => (value.trim() ? Number(value) : null);
  return {
    year: whole(form.year),
    colour: text(form.colour),
    description: text(form.description),
    fuel_type: text(form.fuel_type),
    engine_cc: whole(form.engine_cc),
    battery_kwh: text(form.battery_kwh),
    power_bhp: whole(form.power_bhp),
    transmission: text(form.transmission),
    seats: whole(form.seats),
    mileage_kmpl: text(form.mileage_kmpl),
    range_km: whole(form.range_km)
  };
}

/** A titled group of form fields, laid out in the form's two columns. */
function FormSection({
  title,
  children
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <fieldset className="border-t border-zinc-100 pt-4 sm:col-span-2">
      <legend className="float-left mb-3 w-full text-sm font-semibold text-zinc-900">
        {title}
      </legend>
      <div className="clear-both grid gap-4 sm:grid-cols-2">{children}</div>
    </fieldset>
  );
}
