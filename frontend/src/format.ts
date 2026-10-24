const inr = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR"
});

/** Format an exact decimal INR string (ADR 0010) with Indian digit grouping. */
export function formatPrice(price: string): string {
  return inr.format(Number(price));
}

export function formatStock(quantity: number): string {
  return quantity > 0 ? `${quantity} in stock` : "Out of stock";
}
