# Changelog

All notable changes to the Amplifier SDK project.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-02-03

### 🎉 Major Milestone: 100% Roadmap Completion

This release completes all planned features across 4 development phases over 11 sprints.

**Total Development:**
- 11 sprints over ~5 weeks
- 273 comprehensive tests
- 14/14 roadmap features (100%)
- TypeScript + Python SDK parity

---

## Phase 4: Enterprise Features (Sprints 9-10)

### [Sprint 10] - Hooks & MCP Integration - 2026-02-03

**Added:**
- MCP (Model Context Protocol) server type system
  - `McpServerStdio` - Spawn MCP servers as child processes
  - `McpServerHttp` - Connect to HTTP MCP servers
  - `McpServerSse` - Connect to SSE streaming MCP servers
- `mcpServers` field in `BundleDefinition` and `SessionConfig`
- Hook configuration via `ModuleConfig` (module, source, config)
- Complete MCP server API documentation with examples
- Enterprise integration examples combining hooks and MCP

**Tests:** 42 new tests (20 TypeScript + 22 Python)

**TypeScript:**
- Added MCP server types to type system
- Exported MCP types in index.ts
- 20 comprehensive tests for hooks and MCP configuration

**Python:**
- Added matching MCP server types with Python idioms
- Exported MCP types in __init__.py
- 22 comprehensive tests

### [Sprint 9] - Recipes Integration - 2026-02-02

**Added:**
- Multi-step workflow orchestration via recipes
- `RecipeBuilder` and `StepBuilder` fluent APIs
- Recipe execution API (`executeRecipe`, `resumeRecipe`)
- Recipe CRUD operations (save, get, list, delete)
- `RecipeExecution` monitor with event handlers
- Approval gate handling (`onApproval`, `approveRecipeStage`, `denyRecipeStage`)
- Step-level configuration (timeout, error handling, conditions)
- Recipe progress monitoring and step events
- Complex recipe examples (code review, CI/CD, research workflows)

**Tests:** 59 new tests (31 TypeScript + 28 Python)

**TypeScript:**
- Complete recipe type system
- Recipe builder validation
- Client-side recipe storage
- Recipe exports in index.ts

**Python:**
- Matching recipe functionality with Python idioms
- Recipe builder with lambda-based step configuration
- Recipe exports in __init__.py

---

## Phase 3: Multi-Agent Workflows (Sprints 5-8)

### [Sprint 8] - Sub-Agent Configuration - 2026-01-30

**Added:**
- `AgentConfig` type for defining spawnable agents
- `agents` field in `BundleDefinition`
- Agent definition with name, description, instructions, tools
- Agent configuration serialization
- Multi-agent bundle examples

**Tests:** 18 new tests (10 TypeScript + 8 Python)

### [Sprint 7] - Client-Side Behaviors - 2026-01-28

**Added:**
- `defineBehavior()` API for reusable capability packages
- Behavior composition logic
- Instruction merging strategy (concatenation with separators)
- Tool merging strategy (deduplication)
- Behavior validation
- Example behaviors library

**Tests:** 10 new tests

**TypeScript:**
- `BehaviorDefinition` interface
- Behavior merging engine
- Client-side behavior composition

**Python:**
- Matching behavior functionality
- Python-idiomatic behavior patterns

### [Sprint 6] - Thinking Stream - 2026-01-27

**Added:**
- `onThinking()` convenience method for reasoning visibility
- Thinking stream state tracking (start/end boundaries)
- Thinking event handlers
- Enhanced playground thinking visualization

**Tests:** 8 new tests

### [Sprint 5] - Agent Spawning Visibility - 2026-01-26

**Added:**
- `onAgentSpawned()` convenience method
- `onAgentCompleted()` convenience method
- Agent hierarchy tracking with `parent_id`
- `AgentNode` type for agent metadata
- Multi-agent workflow support
- Playground agent visualization

**Tests:** 15 new tests

---

## Phase 2: Advanced Features (Sprint 2)

### [Sprint 2] - Phase 2 Features - 2026-01-20

**Added:**
- Event correlation fields (`toolCallId`, `agentId`)
- TypeScript discriminated union for typed events
- Client-side tools (`registerTool()` API)
- Automatic tool call interception
- Event handler convenience API (`on()`, `off()`, `once()`)
- Approval convenience API (`onApproval()`)
- Session resume helper (`resumeSession()`)

**Tests:** 29 new tests

**Client-Side Tools:**
- Register tools that run locally in your app
- Automatic SDK-side execution
- Zero deployment required
- Demo tools in playground (get-time, calculate, get-random)

