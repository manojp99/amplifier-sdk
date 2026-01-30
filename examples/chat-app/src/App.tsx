import { useState, useEffect, useRef, useCallback } from "react";
import { AmplifierClient, type Event } from "amplifier-sdk";

// Use empty baseUrl to leverage vite's proxy (see vite.config.ts)
const client = new AmplifierClient({ baseUrl: "" });

interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  toolCalls?: { name: string; args: string }[];
  isStreaming?: boolean;
}

function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Initialize session on mount
  useEffect(() => {
    const init = async () => {
      try {
        console.log("Checking server health...");
        // Check server health
        const healthy = await client.ping();
        console.log("Server healthy:", healthy);
        if (!healthy) {
          setError("Server not available. Make sure amplifier-app-runtime is running on port 4096.");
          return;
        }

        // Create session
        console.log("Creating session...");
        const session = await client.createSession({ bundle: "foundation" });
        console.log("Session created:", session);
        setSessionId(session.id);
        setIsConnected(true);
        
        setMessages([
          {
            id: "welcome",
            role: "system",
            content: `Connected to Amplifier! Session: ${session.id.slice(0, 8)}...`,
          },
        ]);
      } catch (err) {
        console.error("Connection error:", err);
        setError(`Failed to connect: ${err instanceof Error ? err.message : String(err)}`);
      }
    };

    init();

    // Cleanup on unmount
    return () => {
      if (sessionId) {
        client.deleteSession(sessionId).catch(console.error);
      }
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !sessionId || isLoading) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: input.trim(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);
    setError(null);

    // Create assistant message placeholder for streaming
    const assistantId = `assistant-${Date.now()}`;
    const assistantMessage: Message = {
      id: assistantId,
      role: "assistant",
      content: "",
      toolCalls: [],
      isStreaming: true,
    };
    setMessages((prev) => [...prev, assistantMessage]);

    try {
      // Stream the response
      for await (const event of client.prompt(sessionId, userMessage.content)) {
        handleEvent(event, assistantId);
      }

      // Mark streaming as complete
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId ? { ...m, isStreaming: false } : m
        )
      );
    } catch (err) {
      setError(`Error: ${err instanceof Error ? err.message : "Unknown error"}`);
      // Remove the empty assistant message on error
      setMessages((prev) => prev.filter((m) => m.id !== assistantId || m.content));
    } finally {
      setIsLoading(false);
    }
  };

  const handleEvent = (event: Event, messageId: string) => {
    switch (event.type) {
      case "content.delta":
        // Append content delta
        setMessages((prev) =>
          prev.map((m) =>
            m.id === messageId
              ? { ...m, content: m.content + (event.data.delta as string || "") }
              : m
          )
        );
        break;

      case "thinking.delta":
        // Could show thinking indicator
        console.log("Thinking:", event.data.delta);
        break;

      case "tool.call":
        // Add tool call info
        setMessages((prev) =>
          prev.map((m) =>
            m.id === messageId
              ? {
                  ...m,
                  toolCalls: [
                    ...(m.toolCalls || []),
                    {
                      name: event.data.tool_name as string,
                      args: JSON.stringify(event.data.arguments || {}, null, 2),
                    },
                  ],
                }
              : m
          )
        );
        break;

      case "tool.result":
        console.log("Tool result:", event.data);
        break;

      case "error":
        setError(`Agent error: ${event.data.error || event.data.message || "Unknown"}`);
        break;

      default:
        // Log other events for debugging
        if (event.type !== "content.end" && event.type !== "ack") {
          console.log("Event:", event.type, event.data);
        }
    }
  };

  return (
    <div className="app">
      <header className="header">
        <h1>Amplifier Chat</h1>
        <span className={`session-info ${isConnected ? "connected" : ""}`}>
          {isConnected ? `● Connected` : "○ Disconnected"}
        </span>
      </header>

      <div className="messages">
        {error && <div className="error">{error}</div>}
        
        {messages.map((message) => (
          <div key={message.id} className={`message ${message.role}`}>
            <span className="message-role">{message.role}</span>
            <div className="message-content">
              {message.content || (message.isStreaming && <LoadingDots />)}
            </div>
            {message.toolCalls?.map((tool, i) => (
              <div key={i} className="tool-call">
                <div className="tool-call-header">{tool.name}</div>
              </div>
            ))}
          </div>
        ))}
        
        <div ref={messagesEndRef} />
      </div>

      <div className="input-area">
        <form className="input-form" onSubmit={handleSubmit}>
          <input
            type="text"
            className="input-field"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={isConnected ? "Type your message..." : "Connecting..."}
            disabled={!isConnected || isLoading}
          />
          <button
            type="submit"
            className="send-button"
            disabled={!isConnected || isLoading || !input.trim()}
          >
            {isLoading ? "..." : "Send"}
          </button>
        </form>
      </div>
    </div>
  );
}

function LoadingDots() {
  return (
    <div className="loading-dots">
      <span></span>
      <span></span>
      <span></span>
    </div>
  );
}

export default App;
