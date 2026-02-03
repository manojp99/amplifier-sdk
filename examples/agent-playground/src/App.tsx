import { useState, useEffect, useRef, useCallback } from "react";
import {
  AmplifierClient,
  type Event,
  type BundleDefinition,
  type AgentNode,
} from "amplifier-sdk";

// Available tools that can be selected
const AVAILABLE_TOOLS = [
  { id: "tool-filesystem", name: "Filesystem", icon: "📁" },
  { id: "tool-bash", name: "Bash", icon: "💻" },
  { id: "tool-web", name: "Web Search", icon: "🔍" },
  { id: "tool-web-fetch", name: "Web Fetch", icon: "🌐" },
];

// Available providers
const AVAILABLE_PROVIDERS = [
  { id: "anthropic", name: "Anthropic", models: ["claude-sonnet-4-5-20250514", "claude-opus-4-20250514", "claude-haiku-3-5-20250307"] },
  { id: "openai", name: "OpenAI", models: ["gpt-4o", "gpt-4o-mini", "o1", "o1-mini"] },
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
  "demo-client-tools": {
    name: "demo-client-tools",
    instructions: `You are a demo assistant showing off client-side tools.

You have access to these LOCAL tools (run in the browser, not on server):
- get-time: Get current time in a specific timezone
- calculate: Perform calculations
- get-random: Get a random number in a range

Use these tools when asked to demonstrate client-side tool execution!`,
    tools: [],
    clientTools: ["get-time", "calculate", "get-random"],
  },
};

interface AgentConfig {
  name: string;
  instructions: string;
  tools: string[];
  clientTools?: string[];
  provider?: string;
  model?: string;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolCalls?: ToolCallInfo[];
  thinking?: string;
  subAgents?: SubAgentInfo[];
  isStreaming?: boolean;
}

interface ToolCallInfo {
  id?: string;  // toolCallId for correlation
  name: string;
  args: string;
  result?: string;
}

interface SubAgentInfo {
  id: string;
  name: string;
  status: "running" | "completed";
  result?: string;
}

interface PendingApproval {
  requestId: string;
  prompt: string;
  toolName?: string;
  args?: Record<string, unknown>;
}

interface AgentHierarchyState {
  nodes: Map<string, AgentNode>;
  lastUpdate: number;
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

// Register agent spawning visibility handlers
client.onAgentSpawned((info) => {
  console.log(`🤖 [Agent Spawned] ${info.agentName} (${info.agentId})`);
  if (info.parentId) {
    console.log(`   Parent: ${info.parentId}`);
  }
});

client.onAgentCompleted((info) => {
  console.log(`✅ [Agent Completed] ${info.agentId}`);
  if (info.error) {
    console.error(`   Error: ${info.error}`);
  }
});

// Register demo client-side tools
client.registerTool({
  name: "get-time",
  description: "Get current time in a specific timezone",
  parameters: {
    type: "object",
    properties: {
      timezone: { 
        type: "string",
        description: "Timezone (e.g., 'America/New_York', 'Europe/London', 'Asia/Tokyo')"
      },
    },
    required: ["timezone"],
  },
  handler: async ({ timezone }) => {
    const now = new Date();
    const formatter = new Intl.DateTimeFormat("en-US", {
      timeZone: timezone as string,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: true,
    });
    return {
      timezone,
      time: formatter.format(now),
      timestamp: now.toISOString(),
    };
  },
});

client.registerTool({
  name: "calculate",
  description: "Perform mathematical calculations",
  parameters: {
    type: "object",
    properties: {
      expression: {
        type: "string",
        description: "Math expression to evaluate (e.g., '2 + 2', '10 * 5')",
      },
    },
    required: ["expression"],
  },
  handler: async ({ expression }) => {
    try {
      // Safe eval for basic math (in real app, use math.js or similar)
      const result = Function(`"use strict"; return (${expression})`)();
      return {
        expression,
        result,
        valid: true,
      };
    } catch (error) {
      return {
        expression,
        error: (error as Error).message,
        valid: false,
      };
    }
  },
});

client.registerTool({
  name: "get-random",
  description: "Generate a random number within a range",
  parameters: {
    type: "object",
    properties: {
      min: { type: "number", description: "Minimum value" },
      max: { type: "number", description: "Maximum value" },
    },
    required: ["min", "max"],
  },
  handler: async ({ min, max }) => {
    const minNum = Number(min);
    const maxNum = Number(max);
    const random = Math.floor(Math.random() * (maxNum - minNum + 1)) + minNum;
    return {
      min: minNum,
      max: maxNum,
      result: random,
    };
  },
});

function App() {
  // Config state
  const [config, setConfig] = useState<AgentConfig>(PRESETS.assistant);
  const [appliedConfig, setAppliedConfig] = useState<AgentConfig | null>(null);
  const [customTools, setCustomTools] = useState<string[]>([]);

  // Session state
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isCreatingSession, setIsCreatingSession] = useState(false);