**Event Handlers:**
- Type-safe event subscription
- Automatic handler invocation
- Support for async handlers

---

## Phase 1: Core SDK (Sprints 0-1)

### [Sprint 4] - Publishing Setup - 2026-01-23

**Added:**
- Package metadata configuration
- Semantic versioning support
- npm/PyPI publishing preparation
- Release documentation

### [Sprint 3] - Documentation - 2026-01-22

**Added:**
- Comprehensive Getting Started guide (`GETTING_STARTED.md`)
- Complete API reference (`API_REFERENCE.md`)
- Code examples (`EXAMPLES.md`)
- Troubleshooting guide
- Updated README with Phase 2 features

### [Sprint 1] - Core Quality - 2026-01-18

**Added:**
- Error handling tests (24 new tests)
- Input validation for all public methods (17 validation tests)
- Security documentation (`SECURITY.md`)
- TypeScript export verification
- Python export completeness
- Test coverage documentation (`TESTING.md`)

**Tests:** 58 new tests

**Security:**
- Hardcoded secret detection
- Input sanitization patterns
- Rate limiting guidance
- Token management best practices

### [Sprint 0] - Foundation - 2026-01-15

**Added:**
- Session CRUD operations (create, get, list, delete)
- Streaming responses via Server-Sent Events (SSE)
- Runtime bundle definitions
- Basic type definitions
- Initial test suite
- TypeScript and Python SDK implementations

**Tests:** 34 initial tests

**TypeScript:**
- HTTP client with SSE streaming
- Type-safe event handling
- Error handling with structured codes
- Observable connection states

**Python:**
- httpx-based async client
- Context manager support
- Type hints throughout
- Matching API with TypeScript

---

## Feature Summary by Phase

### Phase 1: Core SDK (3/3 features)
- ✅ Session CRUD operations
- ✅ Streaming responses (SSE)
- ✅ Runtime bundle definitions

### Phase 2: Advanced Features (4/4 features)
- ✅ Client-side tools
- ✅ Approval flow handling
- ✅ Session resume
- ✅ Event handler convenience API

### Phase 3: Multi-Agent Workflows (4/4 features)
- ✅ Agent spawning visibility
- ✅ Thinking stream
- ✅ Client-side behaviors
- ✅ Sub-agent configuration

### Phase 4: Enterprise Features (3/3 features)
- ✅ Recipe orchestration
- ✅ Hook configuration
- ✅ MCP server integration

---

## Test Coverage Evolution

| Sprint | TypeScript | Python | Total | Cumulative |
|--------|------------|--------|-------|------------|
| Sprint 0 | 34 | - | 34 | 34 |
| Sprint 1 | +37 | +21 | +58 | 92 |
| Sprint 2 | +29 | - | +29 | 121 |
| Sprint 3-4 | - | - | - | 121 |
| Sprint 5 | +15 | - | +15 | 136 |
| Sprint 6 | +8 | - | +8 | 144 |
| Sprint 7 | +10 | - | +10 | 154 |
| Sprint 8 | +10 | +8 | +18 | 172 |
| Sprint 9 | +31 | +28 | +59 | 231 |
| Sprint 10 | +20 | +22 | +42 | 273 |

**Final Coverage:** 273 tests (100% passing)

---

## Breaking Changes

**None** - This is the initial 1.0.0 release with stable API contracts.

---

## Migration Guide

**From pre-release versions:**

No breaking changes. If you were using 0.1.0, all APIs remain compatible.

**Key additions to be aware of:**
- MCP servers can now be configured in bundles and sessions
- Recipes provide multi-step workflow orchestration
- Behaviors enable reusable capability composition
- Agent spawning provides visibility into multi-agent workflows

---

## Known Limitations

1. **Recipe Execution:** Currently uses natural language prompts to the runtime. Future versions will use direct API calls for better reliability.

2. **MCP Server Management:** MCP servers are configured but actual connection/tool discovery is handled by the runtime. SDK provides configuration types only.

3. **Hook Configuration:** Hooks are configured via bundle definitions. Runtime hook validation not yet exposed to SDK.

---

## Acknowledgments

Built with contributions from the Amplifier team over 11 focused sprints, delivering a production-ready SDK for AI agent applications.

---

## Links

- **GitHub:** [amplifier-sdk](https://github.com/manojp99/amplifier-sdk)
- **Runtime:** [amplifier-app-runtime](https://github.com/manojp99/amplifier-app-runtime)
- **Documentation:** [Getting Started](sdks/GETTING_STARTED.md)
- **API Reference:** [API Reference](sdks/API_REFERENCE.md)
