import { useState, useEffect, useRef } from "react";
import {
  AmplifierClient,
  type BundleDefinition,
} from "amplifier-sdk";

// Pre-configured bundle with hooks, tools, and custom client-side tool
const DEMO_BUNDLE: BundleDefinition = {
  name: "demo-chat-agent",
  version: "1.0.0",
  description: "Fully loaded demo agent showcasing SDK features",
  
  // Provider
  providers: [{ module: "provider-anthropic" }],
  
  // Server-side tools
  tools: [
    { module: "tool-bash" },
    { module: "tool-filesystem" },
    { module: "tool-web" },  // Correct name!
  ],
  
  // Client-side tools (THE killer feature!)
  clientTools: ["get-browser-info", "local-storage"],
  
  // Hooks for observability
  hooks: [
    { module: "hooks-logging" },  // Plural - correct name!
  ],
  
  // Instructions
  instructions: `You are a helpful AI assistant with special powers:

🔧 SERVER-SIDE TOOLS:
- bash: Execute shell commands
- filesystem: Read/write files
- web-fetch: Fetch web content

⚡ CLIENT-SIDE TOOLS (run in browser!):
- get-browser-info: Get user's browser details
- local-storage: Save/retrieve data in browser storage

Use these tools to help users effectively. Client-side tools are special - they run directly in the user's browser with zero deployment!`,
  
  session: {
    debug: true,
    maxTurns: 20,
  },
};

