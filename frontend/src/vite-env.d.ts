/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  // Published demo logins for the sign-in page; leave unset to hide them.
  readonly VITE_DEMO_ADMIN_EMAIL?: string;
  readonly VITE_DEMO_ADMIN_PASSWORD?: string;
  readonly VITE_DEMO_BUYER_EMAIL?: string;
  readonly VITE_DEMO_BUYER_PASSWORD?: string;
}
