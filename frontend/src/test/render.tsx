import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { screen } from "@testing-library/react";
import type { User } from "../api/types";
import { signedInAs } from "./handlers";
import { server } from "./server";
import App from "../App";
import { AuthProvider } from "../auth/AuthContext";

/** Render the whole app at a route with fresh query, auth, and router state. */
export function renderApp(path = "/") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
  });
  const user = userEvent.setup();
  const view = render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
  return { user, ...view };
}

/** Sign in through the real form as the given account and wait for the dashboard. */
export async function renderSignedIn(account: User) {
  server.use(...signedInAs(account));
  const view = renderApp("/login");
  await view.user.type(screen.getByLabelText(/email/i), account.email);
  await view.user.type(screen.getByLabelText(/password/i), "valid-password");
  await view.user.click(screen.getByRole("button", { name: /sign in/i }));
  await screen.findByRole("button", { name: /log out/i });
  return view;
}
