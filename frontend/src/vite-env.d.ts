/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Deployed backend origin for cross-origin API calls (empty in local dev). */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
