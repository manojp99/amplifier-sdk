/**
 * Amplifier SDK - TypeScript client for amplifier-app-runtime.
 *
 * @example Basic usage:
 * ```typescript
 * import { AmplifierClient } from "amplifier-sdk";
 *
 * const client = new AmplifierClient();
 *
 * // Create session and stream response
 * const session = await client.createSession({ bundle: "foundation" });
 * for await (const event of client.prompt(session.id, "Hello!")) {
 *   if (event.type === "content.delta") {
 *     process.stdout.write(event.data.delta as string);
 *   }
 * }
 * ```
 *
 * @example With observability hooks:
 * ```typescript
 * import { AmplifierClient, ConnectionState } from "amplifier-sdk";
 *
 * const client = new AmplifierClient({
 *   debug: true,
 *   onRequest: (req) => console.log(`[${req.requestId}] ${req.method} ${req.url}`),
 *   onResponse: (res) => console.log(`[${res.requestId}] ${res.status} in ${res.durationMs}ms`),
 *   onError: (err) => console.error(`[${err.code}] ${err.message}`),
 *   onStateChange: (info) => updateUI(info.to),
 *   onEvent: (event) => logEvent(event),
 * });
 * ```
 *
 * @packageDocumentation
 */

// Client
export { AmplifierClient, run } from "./client";

// Error handling
export { AmplifierError, ErrorCode } from "./types";

// Connection state
export { ConnectionState } from "./types";

// Event types
export { EventType } from "./types";

// Type definitions
export type {
  // Core types
  ApprovalRequest,
  Capabilities,
  ClientConfig,
  Event,
  PromptResponse,
  SessionConfig,
  SessionInfo,
  ToolCall,
  // Bundle definition
  BundleDefinition,
  ModuleConfig,
  AgentConfig,
  // Observability types
  RequestInfo,
  ResponseInfo,
  StateChangeInfo,
} from "./types";
