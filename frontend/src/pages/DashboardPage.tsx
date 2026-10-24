import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ApiError, errorMessage, splitErrors } from "../api/client";
import { patchCachedListing } from "../api/listingCache";
import type { ListingPage, VehicleListing } from "../api/types";
import { useApi } from "../api/useApi";
import { AppHeader } from "../components/AppHeader";
import { DeleteListingDialog } from "../components/DeleteListingDialog";
import { FormAlert } from "../components/FormAlert";
import { Pagination } from "../components/Pagination";
import {
  FILTER_KEYS,
  SearchFilters,
  type Filters
} from "../components/SearchFilters";
import { RestockDialog } from "../components/RestockDialog";
import { useToast } from "../components/Toast";
import { VehicleCard, type AdminActions } from "../components/VehicleCard";
import { VehicleFormDialog } from "../components/VehicleFormDialog";
import { primaryButton } from "../components/buttonStyles";
import { useAuth } from "../auth/AuthContext";

type Dialog =
  | { kind: "add" }
  | { kind: "edit"; listing: VehicleListing }
  | { kind: "delete"; listing: VehicleListing }
  | { kind: "restock"; listing: VehicleListing };

export function DashboardPage() {
  const api = useApi();
  const queryClient = useQueryClient();
  const toast = useToast();
  const { session } = useAuth();
  const isAdmin = session?.user.role === "administrator";
  const [dialog, setDialog] = useState<Dialog | null>(null);
  // Stable so an open dialog doesn't re-run its focus effect on every render.
  const closeDialog = useCallback(() => setDialog(null), []);
  const adminActions: AdminActions = {
    onEdit: (listing) => setDialog({ kind: "edit", listing }),
    onRestock: (listing) => setDialog({ kind: "restock", listing }),
    onDelete: (listing) => setDialog({ kind: "delete", listing })
  };
  const [searchParams, setSearchParams] = useSearchParams();
  // Submitted filters live in the URL so back/forward and shared links keep them.
  const filters: Filters = Object.fromEntries(
    FILTER_KEYS.flatMap((key) => {
      const value = searchParams.get(key);
      return value ? [[key, value]] : [];
    })
  );

  const page = searchParams.get("page") ?? undefined;
  const listings = useQuery({
    queryKey: ["vehicles", "search", filters, page],
    queryFn: () =>
      api<ListingPage>("/api/vehicles/search", {
        query: { ...filters, page }
      })
  });

  function goToPage(next: number) {
    setSearchParams({ ...filters, page: String(next) });
  }
  const categories = useQuery({
    queryKey: ["vehicles", "categories"],
    queryFn: () => api<{ items: string[] }>("/api/vehicles/categories"),
    staleTime: Infinity
  });
  const { fields: searchErrors, alert: searchAlert } = splitErrors(
    listings.error,
    FILTER_KEYS
  );

  const purchase = useMutation({
    mutationFn: (listing: VehicleListing) =>
      api<VehicleListing>(`/api/vehicles/${listing.id}/purchase`, {
        method: "POST"
      }),
    onSuccess: (updated) => {
      // The response is the listing after the sale.
      patchCachedListing(queryClient, updated);
      toast(`Purchased ${updated.make} ${updated.model}`);
    },
    onError: (error) => {
      toast(errorMessage(error));
      if (error instanceof ApiError && error.status === 409) {
        void queryClient.invalidateQueries({
          queryKey: ["vehicles", "search"]
        });
      }
    }
  });

  return (
    <div className="min-h-screen">
      <AppHeader />
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold tracking-tight text-zinc-900">
              Inventory
            </h2>
            <p className="mt-0.5 text-sm text-zinc-500">
              {listings.data
                ? `${listings.data.total} ${listings.data.total === 1 ? "vehicle" : "vehicles"}`
                : "\u00a0"}
            </p>
          </div>
          {isAdmin && (
            <button
              type="button"
              className={primaryButton}
              onClick={() => setDialog({ kind: "add" })}
            >
              <PlusIcon />
              Add vehicle
            </button>
          )}
        </div>
        <SearchFilters
          key={new URLSearchParams(filters).toString()}
          initial={filters}
          categories={categories.data?.items ?? []}
          errors={searchErrors}
          onSearch={(next) => setSearchParams(next)}
        />
        {searchAlert && (
          <div className="mt-6">
            <FormAlert message={searchAlert} />
          </div>
        )}
        {listings.isPending && (
          <p className="mt-6 text-sm text-zinc-500">Loading vehicles…</p>
        )}
        {listings.data && listings.data.items.length === 0 && (
          <p className="mt-6 rounded-xl border border-dashed border-zinc-300 bg-white px-6 py-12 text-center text-sm text-zinc-500">
            No vehicles match your search.
          </p>
        )}
        {listings.data && listings.data.items.length > 0 && (
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {listings.data.items.map((listing) => (
              <VehicleCard
                key={listing.id}
                listing={listing}
                // One purchase at a time: a second click anywhere waits for the first.
                purchasing={purchase.isPending}
                onPurchase={(selected) => purchase.mutate(selected)}
                admin={isAdmin ? adminActions : undefined}
              />
            ))}
          </div>
        )}
        {listings.data && (
          <Pagination
            page={listings.data.page}
            pageSize={listings.data.page_size}
            total={listings.data.total}
            onPageChange={goToPage}
          />
        )}
      </main>
      {dialog?.kind === "restock" && (
        <RestockDialog listing={dialog.listing} onClose={closeDialog} />
      )}
      {dialog?.kind === "delete" && (
        <DeleteListingDialog listing={dialog.listing} onClose={closeDialog} />
      )}
      {(dialog?.kind === "add" || dialog?.kind === "edit") && (
        <VehicleFormDialog
          listing={dialog.kind === "edit" ? dialog.listing : undefined}
          categories={categories.data?.items ?? []}
          onClose={closeDialog}
        />
      )}
    </div>
  );
}

/** Decorative "+" for the Add vehicle button; hidden so the button's name stays "Add vehicle". */
function PlusIcon() {
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
      <path d="M8 3.5v9M3.5 8h9" />
    </svg>
  );
}
