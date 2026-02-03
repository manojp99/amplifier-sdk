"""Tests for hooks and MCP server configuration."""

from amplifier_sdk import (
    BundleDefinition,
    McpServerHttp,
    McpServerSse,
    McpServerStdio,
    ModuleConfig,
)


class TestHookConfiguration:
    """Test cases for hook configuration in bundles."""

    def test_bundle_with_hooks(self):
        """Test that bundle accepts hooks configuration."""
        bundle = BundleDefinition(
            name="test-bundle",
            version="1.0.0",
            hooks=[
                ModuleConfig(module="hook-logging"),
                ModuleConfig(module="hook-redaction", config={"patterns": ["secret"]}),
            ],
        )

        assert bundle.hooks is not None
        assert len(bundle.hooks) == 2
        assert bundle.hooks[0].module == "hook-logging"
        assert bundle.hooks[1].config == {"patterns": ["secret"]}

    def test_empty_hooks_array(self):
        """Test that empty hooks array is supported."""
        bundle = BundleDefinition(name="no-hooks", version="1.0.0", hooks=[])

        assert bundle.hooks == []

    def test_hooks_with_custom_config(self):
        """Test hooks with custom configuration."""
        bundle = BundleDefinition(
            name="configured-hooks",
            version="1.0.0",
            hooks=[
                ModuleConfig(module="hook-approval", config={"auto_approve": False, "timeout": 300})
            ],
        )

        assert bundle.hooks[0].config == {"auto_approve": False, "timeout": 300}

    def test_hooks_with_source_urls(self):
        """Test hooks with custom source URLs."""
        bundle = BundleDefinition(
            name="custom-hooks",
            version="1.0.0",
            hooks=[
                ModuleConfig(
                    module="hook-custom",
                    source="git+https://github.com/org/amplifier-hook-custom.git",
                )
            ],
        )

        assert bundle.hooks[0].source == "git+https://github.com/org/amplifier-hook-custom.git"

    def test_multiple_hooks_mixed_config(self):
        """Test multiple hooks with mixed configuration."""
        bundle = BundleDefinition(
            name="multi-hooks",
            version="1.0.0",
            hooks=[
                ModuleConfig(module="hook-logging"),
                ModuleConfig(module="hook-redaction", config={"enabled": True}),
                ModuleConfig(module="hook-custom", source="git+https://example.com/hook.git"),
            ],
        )

        assert len(bundle.hooks) == 3
        assert bundle.hooks[0].config == {} or bundle.hooks[0].config is None
        assert bundle.hooks[1].config == {"enabled": True}
        assert bundle.hooks[2].source is not None

    def test_hooks_serialization(self):
        """Test that hooks serialize correctly to dict."""
        bundle = BundleDefinition(
            name="serialize-test",
            version="1.0.0",
            hooks=[ModuleConfig(module="hook-test", config={"key": "value"})],
        )

        bundle_dict = bundle.to_dict()
        assert "hooks" in bundle_dict
        assert len(bundle_dict["hooks"]) == 1
        assert bundle_dict["hooks"][0]["module"] == "hook-test"


class TestMcpServerConfiguration:
    """Test cases for MCP server configuration."""

    def test_stdio_mcp_server(self):
        """Test stdio MCP server configuration."""
        server = McpServerStdio(
            type="stdio",
            command="/usr/local/bin/mcp-server",
            args=["--config", "/path/config.json"],
        )

        assert server.type == "stdio"
        assert server.command == "/usr/local/bin/mcp-server"
        assert server.args == ["--config", "/path/config.json"]

    def test_stdio_with_environment(self):
        """Test stdio server with environment variables."""
        server = McpServerStdio(
            type="stdio", command="mcp-server", env={"API_KEY": "test-key", "DEBUG": "true"}
        )

        assert server.env == {"API_KEY": "test-key", "DEBUG": "true"}

    def test_stdio_minimal_config(self):
        """Test stdio server with minimal configuration."""
        server = McpServerStdio(type="stdio", command="simple-mcp")

        assert server.command == "simple-mcp"
        assert server.args == []
        assert server.env == {}

    def test_http_mcp_server(self):
        """Test HTTP MCP server configuration."""
        server = McpServerHttp(type="http", url="http://localhost:8080/mcp")

        assert server.type == "http"
        assert server.url == "http://localhost:8080/mcp"

    def test_http_with_auth_headers(self):
        """Test HTTP server with authentication headers."""
        server = McpServerHttp(
            type="http",
            url="https://api.example.com/mcp",
            headers={"Authorization": "Bearer token123", "X-API-Key": "key456"},
        )

        assert server.headers == {"Authorization": "Bearer token123", "X-API-Key": "key456"}

    def test_sse_mcp_server(self):
        """Test SSE MCP server configuration."""
        server = McpServerSse(type="sse", url="http://localhost:8080/mcp/events")

        assert server.type == "sse"
        assert server.url == "http://localhost:8080/mcp/events"

    def test_sse_with_auth_headers(self):
        """Test SSE server with authentication headers."""
        server = McpServerSse(
            type="sse",
            url="https://api.example.com/mcp/stream",
            headers={"Authorization": "Bearer token789"},
        )

        assert server.headers["Authorization"] == "Bearer token789"

    def test_mcp_server_serialization(self):
        """Test MCP server serialization to dict."""
        server = McpServerStdio(
            type="stdio", command="test-server", args=["--verbose"], env={"KEY": "value"}
        )

        server_dict = server.to_dict()
        assert server_dict["type"] == "stdio"
        assert server_dict["command"] == "test-server"
        assert server_dict["args"] == ["--verbose"]
        assert server_dict["env"] == {"KEY": "value"}


