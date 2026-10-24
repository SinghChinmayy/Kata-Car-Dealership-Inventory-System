import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

export const emptyPage = { items: [], total: 0, page: 1, page_size: 20 };

export const categories = [
  "Sedan",
  "SUV",
  "Hatchback",
  "Truck",
  "Coupe",
  "Convertible",
  "Van"
];

/**
 * Shared MSW server. The defaults answer the dashboard's background reads so tests only
 * register the handlers their behavior is about; resetHandlers() restores these.
 */
export const server = setupServer(
  http.get("*/api/vehicles/search", () => HttpResponse.json(emptyPage)),
  http.get("*/api/vehicles/categories", () =>
    HttpResponse.json({ items: categories })
  )
);
