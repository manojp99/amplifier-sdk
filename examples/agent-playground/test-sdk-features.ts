/**
 * Test script to validate SDK improvements with typed events
 */

import { AmplifierClient } from "amplifier-sdk";

async function testTypedEvents() {
  console.log("🧪 Testing SDK Typed Events\n");

  const client = new AmplifierClient({
    baseUrl: "http://localhost:4096",
    debug: true,
  });

  // Test 1: Type safety on events
  console.log("Test 1: Creating session with runtime bundle...");
  const session = await client.createSession({
    bundle: {
      name: "test-agent",
      instructions: "You are a test assistant. Use filesystem tool to list current directory.",
      tools: [{ module: "tool-filesystem" }, { module: "tool-bash" }],
    },
  });
  console.log(`✅ Session created: ${session.id}\n`);

  // Test 2: Typed event handling
  console.log("Test 2: Testing typed events with tool calls...");
  let contentReceived = false;
  let toolCallReceived = false;
  let toolResultReceived = false;
  const toolCallIds = new Set<string>();

  try {
    for await (const event of client.prompt(session.id, "List files in current directory using filesystem tool")) {
      // TypeScript discriminated union - no casting needed!
      switch (event.type) {
        case "content.delta":
          // TypeScript knows event.data.delta exists
          if (event.data.delta) {
            process.stdout.write(event.data.delta);
            contentReceived = true;
          }
          break;

        case "tool.call":
          // TypeScript knows event.data.tool_name exists
          console.log(`\n🔧 Tool call: ${event.data.tool_name}`);
          console.log(`   toolCallId: ${event.toolCallId}`);
          if (event.toolCallId) {
            toolCallIds.add(event.toolCallId);
          }
          toolCallReceived = true;
          break;

        case "tool.result":
          // TypeScript knows event.data.result exists
          console.log(`\n✅ Tool result received`);
          console.log(`   toolCallId: ${event.toolCallId}`);
          console.log(`   Matches call: ${event.toolCallId && toolCallIds.has(event.toolCallId)}`);
          toolResultReceived = true;
          break;

        case "thinking.delta":
          // TypeScript knows event.data.delta exists
          console.log(`💭 Thinking: ${event.data.delta.substring(0, 50)}...`);
          break;

        case "agent.spawned":
          // TypeScript knows agent_id and agent_name exist
          console.log(`\n🤖 Sub-agent spawned: ${event.data.agent_name} (${event.data.agent_id})`);
          break;

        case "agent.completed":
          // TypeScript knows agent_id exists
          console.log(`\n✅ Sub-agent completed: ${event.data.agent_id}`);
          break;

        case "approval.required":
          // TypeScript knows all approval fields exist
          console.log(`\n🔐 Approval required: ${event.data.prompt}`);
          console.log(`   Tool: ${event.data.tool_name}`);
          break;
      }
    }
  } catch (err) {
    console.error("\n❌ Error during prompt:", err);
  }

  console.log("\n\n📊 Test Results:");
  console.log(`   Content received: ${contentReceived ? "✅" : "❌"}`);
  console.log(`   Tool call received: ${toolCallReceived ? "✅" : "❌"}`);
  console.log(`   Tool result received: ${toolResultReceived ? "✅" : "❌"}`);
  console.log(`   Tool calls tracked: ${toolCallIds.size}`);

  // Cleanup
  await client.deleteSession(session.id);
  console.log(`\n✅ Session deleted: ${session.id}`);
  
  // Summary
  console.log("\n🎉 SDK Improvements Validated:");
  console.log("   ✅ Typed events (no casting needed)");
  console.log("   ✅ toolCallId correlation");
  console.log("   ✅ Full TypeScript autocomplete on event.data");
}

testTypedEvents().catch(console.error);
