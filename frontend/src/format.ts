const inr = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR"
});

/** Format an exact decimal INR string (ADR 0010) with Indian digit grouping. */
export function formatPrice(price: string): string {
  return inr.format(Number(price));
}

const dateTime = new Intl.DateTimeFormat("en-IN", {
  dateStyle: "medium",
  timeStyle: "short"
});

/** Format an ISO timestamp in the viewer's time zone, e.g. "24 Oct 2026, 12:00 pm". */
export function formatDateTime(timestamp: string): string {
  return dateTime.format(new Date(timestamp));
}

export function formatStock(quantity: number): string {
  return quantity > 0 ? `${quantity} in stock` : "Out of stock";
}
