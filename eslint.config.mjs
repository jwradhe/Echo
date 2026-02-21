import js from "@eslint/js";
import globals from "globals";
import tseslint from "typescript-eslint";
import markdown from "@eslint/markdown";
import { defineConfig } from "eslint/config";

export default defineConfig([

  // Ignore generated files and deps
  {
    ignores: [
      "node_modules/**",
      "playwright-report/**",
      "test-results/**",
      "coverage/**",
      "dist/**",
      "build/**",
      "venv/**",
      ".venv/**",
      "*.min.js",
    ],
  },

  // JS / TS (Node)
  { 
    files: ["**/*.{js,mjs,cjs,ts,mts,cts}"],
    plugins: { js },
    extends: ["js/recommended"],
    languageOptions: {
      globals: {
        ...globals.browser,
        bootstrap: "readonly" }
      },
  },

  // CommonJS
  {
    files: ["**/*.js"],
    languageOptions: { sourceType: "commonjs" }
  },

  // TypeScript
  tseslint.configs.recommended,
  {
    rules: {
      "@typescript-eslint/no-unused-vars": ["error", { 
        "caughtErrorsIgnorePattern": "^_" 
      }]
    }
  },

  // Markdown (README etc.)
  {
    files: ["**/*.md"],
    plugins: { markdown },
    language: "markdown/commonmark",
    extends: ["markdown/recommended"]
  },

]);