class TestBundleWithMcpServers:
    """Test cases for bundles with MCP server configuration."""

    def test_bundle_with_mcp_servers(self):
        """Test bundle definition with MCP servers."""
        bundle = BundleDefinition(
            name="mcp-bundle",
            version="1.0.0",
            mcp_servers=[
                McpServerStdio(type="stdio", command="mcp-server"),
                McpServerHttp(type="http", url="http://localhost:8080/mcp"),
            ],
        )

        assert bundle.mcp_servers is not None
        assert len(bundle.mcp_servers) == 2
        assert bundle.mcp_servers[0].type == "stdio"
        assert bundle.mcp_servers[1].type == "http"

    def test_mixed_mcp_server_types(self):
        """Test bundle with mixed MCP server types."""
        bundle = BundleDefinition(
            name="multi-mcp",
            version="1.0.0",
            mcp_servers=[
                McpServerStdio(type="stdio", command="local-mcp", args=["--verbose"]),
                McpServerHttp(
                    type="http",
                    url="http://api.example.com/mcp",
                    headers={"X-API-Key": "key"},
                ),
                McpServerSse(type="sse", url="http://events.example.com/mcp"),
            ],
        )

        assert len(bundle.mcp_servers) == 3
        assert bundle.mcp_servers[0].type == "stdio"
        assert bundle.mcp_servers[1].type == "http"
        assert bundle.mcp_servers[2].type == "sse"

    def test_empty_mcp_servers(self):
        """Test bundle with empty MCP servers array."""
        bundle = BundleDefinition(name="no-mcp", version="1.0.0", mcp_servers=[])

        assert bundle.mcp_servers == []

    def test_mcp_servers_serialization(self):
        """Test that MCP servers serialize correctly in bundle.to_dict()."""
        bundle = BundleDefinition(
            name="serialize-mcp",
            version="1.0.0",
            mcp_servers=[
                McpServerStdio(type="stdio", command="test-mcp"),
                McpServerHttp(type="http", url="http://localhost:8080"),
            ],
        )

        bundle_dict = bundle.to_dict()
        assert "mcpServers" in bundle_dict
        assert len(bundle_dict["mcpServers"]) == 2
        assert bundle_dict["mcpServers"][0]["type"] == "stdio"
        assert bundle_dict["mcpServers"][1]["type"] == "http"


class TestSessionConfigMcp:
    """Test cases for session configuration with MCP servers."""

    def test_session_with_mcp_servers(self):
        """Test session config with MCP servers."""
        from amplifier_sdk.types import SessionConfig

        config = SessionConfig(
            bundle="foundation",
            mcp_servers=[McpServerStdio(type="stdio", command="mcp-tools")],
        )

        assert config.mcp_servers is not None
        assert len(config.mcp_servers) == 1

    def test_session_mcp_serialization(self):
        """Test that MCP servers serialize in SessionConfig.to_dict()."""
        from amplifier_sdk.types import SessionConfig

        config = SessionConfig(
            bundle="foundation",
            mcp_servers=[
                McpServerStdio(type="stdio", command="test-mcp"),
                McpServerHttp(type="http", url="http://localhost:8080"),
            ],
        )

        config_dict = config.to_dict()
        assert "mcpServers" in config_dict
        assert len(config_dict["mcpServers"]) == 2


class TestCompleteIntegration:
    """Test cases for complete hook and MCP integration."""

    def test_enterprise_bundle_with_all_features(self):
        """Test enterprise bundle with hooks, MCP, tools, and providers."""
        bundle = BundleDefinition(
            name="enterprise-agent",
            version="1.0.0",
            description="Enterprise agent with hooks and MCP",
            providers=[ModuleConfig(module="provider-anthropic")],
            tools=[ModuleConfig(module="tool-filesystem")],
            hooks=[
                ModuleConfig(module="hook-logging"),
                ModuleConfig(module="hook-approval", config={"auto_approve": False}),
            ],
            mcp_servers=[
                McpServerStdio(
                    type="stdio",
                    command="/opt/mcp/database-mcp",
                    args=["--db", "postgresql://localhost/mydb"],
                    env={"DB_PASSWORD": "secret"},
                ),
                McpServerHttp(
                    type="http",
                    url="https://api.company.com/mcp",
                    headers={"Authorization": "Bearer company-token"},
                ),
            ],
            instructions="You are an enterprise assistant with database access.",
        )

        # Verify complete structure
        assert bundle.name == "enterprise-agent"
        assert len(bundle.hooks) == 2
        assert len(bundle.mcp_servers) == 2
        assert len(bundle.providers) == 1
        assert len(bundle.tools) == 1
        assert bundle.instructions is not None

    def test_serialization_roundtrip(self):
        """Test that bundle with hooks and MCP serializes correctly."""
        bundle = BundleDefinition(
            name="roundtrip-test",
            version="1.0.0",
            hooks=[ModuleConfig(module="hook-test")],
            mcp_servers=[McpServerStdio(type="stdio", command="mcp-test")],
        )

        bundle_dict = bundle.to_dict()

        # Verify serialization
        assert "hooks" in bundle_dict
        assert "mcpServers" in bundle_dict
        assert bundle_dict["hooks"][0]["module"] == "hook-test"
        assert bundle_dict["mcpServers"][0]["type"] == "stdio"
        assert bundle_dict["mcpServers"][0]["command"] == "mcp-test"