  // Chat state
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [pendingApproval, setPendingApproval] = useState<PendingApproval | null>(null);

  // UI state
  const [showThinking, setShowThinking] = useState(true);
  const [showSubAgents, setShowSubAgents] = useState(true);
  const [showToolResults, setShowToolResults] = useState(true);
  const [showAgentHierarchy, setShowAgentHierarchy] = useState(true);

  // Agent hierarchy state
  const [agentHierarchy, setAgentHierarchy] = useState<AgentHierarchyState>({
    nodes: new Map(),
    lastUpdate: 0,
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Check if config has changed from applied
  const configChanged = appliedConfig && (
    config.name !== appliedConfig.name ||
    config.instructions !== appliedConfig.instructions ||
    config.provider !== appliedConfig.provider ||
    config.model !== appliedConfig.model ||
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

  // Load saved configs from localStorage
  useEffect(() => {
    const saved = localStorage.getItem("agent-playground-configs");
    if (saved) {
      try {
        JSON.parse(saved);
        // Could restore last used config here
      } catch (err) {
        console.error("Failed to load saved configs:", err);
      }
    }
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
        tools: [...config.tools, ...customTools].map((t) => ({ module: t })),
      };

      // Add client-side tools if specified
      if (config.clientTools && config.clientTools.length > 0) {
        bundle.clientTools = config.clientTools;
      }

      // Add provider config if specified
      if (config.provider) {
        bundle.providers = [{ 
          module: `provider-${config.provider}`,
          config: config.model ? { model: config.model } : undefined
        }];
      }

      // Create new session with runtime bundle
      const session = await client.createSession({ bundle });

      setSessionId(session.id);
      setAppliedConfig({ ...config });
      setMessages([]);
      setIsConnected(true);

      console.log(`[Session] Created ${session.id} with bundle:`, bundle);
      
      // Save config to localStorage
      saveConfig(config);
    } catch (err) {
      console.error("Failed to create session:", err);
      setIsConnected(false);
    } finally {
      setIsCreatingSession(false);
    }
  };

  // Save configuration
  const saveConfig = (cfg: AgentConfig) => {
    const saved = JSON.parse(localStorage.getItem("agent-playground-configs") || "[]");
    const existing = saved.find((c: AgentConfig) => c.name === cfg.name);
    
    if (!existing) {
      saved.push(cfg);
      localStorage.setItem("agent-playground-configs", JSON.stringify(saved));
    }
  };

  // Export chat
  const exportChat = () => {
    const timestamp = new Date().toISOString();
    const data = {
      sessionId,
      config: appliedConfig,
      messages: messages.map(m => ({
        role: m.role,
        content: m.content,
        toolCalls: m.toolCalls,
        thinking: m.thinking,
        subAgents: m.subAgents,
      })),
      exportedAt: timestamp,
    };

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `chat-${sessionId?.slice(0, 8)}-${timestamp}.json`;
    a.click();
    URL.revokeObjectURL(url);
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
      subAgents: [],
      isStreaming: true,
    };
    setMessages((prev) => [...prev, assistantMessage]);

    try {
      for await (const event of client.prompt(sessionId, userMessage.content)) {
        handleEvent(event, assistantId);
        
        // Update hierarchy after each agent event
        if (event.type === "agent.spawned" || event.type === "agent.completed") {
          setAgentHierarchy({
            nodes: client.getAgentHierarchy(),
            lastUpdate: Date.now(),
          });
        }
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

      case "thinking.delta":
        if (showThinking) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === messageId
                ? { ...m, thinking: (m.thinking || "") + ((event.data.delta as string) || "") }
                : m
            )
          );
        }
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

      case "tool.result":
        if (showToolResults) {
          setMessages((prev) =>
            prev.map((m) => {
              if (m.id !== messageId) return m;
              const toolCalls = [...(m.toolCalls || [])];
              const lastTool = toolCalls[toolCalls.length - 1];
              if (lastTool) {
                lastTool.result = typeof event.data.result === "string" 
                  ? event.data.result 
                  : JSON.stringify(event.data.result, null, 2);
              }
              return { ...m, toolCalls };
            })
          );
        }
        break;

      case "approval.required":
        setPendingApproval({
          requestId: event.data.request_id as string,
          prompt: event.data.prompt as string,
          toolName: event.data.tool_name as string | undefined,
          args: event.data.arguments as Record<string, unknown> | undefined,
        });
        break;

      case "agent.spawned":
        if (showSubAgents) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === messageId
                ? {
                    ...m,
                    subAgents: [
                      ...(m.subAgents || []),
                      {
                        id: event.data.agent_id as string,
                        name: event.data.agent_name as string,
                        status: "running",
                      },
                    ],
                  }
                : m
            )
          );
        }
        break;

      case "agent.completed":
        if (showSubAgents) {
          setMessages((prev) =>
            prev.map((m) => {
              if (m.id !== messageId) return m;
              const subAgents = (m.subAgents || []).map((agent) =>
                agent.id === event.data.agent_id
                  ? { 
                      ...agent, 
                      status: "completed" as const,
                      result: event.data.result as string | undefined,
                    }
                  : agent
              );
              return { ...m, subAgents };
            })
          );
        }
        break;

      default:
        if (!["content.end", "content.start", "ack", "result"].includes(event.type)) {
          console.log("Event:", event.type, event.data);
        }
    }
  };

  const handleApproval = async (approve: boolean) => {
    if (!pendingApproval || !sessionId) return;

    try {
      // SDK expects string choice, convert boolean to string
      await client.respondApproval(sessionId, pendingApproval.requestId, approve.toString());
      setPendingApproval(null);
    } catch (err) {
      console.error("Failed to respond to approval:", err);
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

  const addCustomTool = () => {
    const toolName = prompt("Enter custom tool module name (e.g., 'tool-custom'):");
    if (toolName && toolName.trim()) {
      setCustomTools((prev) => [...prev, toolName.trim()]);
    }
  };

  // Render agent hierarchy tree
  const renderAgentTree = () => {
    const rootAgents = Array.from(agentHierarchy.nodes.values()).filter(
      (node) => node.parentId === null
    );

    if (rootAgents.length === 0) {
      return <div className="empty-hierarchy">No agents spawned yet</div>;
    }

    const renderNode = (node: AgentNode, depth: number = 0): JSX.Element => {
      const children = node.children
        .map((id) => agentHierarchy.nodes.get(id))
        .filter((n): n is AgentNode => n !== undefined);

      const status = node.completedAt ? "✅" : "⏳";
      const hasError = node.error ? " ❌" : "";

      return (
        <div key={node.agentId} className="hierarchy-node" style={{ marginLeft: `${depth * 20}px` }}>
          <div className={`hierarchy-node-content ${node.completedAt ? "completed" : "running"}`}>
            <span className="hierarchy-status">{status}{hasError}</span>
            <span className="hierarchy-name">{node.agentName}</span>
            <span className="hierarchy-id">({node.agentId.slice(0, 8)}...)</span>
          </div>
          {children.length > 0 && (
            <div className="hierarchy-children">
              {children.map((child) => renderNode(child, depth + 1))}
            </div>
          )}
        </div>
      );
    };

    return (
      <div className="agent-hierarchy-tree">
        {rootAgents.map((root) => renderNode(root, 0))}
      </div>
    );
  };

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <h1>Agent Playground</h1>
        <div className="header-controls">
          <label className="toggle-label">
            <input
              type="checkbox"
              checked={showThinking}
              onChange={(e) => setShowThinking(e.target.checked)}
            />
            Show Thinking
          </label>
          <label className="toggle-label">
            <input
              type="checkbox"
              checked={showSubAgents}
              onChange={(e) => setShowSubAgents(e.target.checked)}
            />
            Show Sub-agents
          </label>
          <label className="toggle-label">
            <input
              type="checkbox"
              checked={showToolResults}
              onChange={(e) => setShowToolResults(e.target.checked)}
            />
            Show Tool Results
          </label>
          <label className="toggle-label">
            <input
              type="checkbox"
              checked={showAgentHierarchy}
              onChange={(e) => setShowAgentHierarchy(e.target.checked)}
            />
            Show Agent Tree
          </label>
          <div className={`connection-status ${isConnected ? "connected" : "disconnected"}`}>
            <span className="status-dot" />
            {isConnected ? "Connected" : "Disconnected"}
          </div>
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
          <h3>Provider & Model</h3>
          <select
            className="config-input"
            value={config.provider || ""}
            onChange={(e) => setConfig((prev) => ({ ...prev, provider: e.target.value || undefined, model: undefined }))}
          >
            <option value="">Default</option>
            {AVAILABLE_PROVIDERS.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          {config.provider && (
            <select
              className="config-input"
              value={config.model || ""}
              onChange={(e) => setConfig((prev) => ({ ...prev, model: e.target.value || undefined }))}
            >
              <option value="">Default</option>
              {AVAILABLE_PROVIDERS.find(p => p.id === config.provider)?.models.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          )}
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
          {customTools.length > 0 && (
            <div className="custom-tools">
              {customTools.map((tool, i) => (
                <div key={i} className="custom-tool-item">
                  🔧 {tool}
                  <button onClick={() => setCustomTools(prev => prev.filter((_, idx) => idx !== i))}>×</button>
                </div>
              ))}
            </div>
          )}
          <button className="btn-secondary" onClick={addCustomTool} style={{ marginTop: "8px", width: "100%" }}>
            + Add Custom Tool
          </button>
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
            <>
              <button
                className="btn btn-secondary"
                onClick={() => setMessages([])}
              >
                Clear Chat
              </button>
              <button
                className="btn btn-secondary"
                onClick={exportChat}
              >
                Export
              </button>
            </>
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
                    {appliedConfig?.tools.length || 0} tools • {appliedConfig?.provider || "default provider"}
                  </div>
                </div>
              </div>
              <div className="session-badge">{sessionId.slice(0, 12)}...</div>
            </div>

            {/* Agent Hierarchy Panel */}
            {showAgentHierarchy && agentHierarchy.nodes.size > 0 && (
              <div className="agent-hierarchy-panel">
                <div className="hierarchy-header">
                  <span>🌳 Agent Delegation Tree</span>
                  <button 
                    className="btn-icon" 
                    onClick={() => {
                      client.clearAgentHierarchy();
                      setAgentHierarchy({ nodes: new Map(), lastUpdate: Date.now() });
                    }}
                    title="Clear hierarchy"
                  >
                    🗑️
                  </button>
                </div>
                {renderAgentTree()}
              </div>
            )}

            {/* Approval Modal */}
            {pendingApproval && (
              <div className="approval-overlay">
                <div className="approval-modal">
                  <h3>🔐 Approval Required</h3>
                  <p>{pendingApproval.prompt}</p>
                  {pendingApproval.toolName && (
                    <div className="approval-details">
                      <strong>Tool:</strong> {pendingApproval.toolName}
                      {pendingApproval.args && (
                        <pre>{JSON.stringify(pendingApproval.args, null, 2)}</pre>
                      )}
                    </div>
                  )}
                  <div className="approval-actions">
                    <button className="btn btn-primary" onClick={() => handleApproval(true)}>
                      ✓ Approve
                    </button>
                    <button className="btn btn-secondary" onClick={() => handleApproval(false)}>
                      ✗ Deny
                    </button>
                  </div>
                </div>
              </div>
            )}

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
                    <div className="message-body">
                      {message.thinking && showThinking && (
                        <div className="thinking-block">
                          <div className="thinking-header">💭 Thinking</div>
                          <div className="thinking-content">{message.thinking}</div>
                        </div>
                      )}
                      <div className="message-content">
                        {message.content || (message.isStreaming && <LoadingDots />)}
                      </div>
                      {message.toolCalls?.map((tool, i) => (
                        <div key={i} className="tool-call">
                          <div className="tool-call-header">🔧 {tool.name}</div>
                          {showToolResults && tool.result && (
                            <div className="tool-result">
                              <strong>Result:</strong>
                              <pre>{tool.result}</pre>
                            </div>
                          )}
                        </div>
                      ))}
                      {message.subAgents?.map((agent, i) => (
                        <div key={i} className="sub-agent">
                          <div className="sub-agent-header">
                            {agent.status === "running" ? "⏳" : "✓"} Sub-agent: {agent.name}
                          </div>
                          {agent.result && (
                            <div className="sub-agent-result">{agent.result}</div>
                          )}
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
                  disabled={isLoading || !!pendingApproval}
                />
                <button
                  type="submit"
                  className="send-btn"
                  disabled={isLoading || !input.trim() || !!pendingApproval}
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
