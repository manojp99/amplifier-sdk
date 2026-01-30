import { useState, useEffect, useRef, useCallback } from "react";
import {
  AmplifierClient,
  type Event,
  type BundleDefinition,
  ConnectionState,
} from "amplifier-sdk";

// Available tools that can be selected
const AVAILABLE_TOOLS = [
  { id: "tool-filesystem", name: "Filesystem", icon: "📁" },
  { id: "tool-bash", name: "Bash", icon: "💻" },
  { id: "tool-web", name: "Web Search", icon: "🔍" },
  { id: "tool-web-fetch", name: "Web Fetch", icon: "🌐" },
];

// Preset agent configurations
const PRESETS: Record<string, AgentConfig> = {
  assistant: {
    name: "helpful-assistant",
    instructions: "You are a helpful, friendly assistant. Answer questions clearly and concisely.",
    tools: [],
  },
  coder: {
    name: "coding-assistant",
    instructions: `You are an expert coding assistant. Help users with:
- Writing and debugging code
- Explaining programming concepts
- Code reviews and best practices
- Architecture decisions

Be concise but thorough. Show code examples when helpful.`,
    tools: ["tool-filesystem", "tool-bash"],
  },
  researcher: {
    name: "research-assistant", 
    instructions: `You are a research assistant. Help users by:
- Searching for information online
- Summarizing findings
- Providing citations and sources
- Comparing different perspectives

Always cite your sources and be objective.`,
    tools: ["tool-web", "tool-web-fetch"],
  },
  tutor: {
    name: "coding-tutor",
    instructions: `You are a patient coding tutor. Your approach:
- Use simple analogies to explain complex concepts
- Ask guiding questions rather than giving direct answers
- Celebrate progress and encourage experimentation
- Break problems into smaller, manageable steps

Adapt your teaching style to the student's level.`,
    tools: [],
  },
};

interface AgentConfig {
  name: string;
  instructions: string;
  tools: string[];
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolCalls?: { name: string; args: string }[];
  isStreaming?: boolean;
}

// Initialize client with observability
const client = new AmplifierClient({
  baseUrl: "",
  debug: true,
  onStateChange: (info) => {
    console.log(`[Connection] ${info.from} -> ${info.to}`);
  },
  onError: (err) => {
    console.error(`[Error] ${err.code}: ${err.message}`);
  },
});

