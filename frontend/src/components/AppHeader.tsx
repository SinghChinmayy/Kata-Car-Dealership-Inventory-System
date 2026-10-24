import { useAuth } from "../auth/AuthContext";
import { BrandMark } from "./BrandMark";
import { textButton } from "./buttonStyles";

export function AppHeader() {
  const { session, logout } = useAuth();
  return (
    <header className="border-b border-zinc-200 bg-white">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-x-6 gap-y-2 px-4 py-3 sm:px-6">
        <div className="flex items-center gap-2">
          <BrandMark />
          <h1 className="text-sm font-semibold text-zinc-900">
            Car Dealership Inventory
          </h1>
        </div>
        {session && (
          <div className="flex min-w-0 items-center gap-3 text-sm">
            <span className="min-w-0 truncate text-zinc-500">
              {session.user.email}
            </span>
            {session.user.role === "administrator" && (
              <span className="shrink-0 rounded-full border border-zinc-200 px-2 py-0.5 text-xs text-zinc-600">
                Administrator
              </span>
            )}
            <button
              type="button"
              className={`${textButton} shrink-0 whitespace-nowrap`}
              onClick={logout}
            >
              Log out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
