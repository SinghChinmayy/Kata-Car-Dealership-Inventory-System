// Clean light design: near-black primary, white bordered secondary, red only where destructive.
const base =
  "inline-flex h-9 items-center justify-center gap-1.5 whitespace-nowrap rounded-md px-3.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:cursor-not-allowed";

export const primaryButton = `${base} bg-zinc-900 text-white hover:bg-zinc-800 focus-visible:ring-zinc-900 disabled:bg-zinc-100 disabled:text-zinc-400`;

export const secondaryButton = `${base} border border-zinc-200 bg-white text-zinc-900 hover:bg-zinc-50 focus-visible:ring-zinc-900 disabled:bg-white disabled:text-zinc-400`;

export const dangerButton = `${base} bg-red-600 text-white hover:bg-red-700 focus-visible:ring-red-600 disabled:bg-red-300`;

/** Quiet text-style action, e.g. the admin row on a card or "Log out". */
export const textButton =
  "rounded-sm text-sm text-zinc-500 transition-colors hover:text-zinc-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-2";

export const dangerTextButton =
  "rounded-sm text-sm text-red-600 transition-colors hover:text-red-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-600 focus-visible:ring-offset-2";

export const textLink =
  "rounded-sm font-medium text-zinc-900 underline decoration-zinc-300 underline-offset-4 transition-colors hover:decoration-zinc-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-2";
