import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";

// Mirrors the "@/*" -> "./src/*" path alias in tsconfig.json so tests can import
// application modules the same way the application does.
export default defineConfig({
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
});