function App() {
  const [logs, setLogs] = useState<string[]>([]);
  
  const addLog = (message: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs(prev => [...prev.slice(-50), `[${timestamp}] ${message}`]);
  };
  
  const [client] = useState(() => new AmplifierClient({ 
    baseUrl: "",  // Empty = use Vite proxy
    debug: true,
    
    // Observability hooks (THE feature!)
    onRequest: (info) => {
      addLog(`📤 ${info.method} ${info.url}`);
    },
    
    onResponse: (info) => {
      addLog(`📥 ${info.status} in ${info.durationMs}ms`);
    },
    
    onError: (err) => {
      addLog(`❌ ${err.code}: ${err.message}`);
    },
    
    onStateChange: (info) => {
      addLog(`🔄 ${info.from} → ${info.to}`);
    },
    
    onEvent: (event) => {
      if (event.type === "tool.call") {
        addLog(`🔧 Tool: ${event.data.tool_name}`);
      } else if (event.type === "content.start") {
        addLog(`💬 Response starting...`);
      } else if (event.type === "thinking.delta") {
        addLog(`🧠 Thinking...`);
      }
    },
  }));
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Array<{
    role: "user" | "assistant";
    content: string;
  }>>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Register custom client-side tools
  useEffect(() => {
    // Tool 1: Get browser info (demonstrates client-side tool accessing browser APIs)
    client.registerTool({
      name: "get-browser-info",
      description: "Get information about the user's browser and device",
      handler: async () => {
        return {
          userAgent: navigator.userAgent,
          language: navigator.language,
          platform: navigator.platform,
          cookiesEnabled: navigator.cookieEnabled,
          onLine: navigator.onLine,
          screenWidth: window.screen.width,
          screenHeight: window.screen.height,
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        };
      },
    });

    // Tool 2: Local storage (demonstrates client-side tool with state persistence)
    client.registerTool({
      name: "local-storage",
      description: "Save or retrieve data from browser's local storage",
      parameters: {
        type: "object",
        properties: {
          action: {
            type: "string",
            enum: ["set", "get", "clear"],
            description: "Action to perform",
          },
          key: {
            type: "string",
            description: "Storage key",
          },
          value: {
            type: "string",
            description: "Value to store (for 'set' action)",
          },
        },
        required: ["action"],
      },
      handler: async ({ action, key, value }) => {
        if (action === "set" && key && value) {
          localStorage.setItem(key as string, value as string);
          return { success: true, message: `Saved "${key}" to local storage` };
        } else if (action === "get" && key) {
          const stored = localStorage.getItem(key as string);
          return { value: stored, found: stored !== null };
        } else if (action === "clear") {
          localStorage.clear();
          return { success: true, message: "Cleared all local storage" };
        }
        return { error: "Invalid parameters" };
      },
    });
  }, [client]);

  // Auto-create session on mount
  useEffect(() => {
    const initSession = async () => {
      try {
        console.log("Creating session with demo bundle...");
        const session = await client.createSession({ bundle: DEMO_BUNDLE });
        setSessionId(session.id);
        
        // Add welcome message
        setMessages([
          {
            role: "assistant",
            content: `👋 Welcome! I'm a fully-loaded demo agent showcasing the Amplifier SDK.

I have:
✅ Server-side tools (bash, filesystem, web-fetch)
✅ Client-side tools (get-browser-info, local-storage) - these run in YOUR browser!
✅ Hooks (logging) for observability
✅ Anthropic Claude for intelligence

Try asking me to:
- "What browser am I using?" (uses client-side tool)
- "Save my name in local storage" (browser state persistence)
- "Fetch the latest from example.com" (server-side web fetch)
- "List files in the current directory" (server-side filesystem)

Ready to chat! 🚀`,
          },
        ]);
      } catch (err) {
        console.error("Failed to create session:", err);
        setMessages([
          {
            role: "assistant",
            content: `❌ Failed to initialize: ${(err as Error).message}
            
Make sure the runtime is running:
\`\`\`bash
cd amplifier-app-runtime
uv run python -m amplifier_app_runtime.cli --http --port 4096
\`\`\``,
          },
        ]);
      } finally {
        setIsInitializing(false);
      }
    };

    initSession();
  }, [client]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || !sessionId || isLoading) return;

    const userMessage = input.trim();
    setInput("");
    setIsLoading(true);

    // Add user message
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);

    // Prepare for assistant response
    let assistantContent = "";
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    try {
      // Stream response
      for await (const event of client.prompt(sessionId, userMessage)) {
        if (event.type === "content.delta") {
          assistantContent += event.data.delta as string;
          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1].content = assistantContent;
            return updated;
          });
        }
      }
    } catch (err) {
      console.error("Error:", err);
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1].content = `Error: ${(err as Error).message}`;
        return updated;
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  if (isInitializing) {
    return (
      <div className="app">
        <div className="header">
          <h1>⚡ Amplifier SDK Demo</h1>
          <div className="status">Initializing...</div>
        </div>
        <div className="chat-container">
          <div className="loading">
            <div className="spinner"></div>
            <p>Creating session with fully-loaded demo bundle...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <div className="header">
        <h1>⚡ Amplifier SDK Demo</h1>
        <div className="status">
          <span className="status-dot active"></span>
          {sessionId ? `Connected • ${sessionId.slice(0, 12)}...` : "Disconnected"}
        </div>
      </div>

      <div className="chat-container">
        <div className="messages">
          {messages.map((msg, i) => (
            <div key={i} className={`message ${msg.role}`}>
              <div className="message-role">
                {msg.role === "user" ? "You" : "AI"}
              </div>
              <div className="message-content">{msg.content}</div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        <div className="input-container">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type a message... (Enter to send, Shift+Enter for new line)"
            disabled={!sessionId || isLoading}
            rows={3}
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || !sessionId || isLoading}
          >
            {isLoading ? "Sending..." : "Send"}
          </button>
        </div>
      </div>

      <div className="info-panel">
        <h3>🎯 What's Loaded</h3>
        <ul>
          <li>✅ Provider: Anthropic Claude</li>
          <li>✅ Tools: bash, filesystem, web-fetch</li>
          <li>✅ Client Tools: get-browser-info, local-storage</li>
          <li>✅ Hooks: logging</li>
        </ul>
        <p className="hint">
          <strong>Try:</strong> "What browser am I using?"<br />
          This calls the <code>get-browser-info</code> client-side tool!
        </p>
      </div>

      <div className="log-panel">
        <div className="log-header">
          <h3>📊 SDK Observability Log</h3>
          <button onClick={() => setLogs([])}>Clear</button>
        </div>
        <div className="log-content">
          {logs.length === 0 ? (
            <div className="log-empty">Waiting for SDK activity...</div>
          ) : (
            logs.map((log, i) => (
              <div key={i} className="log-entry">{log}</div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>
    </div>
  );
}

export default App;
