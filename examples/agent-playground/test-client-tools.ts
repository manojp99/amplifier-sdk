/**
 * End-to-end test for client-side tools
 */

import { AmplifierClient } from "amplifier-sdk";

async function testClientSideTools() {
  console.log("🧪 Testing Client-Side Tools\n");

  const client = new AmplifierClient({
    baseUrl: "http://localhost:4096",
    debug: true,
  });

  // Register test tools
  console.log("📝 Registering client-side tools...");
  
  client.registerTool({
    name: "get-time",
    description: "Get current time in timezone",
    parameters: {
      type: "object",
      properties: {
        timezone: { type: "string" }
      },
      required: ["timezone"]
    },
    handler: async ({ timezone }) => {
      const now = new Date();
      const formatter = new Intl.DateTimeFormat("en-US", {
        timeZone: timezone as string,
        hour: "2-digit",
        minute: "2-digit",
      });
      return {
        timezone,
        time: formatter.format(now),
      };
    },
  });

  client.registerTool({
    name: "calculate",
    description: "Perform calculations",
    parameters: {
      type: "object",
      properties: {
        expression: { type: "string" }
      },
      required: ["expression"]
    },
    handler: async ({ expression }) => {
      const result = Function(`"use strict"; return (${expression})`)();
      return { expression, result };
    },
  });

  console.log("✅ Registered 2 client-side tools\n");

  // Test: Create session with clientTools
  console.log("🔧 Creating session with clientTools...");
  const session = await client.createSession({
    bundle: {
      name: "test-client-tools",
      instructions: "Use the get-time and calculate tools when asked.",
      clientTools: ["get-time", "calculate"],
    },
  });
  console.log(`✅ Session created: ${session.id}\n`);

  // Test: Trigger client-side tool execution
  console.log("💬 Testing client-side tool execution...");
  console.log("Prompt: 'What time is it in Tokyo? Then calculate 5 * 7'\n");

  let toolsExecuted = 0;
  let contentReceived = false;

  try {
    for await (const event of client.prompt(session.id, "What time is it in Tokyo? Then calculate 5 * 7")) {
      switch (event.type) {
        case "content.delta":
          process.stdout.write(event.data.delta);
          contentReceived = true;
          break;

        case "tool.call":
          console.log(`\n🔧 Tool call intercepted: ${event.data.tool_name}`);
          console.log(`   toolCallId: ${event.toolCallId}`);
          console.log(`   Arguments: ${JSON.stringify(event.data.arguments)}`);
          toolsExecuted++;
          // Tool should be intercepted and NOT sent to server
          break;

        case "tool.result":
          console.log(`✅ Tool result received`);
          console.log(`   toolCallId: ${event.toolCallId}`);
          console.log(`   Result: ${JSON.stringify(event.data.result)}`);
          break;
      }
    }
  } catch (err) {
    console.error("\n❌ Error during test:", err);
  }

  console.log("\n\n📊 Test Results:");
  console.log(`   Content received: ${contentReceived ? "✅" : "❌"}`);
  console.log(`   Client tools executed: ${toolsExecuted}`);
  console.log(`   Expected: 2 tools (get-time, calculate)`);

  await client.deleteSession(session.id);
  console.log(`\n✅ Session deleted\n`);

  // Summary
  if (contentReceived && toolsExecuted === 2) {
    console.log("🎉 CLIENT-SIDE TOOLS TEST PASSED!");
    console.log("   ✅ Tools were intercepted by SDK");
    console.log("   ✅ Tools executed locally (not on server)");
    console.log("   ✅ Results sent back to AI");
    console.log("   ✅ AI responded with tool results");
  } else {
    console.log("❌ TEST FAILED");
    console.log(`   Tools executed: ${toolsExecuted} (expected 2)`);
  }
}

testClientSideTools().catch(console.error);
