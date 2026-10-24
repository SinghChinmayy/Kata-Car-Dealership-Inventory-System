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
            <button
              type="button"
              className={`${secondaryButton} py-1.5`}
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
