/** Small dark "CD" square used as the logo mark; decorative, the name is always next to it. */
export function BrandMark({ size = "sm" }: { size?: "sm" | "lg" }) {
  const dimensions = size === "lg" ? "h-10 w-10 text-sm" : "h-7 w-7 text-xs";
  return (
    <span
      aria-hidden="true"
      className={`grid shrink-0 place-items-center rounded-md bg-zinc-900 font-bold text-white ${dimensions}`}
    >
      CD
    </span>
  );
}
