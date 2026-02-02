# Security Considerations for Amplifier SDK

## Client-Side Tools Security

### Overview

Client-side tools execute code in your application's context. While this provides powerful capabilities, it requires careful security consideration.

### Security Model

**Client-side tools are YOUR code running in YOUR security context.**

```typescript
client.registerTool({
  name: "query-database",
  handler: async ({ query }) => {
    // This runs with YOUR permissions, YOUR credentials, YOUR access
    return await yourDatabase.query(query);
  }
});
```

### Risks & Mitigations

#### 1. Arbitrary Code Execution

**Risk:** Tool handlers execute arbitrary code in your app.

**Mitigation:**
```typescript
// ❌ BAD: Don't eval user input
client.registerTool({
  name: "calculate",
  handler: ({ expression }) => eval(expression)  // DANGEROUS!
});

// ✅ GOOD: Use safe parsing libraries
import { evaluate } from "mathjs";

client.registerTool({
  name: "calculate",
  handler: ({ expression }) => {
    return evaluate(expression, { 
      // Restricted scope, no access to globals
    });
  }
});
```

#### 2. Data Injection / XSS

**Risk:** Tool results from untrusted sources could contain malicious data.

**Mitigation:**
```typescript
import DOMPurify from "dompurify";

client.registerTool({
  name: "fetch-content",
  handler: async ({ url }) => {
    const response = await fetch(url);
    const html = await response.text();
    
    // ✅ Sanitize before returning
    return DOMPurify.sanitize(html);
  }
});
```

#### 3. Credential Exposure

**Risk:** Tool handlers have access to your app's credentials and secrets.

**Mitigation:**
```typescript
// ✅ GOOD: Explicit credential handling
client.registerTool({
  name: "send-email",
  handler: async ({ to, subject, body }) => {
    // Use environment variables, not hardcoded keys
    return await emailAPI.send({
      apiKey: process.env.EMAIL_API_KEY,
      to,
      subject,
      body
    });
  }
});

// ❌ BAD: Don't pass credentials through tool arguments
// AI could log them, expose them, or leak them
```

#### 4. Authorization Bypass

**Risk:** AI could call tools without proper user authorization.

**Mitigation:**
```typescript
// ✅ GOOD: Check user permissions in handler
client.registerTool({
  name: "delete-user",
  handler: async ({ userId }, context) => {
    // Verify current user has permission
    if (!context.user.hasRole("admin")) {
      throw new Error("Unauthorized: Admin role required");
    }
    
    return await db.users.delete(userId);
  }
});

// ✅ BETTER: Use approval flow for sensitive operations
client.onApproval(async (request) => {
  if (request.toolName === "delete-user") {
    return await showAdminConfirmationDialog(request);
  }
  return true;
});
```

#### 5. Resource Exhaustion

**Risk:** AI could call tools in loops causing resource exhaustion.

**Mitigation:**
```typescript
// ✅ GOOD: Add rate limiting
const rateLimiter = new Map<string, number>();

client.registerTool({
  name: "expensive-operation",
  handler: async (args) => {
    const lastCall = rateLimiter.get("expensive-operation") || 0;
    const now = Date.now();
    
    if (now - lastCall < 1000) {  // Max once per second
      throw new Error("Rate limit exceeded");
    }
    
    rateLimiter.set("expensive-operation", now);
    return await expensiveOperation(args);
  }
});
```

### Best Practices

#### Principle of Least Privilege

```typescript
// ✅ GOOD: Tools have minimal necessary access
client.registerTool({
  name: "read-order",
  handler: async ({ orderId }) => {
    // Returns only public order info, not payment details
    return await db.orders.findById(orderId, { 
      select: ["id", "status", "items", "total"] 
    });
  }
});

// ❌ BAD: Tool has excessive access
client.registerTool({
  name: "query-database",
  handler: async ({ query }) => {
    // AI can read ANYTHING in the database!
    return await db.raw(query);
  }
});
```

#### Input Sanitization

```typescript
client.registerTool({
  name: "search-users",
  handler: async ({ searchTerm }) => {
    // ✅ Sanitize inputs
    const sanitized = searchTerm.replace(/[^a-zA-Z0-9\s]/g, "");
    
    // ✅ Use parameterized queries
    return await db.users.where("name", "like", `%${sanitized}%`).limit(10);
  }
});
```

#### Timeout Protection

```typescript
client.registerTool({
  name: "long-running-task",
  handler: async (args) => {
    // ✅ Add timeout
    return await Promise.race([
      actualTask(args),
      new Promise((_, reject) => 
        setTimeout(() => reject(new Error("Timeout")), 30000)
      )
    ]);
  }
});
```

#### Error Information Leakage

```typescript
client.registerTool({
  name: "query-api",
  handler: async (args) => {
    try {
      return await externalAPI.call(args);
    } catch (err) {
      // ❌ BAD: Exposes internal details
      // throw err;
      
      // ✅ GOOD: Generic error message
      throw new Error("API request failed");
    }
  }
});
```

### Approval Flow Security

The approval system adds a security layer for sensitive operations:

```typescript
// Configure which tools require approval
const SENSITIVE_TOOLS = new Set(["delete-user", "process-payment", "send-email"]);

client.onApproval(async (request) => {
  // Always require explicit user confirmation for sensitive tools
  if (SENSITIVE_TOOLS.has(request.toolName)) {
    return await showUserConfirmDialog({
      title: "⚠️ Sensitive Operation",
      message: request.prompt,
      tool: request.toolName,
      args: request.arguments
    });
  }
  
  // Auto-approve safe tools
  return true;
});
```

### Content Security Policy (CSP)

If running in a browser, configure CSP headers:

```html
<meta http-equiv="Content-Security-Policy" 
      content="default-src 'self'; 
               script-src 'self'; 
               connect-src 'self' http://localhost:4096;">
```

### Audit Logging

Log all tool executions for security auditing:

```typescript
client.on("tool.call", (event) => {
  auditLog.record({
    timestamp: new Date(),
    tool: event.data.tool_name,
    arguments: event.data.arguments,
    userId: currentUser.id,
    sessionId: currentSessionId,
  });
});
```

---

## Reporting Vulnerabilities

If you discover a security vulnerability in the Amplifier SDK, please report it to:

**Email:** security@amplifier.dev (or your designated security contact)

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will respond within 48 hours and work with you on a fix.

---

## Security Checklist for SDK Users

Before deploying apps using client-side tools:

- [ ] All tool handlers sanitize inputs
- [ ] Sensitive tools require approval
- [ ] No eval() or Function() on untrusted input
- [ ] Tool results are sanitized before display
- [ ] Rate limiting on expensive tools
- [ ] Timeouts on long-running tools
- [ ] Audit logging for sensitive operations
- [ ] Error messages don't leak internal details
- [ ] Credentials stored securely (env vars, not code)
- [ ] Authorization checks in tool handlers

---

## Updates

This security guide will be updated as new features are added to the SDK.

Last updated: 2026-02-02
