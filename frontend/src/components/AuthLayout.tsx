import type { ReactNode } from "react";

/** Centered card shared by the sign-in and registration screens. */
export function AuthLayout({
  title,
  children
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <h1 className="text-center text-3xl font-semibold tracking-tight text-white">
          Car Dealership Inventory
        </h1>
        <section className="mt-8 rounded-2xl border border-slate-800 bg-slate-900/80 p-8 shadow-xl">
          <h2 className="text-xl font-medium text-slate-100">{title}</h2>
          {children}
        </section>
      </div>
    </main>
  );
}
