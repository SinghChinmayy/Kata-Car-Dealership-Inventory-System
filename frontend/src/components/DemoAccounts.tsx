import { useId } from "react";
import { secondaryButton } from "./buttonStyles";

type DemoAccount = { role: string; email: string; password: string };

/** Published demo logins, set at build time; none are shown when they are unset. */
function demoAccounts(): DemoAccount[] {
  const env = import.meta.env;
  const accounts = [
    {
      role: "admin",
      email: env.VITE_DEMO_ADMIN_EMAIL,
      password: env.VITE_DEMO_ADMIN_PASSWORD
    },
    {
      role: "buyer",
      email: env.VITE_DEMO_BUYER_EMAIL,
      password: env.VITE_DEMO_BUYER_PASSWORD
    }
  ];
  return accounts.filter(
    (account): account is DemoAccount =>
      Boolean(account.email) && Boolean(account.password)
  );
}

export function DemoAccounts({
  onUse
}: {
  onUse: (email: string, password: string) => void;
}) {
  const headingId = useId();
  const accounts = demoAccounts();
  if (accounts.length === 0) return null;

  return (
    <section
      aria-labelledby={headingId}
      className="mt-6 rounded-lg border border-zinc-200 bg-zinc-50 p-4"
    >
      <h3 id={headingId} className="text-sm font-semibold text-zinc-900">
        Demo accounts
      </h3>
      <p className="mt-1 text-xs text-zinc-500">
        Shared for testing; anyone can use them, and the demo data is reset from
        time to time.
      </p>
      <ul className="mt-3 space-y-3">
        {accounts.map((account) => (
          <li key={account.role} className="space-y-2">
            {/* Full width and wrapping: testers must be able to read every character. */}
            <dl className="text-xs">
              <dt className="font-medium capitalize text-zinc-900">
                {account.role}
              </dt>
              <dd className="break-all text-zinc-600">{account.email}</dd>
              <dd className="break-all font-mono text-zinc-600">
                {account.password}
              </dd>
            </dl>
            <button
              type="button"
              className={`${secondaryButton} w-full`}
              onClick={() => onUse(account.email, account.password)}
            >
              Use demo {account.role}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
