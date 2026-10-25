import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import type { PurchasePage } from "../api/types";
import { useApi } from "../api/useApi";
import { AppHeader } from "../components/AppHeader";
import { textLink } from "../components/buttonStyles";
import { formatDateTime, formatPrice } from "../format";

export function PurchasesPage() {
  const api = useApi();
  const purchases = useQuery({
    queryKey: ["purchases", "me"],
    queryFn: () => api<PurchasePage>("/api/purchases/me")
  });

  return (
    <div className="min-h-screen">
      <AppHeader />
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <h2 className="text-xl font-semibold tracking-tight text-zinc-900">
          My purchases
        </h2>
        <p className="mt-0.5 text-sm text-zinc-500">
          {purchases.data
            ? `${purchases.data.total} ${purchases.data.total === 1 ? "purchase" : "purchases"}`
            : "\u00a0"}
        </p>
        {purchases.isPending && (
          <p className="mt-6 text-sm text-zinc-500">Loading purchases…</p>
        )}
        {purchases.data && purchases.data.items.length === 0 && (
          <div className="mt-6 rounded-xl border border-dashed border-zinc-300 bg-white px-6 py-12 text-center text-sm text-zinc-500">
            <p>You haven't bought any vehicles yet.</p>
            <p className="mt-2">
              <Link to="/" className={textLink}>
                Browse inventory
              </Link>
            </p>
          </div>
        )}
        {purchases.data && purchases.data.items.length > 0 && (
          <ul
            aria-label="Purchases"
            className="mt-6 divide-y divide-zinc-200 rounded-xl border border-zinc-200 bg-white"
          >
            {purchases.data.items.map((purchase) => (
              <li
                key={purchase.id}
                className="flex flex-wrap items-end justify-between gap-x-6 gap-y-2 px-5 py-4"
              >
                <div className="min-w-0">
                  <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">
                    {purchase.category}
                  </p>
                  <h3 className="mt-1 text-base font-semibold text-zinc-900">
                    {purchase.make} {purchase.model}
                  </h3>
                </div>
                <div className="sm:text-right">
                  <p className="text-base font-semibold tabular-nums text-zinc-900">
                    {formatPrice(purchase.price)}
                  </p>
                  <p className="mt-0.5 text-sm text-zinc-500">
                    <time dateTime={purchase.purchased_at}>
                      {formatDateTime(purchase.purchased_at)}
                    </time>
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </main>
    </div>
  );
}
