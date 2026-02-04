#!/usr/bin/env node
/**
 * SDK Debug CLI
 * 
 * Simple script to test SDK end-to-end without browser complexity.
 */

import { AmplifierClient } from "../sdks/typescript/dist/index.mjs";

console.log("🧪 SDK Debug CLI\n");

const client = new AmplifierClient({
  baseUrl: "http://localhost:4096",
  debug: true,  // Enable debug logs
  
  // Observability hooks
  onRequest: (info) => {
    console.log(`📤 ${info.method} ${info.url}`);
  },
  
  onResponse: (info) => {
    console.log(`📥 ${info.status} in ${info.durationMs}ms`);
  },
  
  onError: (err) => {
    console.log(`❌ ${err.code}: ${err.message}`);
  },
  
  onEvent: (event) => {
    if (event.type === "tool.call") {
      console.log(`🔧 Tool call: ${event.data.tool_name}`);
      console.log(`   Args: ${JSON.stringify(event.data.arguments)}`);
    } else if (event.type === "tool.result") {
      console.log(`✅ Tool result: ${JSON.stringify(event.data.result).slice(0, 100)}`);
    } else if (event.type === "content.delta") {
      process.stdout.write(event.data.delta);
    } else if (event.type === "content.end") {
      console.log("\n");
    }
  },
});

// Register client-side tool
console.log("Registering client-side tool: get-test-data\n");
client.registerTool({
  name: "get-test-data",
  description: "Get test data (runs client-side)",
  parameters: {
    type: "object",
    properties: {
      key: { type: "string", description: "Data key to retrieve" }
    }
  },
  handler: async ({ key }) => {
    console.log(`  🎯 CLIENT-SIDE HANDLER EXECUTED! Key: ${key}`);
    return {
      success: true,
      data: `Test data for ${key}`,
      timestamp: new Date().toISOString(),
      executedIn: "client-side (Node.js process)"
    };
  }
});

// Bundle configuration
const bundle = {
  name: "cli-test-agent",
  version: "1.0.0",
  
  providers: [{ module: "provider-anthropic" }],
  
  tools: [
    { module: "tool-bash" },
    { module: "tool-filesystem" },
  ],
  
  clientTools: ["get-test-data"],  // Reference to registered tool
  
  hooks: [
    { module: "hooks-logging" },  // Correct name with 's'
  ],
  
  instructions: `You are a test agent. You have access to:
- tool-bash: Execute shell commands
- tool-filesystem: Read/write files
- get-test-data: A CLIENT-SIDE tool (runs in the client, not server)

When asked about "test data" or "client-side", use the get-test-data tool.`,
};

console.log("Creating session with bundle...\n");

try {
  const session = await client.createSession({ bundle });
  console.log(`✅ Session created: ${session.id}\n`);
  
  // Test prompt
  const prompt = "Use the get-test-data tool to retrieve data for key 'example'";
  console.log(`Prompt: "${prompt}"\n`);
  console.log("Response:\n");
  
  for await (const event of client.prompt(session.id, prompt)) {
    // Events handled by onEvent callback above
  }
  
  console.log("\n✅ Test complete!");
  
  // Cleanup
  await client.deleteSession(session.id);
  
  process.exit(0);
} catch (err) {
  console.error("\n❌ Error:", err.message);
  console.error("Details:", err);
  process.exit(1);
}
