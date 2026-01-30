/**
 * Amplifier SDK Client for the chat app.
 *
 * Uses amplifier-app-runtime API (/v1/session/*).
 */

export interface Event {
  type: string;
  data: Record<string, unknown>;
  id?: string;
  correlationId?: string;
  sequence?: number;
  final?: boolean;
}

export interface SessionInfo {
  id: string;
  title?: string;
  state?: string;
}

export interface PromptResponse {
  content: string;
  toolCalls: ToolCall[];
  sessionId?: string;
  stopReason?: string;
}

export interface ToolCall {
  toolName: string;
  toolCallId: string;
  arguments: Record<string, unknown>;
  output?: unknown;
}

export class AmplifierClient {
  private baseUrl: string;

  constructor(baseUrl = "") {
    this.baseUrl = baseUrl;
  }

  async ping(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/v1/ping`);
      return response.ok;
    } catch {
      return false;
    }
  }

  async createSession(config: {
    bundle?: string;
    provider?: string;
    model?: string;
  } = {}): Promise<SessionInfo> {
    const body: Record<string, unknown> = {};
    
    if (config.bundle) body.bundle = config.bundle;
    if (config.provider) body.provider = config.provider;
    if (config.model) body.model = config.model;

    const response = await fetch(`${this.baseUrl}/v1/session`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to create session: ${response.status} - ${error}`);
    }

    const data = await response.json();
    return {
      id: data.session_id || data.id,
      title: "Chat Session",
      state: data.state || "ready",
    };
  }

  async deleteSession(sessionId: string): Promise<boolean> {
    const response = await fetch(`${this.baseUrl}/v1/session/${sessionId}`, {
      method: "DELETE",
    });
    return response.ok;
  }

  async *prompt(sessionId: string, content: string): AsyncGenerator<Event> {
    const response = await fetch(`${this.baseUrl}/v1/session/${sessionId}/prompt`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify({ content, stream: true }),
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to send prompt: ${response.status} - ${error}`);
    }

    if (!response.body) {
      throw new Error("No response body");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith("data:")) continue;

          const dataStr = trimmed.slice(5).trim();
          if (!dataStr) continue;

          try {
            const data = JSON.parse(dataStr);
            
            // Parse event from data
            const eventType = data.type || "";
            const eventData = data.data || {};
            
            // Map to chat app expected format
            if (eventType === "content.delta") {
              yield {
                type: "content.delta",
                data: { delta: eventData.delta || eventData.content || "" },
                final: false,
              };
            } else if (eventType === "content.end") {
              // Server sends full content in content.end - emit as delta for the UI
              const content = eventData.content as string;
              if (content) {
                yield {
                  type: "content.delta",
                  data: { delta: content },
                  final: false,
                };
              }
              yield {
                type: "content.end",
                data: eventData,
                final: true,
              };
            } else if (eventType === "tool.call") {
              yield {
                type: "tool.call",
                data: {
                  toolName: eventData.tool_name || eventData.name,
                  toolCallId: eventData.tool_call_id || eventData.id,
                  arguments: eventData.arguments || eventData.input || {},
                },
                final: false,
              };
            } else if (eventType === "tool.result") {
              yield {
                type: "tool.result",
                data: {
                  toolCallId: eventData.tool_call_id || eventData.id,
                  output: eventData.output || eventData.result,
                },
                final: false,
              };
            } else if (eventType === "error") {
              yield {
                type: "error",
                data: { message: eventData.message || eventData.error || "Unknown error" },
                final: true,
              };
            } else {
              // Pass through other events
              yield {
                type: eventType,
                data: eventData,
                final: data.final || false,
              };
            }
          } catch {
            // Skip invalid JSON
          }
        }
      }

      // Send final event
      yield {
        type: "content.end",
        data: {},
        final: true,
      };
    } finally {
      reader.releaseLock();
    }
  }

  async promptSync(sessionId: string, content: string): Promise<PromptResponse> {
    const response = await fetch(`${this.baseUrl}/v1/session/${sessionId}/prompt/sync`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to send prompt: ${response.status} - ${error}`);
    }

    const data = await response.json();
    return {
      content: data.content || "",
      toolCalls: (data.tool_calls || []).map((tc: Record<string, unknown>) => ({
        toolName: tc.tool_name as string,
        toolCallId: tc.tool_call_id as string,
        arguments: tc.arguments as Record<string, unknown>,
        output: tc.output,
      })),
      sessionId: sessionId,
      stopReason: data.stop_reason,
    };
  }
}

export const client = new AmplifierClient();
