import { useAuth } from "../auth/AuthContext";
import { secondaryButton } from "./buttonStyles";

export function AppHeader() {
  const { session, logout } = useAuth();
  return (
    <header className="border-b border-slate-800 bg-slate-950/80">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-4 sm:px-6">
        <h1 className="text-xl font-semibold tracking-tight text-white">
          Car Dealership Inventory
        </h1>
        {session && (
          <div className="flex items-center gap-3 text-sm">
            <span className="text-slate-300">{session.user.email}</span>
            {session.user.role === "administrator" && (
              <span className="rounded-full bg-amber-400/15 px-2.5 py-0.5 text-xs font-medium text-amber-300">
                Administrator
              </span>
            )}
            <button
              type="button"
              className={`${secondaryButton} whitespace-nowrap py-1.5`}
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
