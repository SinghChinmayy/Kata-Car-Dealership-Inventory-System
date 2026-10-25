import { useState } from "react";
import type { VehicleListing } from "../api/types";

const photoFrame = "aspect-[16/10] w-full bg-zinc-100";

/**
 * The listing's photo, or a placeholder of the same shape so every card lines up. A photo
 * that fails to load is replaced by the placeholder too.
 */
export function VehiclePhoto({ listing }: { listing: VehicleListing }) {
  const [failed, setFailed] = useState(false);
  if (!listing.image_url || failed) {
    return (
      <div
        role="img"
        aria-label="No photo available"
        className={`${photoFrame} flex items-center justify-center text-zinc-300`}
      >
        <CarIcon />
      </div>
    );
  }
  return (
    <img
      src={listing.image_url}
      alt={`${listing.make} ${listing.model}`}
      loading="lazy"
      decoding="async"
      onError={() => setFailed(true)}
      className={`${photoFrame} object-cover`}
    />
  );
}

/** Outline of a car for the placeholder; its frame carries the accessible name. */
function CarIcon() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 48 48"
      className="h-12 w-12"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M6 30v-5l5-9h20l7 8 4 1.5V30h-3" />
      <path d="M17 30h12" />
      <circle cx="12.5" cy="31" r="3.5" />
      <circle cx="33.5" cy="31" r="3.5" />
      <path d="M13 16v8h21" />
    </svg>
  );
}
