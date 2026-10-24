import { useQuery } from "@tanstack/react-query";
import type { ListingPage } from "../api/types";
import { useApi } from "../api/useApi";
import { AppHeader } from "../components/AppHeader";
import { VehicleCard } from "../components/VehicleCard";

export function DashboardPage() {
  const api = useApi();
  const listings = useQuery({
    queryKey: ["vehicles", "search"],
    queryFn: () => api<ListingPage>("/api/vehicles/search")
  });

  return (
    <div className="min-h-screen">
      <AppHeader />
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <h2 className="text-2xl font-semibold text-white">
          Available vehicles
        </h2>
        {listings.isPending && (
          <p className="mt-6 text-slate-400">Loading vehicles…</p>
        )}
        {listings.data && listings.data.items.length === 0 && (
          <p className="mt-6 rounded-xl border border-dashed border-slate-700 p-8 text-center text-slate-400">
            No vehicles match your search.
          </p>
        )}
        {listings.data && listings.data.items.length > 0 && (
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {listings.data.items.map((listing) => (
              <VehicleCard key={listing.id} listing={listing} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
