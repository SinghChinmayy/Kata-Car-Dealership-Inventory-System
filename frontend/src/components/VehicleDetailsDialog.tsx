import { useId, type ReactNode } from "react";
import type { VehicleListing } from "../api/types";
import { formatPrice, formatStock } from "../format";
import { Modal } from "./Modal";
import { secondaryButton } from "./buttonStyles";

type Props = { listing: VehicleListing; onClose: () => void };

/** Everything known about one listing, opened from its card. */
export function VehicleDetailsDialog({ listing, onClose }: Props) {
  const inStock = listing.quantity > 0;
  const summary = [listing.category, listing.year, listing.colour]
    .filter((part) => part !== null)
    .join(" · ");
  return (
    <Modal title={`${listing.make} ${listing.model}`} onClose={onClose} wide>
      <p className="mt-1 text-xs font-medium uppercase tracking-wide text-zinc-500">
        {summary}
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
      <div className="mt-6 space-y-5">
        {listing.description && (
          <Section title="Overview">
            <p className="mt-2 text-sm leading-6 text-zinc-600">
              {listing.description}
            </p>
          </Section>
        )}
        <SpecSection
          title="Engine & performance"
          specs={[
            ["Fuel", listing.fuel_type],
            ["Engine", withUnit(listing.engine_cc, "cc")],
            ["Power", withUnit(listing.power_bhp, "bhp")],
            ["Transmission", listing.transmission]
          ]}
        />
        <SpecSection
          title="Practicality"
          specs={[
            ["Seats", listing.seats === null ? null : String(listing.seats)],
            ["Mileage", withUnit(listing.mileage_kmpl, "km/l")]
          ]}
        />
      </div>
      <div className="mt-6 flex justify-end">
        <button type="button" className={secondaryButton} onClick={onClose}>
          Close
        </button>
      </div>
    </Modal>
  );
}

const withUnit = (value: number | string | null, unit: string) =>
  value === null ? null : `${value} ${unit}`;

/** A titled region of the dialog, announced by its heading. */
function Section({
  title,
  children
}: {
  title: string;
  children: ReactNode;
}) {
  const headingId = useId();
  return (
    <section
      aria-labelledby={headingId}
      className="border-t border-zinc-100 pt-4"
    >
      <h3 id={headingId} className="text-sm font-semibold text-zinc-900">
        {title}
      </h3>
      {children}
    </section>
  );
}

/** Label/value rows; rows without a value are left out, and an empty section entirely. */
function SpecSection({
  title,
  specs
}: {
  title: string;
  specs: [label: string, value: string | null][];
}) {
  const known = specs.filter(
    (spec): spec is [string, string] => spec[1] !== null
  );
  if (known.length === 0) return null;
  return (
    <Section title={title}>
      <dl className="mt-2 grid gap-x-8 text-sm sm:grid-cols-2">
        {known.map(([label, value]) => (
          <div
            key={label}
            className="flex justify-between gap-4 border-b border-zinc-100 py-2"
          >
            <dt className="text-zinc-500">{label}</dt>
            <dd className="font-medium text-zinc-900">{value}</dd>
          </div>
        ))}
      </dl>
    </Section>
  );
}
