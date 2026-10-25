export const buyer = {
  id: "7d0c3c4e-1f7c-4a8e-9a39-6a3d2b9f0001",
  email: "buyer@example.com",
  role: "standard_user" as const
};

export const administrator = {
  id: "7d0c3c4e-1f7c-4a8e-9a39-6a3d2b9f0002",
  email: "admin@example.com",
  role: "administrator" as const
};

export function listing(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: "a1b2c3d4-0000-4000-8000-000000000001",
    make: "Tata",
    model: "Nexon",
    category: "SUV",
    price: "1250000.00",
    quantity: 3,
    image_url: null,
    created_at: "2026-10-24T05:00:00Z",
    updated_at: "2026-10-24T05:00:00Z",
    ...overrides
  };
}

export function page(
  items: unknown[],
  extra: Partial<Record<string, number>> = {}
) {
  return { items, total: items.length, page: 1, page_size: 20, ...extra };
}
