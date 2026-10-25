import { useId, type ReactNode } from "react";
import type { VehicleListing } from "../api/types";
import { formatPrice, formatStock } from "../format";
import { Modal } from "./Modal";
import { VehiclePhoto } from "./VehiclePhoto";
import { primaryButton } from "./buttonStyles";

type Props = {
  listing: VehicleListing;
  onClose: () => void;
  /** Hands over to the usual purchase confirmation. */
  onPurchase: (listing: VehicleListing) => void;
};

/** Everything known about one listing, opened from its card. */
export function VehicleDetailsDialog({ listing, onClose, onPurchase }: Props) {
  const inStock = listing.quantity > 0;
  const summary = [listing.category, listing.year, listing.colour]
    .filter((part) => part !== null)
    .join(" · ");
  return (
    <Modal title={`${listing.make} ${listing.model}`} onClose={onClose} wide>
      {/* First in the dialog, so opening it focuses Close rather than an action. */}
      <button
        type="button"
        aria-label="Close"
        className={closeButton}
        onClick={onClose}
      >
        <CloseIcon />
      </button>
      <div className="mt-4 overflow-hidden rounded-lg">
        <VehiclePhoto key={listing.image_url} listing={listing} />
      </div>
      <p className="mt-4 text-xs font-medium uppercase tracking-wide text-zinc-500">
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
        {!SECTION_FIELDS.some((field) => listing[field] !== null) && (
          <p className="border-t border-zinc-100 pt-4 text-sm text-zinc-500">
            No specifications yet.
          </p>
        )}
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
            ["Battery", withUnit(listing.battery_kwh, "kWh")],
            ["Power", withUnit(listing.power_bhp, "bhp")],
            ["Transmission", listing.transmission]
          ]}
        />
        <SpecSection
          title="Practicality"
          specs={[
            ["Seats", listing.seats === null ? null : String(listing.seats)],
            ["Mileage", withUnit(listing.mileage_kmpl, "km/l")],
            ["Range", withUnit(listing.range_km, "km")]
          ]}
        />
      </div>
      <div className="mt-6 flex justify-end border-t border-zinc-100 pt-4">
        <button
          type="button"
          className={primaryButton}
          onClick={() => onPurchase(listing)}
        >
          Purchase
        </button>
      </div>
    </Modal>
  );
}

/** The fields the sections below show; year and colour sit in the summary line. */
const SECTION_FIELDS = [
  "description",
  "fuel_type",
  "engine_cc",
  "battery_kwh",
  "power_bhp",
  "transmission",
  "seats",
  "mileage_kmpl",
  "range_km"
] as const satisfies readonly (keyof VehicleListing)[];

const withUnit = (value: number | string | null, unit: string) =>
  value === null ? null : `${value} ${unit}`;

/** A titled region of the dialog, announced by its heading. */
function Section({ title, children }: { title: string; children: ReactNode }) {
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

const closeButton =
  "absolute right-4 top-4 rounded-md p-1.5 text-zinc-400 transition-colors hover:bg-zinc-100 hover:text-zinc-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900";

/** Decorative "×"; the button carries the accessible name. */
function CloseIcon() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 16 16"
      className="h-4 w-4"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
    >
      <path d="M4 4l8 8M12 4l-8 8" />
    </svg>
  );
}
