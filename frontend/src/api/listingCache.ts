import type { QueryClient } from "@tanstack/react-query";
import type { ListingPage, VehicleListing } from "./types";

/** Replace one listing in every cached search page with the API's updated copy. */
export function patchCachedListing(
  queryClient: QueryClient,
  updated: VehicleListing
) {
  queryClient.setQueriesData<ListingPage>(
    { queryKey: ["vehicles", "search"] },
    (current) =>
      current
        ? {
            ...current,
            items: current.items.map((item) =>
              item.id === updated.id ? updated : item
            )
          }
        : current
  );
}
