import { setupServer } from "msw/node";

/** Shared MSW server; each test registers the API handlers it needs. */
export const server = setupServer();
