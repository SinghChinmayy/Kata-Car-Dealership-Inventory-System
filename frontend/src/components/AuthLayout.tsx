import type { ReactNode } from "react";
import { BrandMark } from "./BrandMark";

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
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center text-center">
          <BrandMark size="lg" />
          <h1 className="mt-4 text-xl font-semibold tracking-tight text-zinc-900">
            Car Dealership Inventory
          </h1>
        </div>
        <section className="mt-8 rounded-xl border border-zinc-200 bg-white p-6 shadow-sm sm:p-8">
          <h2 className="text-base font-semibold text-zinc-900">{title}</h2>
          {children}
        </section>
      </div>
    </main>
  );
}
