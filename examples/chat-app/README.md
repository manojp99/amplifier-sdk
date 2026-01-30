# Amplifier Chat App

A simple chat UI example using the Amplifier SDK.

![Chat App Screenshot](screenshot.png)

## Features

- Real-time streaming responses
- Tool call visualization
- Session management
- Error handling
- Modern dark UI

## Prerequisites

1. **Start the Amplifier server:**
   ```bash
   cd ../../amplifier-app-runtime
   uv run python -m amplifier_app_runtime.cli --port 4096
   ```

2. **Set your API key:**
   ```bash
   export ANTHROPIC_API_KEY=your-key-here
   ```

## Quick Start

```bash
# Install dependencies
npm install

# Start the dev server
npm run dev
```

Open http://localhost:3000 in your browser.

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│  Browser (localhost:3000)                                   │
│  ┌───────────────────────────────────────────────────────┐ │
│  │                    React Chat UI                       │ │
│  │  • Messages list with streaming                        │ │
│  │  • Input form                                          │ │
│  │  • Tool call display                                   │ │
│  └───────────────────────────────────────────────────────┘ │
│                           │                                 │
│                           │ HTTP + SSE                      │
│                           ▼                                 │
│  ┌───────────────────────────────────────────────────────┐ │
│  │              Vite Dev Server (proxy)                   │ │
│  │              /v1/* → localhost:4096                    │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  amplifier-app-runtime (localhost:4096)                     │
│  • Session management                                       │
│  • LLM integration (Anthropic, OpenAI, etc.)               │
│  • Tool execution                                           │
└─────────────────────────────────────────────────────────────┘
```

## Code Structure

```
chat-app/
├── src/
│   ├── main.tsx      # React entry point
│   ├── App.tsx       # Main chat component
│   ├── client.ts     # Amplifier SDK client
│   └── styles.css    # Dark theme styles
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## Key Components

### Client (`src/client.ts`)

The SDK client handles:
- Session creation/deletion
- Streaming prompts via SSE
- Synchronous prompts

```typescript
import { client } from "./client";

// Create session
const session = await client.createSession({ bundle: "foundation" });

// Stream response
for await (const event of client.prompt(session.id, "Hello!")) {
  if (event.type === "content.delta") {
    console.log(event.data.delta);
  }
}
```

### Event Types

| Event | Description |
|-------|-------------|
| `content.delta` | Streaming text chunk |
| `content.end` | Content complete |
| `tool.call` | Tool being invoked |
| `tool.result` | Tool finished |
| `error` | Error occurred |

## Customization

### Change the bundle

Edit `App.tsx`:
```typescript
const session = await client.createSession({ 
  bundle: "your-bundle-name",
  provider: "anthropic",
  model: "claude-sonnet-4-20250514"
});
```

### Change the server URL

Edit `vite.config.ts`:
```typescript
proxy: {
  "/v1": {
    target: "http://your-server:port",
  },
},
```

### Change the theme

Edit `src/styles.css` - the app uses CSS custom properties for easy theming.

## Production Build

```bash
npm run build
npm run preview
```

The build output will be in `dist/`.

## Troubleshooting

### "Server not available"

Make sure the amplifier-app-runtime server is running:
```bash
cd ../../amplifier-app-runtime
uv run python -m amplifier_app_runtime.cli --port 4096
```

### "Failed to create session"

Check that your API key is set:
```bash
echo $ANTHROPIC_API_KEY
```

### CORS errors

The Vite dev server proxies requests to avoid CORS. Make sure you're accessing the app at `http://localhost:3000`, not directly calling the API.

## License

MIT
