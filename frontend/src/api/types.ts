export type Role = "standard_user" | "administrator";

export type User = { id: string; email: string; role: Role };

export type TokenResponse = { access_token: string; token_type: "bearer" };

export type VehicleListing = {
  id: string;
  make: string;
  model: string;
  category: string;
  /** Exact decimal string in INR, e.g. "1250000.00" (ADR 0010). */
  price: string;
  quantity: number;
  /** Absolute http(s) photo URL, or null when the listing has none. */
  image_url: string | null;
  created_at: string;
  updated_at: string;
};

export type ListingPage = {
  items: VehicleListing[];
  total: number;
  page: number;
  page_size: number;
};
