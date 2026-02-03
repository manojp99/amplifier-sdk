/**
 * Amplifier Module Catalog
 * 
 * Hardcoded catalog of known Amplifier modules from the ecosystem.
 * Updated from: https://github.com/microsoft/amplifier/blob/main/docs/MODULES.md
 * 
 * This catalog ships with the SDK so clients can discover available modules
 * without needing a runtime API endpoint.
 * 
 * Note: This is a static catalog. New modules won't appear until SDK is updated.
 */

export interface ModuleInfo {
  /** Module identifier (e.g., "provider-anthropic") */
  id: string;
  /** Module type */
  type: "provider" | "tool" | "orchestrator" | "context" | "hook";
  /** Display name */
  name: string;
  /** Short description */
  description: string;
  /** GitHub repository URL */
  repository?: string;
}

/**
 * Provider modules - LLM backends
 */
export const PROVIDERS: ModuleInfo[] = [
  {
    id: "provider-anthropic",
    type: "provider",
    name: "Anthropic",
    description: "Claude models via Anthropic API",
    repository: "https://github.com/microsoft/amplifier-module-provider-anthropic"
  },
  {
    id: "provider-openai",
    type: "provider",
    name: "OpenAI",
    description: "GPT models via OpenAI API",
    repository: "https://github.com/microsoft/amplifier-module-provider-openai"
  },
  {
    id: "provider-azure",
    type: "provider",
    name: "Azure OpenAI",
    description: "GPT models via Azure OpenAI Service",
    repository: "https://github.com/microsoft/amplifier-module-provider-azure"
  },
  {
    id: "provider-ollama",
    type: "provider",
    name: "Ollama",
    description: "Local LLM inference via Ollama",
    repository: "https://github.com/microsoft/amplifier-module-provider-ollama"
  },
  {
    id: "provider-google",
    type: "provider",
    name: "Google Gemini",
    description: "Gemini models via Google AI API",
    repository: "https://github.com/microsoft/amplifier-module-provider-google"
  }
];

/**
 * Tool modules - Agent capabilities
 */
export const TOOLS: ModuleInfo[] = [
  {
    id: "tool-bash",
    type: "tool",
    name: "Bash",
    description: "Execute shell commands",
    repository: "https://github.com/microsoft/amplifier-module-tool-bash"
  },
  {
    id: "tool-filesystem",
    type: "tool",
    name: "Filesystem",
    description: "Read/write files and directories",
    repository: "https://github.com/microsoft/amplifier-module-tool-filesystem"
  },
  {
    id: "tool-web",
    type: "tool",
    name: "Web Search",
    description: "Search the web",
    repository: "https://github.com/microsoft/amplifier-module-tool-web"
  },
  {
    id: "tool-web-fetch",
    type: "tool",
    name: "Web Fetch",
    description: "Fetch content from URLs",
    repository: "https://github.com/microsoft/amplifier-module-tool-web-fetch"
  },
  {
    id: "tool-task",
    type: "tool",
    name: "Task",
    description: "Multi-file exploration and search",
    repository: "https://github.com/microsoft/amplifier-module-tool-task"
  },
  {
    id: "tool-delegate",
    type: "tool",
    name: "Delegate",
    description: "Spawn specialized agents",
    repository: "https://github.com/microsoft/amplifier-module-tool-delegate"
  },
  {
    id: "tool-recipes",
    type: "tool",
    name: "Recipes",
    description: "Execute multi-step workflows",
    repository: "https://github.com/microsoft/amplifier-module-tool-recipes"
  }
];

/**
 * Orchestrator modules - Execution strategies
 */
export const ORCHESTRATORS: ModuleInfo[] = [
  {
    id: "loop-basic",
    type: "orchestrator",
    name: "Basic Loop",
    description: "Simple synchronous execution loop",
    repository: "https://github.com/microsoft/amplifier-module-loop-basic"
  },
  {
    id: "loop-streaming",
    type: "orchestrator",
    name: "Streaming Loop",
    description: "Real-time streaming responses",
    repository: "https://github.com/microsoft/amplifier-module-loop-streaming"
  },
  {
    id: "loop-events",
    type: "orchestrator",
    name: "Event Loop",
    description: "Event-driven execution with rich observability",
    repository: "https://github.com/microsoft/amplifier-module-loop-events"
  }
];

/**
 * Context modules - Memory management
 */
export const CONTEXTS: ModuleInfo[] = [
  {
    id: "context-simple",
    type: "context",
    name: "Simple Context",
    description: "In-memory conversation history",
    repository: "https://github.com/microsoft/amplifier-module-context-simple"
  },
  {
    id: "context-persistent",
    type: "context",
    name: "Persistent Context",
    description: "Disk-backed conversation history",
    repository: "https://github.com/microsoft/amplifier-module-context-persistent"
  }
];

/**
 * Hook modules - Lifecycle observers
 */
export const HOOKS: ModuleInfo[] = [
  {
    id: "hook-logging",
    type: "hook",
    name: "Logging Hook",
    description: "Log all events to file/console",
    repository: "https://github.com/microsoft/amplifier-module-hook-logging"
  },
  {
    id: "hook-approval",
    type: "hook",
    name: "Approval Hook",
    description: "Request user approval for sensitive operations",
    repository: "https://github.com/microsoft/amplifier-module-hook-approval"
  },
  {
    id: "hook-shell",
    type: "hook",
    name: "Shell Hook",
    description: "Approve shell commands before execution",
    repository: "https://github.com/microsoft/amplifier-module-hook-shell"
  },
  {
    id: "hook-redaction",
    type: "hook",
    name: "Redaction Hook",
    description: "Redact sensitive information from logs",
    repository: "https://github.com/microsoft/amplifier-module-hook-redaction"
  }
];

/**
 * Complete module catalog
 */
export const MODULE_CATALOG = {
  providers: PROVIDERS,
  tools: TOOLS,
  orchestrators: ORCHESTRATORS,
  contexts: CONTEXTS,
  hooks: HOOKS
};

/**
 * Get modules by type
 */
export function getModulesByType(type: ModuleInfo["type"]): ModuleInfo[] {
  switch (type) {
    case "provider": return PROVIDERS;
    case "tool": return TOOLS;
    case "orchestrator": return ORCHESTRATORS;
    case "context": return CONTEXTS;
    case "hook": return HOOKS;
  }
}

/**
 * Find module by ID
 */
export function findModule(id: string): ModuleInfo | undefined {
  return [
    ...PROVIDERS,
    ...TOOLS,
    ...ORCHESTRATORS,
    ...CONTEXTS,
    ...HOOKS
  ].find(m => m.id === id);
}

/**
 * Get all modules
 */
export function getAllModules(): ModuleInfo[] {
  return [
    ...PROVIDERS,
    ...TOOLS,
    ...ORCHESTRATORS,
    ...CONTEXTS,
    ...HOOKS
  ];
}