function App() {
  // Config state
  const [config, setConfig] = useState<AgentConfig>(PRESETS.assistant);
  const [appliedConfig, setAppliedConfig] = useState<AgentConfig | null>(null);

  // Session state
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isCreatingSession, setIsCreatingSession] = useState(false);

  // Chat state
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Check if config has changed from applied
  const configChanged = appliedConfig && (
    config.name !== appliedConfig.name ||
    config.instructions !== appliedConfig.instructions ||
    JSON.stringify(config.tools) !== JSON.stringify(appliedConfig.tools)
  );

  // Auto-scroll
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Check connection on mount
  useEffect(() => {
    client.ping().then(setIsConnected);
  }, []);

  // Create/recreate session with current config
  const applyConfig = async () => {
    setIsCreatingSession(true);

    try {
      // Delete old session if exists
      if (sessionId) {
        await client.deleteSession(sessionId);
      }

      // Create bundle definition from config
      const bundle: BundleDefinition = {
        name: config.name,
        instructions: config.instructions,
        tools: config.tools.map((t) => ({ module: t })),
      };

      // Create new session with runtime bundle
      const session = await client.createSession({ bundle });

      setSessionId(session.id);
      setAppliedConfig({ ...config });
      setMessages([]);
      setIsConnected(true);

      console.log(`[Session] Created ${session.id} with bundle:`, bundle);
    } catch (err) {
      console.error("Failed to create session:", err);
      setIsConnected(false);
    } finally {
      setIsCreatingSession(false);
    }
  };

  // Send message
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
      for await (const event of client.prompt(sessionId, userMessage.content)) {
        handleEvent(event, assistantId);
      }

      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId ? { ...m, isStreaming: false } : m
        )
      );
    } catch (err) {
      console.error("Prompt error:", err);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: m.content || "Error: Failed to get response", isStreaming: false }
            : m
        )
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleEvent = (event: Event, messageId: string) => {
    switch (event.type) {
      case "content.delta":
        setMessages((prev) =>
          prev.map((m) =>
            m.id === messageId
              ? { ...m, content: m.content + ((event.data.delta as string) || "") }
              : m
          )
        );
        break;

      case "tool.call":
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

      default:
        if (!["content.end", "content.start", "ack", "result"].includes(event.type)) {
          console.log("Event:", event.type, event.data);
        }
    }
  };

  const loadPreset = (presetName: string) => {
    const preset = PRESETS[presetName];
    if (preset) {
      setConfig({ ...preset });
    }
  };

  const toggleTool = (toolId: string) => {
    setConfig((prev) => ({
      ...prev,
      tools: prev.tools.includes(toolId)
        ? prev.tools.filter((t) => t !== toolId)
        : [...prev.tools, toolId],
    }));
  };

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <h1>Agent Playground</h1>
        <div className={`connection-status ${isConnected ? "connected" : "disconnected"}`}>
          <span className="status-dot" />
          {isConnected ? "Connected" : "Disconnected"}
        </div>
      </header>

      {/* Config Panel */}
      <aside className="config-panel">
        <div className="config-section">
          <h3>Presets</h3>
          <div className="presets-row">
            {Object.keys(PRESETS).map((name) => (
              <button
                key={name}
                className="preset-btn"
                onClick={() => loadPreset(name)}
              >
                {name}
              </button>
            ))}
          </div>
        </div>

        <div className="config-section">
          <h3>Agent Name</h3>
          <input
            type="text"
            className="config-input"
            value={config.name}
            onChange={(e) => setConfig((prev) => ({ ...prev, name: e.target.value }))}
            placeholder="my-agent"
          />
        </div>

        <div className="config-section">
          <h3>Instructions</h3>
          <textarea
            className="config-input config-textarea"
            value={config.instructions}
            onChange={(e) => setConfig((prev) => ({ ...prev, instructions: e.target.value }))}
            placeholder="You are a helpful assistant..."
          />
        </div>

        <div className="config-section">
          <h3>Tools</h3>
          <div className="tools-grid">
            {AVAILABLE_TOOLS.map((tool) => (
              <label
                key={tool.id}
                className={`tool-checkbox ${config.tools.includes(tool.id) ? "selected" : ""}`}
              >
                <input
                  type="checkbox"
                  checked={config.tools.includes(tool.id)}
                  onChange={() => toggleTool(tool.id)}
                />
                <span className="tool-icon">{tool.icon}</span>
                {tool.name}
              </label>
            ))}
          </div>
        </div>

        {configChanged && (
          <div className="config-changed">
            ⚠️ Config changed - click Apply to update agent
          </div>
        )}

        <div className="config-actions">
          <button
            className="btn btn-primary"
            onClick={applyConfig}
            disabled={isCreatingSession}
          >
            {isCreatingSession
              ? "Creating..."
              : sessionId
              ? "Apply Changes"
              : "Create Agent"}
          </button>
          {sessionId && (
            <button
              className="btn btn-secondary"
              onClick={() => {
                setMessages([]);
              }}
            >
              Clear Chat
            </button>
          )}
        </div>
      </aside>

      {/* Chat Panel */}
      <main className="chat-panel">
        {sessionId ? (
          <>
            <div className="chat-header">
              <div className="agent-info">
                <div className="agent-avatar">🤖</div>
                <div>
                  <div className="agent-name">{appliedConfig?.name || config.name}</div>
                  <div className="agent-status">
                    {appliedConfig?.tools.length || 0} tools enabled
                  </div>
                </div>
              </div>
              <div className="session-badge">{sessionId.slice(0, 12)}...</div>
            </div>

            <div className="messages">
              {messages.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-state-icon">💬</div>
                  <h2>Start a conversation</h2>
                  <p>Send a message to test your agent configuration</p>
                </div>
              ) : (
                messages.map((message) => (
                  <div key={message.id} className={`message ${message.role}`}>
                    <div className="message-avatar">
                      {message.role === "user" ? "👤" : "🤖"}
                    </div>
                    <div>
                      <div className="message-content">
                        {message.content || (message.isStreaming && <LoadingDots />)}
                      </div>
                      {message.toolCalls?.map((tool, i) => (
                        <div key={i} className="tool-call">
                          <div className="tool-call-header">🔧 {tool.name}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="input-area">
              <form className="input-form" onSubmit={handleSubmit}>
                <input
                  type="text"
                  className="input-field"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Type a message..."
                  disabled={isLoading}
                />
                <button
                  type="submit"
                  className="send-btn"
                  disabled={isLoading || !input.trim()}
                >
                  {isLoading ? "..." : "Send"}
                </button>
              </form>
            </div>
          </>
        ) : (
          <div className="empty-state">
            <div className="empty-state-icon">⚡</div>
            <h2>Configure your agent</h2>
            <p>
              Set up your agent's name, instructions, and tools, then click
              "Create Agent" to start chatting.
            </p>
          </div>
        )}
      </main>
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
