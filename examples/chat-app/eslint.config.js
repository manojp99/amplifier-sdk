import js from "@eslint/js";
import tseslint from "typescript-eslint";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";

/**
 * Custom rule: no-direct-api-calls
 * 
 * Enforces that all API calls go through the SDK, not directly to the runtime.
 * This ensures the app properly tests the SDK layer.
 */
const noDirectApiCalls = {
  meta: {
    type: "problem",
    docs: {
      description: "Disallow direct API calls to amplifier-app-runtime. Use the SDK instead.",
    },
    messages: {
      noDirectFetch: "Direct API call to '{{url}}' detected. Use AmplifierClient from 'amplifier-sdk' instead.",
      noV1Pattern: "URL pattern '/v1/' detected. All API calls must go through the SDK.",
    },
  },
  create(context) {
    return {
      // Check fetch() calls
      CallExpression(node) {
        if (node.callee.name !== "fetch") return;
        
        const firstArg = node.arguments[0];
        if (!firstArg) return;

        // Check string literals
        if (firstArg.type === "Literal" && typeof firstArg.value === "string") {
          const url = firstArg.value;
          if (url.includes("/v1/") || url.includes("localhost:4096")) {
            context.report({
              node,
              messageId: "noDirectFetch",
              data: { url },
            });
          }
        }

        // Check template literals
        if (firstArg.type === "TemplateLiteral") {
          const quasis = firstArg.quasis.map(q => q.value.raw).join("");
          if (quasis.includes("/v1/") || quasis.includes("localhost:4096")) {
            context.report({
              node,
              messageId: "noV1Pattern",
            });
          }
        }
      },
    };
  },
};

export default tseslint.config(
  { ignores: ["dist", "node_modules"] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2020,
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
      // Register custom plugin inline
      "amplifier": {
        rules: {
          "no-direct-api-calls": noDirectApiCalls,
        },
      },
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
      // Enable our custom rule
      "amplifier/no-direct-api-calls": "error",
    },
  }
);
